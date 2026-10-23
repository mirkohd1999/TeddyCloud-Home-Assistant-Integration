"""Non-scraping image lookup against the community Tonies JSON catalog.

Exact audio ID matching only: no guessed image for ambiguous titles.
"""
import asyncio
import logging
import json
from datetime import timedelta
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)
CATALOG_SOURCES = [
    ("v2", "https://raw.githubusercontent.com/toniebox-reverse-engineering/tonies-json/release/toniesV2.json"),
    ("v2", "https://cdn.jsdelivr.net/gh/toniebox-reverse-engineering/tonies-json@release/toniesV2.json"),
    ("v1", "https://raw.githubusercontent.com/toniebox-reverse-engineering/tonies-json/release/tonies.json"),
]
REFRESH = timedelta(hours=24)
RETRY = timedelta(minutes=10)
MAX_SIZE = 60 * 1024 * 1024

def duration_seconds(entry):
    """Read explicit durations only; never guess length from a track list."""
    seconds = entry.get("duration_seconds")
    if isinstance(seconds, (int, float)) and not isinstance(seconds, bool):
        return int(seconds) if 0 < seconds <= 86400 else None
    minutes = entry.get("runtime")
    if isinstance(minutes, (int, float)) and not isinstance(minutes, bool):
        return round(minutes * 60) if 0 < minutes <= 1440 else None
    return None


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
                errors = []
                for kind, url in CATALOG_SOURCES:
                    try:
                        async with asyncio.timeout(45):
                            async with session.get(url, headers={"Accept": "application/json"}) as response:
                                response.raise_for_status()
                                if response.content_length and response.content_length > MAX_SIZE:
                                    raise ValueError("Catalog exceeds allowed size")
                                content = await response.content.read(MAX_SIZE + 1)
                                if len(content) > MAX_SIZE:
                                    raise ValueError("Catalog exceeds allowed size")
                        try:
                            data = json.loads(content)
                        except json.JSONDecodeError as exc:
                            raise ValueError(
                                f"Invalid/incomplete JSON ({len(content)} bytes; "
                                f"error at byte/character {exc.pos}): {exc.msg}"
                            ) from exc
                        if not isinstance(data, list):
                            raise ValueError("Catalog must contain a list")
                        new_items = {}
                        if kind == "v2":
                            for article in data:
                                if not isinstance(article, dict):
                                    continue
                                for entry in article.get("data", []):
                                    if not isinstance(entry, dict):
                                        continue
                                    pic = entry.get("image")
                                    if not isinstance(pic, str) or not pic.startswith(("https://", "http://")):
                                        pic = None
                                    length = duration_seconds(entry)
                                    series = str(entry.get("series") or "").strip()
                                    episode = str(entry.get("episode") or "").strip()
                                    title = " - ".join(filter(None, (series, episode)))
                                    for ident in entry.get("ids", []):
                                        if not isinstance(ident, dict):
                                            continue
                                        aid = str(ident.get("audio-id") or "").strip()
                                        if aid.isdecimal():
                                            new_items[aid] = {"figure": pic, "catalog_title": title, "duration_seconds": length}
                        else:
                            # Older catalog has artwork but no runtime.
                            for entry in data:
                                if not isinstance(entry, dict):
                                    continue
                                pic = entry.get("pic")
                                if not isinstance(pic, str) or not pic.startswith(("https://", "http://")):
                                    pic = None
                                audio_ids = entry.get("audio_id") or []
                                if not isinstance(audio_ids, list):
                                    audio_ids = [audio_ids]
                                for ident in audio_ids:
                                    aid = str(ident).strip()
                                    if aid.isdecimal():
                                        new_items[aid] = {
                                            "figure": pic,
                                            "catalog_title": str(entry.get("title") or ""),
                                            "duration_seconds": None,
                                        }
                        if not new_items:
                            raise ValueError("Catalog contains no audio IDs")
                        self.items = new_items
                        self.fetched_at = dt_util.utcnow()
                        self.failed_at = None
                        _LOGGER.info("TeddyCloud %s catalog loaded: %s audio IDs", kind, len(new_items))
                        return
                    except Exception as err:
                        errors.append(f"{kind} {url}: {type(err).__name__}: {err}")
                        _LOGGER.warning("TeddyCloud catalog source failed: %s", errors[-1])
                raise ValueError("All catalog sources failed: " + " | ".join(errors))
            except Exception as err:
                # Catalog availability must never interrupt MQTT updates.
                self.failed_at = dt_util.utcnow()
                _LOGGER.warning("Online Tonie image catalog unavailable: %s", err)
