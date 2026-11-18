"""Read-only status snapshots without exposing addresses or household metadata."""
from datetime import datetime, timezone

from homeassistant.components import mqtt

from .const import DOMAIN
from .image_storage import image_reference


def age_seconds(value):
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(value) if isinstance(value, str) else value
        return max(0, int((datetime.now(timezone.utc) - stamp).total_seconds()))
    except (ValueError, TypeError, AttributeError):
        return None


async def async_connection_report(hass, entry):
    data = hass.data.get(DOMAIN, {})
    player = data.get(entry.entry_id)
    try:
        connected = mqtt.is_connected(hass)
    except (KeyError, AttributeError):
        connected = False
    catalog = data.get('online_catalog')
    catalog_status = 'loading' if not catalog or not (catalog.fetched_at or catalog.failed_at) else 'unavailable' if catalog.failed_at else 'limited' if catalog.loaded_format == 'v1' else 'ready'
    image_status = 'not_selected'
    if player and player.figure_present:
        url = player.media_image_url
        ref = image_reference(url)
        if ref:
            images = data.get('images')
            image_status = 'available' if images and await images.async_read(*ref) else 'missing'
        elif url and url.startswith(('http://', 'https://', '/local/')):
            image_status = 'external_not_checked'
        else:
            image_status = 'unknown_figure'
    return {
        'mqtt': {'status':'connected' if connected else 'disconnected'},
        'box': {'status':'online' if player and connected and player.available else 'no_fresh_messages' if connected else 'mqtt_disconnected',
                'last_message_age_seconds':age_seconds(getattr(player, '_last_message_at', None)),
                'availability_source':'last_seen' if player and player._availability.last_seen is not None else 'mqtt',
                'estimated_playback_remaining':round(player._availability.playback_remaining) if player else 0},
        'catalog': {'status':catalog_status, 'last_success_age_seconds':age_seconds(getattr(catalog, 'fetched_at', None)),
                    'last_failure_age_seconds':age_seconds(getattr(catalog, 'failed_at', None))},
        'image': {'status':image_status},
    }
