"""Recover samples for existing collections after fallback catalogs and upgrades."""
import ast
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

from test_previews import catalog_types
import test_library

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = 'https://cdn.tonies.de/o/audio_samples/a/one.mp3'


class TestPreviewRecovery(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ns = catalog_types()
        self.now = datetime.now(timezone.utc)
        self.ns['dt_util'] = SimpleNamespace(utcnow=lambda: self.now)
        self.catalog = self.ns['OnlineCatalog'](None)

    async def test_legacy_fallback_retries_in_seconds_and_keeps_existing_samples(self):
        self.ns['CATALOG_SOURCES'] = [('v2', 'v2'), ('v1', 'v1')]
        requests = []
        recovered = False
        async def download(session, url):
            requests.append(url)
            if url == 'v2':
                if not recovered: raise ValueError('temporary failure')
                return [{'data':[{'episode':'One', 'sample':SAMPLE, 'ids':[{'audio-id':123}]}]}]
            return [{'title':'One', 'audio_id':[123]}]
        self.catalog._download_json = download
        test_library.FakeStore.saved = {}
        lib = test_library.library_module.TonieLibrary(SimpleNamespace())
        await lib.async_seen('box', '123')
        await lib.async_metadata('123', preview_url=SAMPLE)
        await self.catalog.refresh()
        self.assertEqual(self.catalog.loaded_format, 'v1')
        await lib.async_refresh_catalog(self.catalog)
        self.assertEqual(lib.public_entries()[0]['preview_url'], SAMPLE)
        self.assertEqual(requests, ['v2', 'v1'])
        recovered = True
        self.now += timedelta(seconds=22)
        # A new automatic lookup retries the sample-capable catalog, without waiting 24h.
        self.assertEqual((await self.catalog.find('123'))['preview_url'], SAMPLE)
        self.assertEqual(self.catalog.loaded_format, 'v2')
        await lib.async_refresh_catalog(self.catalog)
        self.assertEqual(lib.public_entries()[0]['preview_url'], SAMPLE)
        self.assertEqual(lib.public_entries()[0]['times_seen'], 1)
        self.assertEqual(requests, ['v2', 'v1', 'v2'])

    async def test_manual_refresh_bypasses_daily_cache_but_is_rate_limited(self):
        calls = []
        async def download(session, url):
            calls.append(url)
            return [{'data':[{'episode':'One', 'sample':SAMPLE, 'ids':[{'audio-id':123}]}]}]
        self.catalog._download_json = download
        await self.catalog.refresh()
        await self.catalog.refresh(force=True)
        self.assertEqual(len(calls), 1)
        self.now += timedelta(seconds=22)
        await self.catalog.refresh()
        self.assertEqual(len(calls), 1)
        await self.catalog.refresh(force=True)
        self.assertEqual(len(calls), 2)

    async def test_real_regional_duplicate_does_not_erase_sample_in_either_order(self):
        records = json.loads((ROOT / 'tests/fixtures/preview_catalog_duplicates.json').read_text())
        self.assertEqual(len(records), 2)
        for items in [records, records[::-1]]:
            catalog = self.ns['OnlineCatalog'](None)
            async def download(session, url): return items
            catalog._download_json = download
            await catalog.refresh()
            item = await catalog.find('1538986377')
            self.assertTrue(item['preview_url'])
            self.assertIn('grufallo', item['preview_url'])

    async def test_conflicting_story_or_language_never_inherits_sample(self):
        for episode, language in [('Other', 'en-gb'), ('One', 'de-de')]:
            catalog = self.ns['OnlineCatalog'](None)
            async def download(session, url):
                return [{'data':[
                    {'episode':'One','language':'en-gb','sample':SAMPLE,'ids':[{'audio-id':123}]},
                    {'episode':episode,'language':language,'ids':[{'audio-id':123}]}
                ]}]
            catalog._download_json = download
            await catalog.refresh()
            self.assertIsNone((await catalog.find('123'))['preview_url'])

    async def test_refresh_command_for_both_roles_and_visible_catalog_status(self):
        source = ROOT / 'custom_components/teddycloud_homeassistant/library_websocket.py'
        nodes = [n for n in ast.parse(source.read_text()).body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name in ('library_payload', 'ws_library_refresh')]
        for node in nodes:
            node.decorator_list = []
        catalog = SimpleNamespace(refresh=AsyncMock(), fetched_at=self.now, failed_at=None, loaded_format='v2')
        lib = SimpleNamespace(public_entries=lambda:[{'audio_id':'123', 'preview_url':SAMPLE}], async_refresh_catalog=AsyncMock())
        namespace = {'DOMAIN':'teddycloud_homeassistant', 'get_library':lambda hass:lib}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
        hass = SimpleNamespace(data={'teddycloud_homeassistant':{'online_catalog':catalog}})
        for admin in (False, True):
            connection = SimpleNamespace(user=SimpleNamespace(is_admin=admin), send_result=Mock(), send_error=Mock())
            await namespace['ws_library_refresh'](hass, connection, {'id':1})
            catalog.refresh.assert_awaited_with(force=True)
            lib.async_refresh_catalog.assert_awaited_with(catalog)
            result = connection.send_result.call_args.args[1]
            self.assertEqual(result['preview_catalog_status'], 'ready')
            self.assertEqual(result['entries'][0]['preview_url'], SAMPLE)
            connection.send_error.assert_not_called()
        catalog.loaded_format = 'v1'
        self.assertEqual(namespace['library_payload'](hass, lib)['preview_catalog_status'], 'unavailable')
        catalog.loaded_format, catalog.fetched_at = None, None
        self.assertEqual(namespace['library_payload'](hass, lib)['preview_catalog_status'], 'loading')
        catalog.failed_at = self.now
        self.assertEqual(namespace['library_payload'](hass, lib)['preview_catalog_status'], 'unavailable')

    async def test_unmatched_existing_collection_still_broadcasts_refresh_status(self):
        test_library.events.clear()
        lib = test_library.library_module.TonieLibrary(SimpleNamespace())
        await lib.async_seen('box', 'unknown')
        test_library.events.clear()
        await lib.async_refresh_catalog(SimpleNamespace(find=AsyncMock(return_value=None)))
        self.assertEqual(test_library.events[-1][-1], None)
        self.assertEqual(lib.public_entries()[0]['times_seen'], 1)
