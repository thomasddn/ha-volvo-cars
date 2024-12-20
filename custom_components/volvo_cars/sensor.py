"""Volvo Cars sensors."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,  # type: ignore # noqa: PGH003
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,  # type: ignore # noqa: PGH003
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity_description import VolvoCarsDescription

from .const import OPT_FUEL_CONSUMPTION_UNIT, OPT_UNIT_MPG_UK, OPT_UNIT_MPG_US
from .coordinator import VolvoCarsConfigEntry, VolvoCarsDataCoordinator
from .entity import VolvoCarsEntity, value_to_translation_key
from .volvo.models import (
    VolvoCarsApiBaseModel,
    VolvoCarsValue,
    VolvoCarsValueField,
    VolvoCarsVehicle,
)

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class VolvoCarsSensorDescription(VolvoCarsDescription, SensorEntityDescription):
    """Describes a Volvo Cars sensor entity."""

    value_fn: Callable[[VolvoCarsValue, VolvoCarsConfigEntry], Any] | None = None
    available_fn: Callable[[VolvoCarsVehicle], bool] = lambda vehicle: True
    unit_fn: Callable[[VolvoCarsConfigEntry], str] | None = None


def _availability_status(field: VolvoCarsValue, _: VolvoCarsConfigEntry) -> str:
    reason = field.get("unavailable_reason")
    return reason if reason else field.value


def _calculate_time_to_service(field: VolvoCarsValue, _: VolvoCarsConfigEntry) -> int:
    # Always express value in days
    if isinstance(field, VolvoCarsValueField) and field.unit == "months":
        return field.value * 30

    return field.value


def _calculate_engine_time_to_service(
    field: VolvoCarsValue, _: VolvoCarsConfigEntry
) -> int:
    # Express value in days instead of hours
    return round(field.value / 24)


def _determine_fuel_consumption_unit(entry: VolvoCarsConfigEntry) -> str:
    unit_key = entry.options[OPT_FUEL_CONSUMPTION_UNIT]

    if unit_key in (OPT_UNIT_MPG_UK, OPT_UNIT_MPG_US):
        return "mpg"

    return "L/100km"


def _convert_fuel_consumption(
    field: VolvoCarsValue, entry: VolvoCarsConfigEntry
) -> Decimal:
    unit_key = entry.options[OPT_FUEL_CONSUMPTION_UNIT]

    if unit_key == OPT_UNIT_MPG_UK:
        return round(Decimal(282.481) / Decimal(field.value), 2)

    if unit_key == OPT_UNIT_MPG_US:
        return round(Decimal(235.215) / Decimal(field.value), 2)

    return field.value


# pylint: disable=unexpected-keyword-arg
SENSORS: tuple[VolvoCarsSensorDescription, ...] = (
    VolvoCarsSensorDescription(
        key="api_status",
        translation_key="api_status",
        api_field="apiStatus",
        icon="mdi:api",
    ),
    VolvoCarsSensorDescription(
        key="availability",
        translation_key="availability",
        api_field="availabilityStatus",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "available",
            "car_in_use",
            "no_internet",
            "power_saving_mode",
            "unspecified",
        ],
        value_fn=_availability_status,
        icon="mdi:radio-tower",
    ),
    VolvoCarsSensorDescription(
        key="average_energy_consumption",
        translation_key="average_energy_consumption",
        api_field=["averageEnergyConsumption", "averageEnergyConsumptionAutomatic"],
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:car-electric",
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
    ),
    VolvoCarsSensorDescription(
        key="average_fuel_consumption",
        translation_key="average_fuel_consumption",
        api_field=["averageFuelConsumption", "averageFuelConsumptionAutomatic"],
        native_unit_of_measurement="L/100km",
        icon="mdi:gas-station",
        available_fn=lambda vehicle: vehicle.has_combustion_engine(),
        unit_fn=_determine_fuel_consumption_unit,
        value_fn=_convert_fuel_consumption,
    ),
    VolvoCarsSensorDescription(
        key="average_speed",
        translation_key="average_speed",
        api_field=["averageSpeed", "averageSpeedAutomatic"],
        native_unit_of_measurement="km/h",
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
    ),
    VolvoCarsSensorDescription(
        key="battery_charge_level",
        translation_key="battery_charge_level",
        api_field="batteryChargeLevel",
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
    ),
    VolvoCarsSensorDescription(
        key="average_speed_automatic",
        translation_key="average_speed_automatic",
        api_field="averageSpeedAutomatic",
        native_unit_of_measurement="km/h",
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
    ),
    VolvoCarsSensorDescription(
        key="charging_connection_status",
        translation_key="charging_connection_status",
        api_field="chargingConnectionStatus",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "connection_status_connected_ac",
            "connection_status_connected_dc",
            "connection_status_disconnected",
            "connection_status_fault",
            "connection_status_unspecified",
        ],
        icon="mdi:ev-plug-ccs2",
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
    ),
    VolvoCarsSensorDescription(
        key="charging_system_status",
        translation_key="charging_system_status",
        api_field="chargingSystemStatus",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "charging_system_charging",
            "charging_system_done",
            "charging_system_fault",
            "charging_system_idle",
            "charging_system_scheduled",
            "charging_system_unspecified",
        ],
        icon="mdi:ev-station",
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
    ),
    VolvoCarsSensorDescription(
        key="distance_to_empty_battery",
        translation_key="distance_to_empty_battery",
        api_field="distanceToEmptyBattery",
        native_unit_of_measurement="km",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge-empty",
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
    ),
    VolvoCarsSensorDescription(
        key="distance_to_empty_tank",
        translation_key="distance_to_empty_tank",
        api_field="distanceToEmptyTank",
        native_unit_of_measurement="km",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge-empty",
        available_fn=lambda vehicle: vehicle.has_combustion_engine(),
    ),
    VolvoCarsSensorDescription(
        key="distance_to_service",
        translation_key="distance_to_service",
        api_field="distanceToService",
        native_unit_of_measurement="km",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wrench-clock",
    ),
    VolvoCarsSensorDescription(
        key="engine_time_to_service",
        translation_key="engine_time_to_service",
        api_field="engineHoursToService",
        native_unit_of_measurement="d",
        value_fn=_calculate_engine_time_to_service,
        icon="mdi:wrench-clock",
    ),
    VolvoCarsSensorDescription(
        key="estimated_charging_time",
        translation_key="estimated_charging_time",
        api_field="estimatedChargingTime",
        native_unit_of_measurement="min",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-clock",
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
    ),
    VolvoCarsSensorDescription(
        key="fuel_amount",
        translation_key="fuel_amount",
        api_field="fuelAmount",
        native_unit_of_measurement="L",
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gas-station",
        available_fn=lambda vehicle: vehicle.has_combustion_engine(),
    ),
    VolvoCarsSensorDescription(
        key="odometer",
        translation_key="odometer",
        api_field="odometer",
        native_unit_of_measurement="km",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:counter",
    ),
    VolvoCarsSensorDescription(
        key="time_to_service",
        translation_key="time_to_service",
        api_field="timeToService",
        native_unit_of_measurement="d",
        value_fn=_calculate_time_to_service,
        icon="mdi:wrench-clock",
    ),
    VolvoCarsSensorDescription(
        key="trip_meter_automatic",
        translation_key="trip_meter_automatic",
        api_field="tripMeterAutomatic",
        native_unit_of_measurement="km",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:map-marker-distance",
    ),
    VolvoCarsSensorDescription(
        key="trip_meter_manual",
        translation_key="trip_meter_manual",
        api_field="tripMeterManual",
        native_unit_of_measurement="km",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:map-marker-distance",
    ),
)


async def async_setup_entry(
    _: HomeAssistant,
    entry: VolvoCarsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = entry.runtime_data.coordinator
    sensors = [
        VolvoCarsSensor(coordinator, description)
        for description in SENSORS
        if description.available_fn(coordinator.vehicle)
    ]

    async_add_entities(sensors)


class VolvoCarsSensor(VolvoCarsEntity, SensorEntity):
    """Representation of a Volvo Cars sensor."""

    entity_description: VolvoCarsSensorDescription

    def __init__(
        self,
        coordinator: VolvoCarsDataCoordinator,
        description: VolvoCarsSensorDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, Platform.SENSOR)

        if description.unit_fn:
            self._attr_native_unit_of_measurement = description.unit_fn(
                self.coordinator.entry
            )

    def _update_state(self, api_field: VolvoCarsApiBaseModel | None) -> None:
        if not isinstance(api_field, VolvoCarsValue):
            return

        native_value = (
            api_field.value
            if self.entity_description.value_fn is None
            else self.entity_description.value_fn(api_field, self.coordinator.entry)
        )

        if self.device_class == SensorDeviceClass.ENUM:
            native_value = value_to_translation_key(str(native_value))

        self._attr_native_value = native_value
