"""Config flow for SPC FlexC."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.helpers import selector

from .const import (
    CONF_CLOCK_SYNC,
    CONF_COMMAND_PASSWORD,
    CONF_COMMAND_USERNAME,
    CONF_DOOR_CONTROLLERS,
    CONF_ENGINEER_PASSWORD,
    CONF_ENGINEER_USERNAME,
    CONF_KEY,
    CONF_PORT,
    CONF_SIDEBAR_PANEL,
    CONF_USER_ALIASES,
    CONF_WIRELESS_RADIO_IDS,
    CONF_WIRELESS_ZONES,
    DEFAULT_PORT,
    DOMAIN,
)


def _without_empty_engineer_login(data: dict[str, Any]) -> dict[str, Any]:
    """Drop the optional engineer login unless both fields are filled in."""
    cleaned = dict(data)
    if not (
        cleaned.get(CONF_ENGINEER_USERNAME) and cleaned.get(CONF_ENGINEER_PASSWORD)
    ):
        cleaned.pop(CONF_ENGINEER_USERNAME, None)
        cleaned.pop(CONF_ENGINEER_PASSWORD, None)
    return cleaned


def _config_schema(
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    """Return the SPC FlexC configuration schema."""
    defaults = defaults or {}

    return vol.Schema(
        {
            vol.Required(
                CONF_HOST,
                default=defaults.get(CONF_HOST, ""),
            ): str,
            vol.Optional(
                CONF_PORT,
                default=defaults.get(CONF_PORT, DEFAULT_PORT),
            ): int,
            vol.Required(
                CONF_KEY,
                default=defaults.get(CONF_KEY, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                )
            ),
            vol.Required(
                CONF_COMMAND_USERNAME,
                default=defaults.get(CONF_COMMAND_USERNAME, ""),
            ): str,
            vol.Required(
                CONF_COMMAND_PASSWORD,
                default=defaults.get(CONF_COMMAND_PASSWORD, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                )
            ),
            vol.Optional(
                CONF_ENGINEER_USERNAME,
                default=defaults.get(CONF_ENGINEER_USERNAME, ""),
            ): str,
            vol.Optional(
                CONF_ENGINEER_PASSWORD,
                default=defaults.get(CONF_ENGINEER_PASSWORD, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                )
            ),
        }
    )


class SpcFlexCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SPC FlexC."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SpcFlexCOptionsFlow:
        """Expose display-name overrides in integration options."""
        return SpcFlexCOptionsFlow()

    def _host_is_configured(
        self,
        host: str,
        *,
        exclude_entry_id: str | None = None,
    ) -> bool:
        """Return whether the SPC host is already configured."""
        return any(
            entry.entry_id != exclude_entry_id and entry.data.get(CONF_HOST) == host
            for entry in self._async_current_entries()
        )

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial configuration step."""
        if user_input is not None:
            if self._host_is_configured(user_input[CONF_HOST]):
                return self.async_abort(reason="already_configured")

            # Do not use the IP address as the config entry unique_id.
            # A stable panel identifier (serial number) is assigned after
            # PANEL_SUMMARY is successfully retrieved during setup.
            return self.async_create_entry(
                title=f"SPC {user_input[CONF_HOST]}",
                data=_without_empty_engineer_login(user_input),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_config_schema(),
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of an existing SPC FlexC entry."""
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            if self._host_is_configured(
                user_input[CONF_HOST],
                exclude_entry_id=entry.entry_id,
            ):
                return self.async_abort(reason="already_configured")

            return self.async_update_reload_and_abort(
                entry,
                data=_without_empty_engineer_login({**entry.data, **user_input}),
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_config_schema(dict(entry.data)),
        )


class SpcFlexCOptionsFlow(config_entries.OptionsFlow):
    """User-facing display name overrides; never change SPC credentials."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure one alias per line in USER_ID=Display name format."""
        if user_input is not None:
            from .user_names import parse_user_aliases

            try:
                aliases = parse_user_aliases(user_input.get(CONF_USER_ALIASES, ""))
            except ValueError:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._schema(
                        user_input.get(CONF_USER_ALIASES, ""),
                        bool(user_input.get(CONF_SIDEBAR_PANEL, True)),
                        bool(user_input.get(CONF_CLOCK_SYNC, True)),
                    ),
                    errors={"base": "invalid_aliases"},
                )
            self._aliases = aliases
            self._sidebar = bool(user_input.get(CONF_SIDEBAR_PANEL, True))
            self._clock_sync = bool(user_input.get(CONF_CLOCK_SYNC, True))
            return await self.async_step_doors()
        existing = self.config_entry.options.get(CONF_USER_ALIASES, {})
        default = "\n".join(
            f"{user_id}={name}" for user_id, name in sorted(existing.items())
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self._schema(
                default,
                self.config_entry.options.get(CONF_SIDEBAR_PANEL, True),
                self.config_entry.options.get(CONF_CLOCK_SYNC, True),
            ),
        )

    async def async_step_doors(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Choose the door controller of each door (default: by number)."""
        coordinator = getattr(self.config_entry, "runtime_data", None)
        doors = dict(getattr(getattr(coordinator, "data", None), "doors", {}) or {})
        controllers = {
            serial: device
            for serial, device in (
                getattr(getattr(coordinator, "data", None), "xbus_devices", {}) or {}
            ).items()
            if device.device_type == 6
        }
        aliases = getattr(
            self, "_aliases", self.config_entry.options.get(CONF_USER_ALIASES, {})
        )
        if not doors or not controllers:
            self._result = {
                **self.config_entry.options,
                CONF_USER_ALIASES: aliases,
                CONF_SIDEBAR_PANEL: getattr(
                    self,
                    "_sidebar",
                    self.config_entry.options.get(CONF_SIDEBAR_PANEL, True),
                ),
                CONF_CLOCK_SYNC: getattr(
                    self,
                    "_clock_sync",
                    self.config_entry.options.get(CONF_CLOCK_SYNC, True),
                ),
            }
            return await self.async_step_wireless()
        if user_input is not None:
            chosen = {
                key.removeprefix("door_"): value
                for key, value in user_input.items()
                if value != "auto"
            }
            self._result = {
                **self.config_entry.options,
                CONF_USER_ALIASES: aliases,
                CONF_SIDEBAR_PANEL: getattr(
                    self,
                    "_sidebar",
                    self.config_entry.options.get(CONF_SIDEBAR_PANEL, True),
                ),
                CONF_CLOCK_SYNC: getattr(
                    self,
                    "_clock_sync",
                    self.config_entry.options.get(CONF_CLOCK_SYNC, True),
                ),
                CONF_DOOR_CONTROLLERS: chosen,
            }
            return await self.async_step_wireless()
        current = self.config_entry.options.get(CONF_DOOR_CONTROLLERS) or {}
        options = [selector.SelectOptionDict(value="auto", label="Auto")] + [
            selector.SelectOptionDict(
                value=serial,
                label=f"{device.name or 'Door controller'} ({device.device_id})",
            )
            for serial, device in sorted(
                controllers.items(), key=lambda item: item[1].device_id or 0
            )
        ]
        schema = vol.Schema(
            {
                vol.Optional(
                    f"door_{door_id}", default=current.get(str(door_id), "auto")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, mode=selector.SelectSelectorMode.DROPDOWN
                    )
                )
                for door_id in sorted(doors)
            }
        )
        return self.async_show_form(
            step_id="doors",
            data_schema=schema,
            description_placeholders={
                "doors": ", ".join(
                    f"{door_id}: {door.name or door.zone_name or door_id}"
                    for door_id, door in sorted(doors.items())
                )
            },
        )

    async def async_step_wireless(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Choose which zones are on the wireless receiver."""
        from .flexc.device import zone_hardware

        result = getattr(self, "_result", dict(self.config_entry.options))
        coordinator = getattr(self.config_entry, "runtime_data", None)
        data = getattr(coordinator, "data", None)
        if (
            coordinator is None
            or data is None
            or not getattr(data, "wireless_receiver", False)
        ):
            return self.async_create_entry(title="", data=result)
        if user_input is not None:
            self._result = {
                **result,
                CONF_WIRELESS_ZONES: [
                    str(z) for z in user_input.get(CONF_WIRELESS_ZONES, [])
                ],
            }
            return await self.async_step_radio_ids()
        candidates = {}
        for zone_id, zone in sorted(data.zones.items()):
            kind, _ = zone_hardware(coordinator, zone_id)
            if kind in ("wireless", "panel") and zone_id > 8:
                candidates[str(zone_id)] = f"{zone_id}: {zone.name or zone_id}"
        current = self.config_entry.options.get(CONF_WIRELESS_ZONES)
        default = (
            [str(z) for z in current]
            if current is not None
            else [z for z in candidates]
        )
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_WIRELESS_ZONES, default=default
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=k, label=v)
                            for k, v in candidates.items()
                        ],
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="wireless", data_schema=schema)

    async def async_step_radio_ids(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Enter the radio ID of the detector on each wireless zone.

        FlexC does not tell which detector is on which zone; the panel's web
        page does (Status > Hardware > Wireless status).
        """
        result = dict(getattr(self, "_result", self.config_entry.options))
        zones = [str(z) for z in result.get(CONF_WIRELESS_ZONES) or []]
        if not zones:
            return self.async_create_entry(title="", data=result)
        if user_input is not None:
            radio_ids = {
                zone: str(user_input[f"zone_{zone}"]).strip()
                for zone in zones
                if str(user_input.get(f"zone_{zone}") or "").strip().isdigit()
            }
            return self.async_create_entry(
                title="", data={**result, CONF_WIRELESS_RADIO_IDS: radio_ids}
            )
        coordinator = getattr(self.config_entry, "runtime_data", None)
        data = getattr(coordinator, "data", None)
        names = {str(k): v.name for k, v in getattr(data, "zones", {}).items()}
        current = self.config_entry.options.get(CONF_WIRELESS_RADIO_IDS) or {}
        schema = vol.Schema(
            {
                vol.Optional(
                    f"zone_{zone}",
                    description={"suggested_value": current.get(zone, "")},
                ): selector.TextSelector()
                for zone in zones
            }
        )
        return self.async_show_form(
            step_id="radio_ids",
            data_schema=schema,
            description_placeholders={
                "zones": ", ".join(
                    f"zone_{zone} = {zone} {names.get(zone) or ''}".strip()
                    for zone in zones
                )
            },
        )

    @staticmethod
    def _schema(
        default: str, sidebar: bool = True, clock_sync: bool = True
    ) -> vol.Schema:
        return vol.Schema(
            {
                vol.Optional(CONF_USER_ALIASES, default=default): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
                vol.Optional(
                    CONF_SIDEBAR_PANEL, default=sidebar
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_CLOCK_SYNC, default=clock_sync
                ): selector.BooleanSelector(),
            }
        )
