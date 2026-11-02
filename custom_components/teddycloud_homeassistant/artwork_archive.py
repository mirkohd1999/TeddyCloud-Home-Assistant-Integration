"""Small persistent artwork archive for recognized Tonies.

Files remain in private storage after a restart. Lookup only reads the in-memory
index; authenticated image reads and writes run in HA's executor.
"""
import asyncio
import logging
from urllib.parse import urlsplit

from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
MAX_IMAGE_BYTES = 3 * 1024 * 1024
ALLOWED_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


class ArtworkArchive:
    def __init__(self, hass, images):
        self.hass = hass
        self.images = images
        self._tasks = {}

    def lookup(self, audio_id):
        """Return local artwork URL if the ID has a cached image."""
        key = str(audio_id or "").strip()
        if not key.isdecimal():
            return None
        return self.images.lookup("figures", key)

    async def store(self, audio_id, url):
        """Cache an image by exact audio ID. Never replace an existing image."""
        key = str(audio_id or "").strip()
        if not key.isdecimal() or not isinstance(url, str):
            return None
        if self.lookup(key):
            return self.lookup(key)
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname:
            return None
        # Avoid parallel duplicate downloads for multiple boxes.
        if key in self._tasks:
            return await asyncio.shield(self._tasks[key])
        task = self.hass.async_create_task(self._download(key, url))
        self._tasks[key] = task
        def finished(completed):
            if self._tasks.get(key) is completed:
                self._tasks.pop(key, None)
        task.add_done_callback(finished)
        return await asyncio.shield(task)

    async def _download(self, key, url):
        try:
            session = async_get_clientsession(self.hass)
            async with asyncio.timeout(15):
                async with session.get(url, allow_redirects=False) as resp:
                    if resp.status != 200:
                        return None
                    media_type = resp.headers.get("Content-Type", "").split(";")[0].lower().strip()
                    ext = ALLOWED_TYPES.get(media_type)
                    if not ext or (resp.content_length and resp.content_length > MAX_IMAGE_BYTES):
                        return None
                    chunks = []
                    size = 0
                    async for chunk in resp.content.iter_chunked(32 * 1024):
                        size += len(chunk)
                        if size > MAX_IMAGE_BYTES:
                            return None
                        chunks.append(chunk)
                    data = b"".join(chunks)
            if not data:
                return None
            return await self.images.async_write("figures", key, ext, data)
        except Exception as err:
            _LOGGER.debug("Tonie artwork cache unavailable for audio ID %s: %s", key, err)
            return None


    async def async_shutdown(self):
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
