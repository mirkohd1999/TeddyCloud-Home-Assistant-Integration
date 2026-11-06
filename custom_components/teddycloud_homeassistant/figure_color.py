"""Dominant artwork color for the currently placed figurine."""

import asyncio
from io import BytesIO
from aiohttp import ClientError

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback

from .const import CONF_BOX_NAME


def dominant_color(data):
    """Find a foreground color without treating studio backdrops as the figure."""
    from PIL import Image

    if not data or len(data) > 8_000_000:
        return None
    with Image.open(BytesIO(data)) as source:
        if source.width * source.height > 16_000_000:
            return None
        image = source.convert("RGBA")
        image.thumbnail((96, 96))
        width, height = image.size
        pixels = list(image.getdata())
        # Catalog pictures can be transparent cutouts or opaque studio photos.
        # Remove only a near-uniform background connected to the image border.
        # Never remove an interior white/grey part merely because it is neutral.
        border = set(range(width)) | set(range((height - 1) * width, height * width))
        border.update(y * width for y in range(height))
        border.update(y * width + width - 1 for y in range(height))
        opaque_border = [pixels[i] for i in border if pixels[i][3] >= 128]
        background = set()
        if len(opaque_border) >= len(border) * .8:
            buckets = {}
            for r, g, b, _ in opaque_border:
                key = (r // 24, g // 24, b // 24)
                buckets.setdefault(key, []).append((r, g, b))
            common = max(buckets.values(), key=len)
            if len(common) >= len(opaque_border) * .65:
                reference = tuple(sum(rgb[c] for rgb in common) / len(common) for c in range(3))
                def matches(index):
                    return pixels[index][3] >= 128 and max(abs(pixels[index][c] - reference[c]) for c in range(3)) <= 36
                pending = [i for i in border if matches(i)]
                background.update(pending)
                while pending:
                    i = pending.pop()
                    x, y = i % width, i // width
                    neighbors = []
                    if x: neighbors.append(i - 1)
                    if x + 1 < width: neighbors.append(i + 1)
                    if y: neighbors.append(i - width)
                    if y + 1 < height: neighbors.append(i + width)
                    for neighbor in neighbors:
                        if neighbor not in background and matches(neighbor):
                            background.add(neighbor)
                            pending.append(neighbor)
        visible = [(r, g, b) for i, (r, g, b, a) in enumerate(pixels) if a >= 128 and i not in background]
        if not visible:
            # A uniformly colored image still has a meaningful color.
            visible = [(r, g, b) for r, g, b, a in pixels if a >= 128]
        colorful = [(r, g, b) for r, g, b in visible if max(r, g, b) - min(r, g, b) >= 35 and max(r, g, b) >= 65]
        # Prefer a substantial colored part to neutral highlights and shadows.
        # Fully white/grey figurines retain their actual neutral color.
        selected = colorful if len(colorful) >= max(8, len(visible) * .08) else visible
        groups = {}
        for red, green, blue in selected:
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
        color = self._attr_native_value
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
