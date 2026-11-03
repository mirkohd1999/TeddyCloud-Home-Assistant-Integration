"""Physical figurine presence reported by TeddyCloud."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, CONF_BOX_NAME


async def async_setup_entry(hass, entry, async_add_entities):
    player = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ToniePresentSensor(entry, player)])


class ToniePresentSensor(BinarySensorEntity):
    """Report whether TeddyCloud sees a figurine on this box."""

    _attr_should_poll = False
    _attr_icon = "mdi:teddy-bear"

    def __init__(self, entry, player):
        self._player = player
        self._cancel_timer = None
        self._expired = False
        self._figure_generation = player.figure_generation
        self._attr_name = f"{entry.data[CONF_BOX_NAME]} Tonie aufgelegt"
        self._attr_unique_id = f"{entry.entry_id}_tonie_present"
        self._attr_device_info = player.device_info

    @property
    def is_on(self):
        return False if self._expired else self._player.figure_present

    @callback
    def _refresh(self):
        remaining = self._player.figure_playback_remaining
        figure_changed = self._figure_generation != self._player.figure_generation
        self._figure_generation = self._player.figure_generation
        if figure_changed or self._player.figure_present is not True or remaining is not None:
            if self._cancel_timer:
                self._cancel_timer()
                self._cancel_timer = None
            self._expired = remaining is not None and remaining <= 0
            if self._player.figure_present and remaining is not None and remaining > 0:
                self._cancel_timer = async_call_later(self.hass, remaining, self._expire)
        self.async_write_ha_state()

    @callback
    def _expire(self, _now):
        self._cancel_timer = None
        self._expired = True
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._player.on_figure_presence_changed = self._refresh
        self._refresh()

    async def async_will_remove_from_hass(self):
        self._player.on_figure_presence_changed = None
        if self._cancel_timer:
            self._cancel_timer()
        await super().async_will_remove_from_hass()
