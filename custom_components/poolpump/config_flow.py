"""Config flow for the Pool Pump integration."""

from __future__ import annotations

import asyncio
import logging

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HOST, CONF_VERIFY_SSL, DOMAIN

_LOGGER = logging.getLogger(__name__)

_SCHEMA = {
    vol.Required(CONF_HOST, default="http://192.168.1.42:8090"): str,
    vol.Optional(CONF_VERIFY_SSL, default=True): bool,
}


class PoolPumpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pool Pump."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> PoolPumpOptionsFlow:
        return PoolPumpOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")
            verify_ssl = user_input[CONF_VERIFY_SSL]
            try:
                await self._test_connection(host, verify_ssl)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during poolpump config flow")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Pool Pump ({host})",
                    data={CONF_HOST: host, CONF_VERIFY_SSL: verify_ssl},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(_SCHEMA),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")
            verify_ssl = user_input[CONF_VERIFY_SSL]
            try:
                await self._test_connection(host, verify_ssl)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during poolpump reconfigure")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data={CONF_HOST: host, CONF_VERIFY_SSL: verify_ssl},
                    reason="reconfigure_successful",
                )

        current_host = entry.data.get(CONF_HOST, "http://192.168.1.42:8090")
        current_ssl = entry.data.get(CONF_VERIFY_SSL, True)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=current_host): str,
                vol.Optional(CONF_VERIFY_SSL, default=current_ssl): bool,
            }),
            errors=errors,
        )

    async def _test_connection(self, host: str, verify_ssl: bool) -> None:
        """Probe GET /healthz. Raises CannotConnect on any failure."""
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(10):
                resp = await session.get(f"{host}/healthz", ssl=verify_ssl)
                resp.raise_for_status()
        except Exception as err:
            raise CannotConnect from err


class PoolPumpOptionsFlow(config_entries.OptionsFlow):
    """Handle Pool Pump options (reconfiguration after setup)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")
            verify_ssl = user_input[CONF_VERIFY_SSL]
            try:
                await self._test_connection(host, verify_ssl)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during poolpump options flow")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    data={CONF_HOST: host, CONF_VERIFY_SSL: verify_ssl},
                )

        current = self._config_entry.options or self._config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=current.get(CONF_HOST, "http://192.168.1.42:8090")): str,
                vol.Optional(CONF_VERIFY_SSL, default=current.get(CONF_VERIFY_SSL, True)): bool,
            }),
            errors=errors,
        )

    async def _test_connection(self, host: str, verify_ssl: bool) -> None:
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(10):
                resp = await session.get(f"{host}/healthz", ssl=verify_ssl)
                resp.raise_for_status()
        except Exception as err:
            raise CannotConnect from err


class CannotConnect(HomeAssistantError):
    """Error raised when poolpump server is unreachable during config flow."""
