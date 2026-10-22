"""Read-only player representing the state reported by TeddyCloud MQTT."""
import json
from datetime import datetime, timezone
from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature, MediaPlayerState
from homeassistant.helpers.entity import DeviceInfo
from .const import (DOMAIN, CONF_PREFIX, CONF_BOX_ID, CONF_BOX_NAME, CONF_BOX_COLOR,
                    CONF_CATALOG, CONF_FALLBACK_COVER, DEFAULT_COLOR)

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([hass.data[DOMAIN][entry.entry_id]])

class BoxPlayer(MediaPlayerEntity):
    _attr_should_poll = False
    _attr_supported_features = MediaPlayerEntityFeature(0)

    def __init__(self, entry):
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_player"
        self._attr_name = f"{entry.data[CONF_BOX_NAME]} Now Playing"
        self._values = {}
        self._started = None
        self._was_playing = False

    @property
    def device_info(self):
        return DeviceInfo(identifiers={(DOMAIN, self.entry.unique_id)}, name=self.entry.data[CONF_BOX_NAME], manufacturer="TeddyCloud", model="MQTT box monitor")

    def receive(self, field, payload):
        self._values[field] = str(payload)
        if field == "Playback":
            playing = str(payload).strip().upper() in ("ON", "1", "TRUE", "PLAYING")
            if playing and not self._was_playing:
                self._started = datetime.now(timezone.utc)
            if not playing:
                self._started = None
            self._was_playing = playing
        if field == "ContentAudioId" and self._was_playing:
            self._started = datetime.now(timezone.utc)
        if self.platform is not None:
            self.async_write_ha_state()

    @property
    def state(self):
        if "Playback" not in self._values:
            return MediaPlayerState.IDLE
        return MediaPlayerState.PLAYING if self._was_playing else MediaPlayerState.IDLE

    def _metadata(self):
        try:
            catalog = json.loads(self.entry.options.get(CONF_CATALOG, "{}"))
            return catalog.get(self._values.get("ContentAudioId", ""), {})
        except (ValueError, AttributeError):
            return {}

    @property
    def media_title(self):
        return self._metadata().get("title") or self._values.get("ContentTitle") or "Unbekannter Tonie"

    @property
    def media_duration(self):
        duration = self._metadata().get("duration_seconds")
        return duration if isinstance(duration, (int, float)) and duration > 0 else None

    @property
    def extra_state_attributes(self):
        return {
            "content_audio_id": self._values.get("ContentAudioId"),
            "volume_level_raw": self._values.get("VolumeLevel"),
            "volume_db": self._values.get("VolumedB"),
            "charger": self._values.get("Charger"),
            "tag_valid": self._values.get("TagValid"),
            "last_seen": self._values.get("LastSeen"),
            "box_color": self.entry.options.get(CONF_BOX_COLOR, DEFAULT_COLOR),
            "fallback_cover": self.entry.options.get(CONF_FALLBACK_COVER, ""),
            "cover_url": self._metadata().get("cover", ""),
            "estimated_playback_started": self._started.isoformat() if self._started else None,
            "progress_is_estimate": True,
            "playback_control_available": False,
        }
