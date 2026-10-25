"""Authenticated WebSocket commands for a non-admin editable shared Tonie library.

Dashboard users can manage their *library contents*, not HA configuration.
All operations require an authenticated Home Assistant session.
"""
from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
import voluptuous as vol

from .const import DOMAIN
from .library import SIGNAL_CHANGED


def get_library(hass):
    return hass.data.get(DOMAIN, {}).get("library")


@websocket_api.ws_require_user()
@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/library/list",
})
@websocket_api.async_response
async def ws_library_list(hass, connection, msg):
    library = get_library(hass)
    if library is None:
        connection.send_error(msg["id"], "not_ready", "Tonie-Bibliothek nicht bereit")
        return
    connection.send_result(msg["id"], {"entries": library.public_entries()})


@websocket_api.ws_require_user()
@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/library/save",
    vol.Required("audio_id"): str,
    vol.Optional("title"): str,
    vol.Optional("image"): str,
    vol.Optional("duration_seconds"): int,
    vol.Optional("image_data"): str,
})
@websocket_api.async_response
async def ws_library_save(hass, connection, msg):
    library = get_library(hass)
    if library is None:
        connection.send_error(msg["id"], "not_ready", "Tonie-Bibliothek nicht bereit")
        return
    try:
        entry = await library.async_edit(
            msg["audio_id"],
            title=msg.get("title"),
            image=msg.get("image"),
            duration_seconds=msg.get("duration_seconds"),
            image_data=msg.get("image_data"),
        )
    except ValueError as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    connection.send_result(msg["id"], entry)


@websocket_api.ws_require_user()
@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/library/delete",
    vol.Required("audio_id"): str,
})
@websocket_api.async_response
async def ws_library_delete(hass, connection, msg):
    library = get_library(hass)
    if library is None:
        connection.send_error(msg["id"], "not_ready", "Tonie-Bibliothek nicht bereit")
        return
    await library.async_delete(msg["audio_id"])
    connection.send_result(msg["id"], {"deleted": True})


@websocket_api.ws_require_user()
@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/library/subscribe",
})
@callback
def ws_library_subscribe(hass, connection, msg):
    """Push library changes to every signed-in dashboard, including non-admins."""
    library = get_library(hass)
    if library is None:
        connection.send_error(msg["id"], "not_ready", "Tonie-Bibliothek nicht bereit")
        return

    @callback
    def updated(_audio_id):
        connection.send_message(websocket_api.event_message(
            msg["id"], {"entries": library.public_entries()}
        ))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_CHANGED, updated
    )
    connection.send_result(msg["id"])
    updated(None)


@callback
def register_library_websockets(hass):
    """Register websocket endpoints once; they work for all logged-in users."""
    key = f"{DOMAIN}_library_websockets"
    if hass.data.get(key):
        return
    for command in (
        ws_library_list,
        ws_library_save,
        ws_library_delete,
        ws_library_subscribe,
    ):
        websocket_api.async_register_command(hass, command)
    hass.data[key] = True
