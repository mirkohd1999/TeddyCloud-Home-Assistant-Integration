"""Optional room lights driven by the existing presence and color sensors."""

import asyncio
import logging

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
COLOR_MODES = {"hs", "xy", "rgb", "rgbw", "rgbww"}


class RoomLightController:
    """Follow the registered sensors, including the presence expiry timer."""

    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.enabled = False
        self._lock = asyncio.Lock()
        self._tasks = set()
        self._unsubscribe = None
        self._stopped = False

    @property
    def lights(self):
        return self.entry.options.get("room_lights", [])

    def entity_id(self, domain, suffix):
        return er.async_get(self.hass).async_get_entity_id(
            domain, DOMAIN, f"{self.entry.entry_id}_{suffix}"
        )

    @property
    def switch_entity_id(self):
        return self.entity_id("switch", "room_light_auto")

    def _sensor(self, domain, suffix):
        entity_id = self.entity_id(domain, suffix)
        return self.hass.states.get(entity_id) if entity_id else None

    @callback
    def async_start(self):
        self._unsubscribe = self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._changed)
        self.async_schedule()

    @callback
    def _changed(self, event):
        entity_id = event.data["entity_id"]
        if entity_id not in (
            self.entity_id("binary_sensor", "tonie_present"),
            self.entity_id("sensor", "tonie_color"),
            self.entity_id("media_player", "player"),
        ):
            return
        old, new = event.data.get("old_state"), event.data.get("new_state")
        if old and new and old.state == new.state and old.attributes.get("rgb_color") == new.attributes.get("rgb_color"):
            return
        self.async_schedule()

    @callback
    def async_schedule(self):
        if self._stopped or not self.enabled:
            return
        task = self.hass.async_create_task(self.async_sync())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def async_sync(self):
        async with self._lock:
            if not self.enabled or self._stopped:
                return
            present = self._sensor("binary_sensor", "tonie_present")
            if not present or present.state not in {"on", "off"}:
                return
            player = self._sensor("media_player", "player")
            placed = present.state == "on" and not (player and player.state == "unavailable")
            color = self._sensor("sensor", "tonie_color")
            rgb = color.attributes.get("rgb_color") if color else None
            valid_rgb = isinstance(rgb, (list, tuple)) and len(rgb) == 3 and all(
                isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 255 for value in rgb
            )
            for entity_id in self.lights:
                if not self.enabled or self._stopped:
                    return
                light = self.hass.states.get(entity_id)
                if not light or light.state in {"unknown", "unavailable"}:
                    continue
                data = {"entity_id": entity_id}
                service = "turn_on" if placed else "turn_off"
                if service == "turn_on" and valid_rgb and COLOR_MODES.intersection(light.attributes.get("supported_color_modes", [])):
                    data["rgb_color"] = list(rgb)
                try:
                    # No brightness argument: preserve the lamp's own dimming.
                    await self.hass.services.async_call("light", service, data, blocking=True)
                except HomeAssistantError as err:
                    _LOGGER.warning("Could not control room light %s: %s", entity_id, err)

    @callback
    def async_stop(self):
        self._stopped = True
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None
        for task in self._tasks:
            task.cancel()
