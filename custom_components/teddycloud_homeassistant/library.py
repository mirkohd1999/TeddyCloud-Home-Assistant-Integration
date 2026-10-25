"""Persistent Tonie collection shared by all boxes and signed-in HA users.

A figure is collected only after a fresh ContentAudioId transition. Deleting
an entry does not automatically re-add it from asynchronous artwork lookups;
placing the figure again after removal will collect it again.
"""
import asyncio
import base64
import binascii
from datetime import datetime, timezone
from pathlib import Path
import re

from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN

STORE_KEY = "teddycloud_homeassistant.tonie_library"
SIGNAL_CHANGED = f"{DOMAIN}_library_changed"
AUDIO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
MAX_UPLOAD = 2 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def valid_audio_id(value):
    """Only accepted audio IDs may be used as file names or collection keys."""
    return isinstance(value, str) and AUDIO_ID_RE.fullmatch(value) is not None


def validate_upload(data_url):
    """Decode only small raster image data URLs; never accept SVG/HTML."""
    if not isinstance(data_url, str) or len(data_url) > 3_000_000:
        raise ValueError("Bild zu groß (maximal 2 MB)")
    match = re.fullmatch(r"data:(image/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)", data_url)
    if not match:
        raise ValueError("Bitte ein JPG-, PNG- oder WebP-Bild auswählen")
    mime = match.group(1)
    try:
        body = base64.b64decode(match.group(2), validate=True)
    except (ValueError, binascii.Error) as err:
        raise ValueError("Bilddatei konnte nicht gelesen werden") from err
    if len(body) > MAX_UPLOAD or len(body) < 12:
        raise ValueError("Bild muss kleiner als 2 MB sein")
    if not (
        (mime == "image/png" and body.startswith(b"\x89PNG\r\n\x1a\n"))
        or (mime == "image/jpeg" and body.startswith(b"\xff\xd8\xff"))
        or (mime == "image/webp" and body[:4] == b"RIFF" and body[8:12] == b"WEBP")
    ):
        raise ValueError("Ungültige Bilddatei")
    return body, IMAGE_TYPES[mime]


class TonieLibrary:
    """Track once-seen figures, with manual edits persisted in HA storage."""

    def __init__(self, hass):
        self.hass = hass
        self._store = Store(hass, 1, STORE_KEY)
        self._lock = asyncio.Lock()
        self._entries = {}
        self._hidden = set()
        # A box is considered active until ContentAudioId is cleared or changes.
        self._last_ids = {}

    async def async_load(self):
        data = await self._store.async_load() or {}
        entries = data.get("entries", {})
        self._hidden = {key for key in data.get("hidden", []) if valid_audio_id(key)}
        if isinstance(entries, dict):
            self._entries = {
                key: value for key, value in entries.items()
                if valid_audio_id(key) and isinstance(value, dict)
            }

    def entries(self):
        return sorted(
            (dict({"audio_id": key}, **item) for key, item in self._entries.items()),
            key=lambda item: (item.get("title") or item.get("audio_id") or "").casefold(),
        )

    def custom_metadata(self, audio_id):
        item = self._entries.get(audio_id)
        return item.get("custom", {}) if item else {}

    def _notify(self, audio_id):
        async_dispatcher_send(self.hass, SIGNAL_CHANGED, audio_id)

    async def async_seen(self, box_id, audio_id, title=None, image=None, duration=None, retained=False):
        """Collect on a NEW placement; ordinary status replays don't resurrect deletions."""
        if not valid_audio_id(audio_id):
            return
        async with self._lock:
            prev = self._last_ids.get(box_id)
            self._last_ids[box_id] = audio_id
            if prev == audio_id:
                return
            # Keep deliberately deleted figures hidden after restarting HA,
            # until a *new* placement is observed after another figure/removal.
            if audio_id in self._hidden:
                if prev is None and retained:
                    return
                self._hidden.discard(audio_id)
            old = self._entries.get(audio_id)
            if old is None:
                old = {"title": title or "", "image": image or "", "duration_seconds": duration,
                       "first_seen": datetime.now(timezone.utc).isoformat(), "custom": {}}
                self._entries[audio_id] = old
            else:
                if title and not old.get("title"):
                    old["title"] = title
                if image and not old.get("image"):
                    old["image"] = image
                if duration and not old.get("duration_seconds"):
                    old["duration_seconds"] = duration
            old["last_seen"] = datetime.now(timezone.utc).isoformat()
            old["times_seen"] = int(old.get("times_seen") or 0) + 1
            await self._store.async_save({"entries": self._entries, "hidden": sorted(self._hidden)})
        self._notify(audio_id)

    def needs_observation(self, box_id, audio_id):
        return self._last_ids.get(box_id) != audio_id

    def box_cleared(self, box_id):
        """Allow the same figurine to return after removing it from this box."""
        self._last_ids[box_id] = ""

    async def async_metadata(self, audio_id, title=None, image=None, duration=None):
        """Refresh detected metadata only for items still in the collection."""
        async with self._lock:
            item = self._entries.get(audio_id)
            if item is None:
                return
            dirty = False
            for field, value in (("title", title), ("image", image), ("duration_seconds", duration)):
                if value and value != item.get(field):
                    item[field] = value
                    dirty = True
            if not dirty:
                return
            await self._store.async_save({"entries": self._entries, "hidden": sorted(self._hidden)})
        self._notify(audio_id)

    async def async_edit(self, audio_id, title=None, image=None, duration_seconds=None, image_data=None):
        """Save an explicit manual override, including browser-uploaded pictures."""
        if not valid_audio_id(audio_id):
            raise ValueError("Ungültige Audio-ID")
        if title is not None and (not isinstance(title, str) or len(title.strip()) > 200):
            raise ValueError("Titel darf maximal 200 Zeichen haben")
        if image is not None and (
            not isinstance(image, str) or len(image) > 2048 or
            (image.strip() and not (
                image.strip().startswith(("https://", "http://", "/local/"))))
        ):
            raise ValueError("Bildadresse muss http(s) oder /local/ verwenden")
        if duration_seconds is not None and (
            type(duration_seconds) is not int or not 0 <= duration_seconds <= 86400
        ):
            raise ValueError("Laufzeit muss zwischen 0 und 86400 Sekunden liegen")
        # Decode before taking the store lock; never fetch remote URLs on server.
        upload = validate_upload(image_data) if image_data else None
        async with self._lock:
            item = self._entries.get(audio_id)
            if item is None:
                item = {
                    "title": "", "image": "", "duration_seconds": None,
                    "first_seen": datetime.now(timezone.utc).isoformat(),
                    "last_seen": None, "times_seen": 0, "custom": {},
                }
                self._entries[audio_id] = item
            self._hidden.discard(audio_id)
            custom = item.setdefault("custom", {})
            if title is not None:
                custom["title"] = title.strip()
            if image is not None:
                custom["image"] = image.strip()
            if duration_seconds is not None:
                custom["duration_seconds"] = duration_seconds or None
            if upload:
                body, suffix = upload
                directory = Path(self.hass.config.path("www", DOMAIN, "library"))
                directory.mkdir(parents=True, exist_ok=True)
                dest = directory / f"{audio_id}{suffix}"
                await asyncio.to_thread(dest.write_bytes, body)
                # Changing JPG -> PNG must not leave the obsolete uploaded
                # image behind. Never remove files outside our own directory.
                for other_ext in IMAGE_TYPES.values():
                    if other_ext == suffix:
                        continue
                    previous = directory / f"{audio_id}{other_ext}"
                    if previous.is_file() and not previous.is_symlink():
                        await asyncio.to_thread(previous.unlink)
                custom["image"] = f"/local/{DOMAIN}/library/{dest.name}?v={int(datetime.now(timezone.utc).timestamp() * 1000)}"
            await self._store.async_save({"entries": self._entries, "hidden": sorted(self._hidden)})
        self._notify(audio_id)
        return self._public_entry(audio_id)

    def _public_entry(self, audio_id):
        entry = self._entries[audio_id]
        custom = entry.get("custom", {})
        return {
            "audio_id": audio_id,
            "title": custom.get("title") or entry.get("title") or f"Tonie {audio_id}",
            "image": custom.get("image") or entry.get("image") or "",
            "duration_seconds": custom.get("duration_seconds") or entry.get("duration_seconds"),
            "first_seen": entry.get("first_seen"),
            "last_seen": entry.get("last_seen"),
            "times_seen": entry.get("times_seen", 0),
            "custom": dict(custom),
        }

    def public_entries(self):
        return sorted(
            (self._public_entry(audio_id) for audio_id in self._entries),
            key=lambda item: item["title"].casefold(),
        )

    async def async_delete(self, audio_id):
        async with self._lock:
            if audio_id not in self._entries:
                return
            old = self._entries.pop(audio_id)
            self._hidden.add(audio_id)
            # Own uploaded file only, never delete user-supplied /local/ files.
            image = old.get("custom", {}).get("image", "")
            local_prefix = f"/local/{DOMAIN}/library/"
            if image.startswith(local_prefix):
                filename = image.split("?", 1)[0][len(local_prefix):]
                if filename in {f"{audio_id}{ext}" for ext in IMAGE_TYPES.values()}:
                    path = Path(self.hass.config.path("www", DOMAIN, "library", filename))
                    if path.is_file() and not path.is_symlink():
                        await asyncio.to_thread(path.unlink)
            await self._store.async_save({"entries": self._entries, "hidden": sorted(self._hidden)})
        self._notify(audio_id)
