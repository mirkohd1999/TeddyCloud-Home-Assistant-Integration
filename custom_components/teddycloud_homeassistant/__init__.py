"""Local MQTT listener for TeddyCloud box status."""
import asyncio
from homeassistant.core import callback
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, CONF_PREFIX, CONF_BOX_ID
from .online_catalog import OnlineCatalog, REFRESH, RETRY
from .card_registration import async_register_card
from .cleanup import async_remove_owned_data
from .library import TonieLibrary
from .library_websocket import register_library_websockets

FIELDS = {"Playback", "ContentTitle", "ContentAudioId", "VolumeLevel", "VolumedB", "Charger", "TagValid", "LastSeen", "ContentPicture"}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not await mqtt.async_wait_for_mqtt_client(hass):
        return False
    await async_register_card(hass)
    data = hass.data.setdefault(DOMAIN, {})
    # Multiple boxes can be initialized concurrently. Load the shared
    # library only once so no box can overwrite a different instance.
    async with hass.data.setdefault(f"{DOMAIN}_library_init_lock", asyncio.Lock()):
        if "library" not in data:
            library = TonieLibrary(hass)
            await library.async_load()
            data["library"] = library
    register_library_websockets(hass)
    from .media_player import BoxPlayer
    catalog = data.setdefault("online_catalog", OnlineCatalog(hass))
    if "library_catalog_task" not in data:
        data["library_catalog_task"] = hass.async_create_background_task(
            _refresh_library_catalog(data["library"], catalog), "TeddyCloud library catalog refresh"
        )
    player = BoxPlayer(entry, catalog)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = player
    prefix = entry.data[CONF_PREFIX].strip('/')
    box = entry.data[CONF_BOX_ID].strip('/')
    topic = f"{prefix}/box/{box}/+"

    @callback
    def incoming(message):
        field = message.topic.rsplit('/', 1)[-1]
        if field in FIELDS:
            player.receive(field, message.payload, retained=getattr(message, "retain", False))
        else:
            player.note_message(retained=getattr(message, "retain", False))

    await hass.config_entries.async_forward_entry_setups(entry, ["media_player", "number", "sensor"])
    try:
        unsubscribe = await mqtt.async_subscribe(hass, topic, incoming, 0)
    except Exception:
        await hass.config_entries.async_unload_platforms(entry, ["media_player", "number", "sensor"])
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _stop_library_catalog_if_unused(hass.data[DOMAIN])
        raise
    hass.data[DOMAIN][f"{entry.entry_id}_unsubscribe"] = unsubscribe
    entry.async_on_unload(entry.add_update_listener(_update_options))
    return True

async def _refresh_library_catalog(library, catalog):
    """Refresh the shared catalog only; never request samples or shop pages."""
    while True:
        await catalog.refresh()
        await library.async_refresh_catalog(catalog)
        await asyncio.sleep(RETRY.total_seconds() + 2 if catalog.failed_at else REFRESH.total_seconds())


def _stop_library_catalog_if_unused(data):
    """Keep the shared refresh while any box still uses it, including during setup."""
    catalog = data.get("online_catalog")
    if catalog is None or any(getattr(value, "_online_catalog", None) is catalog for value in data.values()):
        return
    task = data.pop("library_catalog_task", None)
    if task:
        task.cancel()


async def _update_options(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass, entry):
    unsubscribe = hass.data[DOMAIN].pop(f"{entry.entry_id}_unsubscribe", None)
    if unsubscribe:
        unsubscribe()
    unloaded = await hass.config_entries.async_unload_platforms(entry, ["media_player", "number", "sensor"])
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _stop_library_catalog_if_unused(hass.data[DOMAIN])
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean integration-owned resources on removal of the final box."""
    await async_remove_owned_data(hass, entry.entry_id)
