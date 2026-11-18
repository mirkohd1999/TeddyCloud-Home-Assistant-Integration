"""Portable, bounded library archives with preview and atomic store publication."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import PurePosixPath
import re
import time
import struct
from uuid import uuid4
from zipfile import BadZipFile, ZipFile, ZIP_DEFLATED
from zlib import error as ZlibError

from .image_storage import image_reference, valid_image_bytes, MAX_IMAGE_BYTES
from .library import valid_audio_id

FORMAT = 'teddycloud-library'
VERSION = 1
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
MAX_ENTRIES = 5000
MAX_MANIFEST = 4 * 1024 * 1024


def revision(entries, hidden):
    return sha256(json.dumps([entries, sorted(hidden)], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def image_value(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('invalid_backup')
    if not value or re.fullmatch(r'backup:images/[a-f0-9]{64}\.(?:png|jpg|webp)', value):
        return value
    if value.startswith(('https://', 'http://', '/local/')) and not image_reference(value):
        return value
    raise ValueError('invalid_backup')


def clean_record(raw, custom=False):
    if not isinstance(raw, dict):
        raise ValueError('invalid_backup')
    result = {}
    for field in ('title', 'image', 'duration_seconds', 'color'):
        if field not in raw:
            continue
        value = raw[field]
        if field == 'title':
            if not isinstance(value, str) or len(value) > (200 if custom else 1000):
                raise ValueError('invalid_backup')
        elif field == 'image':
            value = image_value(value)
        elif field == 'duration_seconds':
            if value is not None and (type(value) is not int or not 0 <= value <= 86400):
                raise ValueError('invalid_backup')
        elif not isinstance(value, str) or (value and not re.fullmatch(r'#[a-fA-F0-9]{6}', value)):
            raise ValueError('invalid_backup')
        result[field] = value
    if custom:
        if set(raw) - {'title', 'image', 'duration_seconds', 'color'}:
            raise ValueError('invalid_backup')
        return result
    result['custom'] = clean_record(raw.get('custom', {}), True)
    for field in ('confirmed_audio_ids', 'catalog_audio_ids'):
        values = raw.get(field, [])
        if not isinstance(values, list) or len(values) > MAX_ENTRIES or any(not valid_audio_id(v) for v in values):
            raise ValueError('invalid_backup')
        result[field] = sorted(set(values))
    for field in ('first_seen', 'last_seen'):
        value = raw.get(field)
        if value is not None:
            if not isinstance(value, str) or len(value) > 64:
                raise ValueError('invalid_backup')
            try:
                if datetime.fromisoformat(value).tzinfo is None:
                    raise ValueError
            except ValueError as err:
                raise ValueError('invalid_backup') from err
        result[field] = value
    count = raw.get('times_seen', 0)
    if type(count) is not int or not 0 <= count <= 1_000_000_000:
        raise ValueError('invalid_backup')
    result['times_seen'] = count
    sample = raw.get('preview_url')
    if sample is not None and (not isinstance(sample, str) or not re.fullmatch(r'https://cdn\.tonies\.de/o/audio_samples/[A-Za-z0-9_./%-]+\.(?:mp3|wav|m4a|ogg)', sample, re.IGNORECASE) or '/../' in sample):
        raise ValueError('invalid_backup')
    result['preview_url'] = sample
    source = raw.get('metadata_source')
    if source in ('catalog', 'mqtt'):
        result['metadata_source'] = source
    return result


def pack_archive(entries, hidden, images):
    manifest = {'format': FORMAT, 'version': VERSION, 'entries': entries, 'hidden': sorted(hidden)}
    body = json.dumps(manifest, ensure_ascii=False).encode()
    if len(body) > MAX_MANIFEST or len(entries) > MAX_ENTRIES:
        raise ValueError('backup_too_large')
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('library.json', body)
        for name, data in sorted(images.items()):
            archive.writestr(name, data)
    result = output.getvalue()
    if len(result) > MAX_ARCHIVE or len(body) + sum(map(len, images.values())) > MAX_EXPANDED:
        raise ValueError('backup_too_large')
    return result


def unpack_archive(body):
    if not body or len(body) > MAX_ARCHIVE:
        raise ValueError('backup_too_large')
    try:
        # Bound the central directory before ZipFile allocates objects for it.
        end = body.rfind(b'PK\x05\x06', max(0, len(body) - 65557))
        if end < 0 or end + 22 > len(body):
            raise ValueError('invalid_backup')
        _, disk, directory_disk, disk_count, count, directory_size, offset, comment = struct.unpack_from('<4s4H2LH', body, end)
        if disk or directory_disk or disk_count != count or end + 22 + comment != len(body) or offset + directory_size > end:
            raise ValueError('invalid_backup')
        if count > 2 * MAX_ENTRIES + 1 or directory_size > (2 * MAX_ENTRIES + 1) * 256:
            raise ValueError('backup_too_large')
        with ZipFile(BytesIO(body)) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            if len(infos) > 2 * MAX_ENTRIES + 1 or len(names) != len(set(names)) or 'library.json' not in names:
                raise ValueError('invalid_backup')
            if sum(i.file_size for i in infos) > MAX_EXPANDED:
                raise ValueError('backup_too_large')
            for info in infos:
                if info.flag_bits & 1 or info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('invalid_backup')
                if info.filename != 'library.json' and not re.fullmatch(r'images/[a-f0-9]{64}\.(?:png|jpg|webp)', info.filename):
                    raise ValueError('invalid_backup')
                if info.file_size > (MAX_MANIFEST if info.filename == 'library.json' else MAX_IMAGE_BYTES):
                    raise ValueError('backup_too_large')
            manifest = json.loads(archive.read('library.json'))
            if not isinstance(manifest, dict) or manifest.get('format') != FORMAT or type(manifest.get('version')) is not int or manifest['version'] != VERSION:
                raise ValueError('invalid_backup')
            entries = manifest.get('entries')
            hidden = manifest.get('hidden', [])
            if not isinstance(entries, dict) or len(entries) > MAX_ENTRIES or any(not valid_audio_id(k) for k in entries):
                raise ValueError('invalid_backup')
            if not isinstance(hidden, list) or len(hidden) > MAX_ENTRIES or any(not valid_audio_id(k) for k in hidden) or set(hidden).intersection(entries):
                raise ValueError('invalid_backup')
            entries = {key: clean_record(value) for key, value in entries.items()}
            images = {}
            used = set()
            for item in entries.values():
                for record in (item, item['custom']):
                    if (url := record.get('image', '')).startswith('backup:'):
                        used.add(url[7:])
            if used != set(names) - {'library.json'}:
                raise ValueError('invalid_backup')
            for name in used:
                data = archive.read(name)
                if not valid_image_bytes(data, PurePosixPath(name).suffix) or sha256(data).hexdigest() != PurePosixPath(name).stem:
                    raise ValueError('invalid_backup')
                try:
                    from PIL import Image
                    with Image.open(BytesIO(data)) as image:
                        if image.width * image.height > 16_000_000:
                            raise ValueError('invalid_backup')
                        image.verify()
                except Exception as err:
                    raise ValueError('invalid_backup') from err
                images[name] = data
            return entries, set(hidden), images
    except (BadZipFile, KeyError, TypeError, UnicodeError, json.JSONDecodeError, RuntimeError, NotImplementedError, OSError, EOFError, ZlibError) as err:
        raise ValueError('invalid_backup') from err


def merge_entries(current, incoming, overwrite=False):
    result = deepcopy(current)
    for key, new in incoming.items():
        if key not in result:
            result[key] = deepcopy(new)
            continue
        old = result[key]
        for field, value in new.items():
            if field == 'custom':
                custom = old.setdefault('custom', {})
                for name, content in value.items():
                    if overwrite or not custom.get(name):
                        custom[name] = content
            elif field == 'times_seen':
                old[field] = max(old.get(field) or 0, value)
            elif field in ('first_seen', 'last_seen'):
                stamps = [v for v in (old.get(field), value) if v]
                old[field] = (min(stamps, key=datetime.fromisoformat) if field == 'first_seen' else max(stamps, key=datetime.fromisoformat)) if stamps else None
            elif overwrite or not old.get(field):
                old[field] = deepcopy(value)
    return result


class LibraryBackup:
    def __init__(self, hass, library):
        self.hass = hass
        self.library = library
        self._previews = {}

    async def _portable(self, strict=True):
        library = self.library
        entries = deepcopy(library._entries)
        images = {}
        for item in entries.values():
            # Do not export box IDs, live state, signed URLs or sample audio.
            item.pop('box_last_seen', None)
            for record in (item, item.get('custom', {})):
                ref = image_reference(record.get('image'))
                if ref:
                    result = await library._images.async_read(*ref) if library._images else None
                    if result is None:
                        if strict:
                            raise ValueError('backup_image_missing')
                        record['image'] = ''
                        continue
                    data, _ = result
                    name = f'images/{sha256(data).hexdigest()}{PurePosixPath(ref[1]).suffix}'
                    images[name] = data
                    record['image'] = 'backup:' + name
            # Whitelist stored fields; future versions cannot accidentally export credentials.
        entries = {key: clean_record(value) for key, value in entries.items()}
        return entries, images

    async def async_export(self):
        async with self.library._lock:
            if self.library._removed:
                raise ValueError('not_ready')
            entries, images = await self._portable()
            return await self.hass.async_add_executor_job(pack_archive, entries, self.library._hidden, images)

    async def async_preview(self, user_id, body):
        incoming, hidden, images = await self.hass.async_add_executor_job(unpack_archive, body)
        async with self.library._lock:
            if self.library._removed:
                raise ValueError('not_ready')
            current, _ = await self._portable(strict=False)
            conflicts = []
            for key in sorted(set(incoming).intersection(current)):
                old, new = current[key], incoming[key]
                fields = [field for field in ('title', 'image', 'duration_seconds', 'color', 'confirmed_audio_ids', 'catalog_audio_ids') if field in new and old.get(field) and old[field] != new[field]]
                fields.extend('custom.' + field for field, value in new['custom'].items() if old['custom'].get(field) and old['custom'][field] != value)
                if fields:
                    conflicts.append({'audio_id': key, 'title': new.get('custom', {}).get('title') or new.get('title') or key, 'fields': fields})
            now = time.monotonic()
            self._previews = {k:v for k,v in self._previews.items() if v['until'] > now and v['user'] != user_id}
            if len(self._previews) >= 32:
                raise ValueError('backup_busy')
            token = uuid4().hex
            self._previews[token] = {'user': user_id, 'hash': sha256(body).hexdigest(), 'revision': revision(self.library._entries, self.library._hidden), 'until': now + 600}
            return {'token':token, 'new':len(set(incoming) - set(current)), 'existing':len(set(incoming).intersection(current)), 'conflicts':conflicts, 'images':len(images), 'hidden':len(hidden)}

    async def async_import(self, user_id, body, token, overwrite=False):
        receipt = self._previews.get(token)
        if not receipt or receipt['user'] != user_id or receipt['until'] <= time.monotonic() or receipt['hash'] != sha256(body).hexdigest():
            raise ValueError('backup_preview_expired')
        incoming, hidden, images = await self.hass.async_add_executor_job(unpack_archive, body)
        library = self.library
        async with library._lock:
            if library._removed:
                raise ValueError('not_ready')
            if token not in self._previews:
                raise ValueError('backup_preview_expired')
            if receipt['revision'] != revision(library._entries, library._hidden):
                raise ValueError('backup_library_changed')
            # Compare/merge using portable references, then remap unchanged local images.
            current, _ = await self._portable(strict=False)
            if images and library._images is None:
                raise ValueError('not_ready')
            merged = merge_entries(current, incoming, overwrite)
            new_hidden = (library._hidden | hidden) - set(merged)
            installed = {}
            created = []
            try:
                for key, item in merged.items():
                    for slot in (None, 'custom'):
                        record = item if slot is None else item['custom']
                        url = record.get('image', '')
                        if not url.startswith('backup:'):
                            continue
                        existing_record = library._entries.get(key, {}) if slot is None else library._entries.get(key, {}).get('custom', {})
                        comparable = current.get(key, {}) if slot is None else current.get(key, {}).get('custom', {})
                        if comparable.get('image') == url:
                            record['image'] = existing_record['image']
                            continue
                        name = url[7:]
                        if name not in installed:
                            ident = 'restore_' + uuid4().hex
                            suffix = PurePosixPath(name).suffix
                            created.append(ident)
                            record_url = await library._images.async_write('library', ident, suffix, images[name])
                            installed[name] = record_url
                        record['image'] = installed[name]
                    # Keep local box history; it does not belong in portable archives.
                    if key in library._entries:
                        local = deepcopy(library._entries[key])
                        local.update(item)
                        merged[key] = local
                # The existing library remains live until the complete new snapshot is saved.
                async def publish():
                    await library._store.async_save({'entries':merged, 'hidden':sorted(new_hidden)})
                    library._entries = merged
                    library._hidden = new_hidden
                    self._previews.pop(token, None)
                    library._notify(None)
                save = asyncio.ensure_future(publish())
                try:
                    await asyncio.shield(save)
                except asyncio.CancelledError:
                    await asyncio.shield(save)
                    raise
            except BaseException:
                if library._entries is not merged:
                    for ident in created:
                        await asyncio.shield(library._images.async_delete('library', ident))
                raise
        return {'imported':len(incoming)}
