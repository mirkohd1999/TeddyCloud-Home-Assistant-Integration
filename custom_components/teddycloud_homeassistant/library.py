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

from .const import DOMAIN, CONF_BOX_COLOR, CONF_BOX_NAME, DEFAULT_COLOR

STORE_KEY = "teddycloud_homeassistant.tonie_library"
SIGNAL_CHANGED = f"{DOMAIN}_library_changed"
AUDIO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
MAX_UPLOAD = 2 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
SYSTEM_SOUND_TITLE_RE = re.compile(
    r"^system\s+sounds?(?:\s+[a-z]{2}[-_][a-z]{2})?(?:\s*[-–:]\s*|\s*$)",
    re.IGNORECASE,
)


def is_system_sound_entry(item):
    """Recognize TeddyCloud system labels, not generic words like 'Startup'.

    Inspect detected metadata even when an admin renamed the entry. Keep raw
    records internally: MQTT titles and audio IDs can arrive out of order, so
    later real figure metadata must be able to correct the classification.
    This also filters existing stored sounds without deleting user data.
    """
    title = item.get("title")
    return isinstance(title, str) and bool(SYSTEM_SOUND_TITLE_RE.match(title.strip()))


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
            (dict({"audio_id": key}, **item) for key, item in self._entries.items()
             if not is_system_sound_entry(item)),
            key=lambda item: (item.get("title") or item.get("audio_id") or "").casefold(),
        )

    def custom_metadata(self, audio_id):
        result = {}
        for ident in self._group_ids(audio_id):
            for field, value in self._entries[ident].get("custom", {}).items():
                if value and not result.get(field):
                    result[field] = value
        return result

    def detected_metadata(self, audio_id):
        """Metadata already associated with this exact ID; never infer by title."""
        item = self._entries.get(audio_id, {})
        return {key: item.get(key) for key in ('title', 'image', 'duration_seconds')}

    async def async_mqtt_metadata(self, audio_id, title=None, image=None, is_current=None):
        """Uncorrelated MQTT may fill a blank entry, never rename a known one."""
        async with self._lock:
            if is_current is not None and not is_current():
                return
            item = self._entries.get(audio_id)
            if item is None or item.get('metadata_source') == 'catalog' or not title:
                return
            if item.get('title') and item['title'] != title:
                return
            aliases = set(self._group_ids(audio_id))
            # Replays of another figure's title/image must not create lookalikes.
            for other_id, other in self._entries.items():
                if other_id not in aliases and (
                    other.get('title') == title or (image and other.get('image') == image)
                ):
                    return
            dirty = False
            for key, value in (('title', title), ('image', image)):
                if value and not item.get(key):
                    item[key] = value
                    dirty = True
            if dirty:
                await self._store.async_save({'entries': self._entries, 'hidden': sorted(self._hidden)})
        if dirty:
            self._notify(audio_id)

    def _notify(self, audio_id):
        async_dispatcher_send(self.hass, SIGNAL_CHANGED, audio_id)

    async def async_seen(self, box_id, audio_id, title=None, image=None, duration=None, retained=False, box_color=None):
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
            if not retained:
                old["last_seen"] = datetime.now(timezone.utc).isoformat()
                old["times_seen"] = int(old.get("times_seen") or 0) + 1
                old.setdefault("box_last_seen", {})[box_id] = {
                    "at": old["last_seen"], "color": box_color or DEFAULT_COLOR,
                }
            await self._store.async_save({"entries": self._entries, "hidden": sorted(self._hidden)})
        self._notify(audio_id)

    def needs_observation(self, box_id, audio_id):
        return self._last_ids.get(box_id) != audio_id

    def box_cleared(self, box_id):
        """Allow the same figurine to return after removing it from this box."""
        self._last_ids[box_id] = ""

    async def async_metadata(self, audio_id, title=None, image=None, duration=None, audio_ids=None):
        """Refresh detected metadata only for items still in the collection."""
        async with self._lock:
            item = self._entries.get(audio_id)
            if item is None:
                return
            dirty = item.get('metadata_source') != 'catalog'
            item['metadata_source'] = 'catalog'
            if audio_ids:
                known = sorted({str(value) for value in audio_ids if valid_audio_id(str(value))})
                if audio_id in known and known != item.get("catalog_audio_ids"):
                    item["catalog_audio_ids"] = known
                    dirty = True
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
            for alias in self._group_ids(audio_id):
                if alias != audio_id:
                    self._entries[alias].setdefault("custom", {}).update(custom)
            await self._store.async_save({"entries": self._entries, "hidden": sorted(self._hidden)})
        for alias in self._group_ids(audio_id):
            self._notify(alias)
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

    def _groups(self):
        parents = {key: key for key in self._entries}

        def find(key):
            while parents[key] != key:
                parents[key] = parents[parents[key]]
                key = parents[key]
            return key

        for key, item in self._entries.items():
            for alias in item.get("catalog_audio_ids", []):
                if alias in parents:
                    a, b = find(key), find(alias)
                    parents[max(a, b)] = min(a, b)
        groups = {}
        for key in parents:
            groups.setdefault(find(key), []).append(key)
        return [sorted(ids) for ids in groups.values()]

    def _group_ids(self, audio_id):
        return next((ids for ids in self._groups() if audio_id in ids), [])

    async def async_refresh_catalog(self, catalog):
        """Resolve existing duplicates without requiring every figure to be replayed."""
        for audio_id in list(self._entries):
            result = await catalog.find(audio_id)
            if result:
                await self.async_metadata(
                    audio_id, title=result.get("catalog_title"),
                    image=result.get("figure"), duration=result.get("duration_seconds"),
                    audio_ids=result.get("audio_ids"),
                )

    def public_entries(self):
        combined = []
        latest_by_box = {}
        config_entries = getattr(self.hass, "config_entries", None)
        configs = {entry.entry_id: entry for entry in config_entries.async_entries(DOMAIN)} if config_entries else {}
        for ids in self._groups():
            visible = [key for key in ids if not is_system_sound_entry(self._entries[key])]
            if not visible:
                continue
            # Prefer fields explicitly edited by the user; retain all source records.
            item = self._public_entry(visible[0])
            item["audio_ids"] = ids
            item["times_seen"] = sum(int(self._entries[key].get("times_seen") or 0) for key in visible)
            item["last_seen"] = max((self._entries[key].get("last_seen") or "" for key in visible), default="") or None
            custom = {}
            for key in visible:
                other = self._public_entry(key)
                if not self._entries[visible[0]].get("title") and self._entries[key].get("title"):
                    item["title"] = self._entries[key]["title"]
                for field in ("image", "duration_seconds"):
                    if not item.get(field) and other.get(field):
                        item[field] = other[field]
                for field, value in other["custom"].items():
                    if value and not custom.get(field):
                        custom[field] = value
                for box_id, observation in self._entries[key].get("box_last_seen", {}).items():
                    if observation.get("at", "") > latest_by_box.get(box_id, {}).get("at", ""):
                        latest_by_box[box_id] = dict(observation, audio_id=item["audio_id"])
            item["custom"] = custom
            item.update(custom)
            combined.append(item)
        for item in combined:
            item["last_heard_boxes"] = []
            for box_id, observation in sorted(latest_by_box.items()):
                if observation["audio_id"] != item["audio_id"]:
                    continue
                entry = configs.get(box_id)
                color = entry.options.get(CONF_BOX_COLOR, entry.data.get(CONF_BOX_COLOR, DEFAULT_COLOR)) if entry else observation.get("color", DEFAULT_COLOR)
                name = entry.data.get(CONF_BOX_NAME, "Toniebox") if entry else "Toniebox"
                item["last_heard_boxes"].append({"box_id": box_id, "name": name, "color": color})
        return sorted(combined, key=lambda item: (-item["times_seen"], item["title"].casefold(), item["audio_id"]))

    async def async_delete(self, audio_id):
        for alias in self._group_ids(audio_id):
            await self._async_delete_one(alias)

    async def _async_delete_one(self, audio_id):
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
