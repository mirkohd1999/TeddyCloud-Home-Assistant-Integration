"""Room-light following uses registered sensor states without changing sensors."""
import ast
import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/teddycloud_homeassistant'

class ServiceError(Exception):
    pass

class RoomLightTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.states = {}
        self.calls = []
        self.listeners = []
        self.unsubscribed = False
        self.fail = set()
        async def call(domain, service, data, blocking):
            self.calls.append((domain, service, data))
            if data['entity_id'] in self.fail:
                raise ServiceError('offline')
        def listen(event, handler):
            self.listeners.append(handler)
            def unsubscribe(): self.unsubscribed = True
            return unsubscribe
        self.hass = SimpleNamespace(
            states=SimpleNamespace(get=self.states.get),
            services=SimpleNamespace(async_call=call),
            bus=SimpleNamespace(async_listen=listen),
            async_create_task=asyncio.create_task)
        registry = SimpleNamespace(async_get_entity_id=lambda domain, platform, unique: f'{domain}.{unique}')
        tree = ast.parse((ROOT / 'room_light.py').read_text())
        nodes = [n for n in tree.body if not isinstance(n, (ast.Import, ast.ImportFrom))]
        ns = dict(asyncio=asyncio, logging=logging, callback=lambda f:f,
                  er=SimpleNamespace(async_get=lambda hass:registry), DOMAIN='teddycloud_homeassistant',
                  EVENT_STATE_CHANGED='state_changed', HomeAssistantError=ServiceError)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'room_light.py', 'exec'), ns)
        self.entry = SimpleNamespace(entry_id='bedroom', options={'room_lights':['light.color','light.white','light.simple']})
        self.controller = ns['RoomLightController'](self.hass, self.entry)
        self.controller.enabled = True
        self.state('binary_sensor.bedroom_tonie_present','on')
        self.state('sensor.bedroom_tonie_color','#123456',rgb_color=[18,52,86])
        self.state('media_player.bedroom_player','playing')
        self.state('light.color','on',supported_color_modes=['rgb'],brightness=37)
        self.state('light.white','on',supported_color_modes=['color_temp'],brightness=60)
        self.state('light.simple','on',supported_color_modes=['onoff'])

    def state(self, entity_id, state, **attributes):
        self.states[entity_id] = SimpleNamespace(state=state, attributes=attributes)

    async def test_color_only_for_color_lamps_and_no_brightness_reset(self):
        await self.controller.async_sync()
        self.assertEqual(self.calls[0], ('light','turn_on',{'entity_id':'light.color','rgb_color':[18,52,86]}))
        self.assertEqual(self.calls[1][2], {'entity_id':'light.white'})
        self.assertEqual(self.calls[2][2], {'entity_id':'light.simple'})
        self.assertTrue(all('brightness' not in data and 'brightness_pct' not in data for _,_,data in self.calls))

    async def test_removal_or_existing_duration_expiry_turns_off_all_lights(self):
        self.state('binary_sensor.bedroom_tonie_present','off')
        await self.controller.async_sync()
        self.assertEqual([s for _,s,_ in self.calls], ['turn_off']*3)
        self.assertTrue(all('rgb_color' not in data for _,_,data in self.calls))

    async def test_offline_box_turns_off(self):
        self.state('media_player.bedroom_player','unavailable')
        await self.controller.async_sync()
        self.assertEqual([s for _,s,_ in self.calls], ['turn_off']*3)

    async def test_unknown_presence_does_not_control_lights(self):
        for value in ('unknown','unavailable'):
            self.state('binary_sensor.bedroom_tonie_present',value)
            await self.controller.async_sync()
        self.assertEqual(self.calls, [])

    async def test_missing_or_invalid_color_keeps_lamp_color(self):
        for rgb in (None, [1,2], [256,0,0], [True,2,3], 'red'):
            self.state('sensor.bedroom_tonie_color','unknown',rgb_color=rgb)
            await self.controller.async_sync()
        self.assertTrue(all('rgb_color' not in data for _,_,data in self.calls))

    async def test_disabled_and_unconfigured_do_not_control_lights(self):
        self.controller.enabled = False
        await self.controller.async_sync()
        self.controller.enabled = True
        self.entry.options['room_lights'] = []
        await self.controller.async_sync()
        self.assertEqual(self.calls, [])

    async def test_unavailable_lamps_skipped_and_failure_does_not_block_others(self):
        self.fail.add('light.color')
        self.state('light.simple','unavailable')
        with self.assertLogs(level='WARNING'):
            await self.controller.async_sync()
        self.assertEqual([d['entity_id'] for _,_,d in self.calls], ['light.color','light.white'])

    async def test_registered_sensor_rename_and_box_isolation(self):
        # Entity IDs may be changed by the user; look up unique IDs, never names.
        self.controller.entity_id = lambda domain, suffix: f'{domain}.renamed_{suffix}'
        self.state('binary_sensor.renamed_tonie_present','off')
        await self.controller.async_sync()
        self.assertEqual([s for _,s,_ in self.calls], ['turn_off']*3)
        self.calls.clear()
        self.controller.async_start()
        await asyncio.sleep(0)
        self.calls.clear()
        self.listeners[0](SimpleNamespace(data={'entity_id':'sensor.other_tonie_color'}))
        await asyncio.sleep(0)
        self.assertEqual(self.calls, [])
        self.controller.async_stop()
        self.assertTrue(self.unsubscribed)

    async def test_stop_cancels_pending_calls(self):
        self.controller.async_schedule()
        self.controller.async_stop()
        await asyncio.sleep(0)
        self.assertEqual(self.calls, [])

class RoomLightSwitchTests(unittest.IsolatedAsyncioTestCase):
    async def test_restore_and_manual_disable(self):
        class Entity:
            async def async_added_to_hass(self): pass
            async def async_get_last_state(self): return SimpleNamespace(state='on')
            def async_write_ha_state(self): pass
        tree = ast.parse((ROOT / 'switch.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        ns = {'SwitchEntity':Entity, 'RestoreEntity':type('Restore', (), {}), 'CONF_BOX_NAME':'box_name'}
        exec(compile(ast.Module(body=[cls], type_ignores=[]), 'switch.py', 'exec'), ns)
        scheduled = []
        controller = SimpleNamespace(enabled=False, async_schedule=lambda:scheduled.append(True))
        switch = ns['RoomLightSwitch'](SimpleNamespace(entry_id='bedroom',data={'box_name':'Box'}),controller,{})
        await switch.async_added_to_hass()
        self.assertTrue(controller.enabled)
        await switch.async_turn_off()
        self.assertFalse(controller.enabled)
        await switch.async_turn_on()
        self.assertTrue(controller.enabled)
        self.assertEqual(scheduled,[True])
        switch.async_get_last_state = self.no_previous_state
        await switch.async_added_to_hass()
        self.assertFalse(controller.enabled)

    async def no_previous_state(self):
        return None
