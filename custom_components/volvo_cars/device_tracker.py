"""Volvo Cars device tracker."""

from dataclasses import dataclass

from homeassistant.components.device_tracker.config_entry import (
    TrackerEntity,
    TrackerEntityDescription,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_API_TIMESTAMP, ATTR_DIRECTION
from .coordinator import VolvoCarsConfigEntry, VolvoCarsDataCoordinator
from .entity import VolvoCarsDescription, VolvoCarsEntity
from .volvo.models import VolvoCarsApiBaseModel, VolvoCarsLocation

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class VolvoCarsTrackerDescription(VolvoCarsDescription, TrackerEntityDescription):
    """Describes a Volvo Cars tracker entity."""


# pylint: disable=unexpected-keyword-arg
TRACKERS: tuple[VolvoCarsTrackerDescription, ...] = (
    VolvoCarsTrackerDescription(
        key="location",
        translation_key="location",
        api_field="location",
        icon="mdi:map-marker-radius",
    ),
)


async def async_setup_entry(
    _: HomeAssistant,
    entry: VolvoCarsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up tracker."""
    coordinator = entry.runtime_data.coordinator
    trackers = [
        VolvoCarsDeviceTracker(coordinator, description)
        for description in TRACKERS
        if coordinator.supports_location
    ]

    async_add_entities(trackers)


class VolvoCarsDeviceTracker(VolvoCarsEntity, TrackerEntity):
    """Representation of a Volvo Cars tracker."""

    entity_description: VolvoCarsTrackerDescription

    def __init__(
        self,
        coordinator: VolvoCarsDataCoordinator,
        description: VolvoCarsTrackerDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, Platform.DEVICE_TRACKER)

    def _update_state(self, api_field: VolvoCarsApiBaseModel | None) -> None:
        if not isinstance(api_field, VolvoCarsLocation):
            return

        if api_field.geometry.coordinates and len(api_field.geometry.coordinates) > 1:
            self._attr_longitude = api_field.geometry.coordinates[0]
            self._attr_latitude = api_field.geometry.coordinates[1]

        if api_field.properties:
            self._attr_extra_state_attributes[ATTR_DIRECTION] = (
                api_field.properties.heading
            )
            self._attr_extra_state_attributes[ATTR_API_TIMESTAMP] = (
                api_field.properties.timestamp
            )
