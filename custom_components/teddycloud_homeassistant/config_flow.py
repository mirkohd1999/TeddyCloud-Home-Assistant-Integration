"""TeddyCloud Home Assistant Integration configuration UI."""
import json
import asyncio
import re
from homeassistant.components import mqtt
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    DOMAIN, CONF_PREFIX, CONF_BOX_ID, CONF_BOX_NAME, CONF_BOX_COLOR,
    CONF_CATALOG, CONF_FALLBACK_COVER, DEFAULT_PREFIX, DEFAULT_COLOR,
)


BOX_COLORS = {
    "#D82F38": "Rot",
    "#5B5D60": "Anthrazit",
    "#78C9E5": "Hellblau",
    "#E95B9D": "Pink",
    "#913A78": "Beere",
    "#8AAB32": "Grün",
    "#B8D75A": "Hellgrün",
    "#35BFC3": "Türkis",
    "#26272B": "Schwarz",
    "#243B70": "Marineblau",
    "#8f77c7": "Lila / Standard",
}


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
        """Offer MQTT discovery first, with manual setup as fallback."""
        if user_input is not None:
            if user_input.get("setup_mode") == "manual":
                return await self.async_step_manual()
            return await self.async_step_discover()
        return self.async_show_menu(step_id="user", menu_options=["discover", "manual"])

    async def async_step_discover(self, user_input=None):
        """Explain how to wake the box before beginning live discovery."""
        if user_input is None:
            return self.async_show_form(step_id="discover", data_schema=vol.Schema({vol.Optional("search_prefix", default=""): str}))
        self._search_prefix = user_input.get("search_prefix", "").strip().strip("/")
        self._scan_task = self.hass.async_create_task(self._scan_mqtt())
        self._discovered = None
        return await self.async_step_scan()

    async def _scan_mqtt(self):
        """Find boxes using retained or freshly published MQTT box status."""
        seen = set()
        found = asyncio.Event()

        @callback
        def receive(message):
            match = re.fullmatch(r"(.+)/box/([^/]+)/([^/]+)", message.topic)
            if match and (not self._search_prefix or match.group(1) == self._search_prefix) and match.group(3) in (
                "LastSeen", "Playback", "ContentTitle", "ContentAudioId",
                "VolumeLevel", "VolumedB", "Charger", "TagValid",
                "ContentPicture",
            ):
                seen.add((match.group(1), match.group(2)))
                found.set()

        if not await mqtt.async_wait_for_mqtt_client(self.hass):
            raise RuntimeError("mqtt_unavailable")
        unsubscribe = await mqtt.async_subscribe(
            self.hass, f"{self._search_prefix}/box/+/+" if self._search_prefix else "#", receive, 0
        )
        try:
            # Return immediately for the first confirmed box status.
            try:
                await asyncio.wait_for(found.wait(), timeout=25)
            except asyncio.TimeoutError:
                pass
        finally:
            unsubscribe()
        return sorted(seen)

    async def async_step_scan(self, user_input=None):
        """Display a live progress message while MQTT discovery runs."""
        if not hasattr(self, "_scan_task") or self._scan_task is None:
            self._search_prefix = ""
            self._scan_task = self.hass.async_create_task(self._scan_mqtt())
        if not self._scan_task.done():
            return self.async_show_progress(
                step_id="scan",
                progress_action="searching_boxes",
                progress_task=self._scan_task,
            )
        return self.async_show_progress_done(next_step_id="scan_result")

    async def async_step_scan_result(self, user_input=None):
        if getattr(self, "_discovered", None) is None:
            try:
                self._discovered = self._scan_task.result()
            except Exception:
                return self.async_abort(reason="mqtt_unavailable")
        if not self._discovered:
            return self.async_show_menu(
                step_id="not_found", menu_options=["discover", "manual"]
            )
        options = {
            f"{prefix}|{box}": f"{box} ({prefix})"
            for prefix, box in self._discovered
        }
        if user_input is not None:
            prefix, box = user_input["box"].split("|", 1)
            return await self._create_box(prefix, box, user_input["name"], user_input[CONF_BOX_COLOR])
        return self.async_show_form(step_id="scan_result", data_schema=vol.Schema({
            vol.Required("box"): vol.In(options),
            vol.Required("name", default="Meine Toniebox"): str,
            vol.Required(CONF_BOX_COLOR, default=DEFAULT_COLOR): vol.In(BOX_COLORS),
        }))

    async def async_step_not_found(self, user_input=None):
        return self.async_show_menu(step_id="not_found", menu_options=["discover", "manual"])

    async def _create_box(self, prefix, box, name, color=DEFAULT_COLOR):
        prefix, box, name = prefix.strip("/"), box.strip("/"), name.strip()
        if not prefix or not box or not name or "/" in box:
            return self.async_abort(reason="invalid_box")
        key = f"{prefix}/{box}"
        await self.async_set_unique_id(key)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=name, data={
            CONF_PREFIX: prefix, CONF_BOX_ID: box, CONF_BOX_NAME: name,
            CONF_BOX_COLOR: color
        })

    async def async_step_manual(self, user_input=None):
        errors = {}
        if user_input is not None:
            return await self._create_box(user_input[CONF_PREFIX], user_input[CONF_BOX_ID], user_input[CONF_BOX_NAME], user_input[CONF_BOX_COLOR])
        return self.async_show_form(step_id="manual", data_schema=vol.Schema({
            vol.Required(CONF_BOX_ID): str,
            vol.Required(CONF_BOX_NAME, default="Meine Toniebox"): str,
            vol.Required(CONF_PREFIX, default=DEFAULT_PREFIX): str,
            vol.Required(CONF_BOX_COLOR, default=DEFAULT_COLOR): vol.In(BOX_COLORS),
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
            vol.Required(CONF_BOX_COLOR, default=current.get(CONF_BOX_COLOR, self.config_entry.data.get(CONF_BOX_COLOR, DEFAULT_COLOR))): str,
            vol.Required("online_images", default=current.get("online_images", True)): bool,
            vol.Optional(CONF_FALLBACK_COVER, default=current.get(CONF_FALLBACK_COVER, "")): str,
            vol.Optional("teddycloud_url", default=current.get("teddycloud_url", "")): str,
            vol.Required(CONF_CATALOG, default=current.get(CONF_CATALOG, "{}")): str,
        })
