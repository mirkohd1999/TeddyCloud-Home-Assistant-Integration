"""Enable optional room light following for each Toniebox."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONF_BOX_NAME


async def async_setup_entry(hass, entry, async_add_entities):
    player = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RoomLightSwitch(entry, player._room_light_controller, player.device_info)])


class RoomLightSwitch(SwitchEntity, RestoreEntity):
    """Persist the user's automatic-light choice across reloads and restarts."""

    _attr_should_poll = False
    _attr_icon = "mdi:lightbulb-auto"
    _attr_is_on = False

    def __init__(self, entry, controller, device_info):
        self._controller = controller
        self._attr_name = f"{entry.data[CONF_BOX_NAME]} Tonie-Lichtautomatik"
        self._attr_unique_id = f"{entry.entry_id}_room_light_auto"
        self._attr_device_info = device_info

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        previous = await self.async_get_last_state()
        self._attr_is_on = previous is not None and previous.state == "on"
        self._controller.enabled = self._attr_is_on

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = self._controller.enabled = True
        self.async_write_ha_state()
        self._controller.async_schedule()

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = self._controller.enabled = False
        self.async_write_ha_state()
