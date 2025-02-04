"""Volvo Cars sensors."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    Platform,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTime,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_BATTERY_CAPACITY,
    DATA_REQUEST_COUNT,
    OPT_ENERGY_CONSUMPTION_UNIT,
    OPT_FUEL_CONSUMPTION_UNIT,
    OPT_UNIT_ENERGY_KWH_PER_100KM,
    OPT_UNIT_ENERGY_MILES_PER_KWH,
    OPT_UNIT_LITER_PER_100KM,
    OPT_UNIT_MPG_UK,
    OPT_UNIT_MPG_US,
)
from .coordinator import VolvoCarsConfigEntry, VolvoCarsDataCoordinator
from .entity import VolvoCarsEntity, value_to_translation_key
from .entity_description import VolvoCarsDescription
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
    unit_fn: Callable[[VolvoCarsConfigEntry], str] | None = None
    available_fn: Callable[[VolvoCarsVehicle], bool] = lambda vehicle: True


def _availability_status(field: VolvoCarsValue, _: VolvoCarsConfigEntry) -> str:
    reason = field.get("unavailable_reason")
    return reason if reason else str(field.value)


def _calculate_time_to_service(field: VolvoCarsValue, _: VolvoCarsConfigEntry) -> int:
    value = int(field.value)

    # Always express value in days
    if isinstance(field, VolvoCarsValueField) and field.unit == "months":
        return value * 30

    return value


def _determine_energy_consumption_unit(entry: VolvoCarsConfigEntry) -> str:
    unit_key = entry.options.get(
        OPT_ENERGY_CONSUMPTION_UNIT, OPT_UNIT_ENERGY_KWH_PER_100KM
    )

    return "kWh/100 km" if unit_key == OPT_UNIT_ENERGY_KWH_PER_100KM else "mi/kWh"


def _convert_energy_consumption(
    field: VolvoCarsValue, entry: VolvoCarsConfigEntry
) -> Decimal:
    value = Decimal(field.value)
    unit_key = entry.options.get(
        OPT_ENERGY_CONSUMPTION_UNIT, OPT_UNIT_ENERGY_KWH_PER_100KM
    )

    converted_value = value

    if unit_key == OPT_UNIT_ENERGY_MILES_PER_KWH:
        converted_value = (100 / Decimal(1.609344) / value) if value else Decimal(0)

    return round(converted_value, 1)


def _determine_fuel_consumption_unit(entry: VolvoCarsConfigEntry) -> str:
    unit_key = entry.options.get(OPT_FUEL_CONSUMPTION_UNIT, OPT_UNIT_LITER_PER_100KM)

    if unit_key in (OPT_UNIT_MPG_UK, OPT_UNIT_MPG_US):
        return "mpg"

    return "L/100 km"


def _convert_fuel_consumption(
    field: VolvoCarsValue, entry: VolvoCarsConfigEntry
) -> Decimal:
    value = Decimal(field.value)
    unit_key = entry.options.get(OPT_FUEL_CONSUMPTION_UNIT, OPT_UNIT_LITER_PER_100KM)

    decimals = 1
    converted_value = value

    if unit_key == OPT_UNIT_MPG_UK:
        decimals = 2
        converted_value = (Decimal(282.481) / value) if value else Decimal(0)

    elif unit_key == OPT_UNIT_MPG_US:
        decimals = 2
        converted_value = (Decimal(235.215) / value) if value else Decimal(0)

    return round(converted_value, decimals)


# pylint: disable=unexpected-keyword-arg
SENSORS: tuple[VolvoCarsSensorDescription, ...] = (
    VolvoCarsSensorDescription(
        key="api_request_count",
        translation_key="api_request_count",
        api_field=DATA_REQUEST_COUNT,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:counter",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    VolvoCarsSensorDescription(
        key="api_status",
        translation_key="api_status",
        api_field="apiStatus",
        icon="mdi:api",
        entity_category=EntityCategory.DIAGNOSTIC,
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
        api_field="averageEnergyConsumption",
        native_unit_of_measurement="kWh/100 km",
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:car-electric",
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
        unit_fn=_determine_energy_consumption_unit,
        value_fn=_convert_energy_consumption,
    ),
    VolvoCarsSensorDescription(
        key="average_energy_consumption_automatic",
        translation_key="average_energy_consumption_automatic",
        api_field="averageEnergyConsumptionAutomatic",
        native_unit_of_measurement="kWh/100 km",
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:car-electric",
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
        unit_fn=_determine_energy_consumption_unit,
        value_fn=_convert_energy_consumption,
    ),
    VolvoCarsSensorDescription(
        key="average_energy_consumption_charge",
        translation_key="average_energy_consumption_charge",
        api_field="averageEnergyConsumptionSinceCharge",
        native_unit_of_measurement="kWh/100 km",
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:car-electric",
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
        unit_fn=_determine_energy_consumption_unit,
        value_fn=_convert_energy_consumption,
    ),
    VolvoCarsSensorDescription(
        key="average_fuel_consumption",
        translation_key="average_fuel_consumption",
        api_field="averageFuelConsumption",
        native_unit_of_measurement="L/100 km",
        icon="mdi:gas-station",
        available_fn=lambda vehicle: vehicle.has_combustion_engine(),
        unit_fn=_determine_fuel_consumption_unit,
        value_fn=_convert_fuel_consumption,
    ),
    VolvoCarsSensorDescription(
        key="average_fuel_consumption_automatic",
        translation_key="average_fuel_consumption_automatic",
        api_field="averageFuelConsumptionAutomatic",
        native_unit_of_measurement="L/100 km",
        icon="mdi:gas-station",
        available_fn=lambda vehicle: vehicle.has_combustion_engine(),
        unit_fn=_determine_fuel_consumption_unit,
        value_fn=_convert_fuel_consumption,
    ),
    VolvoCarsSensorDescription(
        key="average_speed",
        translation_key="average_speed",
        api_field="averageSpeed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
    ),
    VolvoCarsSensorDescription(
        key="average_speed_automatic",
        translation_key="average_speed_automatic",
        api_field="averageSpeedAutomatic",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
    ),
    VolvoCarsSensorDescription(
        key="battery_capacity",
        translation_key="battery_capacity",
        api_field=DATA_BATTERY_CAPACITY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
        icon="mdi:car-battery",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    VolvoCarsSensorDescription(
        key="battery_charge_level",
        translation_key="battery_charge_level",
        api_field="batteryChargeLevel",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
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
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge-empty",
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
    ),
    VolvoCarsSensorDescription(
        key="distance_to_empty_tank",
        translation_key="distance_to_empty_tank",
        api_field="distanceToEmptyTank",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge-empty",
        available_fn=lambda vehicle: vehicle.has_combustion_engine(),
    ),
    VolvoCarsSensorDescription(
        key="distance_to_service",
        translation_key="distance_to_service",
        api_field="distanceToService",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wrench-clock",
    ),
    VolvoCarsSensorDescription(
        key="engine_time_to_service",
        translation_key="engine_time_to_service",
        api_field="engineHoursToService",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:wrench-clock",
    ),
    VolvoCarsSensorDescription(
        key="estimated_charging_time",
        translation_key="estimated_charging_time",
        api_field="estimatedChargingTime",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-clock",
        available_fn=lambda vehicle: vehicle.has_battery_engine(),
    ),
    VolvoCarsSensorDescription(
        key="fuel_amount",
        translation_key="fuel_amount",
        api_field="fuelAmount",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gas-station",
        available_fn=lambda vehicle: vehicle.has_combustion_engine(),
    ),
    VolvoCarsSensorDescription(
        key="odometer",
        translation_key="odometer",
        api_field="odometer",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:counter",
    ),
    VolvoCarsSensorDescription(
        key="time_to_service",
        translation_key="time_to_service",
        api_field="timeToService",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=_calculate_time_to_service,
        icon="mdi:wrench-clock",
    ),
    VolvoCarsSensorDescription(
        key="trip_meter_automatic",
        translation_key="trip_meter_automatic",
        api_field="tripMeterAutomatic",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:map-marker-distance",
    ),
    VolvoCarsSensorDescription(
        key="trip_meter_manual",
        translation_key="trip_meter_manual",
        api_field="tripMeterManual",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
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
        if description.api_field in coordinator.data
        and description.available_fn(coordinator.vehicle)
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
                self.coordinator.config_entry
            )

    def _update_state(self, api_field: VolvoCarsApiBaseModel | None) -> None:
        if not isinstance(api_field, VolvoCarsValue):
            return

        native_value = (
            api_field.value
            if self.entity_description.value_fn is None
            else self.entity_description.value_fn(
                api_field, self.coordinator.config_entry
            )
        )

        if self.device_class == SensorDeviceClass.ENUM:
            native_value = value_to_translation_key(str(native_value))

        self._attr_native_value = native_value
