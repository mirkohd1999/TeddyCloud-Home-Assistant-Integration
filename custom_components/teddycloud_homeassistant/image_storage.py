"""Private image files; every filesystem operation runs in HA's executor."""
import asyncio
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit
from uuid import uuid4

IMAGE_PREFIX = "/api/teddycloud_homeassistant/images/"
LEGACY_PREFIX = "/local/teddycloud_homeassistant/"
KINDS = {"figures", "library"}
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}
MAX_IMAGE_BYTES = 3 * 1024 * 1024
FILENAME = re.compile(r"[A-Za-z0-9_-]{1,80}\.(?:png|jpg|webp)")


def image_reference(url):
    """Parse only our private or previous public relative image routes."""
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme or parts.netloc:
        return None
    prefix = next((p for p in (IMAGE_PREFIX, LEGACY_PREFIX) if parts.path.startswith(p)), None)
    if prefix is None:
        return None
    bits = parts.path[len(prefix):].split("/")
    if len(bits) != 2 or bits[0] not in KINDS or not FILENAME.fullmatch(bits[1]):
        return None
    return bits[0], bits[1]


def valid_image_bytes(data, suffix):
    """Bounded format checks without decoding or trusting an extension alone."""
    if not 16 <= len(data) <= MAX_IMAGE_BYTES:
        return False
    if suffix == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n") and data.endswith(bytes.fromhex("0000000049454e44ae426082"))
    if suffix == ".jpg":
        return data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")
    if suffix == ".webp":
        return data.startswith(b"RIFF") and data[8:12] == b"WEBP" and int.from_bytes(data[4:8], "little") + 8 == len(data)
    return False


class ImageStorage:
    """Memory-only lookup, executor-backed migration/read/write/delete."""

    def __init__(self, hass):
        self.hass = hass
        self.root = Path(hass.config.path(".storage", "teddycloud_homeassistant", "images"))
        self.legacy = Path(hass.config.path("www", "teddycloud_homeassistant"))
        self.generation = uuid4().hex
        self._index = {}
        self._lock = asyncio.Lock()
        self._removed = False

    async def _executor(self, function, *args):
        # Executor jobs cannot be stopped by cancelling the awaiting coroutine.
        # Keep the storage lock until the worker finishes, so uninstall cannot
        # race a still-running write which recreates the directory afterwards.
        job = asyncio.ensure_future(self.hass.async_add_executor_job(function, *args))
        try:
            return await asyncio.shield(job)
        except asyncio.CancelledError:
            await asyncio.shield(job)
            raise

    def _directory(self, kind, create=False):
        """Executor only. Refuse symlinked integration-owned directories."""
        if kind not in KINDS:
            raise ValueError("Invalid image kind")
        directory = self.root / kind
        for parent in (self.root.parent, self.root, directory):
            if parent.is_symlink():
                raise OSError("Refusing symlinked image directory")
        if create:
            directory.mkdir(parents=True, exist_ok=True)
        return directory

    @staticmethod
    def _read_file(path):
        """Executor only; never follow an image symlink or read oversized files."""
        if path.is_symlink() or not path.is_file():
            return None
        if not 16 <= path.stat().st_size <= MAX_IMAGE_BYTES:
            return None
        with path.open("rb") as source:
            data = source.read(MAX_IMAGE_BYTES + 1)
        return data if valid_image_bytes(data, path.suffix) else None

    def _record(self, kind, path):
        """Executor only; the returned mapping is installed on the event loop."""
        version = path.stat().st_mtime_ns
        return (kind, path.name), f"{IMAGE_PREFIX}{kind}/{path.name}?v={version}"

    def _initialize(self):
        """Executor only. Move old owned files out of publicly served www."""
        index = {}
        for kind in sorted(KINDS):
            directory = self._directory(kind, create=True)
            legacy = self.legacy / kind
            if not self.legacy.is_symlink() and not legacy.is_symlink() and legacy.is_dir():
                for old in legacy.iterdir():
                    if not FILENAME.fullmatch(old.name) or old.is_symlink() or not old.is_file():
                        continue
                    destination = directory / old.name
                    if destination.exists() or destination.is_symlink():
                        # Preserve both copies on retry or rollback; backups are
                        # private and never part of the HTTP image index.
                        backup = self.root / "migration-backups"
                        if backup.is_symlink():
                            raise OSError("Refusing symlinked migration backup")
                        backup.mkdir(exist_ok=True)
                        destination = backup / f"{uuid4().hex}-{old.name}"
                    # shutil.move also supports a network-mounted www on a
                    # different filesystem. Corrupt images are preserved too,
                    # but will not be indexed or served as images.
                    shutil.move(str(old), str(destination))
                try:
                    legacy.rmdir()
                except OSError:
                    pass  # Preserve unrelated user files.
            for path in directory.iterdir():
                if FILENAME.fullmatch(path.name) and self._read_file(path) is not None:
                    key, url = self._record(kind, path)
                    index[key] = url
        if not self.legacy.is_symlink():
            try:
                self.legacy.rmdir()
            except OSError:
                pass
        return index

    async def async_initialize(self):
        async with self._lock:
            if self._removed:
                raise ValueError("Bildspeicher nicht bereit")
            self._index = await self._executor(self._initialize)

    def lookup(self, kind, audio_id):
        """Pure in-memory lookup, safe for MQTT callbacks and entity properties."""
        if self._removed:
            return None
        key = str(audio_id or "").strip()
        for suffix in IMAGE_TYPES:
            url = self._index.get((kind, f"{key}{suffix}"))
            if url:
                return url
        return None

    def private_url(self, value):
        """Rewrite previous owned URLs without probing the filesystem."""
        reference = image_reference(value)
        if reference is None:
            return value
        return self._index.get(reference) or f"{IMAGE_PREFIX}{reference[0]}/{reference[1]}"

    def _write(self, kind, audio_id, suffix, body):
        directory = self._directory(kind, create=True)
        target = directory / f"{audio_id}{suffix}"
        if target.is_symlink():
            raise OSError("Refusing image symlink")
        temp = directory / f".{uuid4().hex}.tmp"
        try:
            temp.write_bytes(body)
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)
        removed = []
        for other in IMAGE_TYPES:
            if other != suffix:
                path = directory / f"{audio_id}{other}"
                if not path.is_symlink() and path.is_file():
                    path.unlink()
                    removed.append((kind, path.name))
        return self._record(kind, target), removed

    async def async_write(self, kind, audio_id, suffix, body):
        if kind not in KINDS or not FILENAME.fullmatch(f"{audio_id}{suffix}") or not valid_image_bytes(body, suffix):
            raise ValueError("Ungültige Bilddatei")
        async with self._lock:
            if self._removed:
                raise ValueError("Bildspeicher nicht bereit")
            (key, url), removed = await self._executor(self._write, kind, audio_id, suffix, body)
            for previous in removed:
                self._index.pop(previous, None)
            self._index[key] = url
            return url

    def _read(self, kind, filename):
        directory = self._directory(kind)
        path = directory / filename
        data = self._read_file(path)
        return (data, IMAGE_TYPES[path.suffix]) if data is not None else None

    async def async_read(self, kind, filename):
        if kind not in KINDS or not isinstance(filename, str) or not FILENAME.fullmatch(filename):
            return None
        if self._removed or (kind, filename) not in self._index:
            return None
        try:
            return await self._executor(self._read, kind, filename)
        except OSError:
            return None

    def _delete(self, kind, audio_id):
        directory = self._directory(kind)
        removed = []
        for suffix in IMAGE_TYPES:
            path = directory / f"{audio_id}{suffix}"
            if not path.is_symlink() and path.is_file():
                path.unlink()
            removed.append((kind, path.name))
        return removed

    async def async_delete(self, kind, audio_id):
        if kind not in KINDS or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", str(audio_id)):
            return
        async with self._lock:
            if self._removed:
                return
            removed = await self._executor(self._delete, kind, audio_id)
            for key in removed:
                self._index.pop(key, None)

    def _cleanup_all(self):
        """Executor only: remove our private namespace, including uploads/backups."""
        owned = self.root.parent
        if owned.is_symlink():
            raise OSError("Refusing symlinked integration storage")
        if owned.is_dir():
            shutil.rmtree(owned)
        # Normally migration has already removed these files. Also clean
        # matching old files on uninstall, while preserving unrelated www data.
        if not self.legacy.is_symlink():
            for kind in KINDS:
                directory = self.legacy / kind
                if directory.is_symlink() or not directory.is_dir():
                    continue
                for path in directory.iterdir():
                    if FILENAME.fullmatch(path.name) and not path.is_symlink() and path.is_file():
                        path.unlink()
                try:
                    directory.rmdir()
                except OSError:
                    pass
            try:
                self.legacy.rmdir()
            except OSError:
                pass

    async def async_remove(self):
        async with self._lock:
            self._removed = True
            await self._executor(self._cleanup_all)
            self._index.clear()
