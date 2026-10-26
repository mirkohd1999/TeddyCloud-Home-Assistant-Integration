"""Only audio IDs explicitly attached to the same catalog entry are grouped."""
import ast
import asyncio
from datetime import datetime, timezone, timedelta
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest


class TestCatalogAliases(unittest.TestCase):
    def test_versions_share_ids_but_different_episodes_do_not(self):
        path=Path(__file__).resolve().parents[1]/'custom_components/teddycloud_homeassistant/online_catalog.py'
        tree=ast.parse(path.read_text())
        nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))]
        ns={'asyncio':asyncio,'dt_util':SimpleNamespace(utcnow=lambda:datetime.now(timezone.utc)),
            'REFRESH':timedelta(hours=24),'RETRY':timedelta(seconds=20),
            'async_get_clientsession':lambda hass:None,'_LOGGER':logging.getLogger(__name__)}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
        async def run():
            for kind, data in [
                ('v2',[{'data':[
                    {'series':'Series','episode':'One','ids':[{'audio-id':111},{'audio-id':222}]},
                    {'series':'Series','episode':'Two','ids':[{'audio-id':333}]}
                ]}]),
                ('v1',[{'title':'One','audio_id':[111,222]},{'title':'Two','audio_id':[333]}])
            ]:
                ns['CATALOG_SOURCES']=[(kind,'mock')]
                catalog=ns['OnlineCatalog'](None)
                async def download(session,url):return data
                catalog._download_json=download
                await catalog.refresh()
                self.assertEqual(set(catalog.items['111']['audio_ids']),{'111','222'})
                self.assertEqual(set(catalog.items['333']['audio_ids']),{'333'})
        asyncio.run(run())
