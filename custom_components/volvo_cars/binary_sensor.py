"""Volvo Cars binary sensors."""

from collections.abc import Callable
from dataclasses import dataclass, field

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VolvoCarsConfigEntry, VolvoCarsDataCoordinator
from .entity import VolvoCarsEntity, value_to_translation_key
from .entity_description import VolvoCarsDescription
from .volvo.models import VolvoCarsApiBaseModel, VolvoCarsValue

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class VolvoCarsBinarySensorDescription(
    BinarySensorEntityDescription, VolvoCarsDescription
):
    """Describes a Volvo Cars binary sensor entity."""

    on_values: tuple[str, ...]
    icon_off: str | None = None
    api_value_in_attributes: bool = False
    api_value_attribute_name: str = ""
    api_value_attribute_fn: Callable[[dict[str, VolvoCarsValue]], str] | None = None


@dataclass(frozen=True, kw_only=True)
class VolvoCarsDoorDescription(VolvoCarsBinarySensorDescription):
    """Describes a Volvo Cars door entity."""

    device_class: BinarySensorDeviceClass = BinarySensorDeviceClass.DOOR
    on_values: tuple[str, ...] = field(default=("OPEN", "AJAR"), init=False)
    icon: str = "mdi:car-door-lock-open"
    icon_off: str = "mdi:car-door-lock"


@dataclass(frozen=True, kw_only=True)
class VolvoCarsTyreDescription(VolvoCarsBinarySensorDescription):
    """Describes a Volvo Cars tyre entity."""

    device_class: BinarySensorDeviceClass = BinarySensorDeviceClass.PROBLEM
    on_values: tuple[str, ...] = field(
        default=("VERY_LOW_PRESSURE", "LOW_PRESSURE", "HIGH_PRESSURE"), init=False
    )
    icon: str = "mdi:car-tire-alert"
    icon_off: str = "mdi:tire"
    api_value_in_attributes: bool = True
    api_value_attribute_name: str = "pressure"


@dataclass(frozen=True, kw_only=True)
class VolvoCarsWindowDescription(VolvoCarsBinarySensorDescription):
    """Describes a Volvo Cars window entity."""

    device_class: BinarySensorDeviceClass = BinarySensorDeviceClass.WINDOW
    on_values: tuple[str, ...] = field(default=("OPEN", "AJAR"), init=False)
    icon: str = "mdi:car-door-lock-open"
    icon_off: str = "mdi:car-door-lock"


# pylint: disable=unexpected-keyword-arg
SENSORS: tuple[VolvoCarsBinarySensorDescription, ...] = (
    #
    # DIAGNOSTICS
    #
    VolvoCarsBinarySensorDescription(
        key="service_warning",
        translation_key="service_warning",
        api_field="serviceWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=(
            "DISTANCE_DRIVEN_ALMOST_TIME_FOR_SERVICE",
            "DISTANCE_DRIVEN_OVERDUE_FOR_SERVICE",
            "DISTANCE_DRIVEN_TIME_FOR_SERVICE",
            "ENGINE_HOURS_ALMOST_TIME_FOR_SERVICE",
            "ENGINE_HOURS_OVERDUE_FOR_SERVICE",
            "ENGINE_HOURS_TIME_FOR_SERVICE",
            "REGULAR_MAINTENANCE_ALMOST_TIME_FOR_SERVICE",
            "REGULAR_MAINTENANCE_OVERDUE_FOR_SERVICE",
            "REGULAR_MAINTENANCE_TIME_FOR_SERVICE",
            "UNKNOWN_WARNING",
        ),
        icon="mdi:wrench-clock",
        icon_off="mdi:wrench",
        api_value_in_attributes=True,
        api_value_attribute_name="reason",
    ),
    VolvoCarsBinarySensorDescription(
        key="washer_fluid_level_warning",
        translation_key="washer_fluid_level_warning",
        api_field="washerFluidLevelWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("TOO_LOW",),
        icon="mdi:wiper-wash-alert",
        icon_off="mdi:wiper-wash",
    ),
    VolvoCarsBinarySensorDescription(
        key="brake_fluid_level_warning",
        translation_key="brake_fluid_level_warning",
        api_field="brakeFluidLevelWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("TOO_LOW",),
        icon="mdi:car-brake-alert",
        icon_off="mdi:car-brake-fluid-level",
    ),
    #
    # DOORS
    #
    VolvoCarsDoorDescription(
        key="door_front_left",
        translation_key="door_front_left",
        api_field="frontLeftDoor",
    ),
    VolvoCarsDoorDescription(
        key="door_front_right",
        translation_key="door_front_right",
        api_field="frontRightDoor",
    ),
    VolvoCarsDoorDescription(
        key="door_rear_left",
        translation_key="door_rear_left",
        api_field="rearLeftDoor",
    ),
    VolvoCarsDoorDescription(
        key="door_rear_right",
        translation_key="door_rear_right",
        api_field="rearRightDoor",
    ),
    VolvoCarsDoorDescription(
        key="hood",
        translation_key="hood",
        api_field="hood",
    ),
    VolvoCarsDoorDescription(
        key="tailgate",
        translation_key="tailgate",
        api_field="tailgate",
    ),
    VolvoCarsDoorDescription(
        key="tank_lid",
        translation_key="tank_lid",
        api_field="tankLid",
    ),
    #
    # ENGINE
    #
    VolvoCarsBinarySensorDescription(
        key="coolant_level_warning",
        translation_key="coolant_level_warning",
        api_field="engineCoolantLevelWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("TOO_LOW",),
        icon="mdi:car-coolant-level",
        icon_off="mdi:car-coolant-level",
    ),
    VolvoCarsBinarySensorDescription(
        key="engine_status",
        translation_key="engine_status",
        api_field="engineStatus",
        device_class=BinarySensorDeviceClass.RUNNING,
        on_values=("RUNNING",),
        icon="mdi:engine",
        icon_off="mdi:engine-off",
    ),
    VolvoCarsBinarySensorDescription(
        key="oil_level_warning",
        translation_key="oil_level_warning",
        api_field="oilLevelWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("SERVICE_REQUIRED", "TOO_LOW", "TOO_HIGH"),
        icon="mdi:oil-level",
        icon_off="mdi:oil-level",
        api_value_in_attributes=True,
        api_value_attribute_name="level",
    ),
    #
    # LIGHTS
    #
    VolvoCarsBinarySensorDescription(
        key="brake_light_center_warning",
        translation_key="brake_light_center_warning",
        api_field="brakeLightCenterWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-dimmed",
    ),
    VolvoCarsBinarySensorDescription(
        key="brake_light_left_warning",
        translation_key="brake_light_left_warning",
        api_field="brakeLightLeftWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-dimmed",
    ),
    VolvoCarsBinarySensorDescription(
        key="brake_light_right_warning",
        translation_key="brake_light_right_warning",
        api_field="brakeLightRightWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-dimmed",
    ),
    VolvoCarsBinarySensorDescription(
        key="daytime_running_light_left_warning",
        translation_key="daytime_running_light_left_warning",
        api_field="daytimeRunningLightLeftWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-dimmed",
    ),
    VolvoCarsBinarySensorDescription(
        key="daytime_running_light_right_warning",
        translation_key="daytime_running_light_right_warning",
        api_field="daytimeRunningLightRightWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-dimmed",
    ),
    VolvoCarsBinarySensorDescription(
        key="fog_light_front_warning",
        translation_key="fog_light_front_warning",
        api_field="fogLightFrontWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-fog",
    ),
    VolvoCarsBinarySensorDescription(
        key="fog_light_rear_warning",
        translation_key="fog_light_rear_warning",
        api_field="fogLightRearWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-fog",
    ),
    VolvoCarsBinarySensorDescription(
        key="hazard_lights_warning",
        translation_key="hazard_lights_warning",
        api_field="hazardLightsWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:hazard-lights",
    ),
    VolvoCarsBinarySensorDescription(
        key="high_beam_left_warning",
        translation_key="high_beam_left_warning",
        api_field="highBeamLeftWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-high",
    ),
    VolvoCarsBinarySensorDescription(
        key="high_beam_right_warning",
        translation_key="high_beam_right_warning",
        api_field="highBeamRightWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-high",
    ),
    VolvoCarsBinarySensorDescription(
        key="low_beam_left_warning",
        translation_key="low_beam_left_warning",
        api_field="lowBeamLeftWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-dimmed",
    ),
    VolvoCarsBinarySensorDescription(
        key="low_beam_right_warning",
        translation_key="low_beam_right_warning",
        api_field="lowBeamRightWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-dimmed",
    ),
    VolvoCarsBinarySensorDescription(
        key="position_light_front_left_warning",
        translation_key="position_light_front_left_warning",
        api_field="positionLightFrontLeftWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-parking-lights",
    ),
    VolvoCarsBinarySensorDescription(
        key="position_light_front_right_warning",
        translation_key="position_light_front_right_warning",
        api_field="positionLightFrontRightWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-parking-lights",
    ),
    VolvoCarsBinarySensorDescription(
        key="position_light_rear_left_warning",
        translation_key="position_light_rear_left_warning",
        api_field="positionLightRearLeftWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-parking-lights",
    ),
    VolvoCarsBinarySensorDescription(
        key="position_light_rear_right_warning",
        translation_key="position_light_rear_right_warning",
        api_field="positionLightRearRightWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-parking-lights",
    ),
    VolvoCarsBinarySensorDescription(
        key="registration_plate_light_warning",
        translation_key="registration_plate_light_warning",
        api_field="registrationPlateLightWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:lightbulb-off-outline",
        icon_off="mdi:lightbulb-outline",
    ),
    VolvoCarsBinarySensorDescription(
        key="reverse_lights_warning",
        translation_key="reverse_lights_warning",
        api_field="reverseLightsWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:car-light-dimmed",
    ),
    VolvoCarsBinarySensorDescription(
        key="side_mark_lights_warning",
        translation_key="side_mark_lights_warning",
        api_field="sideMarkLightsWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:wall-sconce-round",
    ),
    VolvoCarsBinarySensorDescription(
        key="turn_indication_front_left_warning",
        translation_key="turn_indication_front_left_warning",
        api_field="turnIndicationFrontLeftWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:arrow-left-top",
    ),
    VolvoCarsBinarySensorDescription(
        key="turn_indication_front_right_warning",
        translation_key="turn_indication_front_right_warning",
        api_field="turnIndicationFrontRightWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:arrow-right-top",
    ),
    VolvoCarsBinarySensorDescription(
        key="turn_indication_rear_left_warning",
        translation_key="turn_indication_rear_left_warning",
        api_field="turnIndicationRearLeftWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:arrow-left-top",
    ),
    VolvoCarsBinarySensorDescription(
        key="turn_indication_rear_right_warning",
        translation_key="turn_indication_rear_right_warning",
        api_field="turnIndicationRearRightWarning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=("FAILURE",),
        icon="mdi:car-light-alert",
        icon_off="mdi:arrow-right-top",
    ),
    #
    # TYRES
    #
    VolvoCarsTyreDescription(
        key="tyre_front_left",
        translation_key="tyre_front_left",
        api_field="frontLeft",
    ),
    VolvoCarsTyreDescription(
        key="tyre_front_right",
        translation_key="tyre_front_right",
        api_field="frontRight",
    ),
    VolvoCarsTyreDescription(
        key="tyre_rear_left",
        translation_key="tyre_rear_left",
        api_field="rearLeft",
    ),
    VolvoCarsTyreDescription(
        key="tyre_rear_right",
        translation_key="tyre_rear_right",
        api_field="rearRight",
    ),
    #
    # WINDOWS
    #
    VolvoCarsWindowDescription(
        key="window_front_left",
        translation_key="window_front_left",
        api_field="frontLeftWindow",
    ),
    VolvoCarsWindowDescription(
        key="window_front_right",
        translation_key="window_front_right",
        api_field="frontRightWindow",
    ),
    VolvoCarsWindowDescription(
        key="window_rear_left",
        translation_key="window_rear_left",
        api_field="rearLeftWindow",
    ),
    VolvoCarsWindowDescription(
        key="window_rear_right",
        translation_key="window_rear_right",
        api_field="rearRightWindow",
    ),
    VolvoCarsWindowDescription(
        key="sunroof",
        translation_key="sunroof",
        api_field="sunroof",
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
        VolvoCarsBinarySensor(coordinator, description)
        for description in SENSORS
        if description.api_field not in coordinator.unsupported_keys
    ]

    async_add_entities(sensors)


class VolvoCarsBinarySensor(VolvoCarsEntity, BinarySensorEntity):
    """Representation of a Volvo Cars binary sensor."""

    entity_description: VolvoCarsBinarySensorDescription

    def __init__(
        self,
        coordinator: VolvoCarsDataCoordinator,
        description: VolvoCarsBinarySensorDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, Platform.BINARY_SENSOR)

    @property
    def icon(self) -> str | None:
        """Return icon based on the state."""
        return (
            self.entity_description.icon
            if self.is_on
            else self.entity_description.icon_off
        )

    def _update_state(self, api_field: VolvoCarsApiBaseModel | None) -> None:
        if not isinstance(api_field, VolvoCarsValue):
            return

        self._attr_is_on = api_field.value in self.entity_description.on_values

        if self.entity_description.api_value_in_attributes:
            attribute_value = (
                api_field.value
                if self.entity_description.api_value_attribute_fn is None
                else self.entity_description.api_value_attribute_fn(api_field.value)
            )

            if isinstance(attribute_value, str):
                attribute_value = value_to_translation_key(attribute_value)

            self._attr_extra_state_attributes[
                self.entity_description.api_value_attribute_name
            ] = attribute_value
