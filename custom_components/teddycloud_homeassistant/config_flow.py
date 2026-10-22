"""TeddyCloud Home Assistant configuration UI."""
import json
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    DOMAIN, CONF_PREFIX, CONF_BOX_ID, CONF_BOX_NAME, CONF_BOX_COLOR,
    CONF_CATALOG, CONF_FALLBACK_COVER, DEFAULT_PREFIX, DEFAULT_COLOR,
)


def valid_catalog(value):
    """JSON keyed by ContentAudioId, with title/cover/duration_seconds."""
    try:
        data = json.loads(value or "{}")
        if not isinstance(data, dict):
            raise ValueError("Expected JSON object")
        for key, item in data.items():
            if not isinstance(key, str) or not isinstance(item, dict):
                raise ValueError("Expected audio-ID => object")
            if "duration_seconds" in item and (not isinstance(item["duration_seconds"], (int, float)) or item["duration_seconds"] <= 0):
                raise ValueError("duration_seconds must be positive")
        return value or "{}"
    except (ValueError, TypeError) as err:
        raise vol.Invalid(str(err)) from err


class TeddyCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            key = f"{user_input[CONF_PREFIX].strip('/')}/{user_input[CONF_BOX_ID].strip('/')}"
            await self.async_set_unique_id(key)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_BOX_NAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required(CONF_BOX_ID): str,
            vol.Required(CONF_BOX_NAME, default="Meine Toniebox"): str,
            vol.Required(CONF_PREFIX, default=DEFAULT_PREFIX): str,
        }), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TeddyCloudOptionsFlow()


class TeddyCloudOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            try:
                valid_catalog(user_input[CONF_CATALOG])
            except vol.Invalid:
                return self.async_show_form(step_id="init", data_schema=self._schema(), errors={CONF_CATALOG: "invalid_catalog"})
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=self._schema())

    def _schema(self):
        current = self.config_entry.options
        return vol.Schema({
            vol.Required(CONF_BOX_COLOR, default=current.get(CONF_BOX_COLOR, DEFAULT_COLOR)): str,
            vol.Optional(CONF_FALLBACK_COVER, default=current.get(CONF_FALLBACK_COVER, "")): str,
            vol.Required(CONF_CATALOG, default=current.get(CONF_CATALOG, "{}")): str,
        })
