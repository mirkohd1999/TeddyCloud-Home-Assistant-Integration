"""Offline deadline and media-player integration without a running HA instance."""
import ast
import asyncio
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/teddycloud_homeassistant'
spec = importlib.util.spec_from_file_location('availability_unit', ROOT / 'availability.py')
availability = importlib.util.module_from_spec(spec)
spec.loader.exec_module(availability)


class TestAvailability(unittest.TestCase):
    def test_deadline_retained_and_recovery(self):
        now = [0]
        state = availability.Availability(clock=lambda: now[0])
        self.assertFalse(state.online)
        state.received(retained=True)
        self.assertFalse(state.online)
        state.received()
        now[0] = 299
        self.assertTrue(state.online)
        state.received(retained=True)
        now[0] = 300
        self.assertFalse(state.online)
        state.received()
        self.assertTrue(state.online)

    def test_configuration_bounds(self):
        self.assertEqual(availability.timeout_minutes(None), 5)
        self.assertEqual(availability.timeout_minutes(0), 1)
        self.assertEqual(availability.timeout_minutes(121), 120)
        self.assertEqual(availability.Availability(7).timeout, 420)

    def make_player(self):
        timers = []
        class Entity:
            hass = None
            capability_attributes = {"supported_test_capability": True}
            def async_write_ha_state(self): pass
            async def async_will_remove_from_hass(self): pass
        def schedule(hass, seconds, callback):
            timer = {'seconds':seconds, 'callback':callback, 'cancelled':False}
            timers.append(timer)
            return lambda: timer.update(cancelled=True)
        source = ast.parse((ROOT / 'media_player.py').read_text())
        nodes = [n for n in source.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        ns = {'MediaPlayerEntity':Entity, 'MediaPlayerEntityFeature':int,
              'callback':lambda fn: fn, 'Availability':availability.Availability,
              'async_call_later':schedule, 'datetime':datetime, 'timezone':timezone,
              'CONF_FALLBACK_COVER':'fallback_cover', 'resolved_picture':lambda v,s:v, 'asyncio':asyncio, 'json':json, 'CONF_CATALOG':'catalog', 'CONF_BOX_NAME':'box_name', 'CONF_BOX_COLOR':'box_color', 'DEFAULT_COLOR':'#8f77c7',
              'MediaPlayerState':SimpleNamespace(IDLE='idle', PLAYING='playing')}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ROOT / 'media_player.py'), 'exec'), ns)
        entry = SimpleNamespace(entry_id='box', data={'box_name':'Box'}, options={'offline_timeout':7})
        player = ns['BoxPlayer'](entry, None)
        now = [0]
        player._availability = availability.Availability(7, clock=lambda: now[0])
        player.hass = SimpleNamespace()
        return player, now, timers

    def test_player_timer_unavailable_and_unload(self):
        player, now, timers = self.make_player()
        player.receive('Playback', 'ON', retained=True)
        self.assertFalse(player.available)
        self.assertEqual(timers, [])
        player.receive('Playback', 'ON')
        self.assertTrue(player.available)
        self.assertEqual(timers[-1]['seconds'], 420)
        player.note_message()
        self.assertTrue(timers[0]['cancelled'])
        now[0] = 420
        timers[-1]['callback'](None)
        self.assertFalse(player.available)
        self.assertTrue(player._was_playing)  # Keep ON edge memory; no infinite restart.
        player.receive('Playback', 'ON')
        self.assertTrue(player.available)
        self.assertEqual(player.state, 'playing')
        asyncio.run(player.async_will_remove_from_hass())
        self.assertTrue(timers[-1]['cancelled'])

    def tracker(self):
        self.now = 0
        return availability.Availability(clock=lambda: self.now, wall_clock=lambda: 1800000000 + self.now)

    def test_screenshot_old_last_seen_overrides_new_receipts(self):
        state = self.tracker()
        for self.now in (0, 60, 300, 3600):
            state.received(last_seen=1799998200)
            self.assertFalse(state.online)
        state.received(last_seen=1800000000 + self.now)
        self.assertTrue(state.online)

    def test_same_last_seen_never_moves_deadline(self):
        state = self.tracker()
        state.received(last_seen=1800000000)
        self.now = 299
        state.received(last_seen='2027-01-15T08:00:00Z')  # Same Unix timestamp.
        self.assertEqual(state.last_seen, 1800000000)
        self.assertEqual(state.remaining, 1)
        self.now = 300
        state.received(last_seen=1800000000)
        self.assertFalse(state.online)

    def test_runtime_protects_long_tonie_but_has_fixed_end(self):
        state = self.tracker()
        state.received(last_seen=1800000000)
        state.start_playback()
        state.duration = 2400
        self.now = 1800
        state.received(last_seen=1800000000)
        self.assertTrue(state.online)
        self.assertEqual(state.remaining, 720)
        self.now = 2520
        self.assertFalse(state.online)
        state.received(last_seen=1800000000)
        self.assertFalse(state.online)

    def test_stop_cancels_runtime_and_starts_normal_timeout(self):
        state = self.tracker()
        state.received(last_seen=1800000000)
        state.start_playback()
        state.duration = 3600
        self.now = 600
        state.stop_playback(fresh=True)
        self.assertEqual(state.remaining, 300)
        self.now = 900
        self.assertFalse(state.online)

    def test_duration_arriving_later_uses_original_start(self):
        state = self.tracker()
        state.received()
        state.start_playback()
        self.now = 200
        state.duration = 600
        self.assertEqual(state.remaining, 520)
        state.duration = 1200  # A corrected catalog/manual duration.
        self.assertEqual(state.remaining, 1120)

    def test_unknown_duration_and_invalid_timestamps(self):
        state = self.tracker()
        state.received(last_seen='invalid')
        state.start_playback()
        self.now = 300
        for duration in (None, 0, -1, float('nan'), float('inf'), True, 90000):
            state.duration = duration
            self.assertFalse(state.online)
        state.received(last_seen=1900000000)  # Implausible future clock.
        self.assertIsNone(state.last_seen)
        self.assertTrue(state.online)  # Receipt fallback until a valid timestamp.
        state.received(last_seen=1800000300)
        self.now = 600
        state.received(last_seen='invalid')
        self.assertFalse(state.online)  # Never downgrade valid LastSeen to receipts.

    def test_retained_snapshot_does_not_start_playback(self):
        state = self.tracker()
        state.received(retained=True, last_seen=1800000000)
        state.start_playback()
        state.duration = 3600
        self.assertFalse(state.online)
        self.assertIsNone(state.playback_started)

    def test_timezone_and_older_timestamp(self):
        self.assertEqual(availability.timestamp('2026-10-26T12:15:22+01:00'),
                         availability.timestamp('2026-10-26T11:15:22Z'))
        self.assertIsNone(availability.timestamp('2026-10-26T11:15:22'))
        state = self.tracker()
        state.received(last_seen=1800000000)
        self.now = 100
        state.received(last_seen=1799990000)
        self.assertEqual(state.remaining, 200)

    def test_player_long_playback_repeats_removal_and_new_tonie(self):
        player, now, timers = self.make_player()
        player._availability.wall_clock = lambda: 1800000000 + now[0]
        player._values['ContentAudioId'] = '123'
        player._figure_present = True
        player.entry.options['catalog'] = json.dumps({'123': {'duration_seconds': 2400}})
        player.receive('LastSeen', '1800000000')
        player.receive('Playback', 'ON')
        self.assertEqual(timers[-1]['seconds'], 2520)
        for now[0] in (600, 1800, 2519):
            player.receive('Playback', 'ON')
            player.receive('LastSeen', '1800000000')
            self.assertTrue(player.available)
            self.assertEqual(player._availability.playback_started, 0)
        now[0] = 2520
        timers[-1]['callback'](None)
        player.receive('Playback', 'ON')
        self.assertFalse(player.available)
        player.receive('LastSeen', str(1800000000 + now[0]))
        self.assertTrue(player.available)
        player.receive('Playback', 'OFF')
        now[0] += 10
        player.receive('Playback', 'ON')
        self.assertEqual(player._availability.playback_started, 2530)
        player.receive('TagValid', '-1')
        self.assertEqual(player._availability.playback_remaining, 0)
        self.assertEqual(player.state, 'idle')
        player.receive('Playback', 'ON')  # Stale ON after removal cannot re-arm.
        self.assertEqual(player._availability.playback_remaining, 0)
        asyncio.run(player.async_will_remove_from_hass())
        self.assertTrue(timers[-1]['cancelled'])

    def test_player_metadata_update_reschedules_from_original_start(self):
        player, now, timers = self.make_player()
        player._values['ContentAudioId'] = '123'
        player.receive('Playback', 'ON')
        now[0] = 200
        player.entry.options['catalog'] = json.dumps({'123': {'duration_seconds': 2400}})
        player._refresh_availability()  # Same callback used by catalog/library updates.
        self.assertEqual(timers[-1]['seconds'], 2320)
        now[0] = 600
        self.assertTrue(player.available)
        player.receive('ContentAudioId', '')
        self.assertEqual(player._availability.playback_remaining, 0)
        self.assertEqual(timers[-1]['seconds'], 420)

    def test_playback_before_fresh_last_seen(self):
        player, now, timers = self.make_player()
        player._availability.wall_clock = lambda: 1800000000 + now[0]
        player._values['ContentAudioId'] = '123'
        player.entry.options['catalog'] = json.dumps({'123': {'duration_seconds': 2400}})
        player.receive('LastSeen', '1799990000')
        player.receive('Playback', 'ON')
        self.assertFalse(player.available)
        now[0] = 2
        player.receive('LastSeen', '1800000002')
        self.assertEqual(player._availability.playback_started, 0)
        self.assertEqual(timers[-1]['seconds'], 2518)
        self.assertIsNotNone(player._started)


    def test_configured_color_survives_unavailable_and_restart(self):
        player, now, _ = self.make_player()
        player.entry.data['box_color'] = '#D82F38'
        def ha_attributes():
            # HA keeps capabilities but deliberately omits live attributes offline.
            return {**player.capability_attributes,
                    **(player.extra_state_attributes if player.available else {})}
        self.assertFalse(player.available)
        self.assertEqual(ha_attributes()['box_color'], '#D82F38')
        self.assertTrue(ha_attributes()['supported_test_capability'])
        player.entry.options['box_color'] = '#12AB34'
        self.assertEqual(ha_attributes()['box_color'], '#12AB34')
        player.receive('Playback', 'ON')
        self.assertEqual(ha_attributes()['box_color'], '#12AB34')
        now[0] = 420
        self.assertFalse(player.available)
        self.assertEqual(ha_attributes()['box_color'], '#12AB34')
        self.assertNotIn('box_online', ha_attributes())
        fresh = type(player)(player.entry, None)
        self.assertFalse(fresh.available)
        self.assertEqual(fresh.capability_attributes['box_color'], '#12AB34')

    def test_unknown_title_flag_does_not_mark_custom_or_detected_titles(self):
        player, _, _ = self.make_player()
        self.assertTrue(player.extra_state_attributes['media_title_is_fallback'])
        player._values['ContentTitle'] = 'Unbekannter Tonie'
        self.assertFalse(player.extra_state_attributes['media_title_is_fallback'])
        player._values['ContentTitle'] = ''
        player._values['ContentAudioId'] = '123'
        player.entry.options['catalog'] = json.dumps({'123': {'title': 'Unbekannter Tonie'}})
        self.assertFalse(player.extra_state_attributes['media_title_is_fallback'])
