"""Exact catalog sample assignment; metadata only, no sample download."""
import ast
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import re
from types import SimpleNamespace
import unittest

import test_library
import test_availability

ROOT = Path(__file__).resolve().parents[1]


def catalog_types():
    path = ROOT / 'custom_components/teddycloud_homeassistant/online_catalog.py'
    nodes = [n for n in ast.parse(path.read_text()).body
             if isinstance(n, (ast.ClassDef, ast.FunctionDef))]
    namespace = {
        'asyncio': asyncio, 're': re, 'json': json,
        'dt_util': SimpleNamespace(utcnow=lambda: datetime.now(timezone.utc)),
        'REFRESH': timedelta(hours=24), 'RETRY': timedelta(seconds=20),
        'CATALOG_SOURCES': [('v2', 'https://catalog.test/toniesV2.json')],
        'async_get_clientsession': lambda hass: None,
        '_LOGGER': logging.getLogger(__name__),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


class TestPreviews(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        test_library.FakeStore.saved = {}
        self.ns = catalog_types()
        self.catalog = self.ns['OnlineCatalog'](None)
        self.fixture = json.loads((ROOT / 'tests/fixtures/preview_catalog.json').read_text())
        self.requests = []

        async def download(session, url):
            self.requests.append(url)
            return self.fixture

        self.catalog._download_json = download
        self.lib = test_library.library_module.TonieLibrary(SimpleNamespace())
        await self.lib.async_load()

    async def test_ten_real_catalog_records_and_existing_collection(self):
        """Frozen metadata fetched 2026-10-29; no external calls during tests."""
        self.assertEqual(len(self.fixture), 10)
        for article in self.fixture:
            entry = article['data'][0]
            await self.lib.async_seen('box', str(entry['ids'][0]['audio-id']))
        await self.lib.async_refresh_catalog(self.catalog)
        entries = {e['audio_id']: e for e in self.lib.public_entries()}
        self.assertEqual(len(entries), 10)
        for article in self.fixture:
            entry = article['data'][0]
            for ident in entry['ids']:
                match = await self.catalog.find(str(ident['audio-id']))
                self.assertEqual(match['preview_url'], entry.get('sample'))
            stored = entries[str(entry['ids'][0]['audio-id'])]
            self.assertEqual(stored['preview_url'], entry.get('sample'))
            self.assertEqual(stored['times_seen'], 1)
        self.assertEqual(sum(bool(e['preview_url']) for e in entries.values()), 9)
        self.assertEqual(self.requests, ['https://catalog.test/toniesV2.json'])
        self.assertIsNone(await self.catalog.find('unrecognized-id'))
        # Only the URL is persisted; there is no audio body or upload.
        saved = test_library.FakeStore.saved[test_library.library_module.STORE_KEY]
        self.assertEqual(sum(bool(e.get('preview_url')) for e in saved['entries'].values()), 9)
        reloaded = test_library.library_module.TonieLibrary(SimpleNamespace())
        await reloaded.async_load()
        self.assertEqual(reloaded.public_entries(), self.lib.public_entries())

    async def test_new_figure_receives_preview_before_slow_artwork(self):
        player, _, _ = test_availability.TestAvailability().make_player()
        tasks = []
        def create(coro):
            task = asyncio.create_task(coro)
            tasks.append(task)
            return task
        player.hass = SimpleNamespace(async_create_task=create)
        player._library = self.lib
        player._online_catalog = self.catalog
        # Use the real fresh MQTT observation and player lookup path.
        entry = self.fixture[0]['data'][0]
        audio_id = str(entry['ids'][0]['audio-id'])
        player.receive('ContentAudioId', audio_id)
        await asyncio.gather(*tasks)
        item = self.lib.public_entries()[0]
        self.assertEqual(item['preview_url'], entry.get('sample'))
        self.assertEqual(item['times_seen'], 1)

    async def test_catalog_can_remove_sample_without_altering_user_data(self):
        await self.lib.async_seen('box', '123')
        await self.lib.async_metadata('123', title='Original', preview_url='https://cdn.tonies.de/o/audio_samples/a/one.mp3')
        await self.lib.async_edit('123', title='My title', duration_seconds=1200)
        await self.lib.async_metadata('123', title='Original', preview_url=None)
        item = self.lib.public_entries()[0]
        self.assertIsNone(item['preview_url'])
        self.assertEqual(item['title'], 'My title')
        self.assertEqual(item['duration_seconds'], 1200)
        self.assertEqual(item['times_seen'], 1)
        await self.lib.async_delete('123')
        await self.lib.async_metadata('123', preview_url='https://cdn.tonies.de/o/audio_samples/a/one.mp3')
        self.assertEqual(self.lib.public_entries(), [])

    async def test_grouped_alias_uses_sample_without_merging_titles(self):
        await self.lib.async_seen('box', '111')
        await self.lib.async_seen('box', '222')
        await self.lib.async_seen('box', '333')
        sample = 'https://cdn.tonies.de/o/audio_samples/a/one.wav'
        await self.lib.async_metadata('222', title='Same', audio_ids=['111', '222'], preview_url=sample)
        await self.lib.async_metadata('333', title='Same')
        entries = self.lib.public_entries()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]['preview_url'], sample)
        self.assertIsNone(entries[1]['preview_url'])

    async def test_only_https_catalog_sample_host_and_no_legacy_guess(self):
        validate = self.ns['preview_url']
        for url in ['http://cdn.tonies.de/o/audio_samples/a/a.mp3',
                    'https://cdn.tonies.de.evil.test/o/audio_samples/a.mp3',
                    'https://example.test/a.mp3', 'javascript:alert(1)',
                    'https://cdn.tonies.de/o/audio_samples/../a.mp3',
                    'https://cdn.tonies.de/o/audio_samples/a.mp3" onerror="x', None]:
            self.assertIsNone(validate(url))
        for extension in ['mp3', 'wav', 'm4a', 'ogg']:
            url = 'https://cdn.tonies.de/o/audio_samples/a/sample.' + extension
            self.assertEqual(validate(url), url)
        self.ns['CATALOG_SOURCES'] = [('v1', 'legacy')]
        async def legacy(session, url):
            return [{'title':'Legacy', 'audio_id':[123], 'sample':'https://example.test/a.mp3'}]
        self.catalog._download_json = legacy
        await self.catalog.refresh()
        self.assertIsNone((await self.catalog.find('123'))['preview_url'])

    async def test_shared_refresh_retries_catalog_only_and_cancels(self):
        path = ROOT / 'custom_components/teddycloud_homeassistant/__init__.py'
        node = next(n for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.AsyncFunctionDef) and n.name == '_refresh_library_catalog')
        delays, calls = [], []
        catalog = SimpleNamespace(failed_at=True)
        async def refresh(): calls.append('catalog')
        async def fill(value):
            self.assertIs(value, catalog)
            calls.append('collection')
        async def sleep(delay):
            delays.append(delay)
            if len(delays) == 2: raise asyncio.CancelledError()
            catalog.failed_at = None
        catalog.refresh = refresh
        namespace = {'asyncio':SimpleNamespace(sleep=sleep), 'RETRY':timedelta(seconds=20), 'REFRESH':timedelta(hours=24)}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
        with self.assertRaises(asyncio.CancelledError):
            await namespace['_refresh_library_catalog'](SimpleNamespace(async_refresh_catalog=fill), catalog)
        self.assertEqual(delays, [22, 86400])
        self.assertEqual(calls, ['catalog', 'collection', 'catalog', 'collection'])

    async def test_shared_refresh_survives_other_box_and_stops_on_last_unload(self):
        path = ROOT / 'custom_components/teddycloud_homeassistant/__init__.py'
        node = next(n for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == '_stop_library_catalog_if_unused')
        namespace = {}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
        cancelled = []
        catalog = object()
        task = SimpleNamespace(cancel=lambda: cancelled.append(True))
        data = {'online_catalog':catalog, 'library_catalog_task':task,
                'remaining_box':SimpleNamespace(_online_catalog=catalog)}
        stop = namespace['_stop_library_catalog_if_unused']
        stop(data)
        self.assertEqual(cancelled, [])
        self.assertIs(data['library_catalog_task'], task)
        del data['remaining_box']
        stop(data)
        stop(data)
        self.assertEqual(cancelled, [True])
        self.assertNotIn('library_catalog_task', data)
