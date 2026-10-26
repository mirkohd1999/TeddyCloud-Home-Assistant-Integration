"""Non-scraping image lookup against the community Tonies JSON catalog.

Exact audio ID matching only: no guessed image for ambiguous titles.
"""
import asyncio
import logging
import json
from datetime import timedelta
import re
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)
CATALOG_SOURCES = [
    ("v2", "https://raw.githubusercontent.com/toniebox-reverse-engineering/tonies-json/release/toniesV2.json"),
    ("v2", "https://cdn.jsdelivr.net/gh/toniebox-reverse-engineering/tonies-json@release/toniesV2.json"),
    ("v1", "https://raw.githubusercontent.com/toniebox-reverse-engineering/tonies-json/release/tonies.json"),
]
REFRESH = timedelta(hours=24)
RETRY = timedelta(seconds=20)
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

    async def _download_json(self, session, url):
        """Read valid JSON; retry truncated responses using HTTP byte ranges."""
        headers = {"Accept": "application/json", "Accept-Encoding": "identity",
                   "Cache-Control": "no-cache"}
        async with asyncio.timeout(45):
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                if response.content_length and response.content_length > MAX_SIZE:
                    raise ValueError("Catalog exceeds allowed size")
                # aiohttp read(n) may return only the first available bytes.
                # Read every chunk until EOF instead of parsing partial JSON.
                chunks = []
                size = 0
                async for chunk in response.content.iter_chunked(64 * 1024):
                    size += len(chunk)
                    if size > MAX_SIZE:
                        raise ValueError("Catalog exceeds allowed size")
                    chunks.append(chunk)
                content = b"".join(chunks)
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            _LOGGER.warning(
                "Tonie catalog JSON incomplete (%s bytes, error at %s); attempting HTTP Range recovery",
                len(content), exc.pos
            )
        # Raw/CDN endpoints may support ranged downloads even when a full
        # response is truncated by a reverse proxy. Never append a server's
        # 200 full response to an existing range.
        part_size = 32768
        offset = 0
        parts = []
        total = None
        async with asyncio.timeout(120):
            while total is None or offset < total:
                end = offset + part_size - 1
                hdrs = dict(headers, Range=f"bytes={offset}-{end}")
                async with session.get(url, headers=hdrs) as response:
                    if response.status != 206:
                        raise ValueError(
                            f"Range recovery unsupported: HTTP {response.status}"
                        )
                    match = re.fullmatch(
                        r"bytes ([0-9]+)-([0-9]+)/([0-9]+)",
                        response.headers.get("Content-Range", ""),
                    )
                    if not match:
                        raise ValueError("Missing valid Content-Range")
                    start, finish, length = map(int, match.groups())
                    if start != offset or finish < start or length > MAX_SIZE:
                        raise ValueError("Inconsistent HTTP range")
                    if total is not None and total != length:
                        raise ValueError("HTTP resource changed during download")
                    total = length
                    chunk = await response.read()
                    if len(chunk) != finish - start + 1:
                        raise ValueError("Truncated HTTP range")
                    parts.append(chunk)
                    offset = finish + 1
        return json.loads(b"".join(parts))

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
                        data = await self._download_json(session, url)
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
                                            new_items[aid] = {"figure": pic, "catalog_title": title, "duration_seconds": length, "audio_ids": sorted({str(i.get("audio-id")) for i in entry.get("ids", []) if isinstance(i, dict) and str(i.get("audio-id", "")).isdecimal()})}
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
                                            "audio_ids": [str(i) for i in audio_ids if str(i).isdecimal()],
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
