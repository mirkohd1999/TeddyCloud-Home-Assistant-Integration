"""Exercise library handlers in isolation, without installing Home Assistant."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock


class LibraryPermissionsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / 'custom_components/teddycloud_homeassistant/library_websocket.py'
        tree = ast.parse(source.read_text())
        handlers = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
                    and node.name in ('ws_library_save', 'ws_library_delete')]
        # Test real handler bodies; HA authentication decorators are outside this unit test.
        for handler in handlers:
            handler.decorator_list = []
        self.library = SimpleNamespace(async_edit=AsyncMock(return_value={}), async_delete=AsyncMock())
        self.handlers = {'get_library': lambda hass: self.library}
        exec(compile(ast.Module(body=handlers, type_ignores=[]), str(source), 'exec'), self.handlers)

    def connection(self, admin):
        return SimpleNamespace(user=SimpleNamespace(is_admin=admin), send_error=Mock(), send_result=Mock())

    async def test_non_admin_cannot_save_or_upload(self):
        connection = self.connection(False)
        await self.handlers['ws_library_save'](None, connection, {
            'id': 1, 'audio_id': '123', 'title': 'Changed', 'image_data': 'upload',
        })
        self.library.async_edit.assert_not_awaited()
        self.assertEqual(connection.send_error.call_args.args[1], 'unauthorized')

    async def test_admin_can_save_and_upload(self):
        connection = self.connection(True)
        await self.handlers['ws_library_save'](None, connection, {
            'id': 1, 'audio_id': '123', 'title': 'Changed', 'image_data': 'upload',
        })
        self.library.async_edit.assert_awaited_once_with('123', title='Changed', image=None,
                                                      duration_seconds=None, image_data='upload')
        connection.send_error.assert_not_called()

    async def test_missing_user_cannot_save(self):
        connection = self.connection(False)
        connection.user = None
        await self.handlers['ws_library_save'](None, connection, {'id': 1, 'audio_id': '123'})
        self.library.async_edit.assert_not_awaited()
        self.assertEqual(connection.send_error.call_args.args[1], 'unauthorized')

    async def test_both_roles_can_delete(self):
        for admin in (False, True):
            with self.subTest(admin=admin):
                self.library.async_delete.reset_mock()
                connection = self.connection(admin)
                await self.handlers['ws_library_delete'](None, connection, {'id': 1, 'audio_id': '123'})
                self.library.async_delete.assert_awaited_once_with('123')
                connection.send_error.assert_not_called()
