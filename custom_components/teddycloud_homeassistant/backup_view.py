"""Admin-only archive transport; uploaded archives never enter public storage."""
from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN
from .library_backup import LibraryBackup, MAX_ARCHIVE


class LibraryBackupView(HomeAssistantView):
    url = '/api/teddycloud_homeassistant/library/backup'
    name = 'api:teddycloud_homeassistant:library_backup'
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    def _manager(self, request):
        user = request.get('hass_user')
        if not user or not user.is_admin:
            raise web.HTTPForbidden()
        data = self.hass.data.get(DOMAIN, {})
        library = data.get('library')
        if not library or library._removed:
            raise web.HTTPServiceUnavailable()
        if 'library_backup' not in data:
            data['library_backup'] = LibraryBackup(self.hass, library)
        return data['library_backup']

    async def get(self, request):
        manager = self._manager(request)
        try:
            body = await manager.async_export()
        except ValueError as err:
            return web.json_response({'error': str(err)}, status=400)
        return web.Response(body=body, content_type='application/zip', headers={
            'Content-Disposition':'attachment; filename="teddycloud-library.zip"',
            'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff'})

    async def post(self, request):
        manager = self._manager(request)
        if request.content_length and request.content_length > MAX_ARCHIVE:
            raise web.HTTPRequestEntityTooLarge(max_size=MAX_ARCHIVE, actual_size=request.content_length)
        # Bound streaming uploads too; do not depend on a Content-Length header.
        chunks, size = [], 0
        async for chunk in request.content.iter_chunked(64 * 1024):
            size += len(chunk)
            if size > MAX_ARCHIVE:
                raise web.HTTPRequestEntityTooLarge(max_size=MAX_ARCHIVE, actual_size=size)
            chunks.append(chunk)
        body = b''.join(chunks)
        try:
            if request.query.get('action') == 'preview':
                result = await manager.async_preview(request['hass_user'].id, body)
            elif request.query.get('action') == 'import':
                mode = request.headers.get('X-TeddyCloud-Mode', 'merge')
                if mode not in {'merge', 'overwrite'}:
                    raise ValueError('invalid_backup')
                result = await manager.async_import(request['hass_user'].id, body,
                    request.headers.get('X-TeddyCloud-Preview', ''), mode == 'overwrite')
            else:
                raise ValueError('invalid_backup')
        except ValueError as err:
            return web.json_response({'error': str(err)}, status=400, headers={'Cache-Control':'no-store'})
        return web.json_response(result, headers={'Cache-Control':'no-store'})


def register_backup_view(hass):
    key = f'{DOMAIN}_backup_view_registered'
    if not hass.data.get(key):
        hass.http.register_view(LibraryBackupView(hass))
        hass.data[key] = True
