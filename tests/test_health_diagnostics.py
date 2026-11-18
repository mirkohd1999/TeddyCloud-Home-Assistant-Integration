"""Connection status separation, redacted diagnostics and options navigation."""
import ast
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]/'custom_components/teddycloud_homeassistant'
DOMAIN='teddycloud_homeassistant'

def definitions(name):
    return [n for n in ast.parse((ROOT/name).read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]

class TestHealth(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.connected=True;self.reads=[]
        async def read(*ref):self.reads.append(ref);return (b'image','image/png')
        self.player=SimpleNamespace(figure_present=True,media_image_url='/api/teddycloud_homeassistant/images/library/100.png',available=False,
            _last_message_at=(datetime.now(timezone.utc)-timedelta(seconds=30)).isoformat(),
            _availability=SimpleNamespace(last_seen=None,playback_remaining=0))
        self.catalog=SimpleNamespace(fetched_at=datetime.now(timezone.utc),failed_at=None,loaded_format='v2')
        self.library=SimpleNamespace(_entries={'secret-audio-id':{'title':'private-title','image':'https://user:password@private-url/?authSig=token'}},_hidden={'secret-hidden'})
        self.hass=SimpleNamespace(data={DOMAIN:{'box':self.player,'online_catalog':self.catalog,'images':SimpleNamespace(async_read=read),'library':self.library}})
        self.entry=SimpleNamespace(entry_id='box',data={'password':'secret-password','box_name':'private-box','prefix':'private/topic'},options={'teddycloud_url':'http://private-server','offline_timeout':5})
        ns={'datetime':datetime,'timezone':timezone,'mqtt':SimpleNamespace(is_connected=lambda hass:self.connected), 'DOMAIN':DOMAIN,
            'image_reference':lambda value:('library','100.png') if value.startswith('/api/') else None}
        exec(compile(ast.Module(body=definitions('health.py'),type_ignores=[]),'health.py','exec'),ns)
        self.report=ns['async_connection_report']

    async def test_broker_connected_and_sleeping_box_are_different(self):
        report=await self.report(self.hass,self.entry)
        self.assertEqual(report['mqtt']['status'],'connected');self.assertEqual(report['box']['status'],'no_fresh_messages')
        self.assertGreaterEqual(report['box']['last_message_age_seconds'],29)
        self.assertEqual(report['image']['status'],'available');self.assertEqual(len(self.reads),1)
        self.connected=False
        report=await self.report(self.hass,self.entry)
        self.assertEqual(report['mqtt']['status'],'disconnected');self.assertEqual(report['box']['status'],'mqtt_disconnected')

    async def test_catalog_failure_or_legacy_and_external_image_are_explicit(self):
        self.player.media_image_url='https://private-server/image.png?secret=token'
        self.catalog.failed_at=datetime.now(timezone.utc)
        report=await self.report(self.hass,self.entry)
        self.assertEqual(report['catalog']['status'],'unavailable');self.assertEqual(report['image']['status'],'external_not_checked');self.assertEqual(self.reads,[])
        self.catalog.failed_at=None;self.catalog.loaded_format='v1'
        self.assertEqual((await self.report(self.hass,self.entry))['catalog']['status'],'limited')
        self.player.figure_present=False
        self.assertEqual((await self.report(self.hass,self.entry))['image']['status'],'not_selected')

    async def test_native_diagnostics_never_return_household_metadata_or_secrets(self):
        ns={'DOMAIN':DOMAIN,'CARD_VERSION':'test','HA_VERSION':'test','async_connection_report':self.report}
        exec(compile(ast.Module(body=definitions('diagnostics.py'),type_ignores=[]),'diagnostics.py','exec'),ns)
        data=await ns['async_get_config_entry_diagnostics'](self.hass,self.entry);body=json.dumps(data)
        for value in ('private','secret','password','authSig','token','secret-audio-id'):
            self.assertNotIn(value,body)
        self.assertEqual(data['library']['records'],1)

    async def test_options_check_is_read_only_and_returns_to_menu(self):
        class Flow:
            def async_show_menu(self,**kwargs):return kwargs
            def async_show_form(self,**kwargs):return kwargs
        ns={'config_entries':SimpleNamespace(OptionsFlow=Flow),'async_connection_report':self.report,
            'vol':SimpleNamespace(Schema=lambda data:data)}
        cls=next(n for n in definitions('config_flow.py') if isinstance(n,ast.ClassDef) and n.name=='TeddyCloudOptionsFlow')
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'config_flow.py','exec'),ns)
        flow=ns['TeddyCloudOptionsFlow']();flow.hass=self.hass;flow.config_entry=self.entry
        menu=await flow.async_step_init();self.assertEqual(menu['menu_options'],['settings','connection'])
        form=await flow.async_step_connection();self.assertEqual(form['step_id'],'connection');self.assertEqual(form['description_placeholders']['mqtt'],'✓')
        self.assertEqual((await flow.async_step_connection({}))['step_id'],'init')
