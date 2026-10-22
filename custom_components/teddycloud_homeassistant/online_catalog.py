"""Non-scraping image lookup against the community Tonies JSON catalog.

Exact audio ID matching only: no guessed image for ambiguous titles.
"""
import asyncio
import logging
from datetime import timedelta
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)
CATALOG_URL = "https://raw.githubusercontent.com/toniebox-reverse-engineering/tonies-json/release/tonies.json"
REFRESH = timedelta(hours=24)
RETRY = timedelta(hours=1)
MAX_SIZE = 30 * 1024 * 1024

class OnlineCatalog:
    def __init__(self, hass):
        self.hass = hass
        self.items = {}
        self.fetched_at = None
        self.failed_at = None
        self._lock = asyncio.Lock()

    async def find(self, audio_id):
        """Lookup by exact ContentAudioId; do not infer from the title."""
        audio_id = str(audio_id or "").strip()
        if not audio_id:
            return None
        now = dt_util.utcnow()
        if (self.fetched_at is None or now - self.fetched_at > REFRESH) and (self.failed_at is None or now - self.failed_at > RETRY):
            await self.refresh()
        return self.items.get(audio_id)

    async def refresh(self):
        async with self._lock:
            now = dt_util.utcnow()
            if self.fetched_at and now - self.fetched_at < REFRESH:
                return
            if self.failed_at and now - self.failed_at < RETRY:
                return
            try:
                session = async_get_clientsession(self.hass)
                async with asyncio.timeout(30):
                    async with session.get(CATALOG_URL, headers={"Accept": "application/json"}) as response:
                        response.raise_for_status()
                        if response.content_length and response.content_length > MAX_SIZE:
                            raise ValueError("Catalog exceeds allowed size")
                        content = await response.content.read(MAX_SIZE + 1)
                        if len(content) > MAX_SIZE:
                            raise ValueError("Catalog exceeds allowed size")
                        import json
                        data = json.loads(content)
                if not isinstance(data, list):
                    raise ValueError("Catalog format is not a list")
                new_items = {}
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    pic = entry.get("pic")
                    if not isinstance(pic, str) or not pic.startswith("https://"):
                        continue
                    ids = entry.get("audio_id") or []
                    if not isinstance(ids, list):
                        ids = [ids]
                    for aid in ids:
                        key = str(aid).strip()
                        if key and key not in new_items:
                            new_items[key] = {"figure": pic, "catalog_title": str(entry.get("title") or "")}
                self.items = new_items
                self.fetched_at = dt_util.utcnow()
                self.failed_at = None
                _LOGGER.info("TeddyCloud image catalog loaded: %s audio IDs", len(new_items))
            except Exception as err:
                # Catalog availability must never interrupt MQTT updates.
                self.failed_at = dt_util.utcnow()
                _LOGGER.warning("Online Tonie image catalog unavailable: %s", err)
