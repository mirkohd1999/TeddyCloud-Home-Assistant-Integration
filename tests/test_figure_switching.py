"""MQTT ordering regressions using the real player and real library."""
import asyncio
from types import SimpleNamespace
import unittest
import test_availability
import test_library


class TestFigureSwitching(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.player, self.now, self.timers = test_availability.TestAvailability().make_player()
        self.tasks = []
        def create(coro):
            task = asyncio.create_task(coro)
            self.tasks.append(task)
            return task
        async def find(aid):
            return self.catalog.get(aid)
        self.catalog = {}
        self.player.hass = SimpleNamespace(async_create_task=create)
        self.player._online_catalog = SimpleNamespace(find=find, failed_at=None)
        self.lib = test_library.library_module.TonieLibrary(self.player.hass)
        self.player._library = self.lib

    async def settle(self):
        while self.tasks:
            tasks, self.tasks = self.tasks, []
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException) and not isinstance(result, asyncio.CancelledError):
                    raise result

    async def send(self, *events, flush=True):
        for field, value in events:
            self.player.receive(field, value)
            await self.settle()
        if flush:
            self.now[0] += 1
            self.player._flush_metadata(None)
            await self.settle()

    async def rocky(self):
        await self.send(('ContentAudioId', '111'), ('ContentTitle', 'Rocky'),
                        ('ContentPicture', 'https://example.test/rocky.png'))
        self.assertEqual(self.lib.detected_metadata('111')['title'], 'Rocky')

    def titles(self):
        return {e['audio_id']: e['title'] for e in self.lib.public_entries()}

    async def test_a_b_a_id_then_title(self):
        await self.rocky()
        await self.send(('ContentAudioId', ''), ('ContentAudioId', '222'), ('ContentTitle', 'Bibi'))
        await self.send(('ContentAudioId', ''), ('ContentAudioId', '111'), ('ContentTitle', 'Rocky'))
        self.assertEqual(self.titles(), {'111':'Rocky', '222':'Bibi'})
        self.assertEqual({e['audio_id']:e['times_seen'] for e in self.lib.public_entries()}, {'111':2,'222':1})

    async def test_a_b_a_title_before_id_after_removal(self):
        await self.rocky()
        await self.send(('TagValid', '-1'), ('ContentTitle', 'Bibi'), ('ContentAudioId', '222'))
        await self.send(('TagValid', '-1'), ('ContentTitle', 'Rocky'), ('ContentAudioId', '111'))
        self.assertEqual(self.titles(), {'111':'Rocky', '222':'Bibi'})

    async def test_direct_switch_title_before_id(self):
        await self.rocky()
        await self.send(('ContentTitle', 'Bibi'), ('ContentAudioId', '222'))
        await self.send(('ContentTitle', 'Rocky'), ('ContentAudioId', '111'))
        self.assertEqual(self.titles(), {'111':'Rocky', '222':'Bibi'})

    async def test_missing_new_title_does_not_copy_old_figure(self):
        await self.rocky()
        await self.send(('TagValid', '-1'), ('ContentAudioId', '222'))
        self.assertEqual(self.titles(), {'111':'Rocky','222':'Tonie 222'})
        self.assertFalse(self.lib.detected_metadata('222')['image'])
        self.assertEqual(self.player.media_title, 'Unbekannter Tonie')

    async def test_late_old_title_and_picture_do_not_create_duplicate(self):
        await self.rocky()
        await self.send(('TagValid', '-1'), ('ContentAudioId', '222'),
                        ('ContentTitle','Rocky'), ('ContentPicture','https://example.test/rocky.png'))
        self.assertEqual(self.titles()['222'], 'Tonie 222')
        await self.send(('ContentTitle','Bibi'), ('ContentPicture','https://example.test/bibi.png'))
        self.assertEqual(self.titles()['222'], 'Bibi')
        self.assertEqual(self.lib.detected_metadata('222')['image'], 'https://example.test/bibi.png')

    async def test_delayed_metadata_cannot_rename_known_entry(self):
        await self.rocky()
        await self.send(('ContentTitle','Bibi'))  # ID has not arrived yet.
        self.assertEqual(self.titles()['111'], 'Rocky')
        await self.send(('ContentAudioId','222'))
        self.assertEqual(self.titles(), {'111':'Rocky','222':'Bibi'})

    async def test_catalog_and_custom_title_win_over_late_mqtt(self):
        self.catalog['222']={'catalog_title':'Bibi','figure':'https://example.test/bibi.png','audio_ids':['222']}
        await self.rocky()
        await self.send(('ContentAudioId','222'), ('ContentTitle','Rocky'))
        self.assertEqual(self.titles()['222'], 'Bibi')
        self.assertEqual(self.player.media_title, 'Bibi')
        await self.lib.async_edit('222',title='Mein Bibi-Hörspiel')
        await self.send(('ContentTitle','Falscher Titel'))
        self.assertEqual(self.titles()['222'], 'Mein Bibi-Hörspiel')
        self.assertEqual(self.player.media_title, 'Mein Bibi-Hörspiel')

    async def test_retained_metadata_never_relabels_active_figure(self):
        await self.rocky()
        self.player.receive('ContentTitle','Bibi',retained=True)
        self.player._flush_metadata(None)
        await self.settle()
        self.assertEqual(self.titles()['111'], 'Rocky')

    async def test_rapid_remove_replace_same_id_is_counted_once_per_placement(self):
        # All callbacks run before the queued storage tasks get CPU time.
        for field,value in [('ContentAudioId','111'),('TagValid','-1'),('ContentAudioId','111')]:
            self.player.receive(field,value)
        await self.settle()
        self.assertEqual(len(self.lib.public_entries()),1)
        self.assertEqual(self.lib.public_entries()[0]['times_seen'],2)

    async def test_switch_during_pending_metadata_write_discards_old_batch(self):
        await self.rocky()
        await self.send(('ContentAudioId','222'),('ContentTitle','Bibi'),flush=False)
        await self.lib._lock.acquire()
        self.player._flush_metadata(None)
        await asyncio.sleep(0)
        self.player.receive('TagValid','-1')
        self.player.receive('ContentAudioId','333')
        self.lib._lock.release()
        await self.settle()
        self.assertEqual(self.titles()['222'],'Tonie 222')
        self.assertEqual(self.titles()['333'],'Tonie 333')

    async def test_unload_cancels_metadata_timer(self):
        await self.send(('ContentAudioId','111'),('ContentTitle','Rocky'),flush=False)
        timer = next(t for t in reversed(self.timers) if t['callback'].__name__=='_flush_metadata')
        await self.player.async_will_remove_from_hass()
        self.assertTrue(timer['cancelled'])

    async def test_direct_switch_id_before_title(self):
        await self.rocky()
        await self.send(('ContentAudioId','222'),('ContentTitle','Bibi'))
        await self.send(('ContentAudioId','111'),('ContentTitle','Rocky'))
        self.assertEqual(self.titles(), {'111':'Rocky','222':'Bibi'})

    async def test_catalog_returning_after_switch_cannot_change_active_player(self):
        started, finish = asyncio.Event(), asyncio.Event()
        async def find(aid):
            if aid == '111':
                started.set()
                try:
                    await finish.wait()
                except asyncio.CancelledError:
                    await finish.wait()  # Simulate a source ignoring cancellation.
                return {'catalog_title':'Rocky','audio_ids':['111']}
            return {'catalog_title':'Bibi','audio_ids':['222']}
        self.player._online_catalog.find = find
        self.player.receive('ContentAudioId','111')
        await started.wait()
        self.player.receive('ContentAudioId','222')
        await asyncio.sleep(0)
        finish.set()
        await self.settle()
        self.assertEqual(self.player.media_title,'Bibi')
        self.assertEqual(self.titles()['222'],'Bibi')

    async def test_old_pending_batch_not_carried_to_unidentified_next_figure(self):
        await self.send(('ContentAudioId','111'),('ContentTitle','Rocky'),flush=False)
        await self.send(('ContentAudioId','222'))
        self.assertEqual(self.titles(), {'111':'Tonie 111','222':'Tonie 222'})
