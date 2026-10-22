"""Toniebox LED mode control via TeddyCloud MQTT."""
from homeassistant.components import mqtt
from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_PREFIX, CONF_BOX_ID, CONF_BOX_NAME
from .media_player import mqtt_text

LED_MODES = {"An": "0", "Aus": "1", "Gedimmt": "2"}
LED_STATES = {code: label for label, code in LED_MODES.items()}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([TonieboxLedMode(entry)])


class TonieboxLedMode(SelectEntity):
    """Select the box LED mode applied at the next freshness check."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(LED_MODES)

    def __init__(self, entry):
        self._attr_name = f"{entry.data[CONF_BOX_NAME]} LED-Helligkeit"
        self._attr_unique_id = f"{entry.entry_id}_led_mode"
        self._attr_current_option = None
        self._topic = (
            f"{entry.data[CONF_PREFIX].strip('/')}/box/"
            f"{entry.data[CONF_BOX_ID].strip('/')}/CmdLed"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.data[CONF_BOX_NAME],
            manufacturer="TeddyCloud",
            model="MQTT box monitor",
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        def received(message):
            option = LED_STATES.get(mqtt_text(message.payload))
            if option is None:
                return
            self._attr_current_option = option
            self.async_write_ha_state()

        self.async_on_remove(
            await mqtt.async_subscribe(self.hass, self._topic, received, 0)
        )

    async def async_select_option(self, option: str):
        if option not in LED_MODES:
            raise ValueError(f"Unsupported LED mode: {option}")
        await mqtt.async_publish(
            self.hass,
            self._topic + "/set",
            LED_MODES[option],
            qos=0,
            retain=False,
        )
        # The MQTT state topic confirms the setting; avoid optimistic updates.
