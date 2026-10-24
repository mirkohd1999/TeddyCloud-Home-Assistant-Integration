"""Read-only Toniebox volume and physical ear-button MQTT sensors."""
from datetime import datetime, timezone

from homeassistant.core import callback
from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_PREFIX, CONF_BOX_ID, CONF_BOX_NAME
from .media_player import mqtt_text
from .ear_events import parse_ear_event


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([
        VolumeSensor(entry),
        EarButtonSensor(entry, "VolUp", "Großes Ohr (lauter)"),
        EarButtonSensor(entry, "VolDown", "Kleines Ohr (leiser)"),
    ])


class VolumeSensor(SensorEntity):
    """Display actual volume; TeddyCloud cannot remotely set this value."""

    _attr_should_poll = False
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:volume-high"

    def __init__(self, entry):
        self._attr_name = f"{entry.data[CONF_BOX_NAME]} Aktuelle Lautstärke"
        self._attr_unique_id = f"{entry.entry_id}_actual_volume"
        self._attr_native_value = None
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._topic = f"{entry.data[CONF_PREFIX].strip('/')}/box/{entry.data[CONF_BOX_ID].strip('/')}/VolumeLevel"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.data[CONF_BOX_NAME],
            manufacturer="TeddyCloud",
            model="MQTT box monitor",
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        @callback
        def received(message):
            try:
                raw = mqtt_text(message.payload)
                level = int(raw)
                if raw != str(level) or not 0 <= level <= 16:
                    return
            except (ValueError, TypeError):
                return
            self._attr_native_value = round(level * 100 / 16)
            self.async_write_ha_state()

        self.async_on_remove(await mqtt.async_subscribe(self.hass, self._topic, received, 0))


class EarButtonSensor(SensorEntity):
    """Show the most recent physical ear press on this Toniebox.

    Repeated identical events still update press_count and last_pressed,
    so state-change automations can detect repeated presses.
    """

    _attr_should_poll = False
    _attr_icon = "mdi:ear-hearing"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, topic_name, friendly_name):
        self._attr_name = f"{entry.data[CONF_BOX_NAME]} {friendly_name}"
        self._attr_unique_id = f"{entry.entry_id}_ear_{topic_name.lower()}"
        self._attr_native_value = None
        self._press_count = 0
        self._last_pressed = None
        self._attr_extra_state_attributes = {
            "last_pressed": None,
            "press_count": 0,
        }
        prefix = entry.data[CONF_PREFIX].strip("/")
        box = entry.data[CONF_BOX_ID].strip("/")
        self._topic = f"{prefix}/box/{box}/{topic_name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.data[CONF_BOX_NAME],
            manufacturer="TeddyCloud",
            model="Toniebox (MQTT)",
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        @callback
        def received(message):
            # Events are instantaneous, not persistent MQTT state. Replayed
            # retained payloads must not be counted as a new physical press.
            if getattr(message, "retain", False):
                return
            event_type = parse_ear_event(message.payload)
            if event_type is None:
                return
            self._press_count += 1
            self._last_pressed = datetime.now(timezone.utc).isoformat()
            self._attr_native_value = event_type
            self._attr_extra_state_attributes = {
                "last_pressed": self._last_pressed,
                "press_count": self._press_count,
            }
            self.async_write_ha_state()

        self.async_on_remove(
            await mqtt.async_subscribe(self.hass, self._topic, received, 0)
        )
