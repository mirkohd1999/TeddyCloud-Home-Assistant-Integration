"""Read-only actual Toniebox playback volume as reported via MQTT."""
from homeassistant.core import callback
from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_PREFIX, CONF_BOX_ID, CONF_BOX_NAME
from .media_player import mqtt_text


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([VolumeSensor(entry)])


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
