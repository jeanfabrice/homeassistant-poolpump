"""Sensor entities for the Pool Pump integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    KEY_AC_VOLTAGE,
    KEY_COMPRESSOR_LOAD_PCT,
    KEY_COMPRESSOR_RATE,
    KEY_DC_LINK_CURRENT_A,
    KEY_DC_LINK_VOLTAGE_V,
    KEY_MAX_INPUT_W,
    KEY_MOTOR_CURRENT_A,
    KEY_TEMP_AMBIENT,
    KEY_TEMP_INLET,
    KEY_TEMP_OUTLET,
)
from .coordinator import PoolPumpCoordinator


@dataclass(frozen=True, kw_only=True)
class PoolPumpSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription — no extra fields needed for now."""


SENSOR_DESCRIPTIONS: tuple[PoolPumpSensorDescription, ...] = (
    PoolPumpSensorDescription(
        key=KEY_AC_VOLTAGE,
        name="AC Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PoolPumpSensorDescription(
        key=KEY_MOTOR_CURRENT_A,
        name="Motor Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PoolPumpSensorDescription(
        key=KEY_DC_LINK_VOLTAGE_V,
        name="DC Link Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PoolPumpSensorDescription(
        key=KEY_DC_LINK_CURRENT_A,
        name="DC Link Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PoolPumpSensorDescription(
        key=KEY_COMPRESSOR_LOAD_PCT,
        name="Compressor Load",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
    ),
    PoolPumpSensorDescription(
        key=KEY_MAX_INPUT_W,
        name="Max Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
        # No state_class: this is a rated constant, not a live measurement.
    ),
    PoolPumpSensorDescription(
        key=KEY_TEMP_AMBIENT,
        name="Ambient Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PoolPumpSensorDescription(
        key=KEY_TEMP_INLET,
        name="Inlet Water Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PoolPumpSensorDescription(
        key=KEY_TEMP_OUTLET,
        name="Outlet Water Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PoolPumpSensorDescription(
        key=KEY_COMPRESSOR_RATE,
        name="Compressor Frequency",
        native_unit_of_measurement="Hz",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sine-wave",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PoolPumpCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PoolPumpSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class PoolPumpSensor(CoordinatorEntity[PoolPumpCoordinator], SensorEntity):
    """A single sensor entity reading one field from the snapshot."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PoolPumpCoordinator,
        entry: ConfigEntry,
        description: PoolPumpSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    @property
    def _snapshot(self) -> dict | None:
        return (self.coordinator.data or {}).get("snapshot")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._snapshot is not None

    @property
    def native_value(self) -> float | int | str | None:
        return (self._snapshot or {}).get(self.entity_description.key)
