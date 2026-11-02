"""Authenticated image endpoint. The frontend obtains short-lived signed paths."""
from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN
from .image_storage import IMAGE_PREFIX


class PrivateImageView(HomeAssistantView):
    url = IMAGE_PREFIX + "{kind}/{filename}"
    name = "api:teddycloud_homeassistant:images"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request, kind, filename):
        images = self.hass.data.get(DOMAIN, {}).get("images")
        result = await images.async_read(kind, filename) if images else None
        if result is None:
            raise web.HTTPNotFound()
        body, content_type = result
        return web.Response(body=body, content_type=content_type, headers={
            "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        })


def register_image_view(hass):
    key = f"{DOMAIN}_image_view_registered"
    if not hass.data.get(key):
        hass.http.register_view(PrivateImageView(hass))
        hass.data[key] = True
