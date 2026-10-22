"""Adjustable TeddyCloud volume limits (not live playback volume)."""
from homeassistant.core import callback
from homeassistant.components import mqtt
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_PREFIX, CONF_BOX_ID, CONF_BOX_NAME
from .media_player import mqtt_text

LIMITS = (
    ("CmdVolLimitSpk", "Lautsprecher-Lautstärkelimit"),
    ("CmdVolLimitHdp", "Kopfhörer-Lautstärkelimit"),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([VolumeLimit(entry, topic, name) for topic, name in LIMITS] + [LedBrightness(entry)])


class VolumeLimit(NumberEntity):
    """A maximum volume limit applied on the next box freshness check."""

    _attr_should_poll = False
    _attr_native_min_value = 25
    _attr_native_max_value = 100
    _attr_native_step = 25
    _attr_native_unit_of_measurement = "%"
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry, command, name):
        self._attr_name = f"{entry.data[CONF_BOX_NAME]} {name}"
        self._attr_unique_id = f"{entry.entry_id}_{command}"
        self._attr_native_value = None
        self._topic = f"{entry.data[CONF_PREFIX].strip('/')}/box/{entry.data[CONF_BOX_ID].strip('/')}/{command}"

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
                if raw != str(level) or level not in range(4):
                    return
            except (ValueError, TypeError):
                return
            self._attr_native_value = (level + 1) * 25
            self.async_write_ha_state()

        self.async_on_remove(await mqtt.async_subscribe(self.hass, self._topic, received, 0))

    async def async_set_native_value(self, value: float):
        if not float(value).is_integer() or int(value) not in (25, 50, 75, 100):
            raise ValueError("Volume limit must be 25, 50, 75 or 100 percent")
        await mqtt.async_publish(self.hass, self._topic + "/set", str(int(value) // 25 - 1), qos=0, retain=False)
        # Do not assume the command was accepted; the state topic confirms it.


class LedBrightness(NumberEntity):
    """LED brightness, limited to TeddyCloud's three supported modes."""

    _attr_should_poll = False
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 50
    _attr_native_unit_of_measurement = "%"
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry):
        self._attr_name = f"{entry.data[CONF_BOX_NAME]} LED-Helligkeit"
        self._attr_unique_id = f"{entry.entry_id}_led_brightness"
        self._attr_native_value = None
        self._topic = f"{entry.data[CONF_PREFIX].strip('/')}/box/{entry.data[CONF_BOX_ID].strip('/')}/CmdLed"
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
            # TeddyCloud: 0 = full brightness, 1 = off, 2 = dimmed.
            values = {"0": 100, "1": 0, "2": 50}
            level = values.get(mqtt_text(message.payload))
            if level is None:
                return
            self._attr_native_value = level
            self.async_write_ha_state()

        self.async_on_remove(
            await mqtt.async_subscribe(self.hass, self._topic, received, 0)
        )

    async def async_set_native_value(self, value: float):
        values = {0: "1", 50: "2", 100: "0"}
        if value not in values:
            raise ValueError("LED brightness must be 0, 50 or 100 percent")
        await mqtt.async_publish(
            self.hass, self._topic + "/set", values[value], qos=0, retain=False
        )
        # Only MQTT confirmation updates the displayed state.
