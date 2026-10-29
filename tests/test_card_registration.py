"""Card resources follow the installed file and migrate only our own routes."""
import ast
from hashlib import sha256
import logging
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[1]


class TestCardRegistration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        source = ROOT / 'custom_components/teddycloud_homeassistant/card_registration.py'
        tree = ast.parse(source.read_text())
        nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 or (isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) and t.id.isupper() for t in node.targets))]
        self.store = SimpleNamespace(async_save=AsyncMock())
        self.ns = {'__file__':str(source), '__name__':__name__, 'logging':logging, 'Path':Path, 'sha256':sha256, 're':re,
                   'LOVELACE_DATA':'lovelace', 'EVENT_HOMEASSISTANT_STARTED':'started',
                   '_LOGGER':logging.getLogger(__name__), 'Store':lambda *args:self.store,
                   'StaticPathConfig':lambda url, path, cache:SimpleNamespace(url=url,path=path,cache=cache)}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), self.ns)
        self.items = []
        self.resources = SimpleNamespace(loaded=False)
        async def load(): self.resources.loaded = True
        async def update(ident, fields):
            self.assertTrue(self.resources.loaded)
            next(item for item in self.items if item['id'] == ident).update(fields)
        async def create(fields):
            self.assertTrue(self.resources.loaded)
            item = dict(fields, id='created')
            self.items.append(item)
            return item
        self.resources.async_items = lambda:self.items
        self.resources.async_load = AsyncMock(side_effect=load)
        self.resources.async_update_item = AsyncMock(side_effect=update)
        self.resources.async_create_item = AsyncMock(side_effect=create)
        self.lovelace = SimpleNamespace(resources=self.resources, resource_mode='storage')
        self.hass = SimpleNamespace(data={'lovelace':self.lovelace}, is_running=True,
            http=SimpleNamespace(async_register_static_paths=AsyncMock()),
            bus=SimpleNamespace(async_listen_once=Mock()))

    async def register(self): await self.ns['async_register_card'](self.hass)

    async def test_url_includes_installed_content_fingerprint(self):
        body = (ROOT / 'custom_components/teddycloud_homeassistant/teddycloud-homeassistant-card.js').read_bytes()
        build = sha256(body).hexdigest()[:12]
        self.assertEqual(self.ns['CARD_VERSION'], '0.5.10')
        self.assertEqual(self.ns['CARD_URL'], f'/teddycloud-homeassistant/card-v0510.js?v=0.5.10&build={build}')

    async def test_migrate_old_and_cache_busting_urls_preserving_other_resources(self):
        urls = ['/teddycloud-homeassistant/card.js',
                '/teddycloud-homeassistant/card-v057.js?v=0.5.7',
                '/teddycloud-homeassistant/card-v058.js?v=0.5.8&refresh=2',
                '/teddycloud-homeassistant/card-v049.js?manual=1']
        self.items[:] = [dict(id=str(i),url=url,res_type='js') for i,url in enumerate(urls)]
        foreign = {'id':'other','url':'/hacsfiles/Bubble-Card/bubble-card.js','res_type':'module'}
        self.items.append(dict(foreign))
        await self.register()
        for item in self.items[:-1]:
            self.assertEqual(item['url'], self.ns['CARD_URL'])
            self.assertEqual(item['res_type'], 'module')
        self.assertEqual(self.items[-1], foreign)
        self.resources.async_create_item.assert_not_awaited()
        self.store.async_save.assert_not_awaited() # Manual resources are not claimed for deletion.

    async def test_create_only_after_loading_and_do_not_duplicate_on_repeat(self):
        await self.register()
        self.resources.async_load.assert_awaited_once()
        self.resources.async_create_item.assert_awaited_once()
        self.store.async_save.assert_awaited_once_with({'resource_id':'created'})
        await self.register()
        self.assertEqual(len(self.items), 1)
        self.resources.async_create_item.assert_awaited_once()

    async def test_right_url_still_repairs_wrong_resource_type(self):
        self.items[:] = [{'id':'old','url':self.ns['CARD_URL'],'res_type':'js'}]
        await self.register()
        self.assertEqual(self.items[0]['res_type'], 'module')

    async def test_routes_served_without_static_cache_including_previous_version(self):
        await self.register()
        routes = [call.args[0][0] for call in self.hass.http.async_register_static_paths.call_args_list]
        self.assertTrue(any(route.url.endswith('card-v058.js') for route in routes))
        self.assertTrue(any(route.url.endswith('card-v0510.js') for route in routes))
        self.assertTrue(all(route.cache is False for route in routes))

    async def test_only_our_relative_routes_are_migrated(self):
        match = self.ns['is_card_resource']
        for url in ['/local/custom-card.js', 'https://other.test/teddycloud-homeassistant/card.js',
                    '/teddycloud-homeassistant/other.js', '/teddycloud-homeassistant/card-v0510.js/evil', None]:
            self.assertFalse(match(url))
        self.assertTrue(match('/teddycloud-homeassistant/card-v058.js?v=0.5.8&refresh=2'))

    async def test_resources_not_ready_are_retried_on_startup(self):
        self.hass.data.clear()
        self.hass.is_running = False
        await self.register()
        self.hass.bus.async_listen_once.assert_called_once()
        callback = self.hass.bus.async_listen_once.call_args.args[1]
        self.hass.data['lovelace'] = self.lovelace
        await callback(None)
        self.assertEqual(len(self.items), 1)
