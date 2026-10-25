"""Serve and register the bundled Lovelace card once per Home Assistant runtime."""
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)
LEGACY_CARD_PATH = "/teddycloud-homeassistant/card.js"
PREVIOUS_CARD_PATH = "/teddycloud-homeassistant/card-v034.js"
CARD_PATH = "/teddycloud-homeassistant/card-v035.js"
CARD_VERSION = "0.3.5"
CARD_URL = f"{CARD_PATH}?v={CARD_VERSION}"
BRANDING_STORE = "teddycloud_homeassistant.owned_resources"


async def async_register_card(hass):
    """Register a static card and a Lovelace resource in storage mode.

    Never create an item before the resource storage collection has loaded:
    on some Home Assistant versions that could replace existing resources.
    """
    key = "teddycloud_homeassistant_card_registered"
    if hass.data.get(key):
        return
    card_file = Path(__file__).parent / "teddycloud-homeassistant-card.js"
    # Versioned *path*, not only a query parameter: forces Home Assistant to
    # load the new visual editor instead of an older browser-cached module.
    # Keep the legacy URL available for hand-written dashboard resources.
    for path in (LEGACY_CARD_PATH, PREVIOUS_CARD_PATH, CARD_PATH):
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(path, str(card_file), False)]
            )
        except RuntimeError:
            # Existing path can survive a config-entry reload.
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
            if item.get("url", "").split("?")[0] in (CARD_PATH, PREVIOUS_CARD_PATH, LEGACY_CARD_PATH)
        ]
        if existing:
            for item in existing:
                if item.get("url") != CARD_URL:
                    await resources.async_update_item(
                        item["id"], {"url": CARD_URL, "res_type": "module"}
                    )
        else:
            created = await resources.async_create_item({"url": CARD_URL, "res_type": "module"})
            if created and created.get("id"):
                await Store(hass, 1, BRANDING_STORE).async_save({"resource_id": created["id"]})
    except Exception:
        _LOGGER.exception(
            "Automatic card registration failed. Add %s as a module under Dashboard resources.",
            CARD_URL,
        )
