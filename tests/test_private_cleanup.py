"""Final removal erases only our data and cannot be undone by late tasks."""
import ast
import asyncio
import base64
import logging
from pathlib import Path
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock
import unittest

import test_library
import test_private_images as image_tests
from test_private_images import ROOT, PNG, load_archive


class TestPrivateCleanup(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = image_tests.TestPrivateImages.asyncSetUp

    async def prepare(self):
        await self.images.async_initialize()
        self.lib = test_library.library_module.TonieLibrary(self.hass,self.images)
        await self.lib.async_edit('123',title='Own upload',image_data='data:image/png;base64,'+base64.b64encode(PNG).decode())
        await self.images.async_write('figures','456','.png',PNG)
        backup = self.images.root/'migration-backups';backup.mkdir()
        (backup/'old-image.bak').write_bytes(b'old private content')
        self.other = self.root/'www/user-photo.png';self.other.parent.mkdir(exist_ok=True);self.other.write_bytes(PNG)
        self.items = [
            {'id':'ours','url':'/teddycloud-homeassistant/card-v0510.js?v=0.5.10'},
            {'id':'old','url':'/teddycloud-homeassistant/card-v058.js?refresh=2'},
            {'id':'foreign','url':'/hacsfiles/Bubble-Card/bubble-card.js'},
        ]
        resources = SimpleNamespace(loaded=False,async_items=lambda:self.items)
        async def load():resources.loaded=True
        async def delete(ident):self.items[:]=[item for item in self.items if item['id']!=ident]
        resources.async_load = AsyncMock(side_effect=load)
        resources.async_delete_item = AsyncMock(side_effect=delete)
        self.entries = [SimpleNamespace(entry_id='old')]
        self.hass.config_entries = SimpleNamespace(async_entries=lambda domain:self.entries)
        self.hass.async_create_task = asyncio.create_task
        self.hass.data.update({
            'lovelace':SimpleNamespace(resources=resources,resource_mode='storage'),
            'teddycloud_homeassistant':{'images':self.images,'library':self.lib},
            'teddycloud_homeassistant_card_registered':True,
            'teddycloud_homeassistant_card_url':'old',
        })
        test_library.FakeStore.saved['teddycloud_homeassistant.owned_resources']={'resource_id':'ours'}
        source = ROOT/'custom_components/teddycloud_homeassistant/cleanup.py'
        node = next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.AsyncFunctionDef))
        ns = {'__name__':'library_unit_pkg.cleanup_contract','__package__':'library_unit_pkg',
              'DOMAIN':'teddycloud_homeassistant','LOVELACE_DATA':'lovelace',
              'BRANDING_STORE':'teddycloud_homeassistant.owned_resources',
              'Store':test_library.FakeStore,'asyncio':asyncio,'_LOGGER':logging.getLogger(__name__),
              'is_card_resource':lambda url:bool(re.fullmatch(r'/teddycloud-homeassistant/card(?:-v[0-9]+)?\.js',url.split('?')[0]))}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),ns)
        self.cleanup = ns['async_remove_owned_data']

    async def test_last_removal_cancels_downloads_deletes_uploads_cache_metadata_resources(self):
        await self.prepare()
        archive = load_archive()(self.hass,self.images)
        entered = asyncio.Event()
        async def download(key,url):
            entered.set()
            await asyncio.Event().wait()
        archive._download = download
        caller = asyncio.create_task(archive.store('999','https://example.test/image.png'))
        await entered.wait()
        background = asyncio.create_task(asyncio.Event().wait())
        data = self.hass.data['teddycloud_homeassistant']
        data.update(artwork_archive=archive,library_catalog_task=background)
        # A symlink inside our namespace must never delete its external target.
        (self.images.root/'library/999.png').symlink_to(self.other)
        await self.cleanup(self.hass,'old')
        with self.assertRaises(asyncio.CancelledError):await caller
        self.assertTrue(background.cancelled())
        self.assertFalse(self.images.root.parent.exists())
        self.assertEqual(self.other.read_bytes(),PNG)
        self.assertEqual(self.items,[{'id':'foreign','url':'/hacsfiles/Bubble-Card/bubble-card.js'}])
        self.assertNotIn(test_library.library_module.STORE_KEY,test_library.FakeStore.saved)
        self.assertNotIn('teddycloud_homeassistant.owned_resources',test_library.FakeStore.saved)
        self.assertNotIn('teddycloud_homeassistant',self.hass.data)
        # Queued events/commands must not resurrect the collection after uninstall.
        await self.lib.async_seen('late','456')
        await self.lib.async_metadata('456',title='Late')
        self.assertEqual(self.lib.public_entries(),[])
        with self.assertRaises(ValueError):await self.lib.async_edit('new',title='Late')
        with self.assertRaises(ValueError):await self.images.async_write('library','777','.png',PNG)
        self.assertFalse(self.images.root.parent.exists())

    async def test_another_box_preserves_shared_uploads_library_and_resources(self):
        await self.prepare()
        self.entries.append(SimpleNamespace(entry_id='other'))
        await self.cleanup(self.hass,'old')
        self.assertEqual(len(self.items),3)
        self.assertTrue(self.images.lookup('library','123'))
        self.assertEqual(len(self.lib.public_entries()),1)
        self.assertIn(test_library.library_module.STORE_KEY,test_library.FakeStore.saved)

    async def test_cleanup_also_works_if_runtime_data_was_already_unloaded(self):
        await self.prepare()
        self.hass.data.pop('teddycloud_homeassistant')
        await self.cleanup(self.hass,'old')
        self.assertFalse(self.images.root.parent.exists())
        self.assertNotIn(test_library.library_module.STORE_KEY,test_library.FakeStore.saved)
        self.assertEqual(self.other.read_bytes(),PNG)
