"""Read-only Toniebox volume and physical ear-button MQTT sensors."""

from homeassistant.core import callback
from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, CONF_PREFIX, CONF_BOX_ID, CONF_BOX_NAME
from .media_player import mqtt_text
from .ear_events import parse_ear_event
from .figure_color import FigureColorSensor


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([
        CurrentTonieSensor(entry, hass.data[DOMAIN][entry.entry_id]),
        FigureColorSensor(entry, hass.data[DOMAIN][entry.entry_id]),
        VolumeSensor(entry),
        EarButtonSensor(entry, "VolUp", "Großes Ohr (lauter)"),
        EarButtonSensor(entry, "VolDown", "Kleines Ohr (leiser)"),
    ])


class CurrentTonieSensor(SensorEntity):
    """Expose the current figurine title for dashboards and automations."""

    _attr_should_poll = False
    _attr_icon = "mdi:teddy-bear"

    def __init__(self, entry, player):
        self._player = player
        self._attr_name = f"{entry.data[CONF_BOX_NAME]} Aktueller Tonie"
        self._attr_unique_id = f"{entry.entry_id}_current_tonie"
        self._attr_device_info = player.device_info

    @property
    def available(self):
        return self._player.available

    @property
    def native_value(self):
        if self._player.figure_present is None:
            return None
        return self._player.media_title[:255]

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._player.on_figure_title_changed = self.async_write_ha_state

    async def async_will_remove_from_hass(self):
        self._player.on_figure_title_changed = None
        await super().async_will_remove_from_hass()


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
    """Show a one-second press pulse for either physical ear."""

    _attr_should_poll = False
    _attr_icon = "mdi:ear-hearing"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, topic_name, friendly_name):
        self._attr_name = f"{entry.data[CONF_BOX_NAME]} {friendly_name}"
        self._attr_unique_id = f"{entry.entry_id}_ear_{topic_name.lower()}"
        self._attr_native_value = "released"
        self._cancel_release = None
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
            self._attr_native_value = "pressed"
            if self._cancel_release:
                self._cancel_release()
            self._cancel_release = async_call_later(self.hass, 1, self._release)
            self.async_write_ha_state()

        self.async_on_remove(
            await mqtt.async_subscribe(self.hass, self._topic, received, 0)
        )

    @callback
    def _release(self, _now):
        self._cancel_release = None
        self._attr_native_value = "released"
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        if self._cancel_release:
            self._cancel_release()
            self._cancel_release = None
        await super().async_will_remove_from_hass()
