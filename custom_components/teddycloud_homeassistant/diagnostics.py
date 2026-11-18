"""Whitelisted diagnostics: no names, audio IDs, URLs, MQTT topics or secrets."""
from homeassistant.const import __version__ as HA_VERSION

from .card_registration import CARD_VERSION
from .const import DOMAIN
from .health import async_connection_report


async def async_get_config_entry_diagnostics(hass, entry):
    library = hass.data.get(DOMAIN, {}).get('library')
    return {'integration_version':CARD_VERSION, 'home_assistant_version':HA_VERSION,
            'connection':await async_connection_report(hass, entry),
            'configuration':{'offline_timeout_minutes':entry.options.get('offline_timeout', 5),
                             'online_images':bool(entry.options.get('online_images', True))},
            'library':{'records':len(library._entries) if library else 0,
                       'hidden_records':len(library._hidden) if library else 0}}
