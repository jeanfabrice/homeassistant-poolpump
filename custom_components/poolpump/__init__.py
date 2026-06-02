"""Pool Pump integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_HOST, CONF_VERIFY_SSL, DOMAIN
from .coordinator import PoolPumpCoordinator

PLATFORMS = ["climate", "sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pool Pump from a config entry."""
    host = entry.data[CONF_HOST]
    verify_ssl = entry.data[CONF_VERIFY_SSL]

    # Dedicated session per config entry so it's closed cleanly on unload.
    session = async_create_clientsession(hass, verify_ssl=verify_ssl)

    coordinator = PoolPumpCoordinator(hass, host, verify_ssl, session)

    # Raises ConfigEntryNotReady if the server is unreachable at startup —
    # HA will retry automatically. Do not catch here.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
