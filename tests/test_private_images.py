"""Executor, migration, privacy, and final-uninstall regressions."""
import asyncio
import ast
import base64
import importlib.util
import inspect
import logging
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace, ModuleType
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch, AsyncMock

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import test_library
import test_availability
from library_unit_pkg.image_storage import ImageStorage, IMAGE_PREFIX, image_reference

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32 + bytes.fromhex("0000000049454e44ae426082")
JPG = b"\xff\xd8\xff" + b"0" * 32 + b"\xff\xd9"
ROOT = Path(__file__).resolve().parents[1]


def load_archive():
    path = ROOT / 'custom_components/teddycloud_homeassistant/artwork_archive.py'
    nodes = [n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef)]
    ns = {'asyncio':asyncio, 'urlsplit':__import__('urllib.parse',fromlist=['urlsplit']).urlsplit,
          '_LOGGER':logging.getLogger(__name__), 'MAX_IMAGE_BYTES':3*1024*1024,
          'ALLOWED_TYPES':{'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}}
    exec(compile(ast.Module(body=nodes,type_ignores=[]), str(path), 'exec'), ns)
    return ns['ArtworkArchive']


class TestPrivateImages(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        test_library.FakeStore.saved = {}
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.executors = []
        self.loop_thread = threading.get_ident()
        async def executor(func, *args):
            self.executors.append(func.__name__)
            return await asyncio.to_thread(func, *args)
        self.hass = SimpleNamespace(config=SimpleNamespace(path=lambda *p:str(self.root.joinpath(*p))),
                                    async_add_executor_job=executor, data={})
        self.images = ImageStorage(self.hass)

    async def test_migrate_archive_and_uploads_rewrite_metadata_and_preserve_collection(self):
        legacy = self.root / 'www/teddycloud_homeassistant'
        for kind in ['library','figures']:
            (legacy/kind).mkdir(parents=True)
            (legacy/kind/'123.png').write_bytes(PNG)
        (legacy/'library/notes.txt').write_text('unrelated')
        key = test_library.library_module.STORE_KEY
        test_library.FakeStore.saved[key] = {'entries':{'123':{
            'image':'/local/teddycloud_homeassistant/figures/123.png?v=old',
            'custom':{'image':'/local/teddycloud_homeassistant/library/123.png?v=old','title':'Family title'},
            'times_seen':7,'box_last_seen':{'box':{'color':'#ff0000','at':'2026-11-01T00:00:00Z'}}
        }},'hidden':['999']}
        await self.images.async_initialize()
        lib = test_library.library_module.TonieLibrary(self.hass,self.images)
        await lib.async_load()
        item = lib.public_entries()[0]
        self.assertTrue(item['image'].startswith(IMAGE_PREFIX+'library/123.png'))
        self.assertTrue(lib._entries['123']['image'].startswith(IMAGE_PREFIX+'figures/123.png'))
        self.assertEqual(item['title'],'Family title')
        self.assertEqual(item['times_seen'],7)
        self.assertEqual(lib._hidden,{'999'})
        self.assertFalse((legacy/'library/123.png').exists())
        self.assertFalse((legacy/'figures/123.png').exists())
        self.assertEqual((legacy/'library/notes.txt').read_text(),'unrelated')
        self.assertEqual((await self.images.async_read('library','123.png'))[0],PNG)
        # A restart is idempotent and never recreates public images.
        second = ImageStorage(self.hass)
        await second.async_initialize()
        self.assertEqual(second.lookup('library','123'),self.images.lookup('library','123'))

    async def test_all_image_file_operations_use_executor_and_lookup_never_probes_disk(self):
        original = {}
        def guarded(name):
            function = getattr(Path,name); original[name] = function
            def call(path,*args,**kwargs):
                self.assertNotEqual(threading.get_ident(),self.loop_thread,name+' on event loop')
                return function(path,*args,**kwargs)
            return call
        archive = load_archive()(self.hass,self.images)
        player,_,_ = test_availability.TestAvailability().make_player()
        player._archive = archive
        player._values['ContentAudioId'] = 'old'
        player.hass = None
        player._online_catalog = SimpleNamespace(find=AsyncMock(return_value={'figure':'https://example.test/123.png'}),failed_at=None)
        type(player).async_get_media_image.__globals__.update(DOMAIN='teddycloud_homeassistant',image_reference=image_reference)
        from contextlib import ExitStack
        with ExitStack() as stack:
            for name in ['stat','is_file','is_dir','is_symlink','iterdir','mkdir','open','read_bytes','write_bytes','unlink','rmdir','replace']:
                stack.enter_context(patch.object(Path,name,guarded(name)))
            await self.images.async_initialize()
            await self.images.async_write('figures','123','.png',PNG)
            player.receive('ContentAudioId','123')
            self.hass.data['teddycloud_homeassistant'] = {'images':self.images}
            player.hass = self.hass
            await player._lookup_image('123')
            self.assertEqual(await player.async_get_media_image(),(PNG,'image/png'))
            for _ in range(10):
                self.assertTrue(archive.lookup('123').startswith(IMAGE_PREFIX))
                self.assertTrue(player.media_image_url.startswith(IMAGE_PREFIX))
                self.assertTrue(player.extra_state_attributes['cover_url'].startswith(IMAGE_PREFIX))
            self.assertEqual((await self.images.async_read('figures','123.png'))[0],PNG)
            await self.images.async_delete('figures','123')
            await self.images.async_remove()
        self.assertIn('_write',self.executors)
        self.assertIn('_cleanup_all',self.executors)

    async def test_upload_switch_delete_and_shared_aliases_keep_files_private(self):
        await self.images.async_initialize()
        lib = test_library.library_module.TonieLibrary(self.hass,self.images)
        encoded = 'data:image/png;base64,'+base64.b64encode(PNG).decode()
        item = await lib.async_edit('123',title='Upload',image_data=encoded)
        self.assertTrue(item['image'].startswith(IMAGE_PREFIX+'library/123.png'))
        self.assertFalse((self.root/'www').exists())
        jpg = 'data:image/jpeg;base64,'+base64.b64encode(JPG).decode()
        await lib.async_edit('123',image_data=jpg)
        self.assertIsNone(await self.images.async_read('library','123.png'))
        self.assertEqual((await self.images.async_read('library','123.jpg'))[0],JPG)
        await lib.async_delete('123')
        self.assertIsNone(await self.images.async_read('library','123.jpg'))

    async def test_bad_names_symlinks_and_corrupt_images_are_not_served(self):
        await self.images.async_initialize()
        await self.images.async_write('figures','123','.png',PNG)
        for kind, filename in [('figures','../secret'),('../library','123.png'),('library','%2e%2e.png'),('figures','123.svg')]:
            self.assertIsNone(await self.images.async_read(kind,filename))
        for value in ['https://evil.test'+IMAGE_PREFIX+'figures/123.png', IMAGE_PREFIX+'../123.png', IMAGE_PREFIX+'figures/../123.png']:
            self.assertIsNone(image_reference(value))
        outside = self.root/'secret.png';outside.write_bytes(PNG)
        target = self.images.root/'figures/123.png';target.unlink();target.symlink_to(outside)
        self.assertIsNone(await self.images.async_read('figures','123.png'))
        with self.assertRaises(ValueError):
            await self.images.async_write('figures','456','.png',b'not an image')
        self.assertIsNone(self.images.lookup('figures','456'))

    async def test_migration_preserves_conflicting_and_corrupt_files_outside_www(self):
        private = self.images.root/'library';private.mkdir(parents=True)
        (private/'123.png').write_bytes(PNG)
        old = self.images.legacy/'library';old.mkdir(parents=True)
        (old/'123.png').write_bytes(PNG+b'older corrupt content')
        (old/'456.png').write_bytes(b'corrupt but user-owned data')
        await self.images.async_initialize()
        self.assertFalse(old.exists())
        self.assertEqual((await self.images.async_read('library','123.png'))[0],PNG)
        self.assertIsNone(await self.images.async_read('library','456.png'))
        backups = list((self.images.root/'migration-backups').iterdir())
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_bytes(),PNG+b'older corrupt content')

    async def test_cancelled_write_finishes_before_final_purge_and_cannot_resurrect(self):
        await self.images.async_initialize()
        entered, release = threading.Event(), threading.Event()
        write = self.images._write
        def slow(*args):
            entered.set();release.wait(5)
            return write(*args)
        self.images._write = slow
        task = asyncio.create_task(self.images.async_write('library','123','.png',PNG))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait,2))
            task.cancel()
            purge = asyncio.create_task(self.images.async_remove())
            await asyncio.sleep(0)
            self.assertFalse(purge.done())
        finally:
            release.set()
        with self.assertRaises(asyncio.CancelledError): await task
        await purge
        self.assertFalse(self.images.root.parent.exists())
        with self.assertRaises(ValueError): await self.images.async_write('library','123','.png',PNG)


class TestPrivateImageHTTP(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = TestPrivateImages.asyncSetUp
    async def test_actual_ha_auth_wrapper_blocks_anonymous_before_disk_and_serves_authorized(self):
        await self.images.async_initialize()
        await self.images.async_write('library','123','.png',PNG)
        # Load our real view with HA's small base-class contract.
        components = sys.modules.setdefault('homeassistant.components',ModuleType('homeassistant.components'))
        http = sys.modules.setdefault('homeassistant.components.http',ModuleType('homeassistant.components.http'))
        http.HomeAssistantView = type('HomeAssistantView',(),{'max_body_size':None})
        source = ROOT/'custom_components/teddycloud_homeassistant/image_view.py'
        spec = importlib.util.spec_from_file_location('library_unit_pkg.image_view',source)
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.hass.data['teddycloud_homeassistant'] = {'images':self.images}
        self.hass.is_stopping = False
        view = module.PrivateImageView(self.hass)
        self.assertTrue(view.requires_auth)
        # Execute the unmodified HA HTTP request wrapper fixture. Only its
        # unrelated imports/types are adapted, not the authentication branch.
        network = ModuleType('image_http_contract.network')
        network.NoURLAvailableError = type('NoURLAvailableError',(Exception,),{})
        network.get_url = lambda *a,**k:'http://homeassistant.local'
        sys.modules['image_http_contract'] = ModuleType('image_http_contract')
        sys.modules['image_http_contract.network'] = network
        ns = {'__package__':'image_http_contract','inspect':inspect,'web':web,
              'HTTPStatus':HTTPStatus,'HTTPUnauthorized':web.HTTPUnauthorized,
              'KEY_AUTHENTICATED':'ha_authenticated','is_callback':lambda handler:False,
              '_LOGGER':logging.getLogger(__name__),'logging':logging,
              'probatio':SimpleNamespace(Invalid=type('Invalid',(Exception,),{})),
              'exceptions':SimpleNamespace(ServiceNotFound=type('ServiceNotFound',(Exception,),{}),
                                           Unauthorized=type('Unauthorized',(Exception,),{}))}
        exec((ROOT/'tests/fixtures/ha_http_auth_gate.py').read_text(),ns)
        @web.middleware
        async def auth(request,handler):
            # HA's middleware validates bearer tokens or signed paths before
            # setting this marker. Cryptographic validation stays in HA Core.
            request['ha_authenticated'] = request.headers.get('Authorization') == 'Bearer test-user'
            return await handler(request)
        app = web.Application(middlewares=[auth])
        app.router.add_get(view.url,ns['request_handler_factory'](self.hass,view,view.get))
        async with TestClient(TestServer(app)) as client:
            self.executors.clear()
            response = await client.get(IMAGE_PREFIX+'library/123.png')
            self.assertEqual(response.status,401)
            self.assertEqual(self.executors,[])
            response = await client.get(IMAGE_PREFIX+'library/123.png',headers={'Authorization':'Bearer test-user'})
            self.assertEqual(response.status,200)
            self.assertEqual(await response.read(),PNG)
            self.assertEqual(response.content_type,'image/png')
            self.assertEqual(response.headers['Cache-Control'],'private, no-store')
            response = await client.get(IMAGE_PREFIX+'library/missing.png',headers={'Authorization':'Bearer test-user'})
            self.assertEqual(response.status,404)
