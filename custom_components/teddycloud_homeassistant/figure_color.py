"""Dominant artwork color for the currently placed figurine."""

import asyncio
from io import BytesIO
from aiohttp import ClientError

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback

from .const import CONF_BOX_NAME


def dominant_color(data):
    """Group visible pixels into similar colors before selecting the largest group."""
    from PIL import Image

    if not data or len(data) > 8_000_000:
        return None
    with Image.open(BytesIO(data)) as source:
        if source.width * source.height > 16_000_000:
            return None
        image = source.convert("RGBA")
        image.thumbnail((96, 96))
        groups = {}
        for red, green, blue, alpha in image.getdata():
            if alpha < 128:
                continue
            bucket = (red // 32, green // 32, blue // 32)
            count, r, g, b = groups.get(bucket, (0, 0, 0, 0))
            groups[bucket] = count + 1, r + red, g + green, b + blue
    if not groups:
        return None
    count, *channels = max(groups.values(), key=lambda group: group[0])
    return "#" + "".join(f"{round(channel / count):02X}" for channel in channels)


class FigureColorSensor(SensorEntity):
    """Publish a hex color and RGB channels for light automations."""

    _attr_should_poll = False
    _attr_icon = "mdi:palette"
    _attr_native_value = None

    def __init__(self, entry, player):
        self._player = player
        self._attr_device_info = player.device_info
        self._attr_name = f"{entry.data[CONF_BOX_NAME]} Tonie-Farbe"
        self._attr_unique_id = f"{entry.entry_id}_tonie_color"
        self._selection = None
        self._task = None

    @property
    def extra_state_attributes(self):
        color = self.native_value
        return {"rgb_color": [int(color[i:i + 2], 16) for i in (1, 3, 5)]} if color else {}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._player.on_figure_artwork_changed = self._refresh
        self._refresh()

    @callback
    def _refresh(self):
        player = self._player
        artwork = player.media_image_url if player.figure_present else None
        override = player.figure_color_override if player.figure_present else None
        selection = (player.figure_generation, artwork, override)
        if selection == self._selection:
            return
        self._selection = selection
        if self._task:
            self._task.cancel()
        self._attr_native_value = override
        self.async_write_ha_state()
        if artwork and not override and not artwork.split("?", 1)[0].endswith(
            ("/unknown-tonie.png", "/img_unknown.png", "/img_custom.png")
        ):
            self._task = self.hass.async_create_task(self._extract(selection))

    async def _extract(self, selection):
        try:
            async with asyncio.timeout(12):
                data, _ = await self._player.async_get_media_image()
                color = await self.hass.async_add_executor_job(dominant_color, data)
        except (OSError, ValueError, ImportError, TimeoutError, ClientError):
            return
        if selection == self._selection:
            self._attr_native_value = color
            self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        self._player.on_figure_artwork_changed = None
        if self._task:
            self._task.cancel()
        await super().async_will_remove_from_hass()
