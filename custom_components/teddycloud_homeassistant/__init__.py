"""Local MQTT listener for TeddyCloud box status."""
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, CONF_PREFIX, CONF_BOX_ID
from .online_catalog import OnlineCatalog

FIELDS = {"Playback", "ContentTitle", "ContentAudioId", "VolumeLevel", "VolumedB", "Charger", "TagValid", "LastSeen", "ContentPicture"}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not await mqtt.async_wait_for_mqtt_client(hass):
        return False
    from .media_player import BoxPlayer
    catalog = hass.data.setdefault(DOMAIN, {}).setdefault("online_catalog", OnlineCatalog(hass))
    player = BoxPlayer(entry, catalog)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = player
    prefix = entry.data[CONF_PREFIX].strip('/')
    box = entry.data[CONF_BOX_ID].strip('/')
    topic = f"{prefix}/box/{box}/+"

    def incoming(message):
        field = message.topic.rsplit('/', 1)[-1]
        if field in FIELDS:
            player.receive(field, message.payload)

    await hass.config_entries.async_forward_entry_setups(entry, ["media_player", "number", "sensor"])
    try:
        unsubscribe = await mqtt.async_subscribe(hass, topic, incoming, 0)
    except Exception:
        await hass.config_entries.async_unload_platforms(entry, ["media_player", "number", "sensor"])
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise
    hass.data[DOMAIN][f"{entry.entry_id}_unsubscribe"] = unsubscribe
    entry.async_on_unload(entry.add_update_listener(_update_options))
    return True

async def _update_options(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass, entry):
    unsubscribe = hass.data[DOMAIN].pop(f"{entry.entry_id}_unsubscribe", None)
    if unsubscribe:
        unsubscribe()
    unloaded = await hass.config_entries.async_unload_platforms(entry, ["media_player", "number", "sensor"])
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
