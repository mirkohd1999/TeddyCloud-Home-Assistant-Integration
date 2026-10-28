"""TeddyCloud MQTT media player (read only)."""
import json
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature, MediaPlayerState
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.core import callback
from .library import SIGNAL_CHANGED
from .availability import Availability
from homeassistant.helpers.event import async_call_later
from .online_catalog import RETRY
from .artwork_archive import ArtworkArchive
from .const import (DOMAIN, CONF_BOX_NAME, CONF_BOX_COLOR, CONF_CATALOG, CONF_FALLBACK_COVER, DEFAULT_COLOR)


def mqtt_text(payload):
    """HA versions and MQTT callbacks may deliver bytes or text."""
    if isinstance(payload, (bytes, bytearray, memoryview)):
        return bytes(payload).decode('utf-8', errors='replace').strip()
    return str(payload).strip()


def resolved_picture(value, server_url):
    """Replace TeddyCloud's container-local `localhost` with a LAN-reachable host."""
    value = mqtt_text(value) if value is not None else ''
    if not value:
        return None
    try:
        original = urlsplit(value)
        if original.scheme not in ('http', 'https'):
            return value if value.startswith('/local/') else None
        if original.hostname not in ('localhost', '127.0.0.1', '::1'):
            return value
        host = urlsplit(server_url.strip().rstrip('/'))
        if host.scheme not in ('http', 'https') or not host.netloc:
            return None
        return urlunsplit((host.scheme, host.netloc, original.path, original.query, ''))
    except ValueError:
        return None


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([hass.data[DOMAIN][entry.entry_id]])


class BoxPlayer(MediaPlayerEntity):
    _attr_should_poll = False
    _attr_supported_features = MediaPlayerEntityFeature(0)

    def __init__(self, entry, online_catalog):
        self.entry = entry
        self._online_catalog = online_catalog
        self._archive = None
        self._local_artwork = None
        self._online_result = None
        self._online_audio_id = None
        self._lookup_task = None
        self._catalog_status = 'waiting_for_audio_id'
        self._attr_unique_id = f'{entry.entry_id}_player'
        self._attr_name = entry.data[CONF_BOX_NAME]
        self._values = {}
        self._started = None
        self._was_playing = False
        self._figure_present = None
        self._figure_removed_at = None
        self._library = None
        self._availability = Availability(entry.options.get("offline_timeout", 5))
        self._offline_cancel = None
        self._last_message_at = None

    @property
    def device_info(self):
        return DeviceInfo(identifiers={(DOMAIN, self.entry.unique_id)}, name=self.entry.data[CONF_BOX_NAME], manufacturer='TeddyCloud', model='Toniebox (MQTT)')

    @property
    def capability_attributes(self):
        """Keep static box appearance available when HA omits live attributes."""
        return {
            **(super().capability_attributes or {}),
            'box_color': self.entry.options.get(CONF_BOX_COLOR, self.entry.data.get(CONF_BOX_COLOR, DEFAULT_COLOR)),
        }

    @property
    def available(self):
        return self._availability.online

    @callback
    def note_message(self, retained=False):
        if retained:
            return
        self._availability.received(last_seen=self._values.get('LastSeen'))
        self._last_message_at = datetime.now(timezone.utc).isoformat()
        if self._started is None and self._availability.playback_started is not None:
            elapsed = self._availability.clock() - self._availability.playback_started
            self._started = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - elapsed, timezone.utc)
        self._refresh_availability()

    @callback
    def _refresh_availability(self):
        self._availability.duration = self.media_duration
        if self._offline_cancel:
            self._offline_cancel()
            self._offline_cancel = None
        if self.hass is not None:
            remaining = self._availability.remaining
            if remaining > 0:
                self._offline_cancel = async_call_later(
                    self.hass, remaining, self._mark_offline
                )
            self.async_write_ha_state()

    @callback
    def _mark_offline(self, _now):
        self._offline_cancel = None
        # Re-evaluate the deadline: runtime metadata may have arrived meanwhile.
        # Preserve the last Playback value so repeated ON cannot restart protection.
        self._refresh_availability()

    def receive(self, field, payload, retained=False):
        text = mqtt_text(payload)
        previous = self._values.get(field)
        observation = None
        # Clear active metadata on removal. Archived images remain on disk.
        # Never display the previous figurine as the currently playing one.
        if field == 'ContentAudioId' and text != previous:
            # Title/picture may arrive BEFORE the audio ID via MQTT.
            # Do not erase valid metadata simply because the ID arrived later.
            self._online_result = None
            self._local_artwork = self._archive.lookup(text) if text and self._archive else None
        self._values[field] = text
        self.note_message(retained)
        if field == 'TagValid' and text and not text.startswith('-'):
            self._figure_present = True
            self._figure_removed_at = None
        if field == 'ContentAudioId' and text:
            self._figure_present = True
            self._figure_removed_at = None
        if field == 'ContentAudioId' and not text:
            self._catalog_status = 'waiting_for_audio_id'
            self._values['ContentTitle'] = ''
            self._values['ContentPicture'] = ''
            self._local_artwork = None
            self._online_result = None
            self._figure_present = False
            self._figure_removed_at = datetime.now(timezone.utc)
        if field == 'ContentAudioId' and not text:
            self._online_audio_id = None
            if self._lookup_task and not self._lookup_task.done():
                self._lookup_task.cancel()
            self._started = None
        if field == 'Playback':
            playing = text.upper() in ('ON', '1', 'TRUE', 'PLAYING') and self._figure_present is not False
            if playing and not self._was_playing and not retained:
                self._availability.start_playback()
                self._started = datetime.now(timezone.utc) if self._availability.playback_started is not None else None
            if not playing:
                self._availability.stop_playback(fresh=self._was_playing and not retained)
                self._started = None
            self._was_playing = playing
        if field == 'ContentAudioId' and previous != text:
            self._online_result = None
            self._local_artwork = self._archive.lookup(text) if self._archive else None
            self._online_audio_id = text
            if text and self._was_playing and not retained:
                self._availability.stop_playback()
                self._availability.start_playback()
                self._started = datetime.now(timezone.utc) if self._availability.playback_started is not None else None
            if text and self.hass is not None:
                self._catalog_status = 'loading'
                if self._lookup_task and not self._lookup_task.done():
                    self._lookup_task.cancel()
        if (field == 'ContentAudioId' and not text) or (field == 'TagValid' and text.startswith('-')):
            self._availability.stop_playback(fresh=self._was_playing and not retained)
            self._was_playing = False
            self._started = None
            self._figure_present = False
        self._refresh_availability()
        if self.hass is not None:
            library = self._library
            audio_id = self._values.get('ContentAudioId')
            if library and field == 'ContentAudioId':
                if not text:
                    library.box_cleared(self.entry.entry_id)
                elif library.needs_observation(self.entry.entry_id, text):
                    # A new Audio-ID (or same ID after a removed figure) is
                    # newly collected; simple status repeats won't re-add
                    # a deleted item.
                    current_image = resolved_picture(
                        self._values.get('ContentPicture', ''),
                        self.entry.options.get('teddycloud_url', ''),
                    )
                    observation = self.hass.async_create_task(library.async_seen(
                        self.entry.entry_id, text,
                        title=self._values.get('ContentTitle'),
                        image=current_image,
                        retained=retained,
                        box_color=self.entry.options.get(CONF_BOX_COLOR, self.entry.data.get(CONF_BOX_COLOR, DEFAULT_COLOR)),
                    ))
            elif library and field == 'TagValid' and text.startswith('-'):
                # Removing the tag unlocks the next placement, including the
                # same figure whose library record was deleted previously.
                library.box_cleared(self.entry.entry_id)
            elif library and field in ('ContentTitle', 'ContentPicture') and audio_id:
                if field == 'ContentTitle':
                    self.hass.async_create_task(library.async_metadata(audio_id, title=text))
                elif field == 'ContentPicture':
                    url = resolved_picture(text, self.entry.options.get('teddycloud_url', ''))
                    self.hass.async_create_task(library.async_metadata(audio_id, image=url))
            if field == 'ContentAudioId' and previous != text and text:
                self._lookup_task = self.hass.async_create_task(self._lookup_image(text, observation))
            self.async_write_ha_state()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._library = self.hass.data.get(DOMAIN, {}).get('library')
        if self._library:
            @callback
            def library_changed(audio_id):
                if self._values.get('ContentAudioId') == audio_id:
                    self._refresh_availability()

            self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_CHANGED, library_changed))
        self._archive = self.hass.data.setdefault(DOMAIN, {}).setdefault('artwork_archive', ArtworkArchive(self.hass))
        audio_id = self._values.get('ContentAudioId')
        if audio_id:
            self._online_audio_id = audio_id
            if not self._lookup_task or self._lookup_task.done():
                self._lookup_task = self.hass.async_create_task(self._lookup_image(audio_id))

    async def async_will_remove_from_hass(self):
        """Stop pending catalog requests when the entity is unloaded."""
        if self._offline_cancel:
            self._offline_cancel()
            self._offline_cancel = None
        if self._lookup_task and not self._lookup_task.done():
            self._lookup_task.cancel()
        await super().async_will_remove_from_hass()

    async def _lookup_image(self, audio_id, observation=None):
        """Wait for collection, then publish metadata before downloading artwork."""
        if observation is not None:
            # A cached catalog hit can finish before async_seen has acquired the
            # library lock. Cancelling a lookup must not cancel collection itself.
            await asyncio.shield(observation)
        while self._online_audio_id == audio_id and self.hass is not None:
            try:
                result = await self._online_catalog.find(audio_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                if self._online_audio_id == audio_id:
                    self._catalog_status = 'error'
                    self.async_write_ha_state()
                return

            if self._online_audio_id != audio_id:
                return
            if result is None and self._online_catalog.failed_at:
                self._catalog_status = 'unavailable'
                self.async_write_ha_state()
                # find() respects its own retry interval. Wait slightly longer
                # before another attempt to avoid hammering catalog servers.
                await asyncio.sleep(RETRY.total_seconds() + 2)
                continue

            self._catalog_status = 'matched' if result else 'audio_id_not_found'
            self._online_result = result
            if self._library and result:
                await self._library.async_metadata(
                    audio_id, title=result.get('catalog_title'),
                    image=result.get('figure'), duration=result.get('duration_seconds'),
                    audio_ids=result.get('audio_ids'),
                )
            self._refresh_availability()
            cached = self._archive.lookup(audio_id) if self._archive else None
            if not cached and result and result.get('figure') and self._archive and self.entry.options.get('online_images', True):
                cached = await self._archive.store(audio_id, result['figure'])
            if self._online_audio_id == audio_id and self.hass is not None:
                self._online_result = result
                self._local_artwork = cached
                if self._library and result:
                    await self._library.async_metadata(
                        audio_id,
                        title=result.get('catalog_title'),
                        image=cached or result.get('figure'),
                        duration=result.get('duration_seconds'),
                        audio_ids=result.get('audio_ids'),
                    )
                self._refresh_availability()
            return

    @property
    def state(self):
        if 'Playback' not in self._values:
            return MediaPlayerState.IDLE
        return MediaPlayerState.PLAYING if self._was_playing else MediaPlayerState.IDLE

    def _metadata(self):
        try:
            catalog = json.loads(self.entry.options.get(CONF_CATALOG, '{}'))
            return catalog.get(self._values.get('ContentAudioId', ''), {})
        except (ValueError, AttributeError, TypeError):
            return {}

    def _known_media_title(self):
        library_title = self._library.custom_metadata(self._values.get('ContentAudioId')) if self._library else {}
        return library_title.get('title') or self._metadata().get('title') or self._values.get('ContentTitle') or ((self._online_result or {}).get('catalog_title') if self._online_audio_id == self._values.get('ContentAudioId') else None)

    @property
    def media_title(self):
        if self._figure_present is False:
            return 'Keine Figur aufgestellt'
        return self._known_media_title() or 'Unbekannter Tonie'

    @property
    def media_duration(self):
        custom = self._library.custom_metadata(self._values.get('ContentAudioId')) if self._library else {}
        duration = custom.get('duration_seconds')
        if isinstance(duration, (int, float)) and not isinstance(duration, bool) and 0 < duration <= 86400:
            return int(duration)
        duration = self._metadata().get('duration_seconds')
        if isinstance(duration, (int, float)) and not isinstance(duration, bool) and 0 < duration <= 86400:
            return int(duration)
        if self._online_audio_id == self._values.get('ContentAudioId'):
            duration = (self._online_result or {}).get('duration_seconds')
            if isinstance(duration, (int, float)) and not isinstance(duration, bool) and 0 < duration <= 86400:
                return int(duration)
        return None

    @property
    def media_image_url(self):
        if self._figure_present is False:
            return None
        manual = self._library.custom_metadata(self._values.get('ContentAudioId')) if self._library else {}
        manual_url = manual.get('image')
        if manual_url:
            valid = resolved_picture(manual_url, self.entry.options.get('teddycloud_url', ''))
            if valid:
                return valid
        custom = self._metadata()
        # User-defined figurine photo overrides catalog; exact Audio-ID match
        # preferred over the book/episode cover reported by TeddyCloud.
        figure = custom.get('figure') or self._local_artwork or ((self._online_result or {}).get('figure') if self.entry.options.get('online_images', True) else None) or (self._archive.lookup(self._values.get('ContentAudioId')) if self._archive else None)
        url = figure or custom.get('cover') or self._values.get('ContentPicture') or self.entry.options.get(CONF_FALLBACK_COVER, '')
        return resolved_picture(url, self.entry.options.get('teddycloud_url', ''))

    @property
    def extra_state_attributes(self):
        return {
            'content_audio_id': self._values.get('ContentAudioId'),
            'media_title_is_fallback': self._figure_present is not False and not bool(self._known_media_title()),
            'box_online': self.available,
            'last_message_received': self._last_message_at,
            'offline_timeout_minutes': self._availability.timeout // 60,
            'availability_source': 'last_seen' if self._availability.last_seen is not None else 'mqtt',
            'playback_protection_remaining': round(self._availability.playback_remaining),
            'figure_present': self._figure_present,
            'figure_removed_at': self._figure_removed_at.isoformat() if self._figure_removed_at else None,
            'volume_level_raw': self._values.get('VolumeLevel'),
            'volume_db': self._values.get('VolumedB'),
            'charger': self._values.get('Charger'),
            'tag_valid': self._values.get('TagValid'),
            'last_seen': self._values.get('LastSeen'),
            'cover_url': self.media_image_url,
            'catalog_match': bool(self._online_result),
            'catalog_status': self._catalog_status,
            'catalog_audio_id': self._online_audio_id,
            'image_source': ('manual_figure' if self._metadata().get('figure') else
                             'local_archive' if self._local_artwork else
                             'online_catalog' if (self._online_result or {}).get('figure') else
                             'teddycloud_cover' if self._values.get('ContentPicture') else 'fallback'),
            'estimated_playback_started': self._started.isoformat() if self._started else None,
            'progress_is_estimate': True,
            'duration_source': ('manual' if self._metadata().get('duration_seconds') else 'online_catalog' if self.media_duration else None),
            'playback_control_available': False,
        }
