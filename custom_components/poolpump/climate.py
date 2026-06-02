"""Climate entity for the Pool Pump integration."""

from __future__ import annotations

import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CMD_MODE_AUTO,
    CMD_MODE_BOOST,
    CMD_MODE_SILENT,
    CMD_OFF,
    CMD_ON,
    CMD_SETMODE_AUTO,
    CMD_SETMODE_COOL,
    CMD_SETMODE_HEAT,
    DOMAIN,
    KEY_BOOST,
    KEY_SILENCE,
    KEY_STATUS_MALFUNC,
    KEY_STATUS_MODE,
    KEY_STATUS_WATERPUMP,
    KEY_SWITCHED_ON,
    KEY_TEMP_AMBIENT,
    KEY_TEMP_INLET,
    KEY_TEMP_OUTLET,
    KEY_TEMP_TARGET,
    KEY_COMPRESSOR_RATE,
    PRESET_AUTO,
    PRESET_BOOST,
    PRESET_SILENT,
    STATUS_MODE_AUTO,
    STATUS_MODE_COOL,
    STATUS_MODE_HEAT,
    TEMP_MAX,
    TEMP_MIN,
    TEMP_STEP,
)
from .coordinator import PoolPumpCoordinator

_LOGGER = logging.getLogger(__name__)

# STATUS_MODE value → HVACMode (pump is on)
_STATUS_MODE_TO_HVAC: dict[int, HVACMode] = {
    STATUS_MODE_HEAT: HVACMode.HEAT,
    STATUS_MODE_AUTO: HVACMode.AUTO,
    STATUS_MODE_COOL: HVACMode.COOL,
}

# HVACMode → setmode command (excludes OFF which uses CMD_OFF)
_HVAC_TO_SETMODE: dict[HVACMode, str] = {
    HVACMode.HEAT: CMD_SETMODE_HEAT,
    HVACMode.AUTO: CMD_SETMODE_AUTO,
    HVACMode.COOL: CMD_SETMODE_COOL,
}

# Preset → mode command
_PRESET_TO_CMD: dict[str, str] = {
    PRESET_AUTO: CMD_MODE_AUTO,
    PRESET_BOOST: CMD_MODE_BOOST,
    PRESET_SILENT: CMD_MODE_SILENT,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PoolPumpCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PoolPumpClimate(coordinator, entry)])


class PoolPumpClimate(CoordinatorEntity[PoolPumpCoordinator], ClimateEntity):
    """Main climate entity — maps HVAC modes and presets to poolpump verbs."""

    _attr_has_entity_name = True
    _attr_name = None  # Entity name = device name ("Pool Pump")

    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO, HVACMode.COOL]
    _attr_preset_modes = [PRESET_AUTO, PRESET_BOOST, PRESET_SILENT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = TEMP_STEP
    _attr_min_temp = TEMP_MIN
    _attr_max_temp = TEMP_MAX

    def __init__(self, coordinator: PoolPumpCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Pool Pump",
            manufacturer="poolpump",
            model="Pool Heat Pump",
        )

    @property
    def _snapshot(self) -> dict | None:
        return (self.coordinator.data or {}).get("snapshot")

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        snapshot = self._snapshot
        if snapshot is None:
            return False
        # SWITCHED_ON can be 0 (off) or 1 (on) — both are valid.
        # Only None means "no telemetry yet".
        return snapshot.get(KEY_SWITCHED_ON) is not None

    @property
    def hvac_mode(self) -> HVACMode:
        snapshot = self._snapshot or {}
        if snapshot.get(KEY_SWITCHED_ON) == 0:
            return HVACMode.OFF
        status_mode = snapshot.get(KEY_STATUS_MODE)
        return _STATUS_MODE_TO_HVAC.get(status_mode, HVACMode.AUTO)

    @property
    def preset_mode(self) -> str:
        snapshot = self._snapshot or {}
        if snapshot.get(KEY_BOOST) == 1:
            return PRESET_BOOST
        if snapshot.get(KEY_SILENCE) == 1:
            return PRESET_SILENT
        return PRESET_AUTO

    @property
    def current_temperature(self) -> float | None:
        return (self._snapshot or {}).get(KEY_TEMP_INLET)

    @property
    def target_temperature(self) -> float | None:
        return (self._snapshot or {}).get(KEY_TEMP_TARGET)

    @property
    def extra_state_attributes(self) -> dict:
        snapshot = self._snapshot or {}
        return {
            "temp_outlet": snapshot.get(KEY_TEMP_OUTLET),
            "temp_ambient": snapshot.get(KEY_TEMP_AMBIENT),
            "compressor_rate_hz": snapshot.get(KEY_COMPRESSOR_RATE),
            "status_waterpump": snapshot.get(KEY_STATUS_WATERPUMP),
            "status_malfunc": snapshot.get(KEY_STATUS_MALFUNC),
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_send_command(CMD_OFF)
        else:
            # If pump is currently off, turn it on first.
            if self.hvac_mode == HVACMode.OFF:
                await self.coordinator.async_send_command(CMD_ON)
            setmode_cmd = _HVAC_TO_SETMODE[hvac_mode]
            await self.coordinator.async_send_command(setmode_cmd)
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.coordinator.async_send_command(_PRESET_TO_CMD[preset_mode])
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        temp_int = int(temp)
        if not (TEMP_MIN <= temp_int <= TEMP_MAX):
            _LOGGER.warning(
                "poolpump: set_temperature %d°C out of range [%d, %d]",
                temp_int,
                TEMP_MIN,
                TEMP_MAX,
            )
            return
        # Use "set-target" (not "settemp") to avoid implicit side-effects
        # (settemp also turns the pump on and forces heat mode).
        await self.coordinator.async_send_command(f"set-target {temp_int}")
        self.async_write_ha_state()
