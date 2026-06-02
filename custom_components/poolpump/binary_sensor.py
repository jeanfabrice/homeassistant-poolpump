"""Binary sensor entities for the Pool Pump integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, KEY_STATUS_WATERPUMP
from .coordinator import PoolPumpCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PoolPumpCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PoolPumpWaterPumpSensor(coordinator, entry),
            PoolPumpConnectedSensor(coordinator, entry),
        ]
    )


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})


class PoolPumpWaterPumpSensor(CoordinatorEntity[PoolPumpCoordinator], BinarySensorEntity):
    """Indicates whether the circulation water pump is running."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_has_entity_name = True
    _attr_name = "Water Pump"

    def __init__(self, coordinator: PoolPumpCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_waterpump"
        self._attr_device_info = _device_info(entry)

    @property
    def _snapshot(self) -> dict | None:
        return (self.coordinator.data or {}).get("snapshot")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._snapshot is not None

    @property
    def is_on(self) -> bool | None:
        snapshot = self._snapshot or {}
        val = snapshot.get(KEY_STATUS_WATERPUMP)
        return bool(val) if val is not None else None


class PoolPumpConnectedSensor(CoordinatorEntity[PoolPumpCoordinator], BinarySensorEntity):
    """Indicates whether the WiFi module has an active Modbus TCP session."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_name = "Module Connected"

    def __init__(self, coordinator: PoolPumpCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_connected"
        self._attr_device_info = _device_info(entry)

    @property
    def available(self) -> bool:
        # healthz is available even when no Modbus telemetry has arrived yet.
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        healthz = (self.coordinator.data or {}).get("healthz", {})
        return bool(healthz.get("connected", False))
