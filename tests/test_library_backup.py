"""Real archive roundtrips, transactional imports and admin-only HTTP routes."""
import asyncio
import ast
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from PIL import Image
import test_library
from library_unit_pkg.image_storage import ImageStorage, image_reference
from library_unit_pkg.library_backup import LibraryBackup, pack_archive, unpack_archive

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/teddycloud_homeassistant'
DOMAIN = 'teddycloud_homeassistant'

def png(color='red'):
    output=BytesIO();Image.new('RGB',(8,8),color).save(output,format='PNG');return output.getvalue()

def manifest_zip(manifest, files=None):
    output=BytesIO()
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        archive.writestr('library.json',json.dumps(manifest))
        for name, data in (files or {}).items(): archive.writestr(name,data)
    return output.getvalue()

class TestBackup(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        test_library.FakeStore.saved={}
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        async def executor(function,*args):return await asyncio.to_thread(function,*args)
        self.hass=SimpleNamespace(data={},async_add_executor_job=executor,config=SimpleNamespace(path=lambda *p:str(Path(self.temp.name).joinpath(*p))))
        self.library=await self.make_library('source')
        self.manager=LibraryBackup(self.hass,self.library)

    async def make_library(self, folder):
        hass=SimpleNamespace(async_add_executor_job=self.hass.async_add_executor_job,
            config=SimpleNamespace(path=lambda *p:str(Path(self.temp.name).joinpath(folder,*p))))
        images=ImageStorage(hass);await images.async_initialize()
        library=test_library.library_module.TonieLibrary(hass,images)
        return library

    async def source(self, count=2):
        for i in range(count):
            aid=str(100+i)
            await self.library.async_edit(aid,title=f'Figur {i}',duration_seconds=1800,
                image_data='data:image/png;base64,'+__import__('base64').b64encode(png('red' if i%2 else 'blue')).decode())
            self.library._entries[aid]['times_seen']=7
            self.library._entries[aid]['box_last_seen']={'private-box':{'at':'2026-11-18T10:00:00+00:00','secret':'hidden-name'}}
        self.library._hidden.add('999')
        self.library._entries['100']['confirmed_audio_ids']=['101'] if count>1 else []
        return await self.manager.async_export()

    async def test_roundtrip_30_figures_custom_images_aliases_counters_and_hidden(self):
        body=await self.source(30)
        entries, hidden, images=unpack_archive(body)
        self.assertEqual(len(entries),30);self.assertEqual(len(images),2);self.assertEqual(hidden,{'999'})
        self.assertNotIn(b'private-box',body)
        self.assertFalse(any('box_last_seen' in v for v in entries.values()))
        target=await self.make_library('target');manager=LibraryBackup(self.hass,target)
        preview=await manager.async_preview('admin',body)
        self.assertEqual(preview['new'],30);self.assertEqual(target.public_entries(),[])
        await manager.async_import('admin',body,preview['token'])
        self.assertEqual(target.custom_metadata('100')['title'],'Figur 0')
        self.assertIn('101',target._group_ids('100'))
        self.assertEqual(target._entries['100']['times_seen'],7)
        self.assertEqual(target._hidden,{'999'})
        for item in target._entries.values():
            self.assertIsNotNone(await target._images.async_read(*image_reference(item['custom']['image'])))
        reloaded=test_library.library_module.TonieLibrary(target.hass,target._images);await reloaded.async_load()
        self.assertEqual(reloaded.public_entries(),target.public_entries())
        # A second import never doubles recognition counts.
        p=await manager.async_preview('admin',body);await manager.async_import('admin',body,p['token'])
        self.assertEqual(target._entries['100']['times_seen'],7)

    async def test_merge_protects_custom_fields_and_explicit_overwrite_works(self):
        body=await self.source()
        target=await self.make_library('target');await target.async_edit('100',title='Mein eigener Titel',color='#2288AA')
        target._entries['100']['preview_url']='https://cdn.tonies.de/o/audio_samples/test/sample.mp3'
        manager=LibraryBackup(self.hass,target);p=await manager.async_preview('a',body)
        self.assertEqual(len(p['conflicts']),1)
        await manager.async_import('a',body,p['token'])
        self.assertEqual(target.custom_metadata('100')['title'],'Mein eigener Titel')
        self.assertEqual(target.custom_metadata('100')['color'],'#2288AA')
        self.assertIsNotNone(target._entries['100']['preview_url'])
        p=await manager.async_preview('a',body);await manager.async_import('a',body,p['token'],True)
        self.assertEqual(target.custom_metadata('100')['title'],'Figur 0')
        self.assertEqual(target.custom_metadata('100')['color'],'#2288AA') # fields absent from backup are retained

    async def test_preview_is_user_bound_expires_and_detects_changed_library(self):
        body=await self.source();p=await self.manager.async_preview('admin',body)
        with self.assertRaisesRegex(ValueError,'preview_expired'):await self.manager.async_import('other',body,p['token'])
        with self.assertRaisesRegex(ValueError,'preview_expired'):await self.manager.async_import('admin',body+b'x',p['token'])
        await self.library.async_edit('100',title='Changed since preview')
        with self.assertRaisesRegex(ValueError,'library_changed'):await self.manager.async_import('admin',body,p['token'])
        p=await self.manager.async_preview('admin',body);self.manager._previews[p['token']]['until']=0
        with self.assertRaisesRegex(ValueError,'preview_expired'):await self.manager.async_import('admin',body,p['token'])

    async def test_store_failure_rolls_back_new_images_and_preserves_old_data(self):
        body=await self.source();target=await self.make_library('target');await target.async_edit('400',title='Keep')
        manager=LibraryBackup(self.hass,target);p=await manager.async_preview('a',body)
        before=deepcopy(target._entries);saved=deepcopy(test_library.FakeStore.saved)
        async def fail(_):raise OSError('disk full')
        with patch.object(target._store,'async_save',fail):
            with self.assertRaises(OSError):await manager.async_import('a',body,p['token'])
        self.assertEqual(target._entries,before);self.assertEqual(test_library.FakeStore.saved,saved)
        self.assertEqual(target._images._index,{})
        self.assertEqual(list((target._images.root/'library').glob('*')),[])

    async def test_partial_image_write_failure_does_not_publish(self):
        body=await self.source();target=await self.make_library('target');manager=LibraryBackup(self.hass,target)
        p=await manager.async_preview('a',body);real=target._images.async_write;calls=[]
        async def write(*args):
            calls.append(args)
            if len(calls)==2:raise OSError('disk full')
            return await real(*args)
        with patch.object(target._images,'async_write',write):
            with self.assertRaises(OSError):await manager.async_import('a',body,p['token'])
        self.assertEqual(target._entries,{});self.assertEqual(target._images._index,{})

    async def test_cancel_during_commit_finishes_consistent_snapshot(self):
        body=await self.source();target=await self.make_library('target');manager=LibraryBackup(self.hass,target)
        p=await manager.async_preview('a',body);started=asyncio.Event();finish=asyncio.Event();real=target._store.async_save
        async def slow(value):started.set();await finish.wait();await real(value)
        with patch.object(target._store,'async_save',slow):
            task=asyncio.create_task(manager.async_import('a',body,p['token']))
            await started.wait();task.cancel();finish.set()
            with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(len(target._entries),2)
        for item in target._entries.values():self.assertIsNotNone(await target._images.async_read(*image_reference(item['custom']['image'])))
        self.assertEqual(test_library.FakeStore.saved[target._store.key]['entries'],target._entries)

    async def test_import_can_repair_missing_owned_image(self):
        body=await self.source();ref=image_reference(self.library._entries['100']['custom']['image'])
        await self.library._images.async_delete(*[ref[0],ref[1].rsplit('.',1)[0]])
        with self.assertRaisesRegex(ValueError,'image_missing'):await self.manager.async_export()
        p=await self.manager.async_preview('a',body);await self.manager.async_import('a',body,p['token'])
        self.assertIsNotNone(await self.library._images.async_read(*image_reference(self.library._entries['100']['custom']['image'])))

    async def test_delete_imported_image_only_after_last_reference(self):
        body=await self.source();target=await self.make_library('target');manager=LibraryBackup(self.hass,target)
        p=await manager.async_preview('a',body);await manager.async_import('a',body,p['token'])
        refs={image_reference(v['custom']['image']) for v in target._entries.values()}
        await target.async_delete('100') # explicit alias group includes 101
        for ref in refs:self.assertIsNone(await target._images.async_read(*ref))

    async def test_http_auth_preview_apply_and_stream_limits(self):
        body=await self.source();self.hass.data[DOMAIN]={'library':self.library}
        tree=ast.parse((ROOT/'backup_view.py').read_text());nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))]
        ns={'web':web,'HomeAssistantView':object,'DOMAIN':DOMAIN,'LibraryBackup':LibraryBackup,'MAX_ARCHIVE':32*1024*1024}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'backup_view.py','exec'),ns)
        view=ns['LibraryBackupView'](self.hass);self.assertTrue(view.requires_auth)
        @web.middleware
        async def auth(request,handler):
            role=request.headers.get('X-Test-Role')
            if not role:return web.Response(status=401)
            request['hass_user']=SimpleNamespace(id=role,is_admin=role=='admin')
            return await handler(request)
        app=web.Application(middlewares=[auth]);app.router.add_get(view.url,view.get);app.router.add_post(view.url,view.post)
        async with TestClient(TestServer(app)) as client:
            for method in (client.get,client.post):
                self.assertEqual((await method(view.url)).status,401)
                self.assertEqual((await method(view.url,headers={'X-Test-Role':'user'})).status,403)
            response=await client.get(view.url,headers={'X-Test-Role':'admin'})
            self.assertEqual(response.status,200);self.assertEqual(response.headers['Cache-Control'],'private, no-store')
            self.assertEqual(len(unpack_archive(await response.read())[0]),2)
            response=await client.post(view.url+'?action=preview',data=body,headers={'X-Test-Role':'admin'});p=await response.json()
            self.assertEqual(response.status,200)
            response=await client.post(view.url+'?action=import',data=body,headers={'X-Test-Role':'admin','X-TeddyCloud-Preview':p['token']})
            self.assertEqual(response.status,200)
            with patch.dict(ns,MAX_ARCHIVE=10):
                response=await client.post(view.url+'?action=preview',data=body,headers={'X-Test-Role':'admin'})
                self.assertEqual(response.status,413)

class TestArchiveValidation(unittest.TestCase):
    def base(self):return {'format':'teddycloud-library','version':1,'entries':{'100':{'title':'Tonie','custom':{}}},'hidden':[]}
    def test_unsupported_versions_and_invalid_fields(self):
        for change in ({'version':2},{'version':True},{'entries':{'../bad':{}}},{'entries':{'100':{'custom':{'color':'red'}}}},{'hidden':['100']}):
            with self.subTest(change=change):
                data=self.base();data.update(change)
                with self.assertRaises(ValueError):unpack_archive(manifest_zip(data))
    def test_path_traversal_symlink_duplicate_and_unreferenced_files(self):
        for name in ('../escape','/etc/passwd','images/../escape','images/not-a-hash.png'):
            with self.assertRaises(ValueError):unpack_archive(manifest_zip(self.base(),{name:b'bad'}))
        output=BytesIO()
        with ZipFile(output,'w') as archive:
            archive.writestr('library.json',json.dumps(self.base()));info=ZipInfo('images/'+'a'*64+'.png');info.external_attr=(0o120777<<16);archive.writestr(info,b'link')
        with self.assertRaises(ValueError):unpack_archive(output.getvalue())
    def test_rejects_bad_hash_invalid_image_and_compression_bomb(self):
        for data in (b'not an image',png()):
            name='images/'+'0'*64+'.png';manifest=self.base();manifest['entries']['100']['image']='backup:'+name
            with self.assertRaises(ValueError):unpack_archive(manifest_zip(manifest,{name:data}))
        import library_unit_pkg.library_backup as module
        with patch.object(module,'MAX_EXPANDED',10):
            with self.assertRaisesRegex(ValueError,'too_large'):unpack_archive(manifest_zip(self.base()))
    def test_corrupted_archive_is_rejected(self):
        with self.assertRaises(ValueError):unpack_archive(b'garbage')
