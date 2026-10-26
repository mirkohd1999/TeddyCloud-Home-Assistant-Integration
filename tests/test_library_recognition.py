"""Exercise actual BoxPlayer collection/catalog ordering with the real library."""
import asyncio
from types import SimpleNamespace
import unittest
import test_availability
import test_library


class TestRecognition(unittest.TestCase):
    def test_immediate_catalog_hit_waits_for_collection(self):
        async def run():
            player, _, _ = test_availability.TestAvailability().make_player()
            tasks = []
            def create(coro):
                task = asyncio.create_task(coro)
                tasks.append(task)
                return task
            player.hass = SimpleNamespace(async_create_task=create)
            lib = test_library.library_module.TonieLibrary(player.hass)
            player._library = lib
            async def find(audio_id):
                return {'catalog_title': 'Yakari', 'duration_seconds': 2340,
                        'figure': 'https://example.test/yakari.png', 'audio_ids': [audio_id]}
            player._online_catalog = SimpleNamespace(find=find, failed_at=None)
            await lib._lock.acquire()
            player.receive('ContentAudioId', '123')
            await asyncio.sleep(0)
            # Lookup must wait for the queued observation even with a cached hit.
            self.assertIsNone(player._online_result)
            lib._lock.release()
            await asyncio.gather(*tasks)
            item = lib.public_entries()[0]
            self.assertEqual(item['title'], 'Yakari')
            self.assertEqual(item['duration_seconds'], 2340)
            self.assertEqual(item['times_seen'], 1)
            self.assertEqual(player.media_title, 'Yakari')
        asyncio.run(run())

    def test_title_is_published_before_slow_artwork(self):
        async def run():
            player, _, _ = test_availability.TestAvailability().make_player()
            lib = test_library.library_module.TonieLibrary(player.hass)
            player._library = lib
            await lib.async_seen('box', '123')
            player._values['ContentAudioId'] = '123'
            player._online_audio_id = '123'
            downloading = asyncio.Event()
            finish = asyncio.Event()
            async def find(audio_id):
                return {'catalog_title':'Bibi Blocksberg', 'figure':'https://example.test/image.png'}
            async def store(audio_id, url):
                downloading.set()
                await finish.wait()
                return '/local/teddycloud/123.png'
            player._online_catalog = SimpleNamespace(find=find, failed_at=None)
            player._archive = SimpleNamespace(lookup=lambda _:None, store=store)
            task = asyncio.create_task(player._lookup_image('123'))
            await downloading.wait()
            self.assertEqual(lib.public_entries()[0]['title'], 'Bibi Blocksberg')
            self.assertEqual(player.media_title, 'Bibi Blocksberg')
            finish.set()
            await task
            self.assertEqual(lib.public_entries()[0]['image'], '/local/teddycloud/123.png')
        asyncio.run(run())

    def test_cancelled_lookup_does_not_cancel_observation(self):
        async def run():
            player, _, _ = test_availability.TestAvailability().make_player()
            lib = test_library.library_module.TonieLibrary(player.hass)
            await lib._lock.acquire()
            observation = asyncio.create_task(lib.async_seen('box', '123'))
            lookup = asyncio.create_task(player._lookup_image('123', observation))
            await asyncio.sleep(0)
            lookup.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await lookup
            self.assertFalse(observation.cancelled())
            lib._lock.release()
            await observation
            self.assertEqual(len(lib.public_entries()), 1)
        asyncio.run(run())
