"""Remove only integration-owned resources when the last box is deleted."""
import asyncio
import logging
from pathlib import Path

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .card_registration import CARD_PATH, OLDER_V057_PATH, OLDER_V056_PATH, OLDER_V054_PATH, PREVIOUS_CARD_PATH, OLDER_V038_PATH, OLDER_V040_PATH, OLDER_V037_PATH, OLDER_V036_PATH, OLDER_V035_PATH, OLDER_CARD_PATH, LEGACY_CARD_PATH, BRANDING_STORE

_LOGGER = logging.getLogger(__name__)


async def async_remove_owned_data(hass, removed_entry_id):
    """Remove our resource and local archive, never unrelated /config/www files."""
    remaining = [
        entry for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.entry_id != removed_entry_id
    ]
    if remaining:
        return

    # Only delete a resource we can prove this integration created.
    # In particular, leave manually registered card resources untouched.
    store = Store(hass, 1, BRANDING_STORE)
    owned = await store.async_load() or {}
    resource_id = owned.get("resource_id")
    lovelace = hass.data.get(LOVELACE_DATA)
    resources = getattr(lovelace, "resources", None)
    if resource_id and resources is not None and getattr(lovelace, "resource_mode", None) == "storage":
        try:
            if not getattr(resources, "loaded", False):
                await resources.async_load()
            match = next(
                (item for item in resources.async_items()
                 if item.get("id") == resource_id
                 and item.get("url", "").split("?")[0] in (CARD_PATH, OLDER_V057_PATH, OLDER_V056_PATH, OLDER_V054_PATH, PREVIOUS_CARD_PATH, OLDER_V038_PATH, OLDER_V040_PATH, OLDER_V037_PATH, OLDER_V036_PATH, OLDER_V035_PATH, OLDER_CARD_PATH, LEGACY_CARD_PATH)),
                None,
            )
            if match:
                await resources.async_delete_item(resource_id)
                await store.async_remove()
        except Exception:
            _LOGGER.exception("Could not remove integration-created Lovelace resource")
    elif not resource_id:
        _LOGGER.debug("No integration-owned Lovelace resource registered")

    # Delete only the dedicated directory created by our own image archive.
    directory = Path(hass.config.path("www", DOMAIN, "figures"))
    parent = Path(hass.config.path("www", DOMAIN))
    try:
        if directory.is_dir() and not directory.is_symlink():
            for child in directory.iterdir():
                # Only audio-ID named images downloaded by this integration.
                if child.is_file() and not child.is_symlink() and child.stem.isdecimal() and child.suffix in (".png", ".jpg", ".webp"):
                    await asyncio.to_thread(child.unlink)
            await asyncio.to_thread(directory.rmdir)
        # Remove the empty parent folder only. Do not touch extra user files.
        if parent.is_dir() and not parent.is_symlink():
            await asyncio.to_thread(parent.rmdir)
    except OSError:
        _LOGGER.info("TeddyCloud images cleaned up; keeping nonempty or custom directory")
    hass.data.pop("teddycloud_homeassistant_card_registered", None)
    hass.data.get(DOMAIN, {}).pop("online_catalog", None)
    hass.data.get(DOMAIN, {}).pop("artwork_archive", None)
