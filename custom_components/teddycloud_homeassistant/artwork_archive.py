"""Small persistent artwork archive for recognized Tonies.

Files remain on Home Assistant's local disk after a restart and are served from
/local/. No bulk redistribution of third-party artwork.
"""
import asyncio
import logging
from pathlib import Path
from urllib.parse import urlsplit

from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
MAX_IMAGE_BYTES = 3 * 1024 * 1024
ALLOWED_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def valid_image_file(path):
    """Reject incomplete cached files (especially truncated PNG/JPEG/WebP)."""
    try:
        size = path.stat().st_size
        if not 16 <= size <= MAX_IMAGE_BYTES:
            return False
        with path.open("rb") as file:
            header = file.read(16)
            file.seek(max(0, size - 16))
            tail = file.read()
        if path.name.endswith(".png") or path.name.endswith(".png.tmp"):
            return header.startswith(bytes.fromhex("89504e470d0a1a0a")) and tail.endswith(bytes.fromhex("0000000049454e44ae426082"))
        if path.name.endswith(".jpg") or path.name.endswith(".jpg.tmp"):
            return header.startswith(bytes.fromhex("ffd8")) and tail.endswith(bytes.fromhex("ffd9"))
        if path.name.endswith(".webp") or path.name.endswith(".webp.tmp"):
            return header.startswith(b"RIFF") and header[8:12] == b"WEBP" and int.from_bytes(header[4:8], "little") + 8 == size
    except OSError:
        return False
    return False


class ArtworkArchive:
    def __init__(self, hass):
        self.hass = hass
        self.path = Path(hass.config.path("www", "teddycloud_homeassistant", "figures"))
        self._tasks = {}

    def lookup(self, audio_id):
        """Return local artwork URL if the ID has a cached image."""
        key = str(audio_id or "").strip()
        if not key.isdecimal():
            return None
        for extension in ALLOWED_TYPES.values():
            candidate = self.path / f"{key}{extension}"
            if candidate.is_file() and valid_image_file(candidate):
                return f"/local/teddycloud_homeassistant/figures/{key}{extension}?v={candidate.stat().st_mtime_ns}"
        return None

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
            return await self._tasks[key]
        task = self.hass.async_create_task(self._download(key, url))
        self._tasks[key] = task
        try:
            return await task
        finally:
            if self._tasks.get(key) is task:
                self._tasks.pop(key, None)

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
            await asyncio.to_thread(self._write, key, ext, data)
            return self.lookup(key)
        except Exception as err:
            _LOGGER.debug("Tonie artwork cache unavailable for audio ID %s: %s", key, err)
            return None

    def _write(self, key, ext, data):
        self.path.mkdir(parents=True, exist_ok=True)
        target = self.path / f"{key}{ext}"
        if not valid_image_file(target):
            temp = target.with_suffix(target.suffix + ".tmp")
            temp.write_bytes(data)
            if valid_image_file(temp):
                temp.replace(target)
            else:
                temp.unlink(missing_ok=True)
