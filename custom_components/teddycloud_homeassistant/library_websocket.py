"""Authenticated WebSocket commands for a shared Tonie library.

Only admins may add or edit entries; all signed-in users may read and delete.
All operations require an authenticated Home Assistant session.
"""
from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
import voluptuous as vol

from .card_registration import CARD_URL, CARD_VERSION
from .const import DOMAIN
from .library import SIGNAL_CHANGED


def get_library(hass):
    return hass.data.get(DOMAIN, {}).get("library")


def library_payload(hass, library):
    """Report whether missing samples are final or still awaiting the catalog."""
    catalog = hass.data.get(DOMAIN, {}).get("online_catalog")
    if catalog is None or (not catalog.fetched_at and not catalog.failed_at):
        status = "loading"
    elif catalog.failed_at or getattr(catalog, "loaded_format", None) == "v1":
        status = "unavailable"
    else:
        status = "ready"
    return {"entries": library.public_entries(), "preview_catalog_status": status,
            "card_url": CARD_URL, "card_version": CARD_VERSION}


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
    connection.send_result(msg["id"], library_payload(hass, library))


@websocket_api.ws_require_user()
@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/library/refresh",
})
@websocket_api.async_response
async def ws_library_refresh(hass, connection, msg):
    """Both roles may request a rate-limited refresh of the one shared catalog."""
    library = get_library(hass)
    catalog = hass.data.get(DOMAIN, {}).get("online_catalog")
    if library is None or catalog is None:
        connection.send_error(msg["id"], "not_ready", "Tonie-Bibliothek nicht bereit")
        return
    await catalog.refresh(force=True)
    await library.async_refresh_catalog(catalog)
    connection.send_result(msg["id"], library_payload(hass, library))


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
    # Enforce permissions server-side, including direct WebSocket requests
    # from old clients that still display the editing controls.
    if not connection.user or not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Nur Administratoren dürfen Tonies hinzufügen oder bearbeiten")
        return
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
            msg["id"], library_payload(hass, library)
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
        ws_library_refresh,
        ws_library_save,
        ws_library_delete,
        ws_library_subscribe,
    ):
        websocket_api.async_register_command(hass, command)
    hass.data[key] = True

