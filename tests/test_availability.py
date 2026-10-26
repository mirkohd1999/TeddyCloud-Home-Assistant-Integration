"""Offline deadline and media-player integration without a running HA instance."""
import ast
import asyncio
from datetime import datetime, timezone
import importlib.util
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

    def test_player_timer_unavailable_and_unload(self):
        timers = []
        class Entity:
            hass = None
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
              'CONF_BOX_NAME':'box_name', 'CONF_BOX_COLOR':'box_color', 'DEFAULT_COLOR':'#8f77c7',
              'MediaPlayerState':SimpleNamespace(IDLE='idle', PLAYING='playing')}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ROOT / 'media_player.py'), 'exec'), ns)
        entry = SimpleNamespace(entry_id='box', data={'box_name':'Box'}, options={'offline_timeout':7})
        player = ns['BoxPlayer'](entry, None)
        player.hass = SimpleNamespace()
        player.receive('Playback', 'ON', retained=True)
        self.assertFalse(player.available)
        self.assertEqual(timers, [])
        player.receive('Playback', 'ON')
        self.assertTrue(player.available)
        self.assertEqual(timers[-1]['seconds'], 420)
        player.note_message()
        self.assertTrue(timers[0]['cancelled'])
        timers[-1]['callback'](None)
        self.assertFalse(player.available)
        self.assertFalse(player._was_playing)
        player.receive('Playback', 'ON')
        self.assertTrue(player.available)
        self.assertEqual(player.state, 'playing')
        asyncio.run(player.async_will_remove_from_hass())
        self.assertTrue(timers[-1]['cancelled'])
