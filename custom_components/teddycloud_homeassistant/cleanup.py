"""Remove integration-owned data only when the last configured box is removed."""
import asyncio
import logging

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .card_registration import is_card_resource, BRANDING_STORE

_LOGGER = logging.getLogger(__name__)


async def async_remove_owned_data(hass, removed_entry_id):
    remaining = [entry for entry in hass.config_entries.async_entries(DOMAIN)
                 if entry.entry_id != removed_entry_id]
    if remaining:
        return

    data = hass.data.get(DOMAIN, {})
    task = data.pop("library_catalog_task", None)
    if task:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    archive = data.get("artwork_archive")
    if archive:
        await archive.async_shutdown()

    lovelace = hass.data.get(LOVELACE_DATA)
    resources = getattr(lovelace, "resources", None)
    if resources is not None and getattr(lovelace, "resource_mode", None) == "storage":
        try:
            if not getattr(resources, "loaded", False):
                await resources.async_load()
            for item in list(resources.async_items()):
                if is_card_resource(item.get("url")):
                    await resources.async_delete_item(item["id"])
        except Exception:
            _LOGGER.exception("Could not remove TeddyCloud dashboard resources")
    await Store(hass, 1, BRANDING_STORE).async_remove()

    library = data.get("library")
    if library:
        await library.async_remove()
    else:
        from .library import STORE_KEY
        await Store(hass, 1, STORE_KEY).async_remove()
    images = data.get("images")
    if images:
        await images.async_remove()
    else:
        from .image_storage import ImageStorage
        await ImageStorage(hass).async_remove()

    hass.data.pop("teddycloud_homeassistant_card_registered", None)
    hass.data.pop("teddycloud_homeassistant_card_url", None)
    hass.data.pop(DOMAIN, None)
