"""Serve and register the bundled Lovelace card once per Home Assistant runtime."""
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA

_LOGGER = logging.getLogger(__name__)
CARD_PATH = "/teddycloud-homeassistant/card.js"
CARD_VERSION = "0.3.0-dev10"
CARD_URL = f"{CARD_PATH}?v={CARD_VERSION}"


async def async_register_card(hass):
    """Register a static card and a Lovelace resource in storage mode.

    Never create an item before the resource storage collection has loaded:
    on some Home Assistant versions that could replace existing resources.
    """
    key = "teddycloud_homeassistant_card_registered"
    if hass.data.get(key):
        return
    card_file = Path(__file__).parent / "teddycloud-homeassistant-card.js"
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_PATH, str(card_file), False)]
        )
    except RuntimeError:
        # Static path may already exist after a config-entry reload.
        pass
    hass.data[key] = True

    lovelace = hass.data.get(LOVELACE_DATA)
    resources = getattr(lovelace, "resources", None)
    if resources is None or getattr(lovelace, "resource_mode", None) != "storage":
        _LOGGER.info("Card served at %s; manual resource registration required in YAML mode", CARD_PATH)
        return

    try:
        # ResourceStorageCollection is lazily initialized in some HA releases.
        if not getattr(resources, "loaded", False):
            await resources.async_load()
        existing = [
            item for item in resources.async_items()
            if item.get("url", "").split("?")[0] == CARD_PATH
        ]
        if existing:
            for item in existing:
                if item.get("url") != CARD_URL:
                    await resources.async_update_item(
                        item["id"], {"url": CARD_URL, "res_type": "module"}
                    )
        else:
            await resources.async_create_item({"url": CARD_URL, "res_type": "module"})
    except Exception:
        _LOGGER.exception(
            "Automatic card registration failed. Add %s as a module under Dashboard resources.",
            CARD_URL,
        )
