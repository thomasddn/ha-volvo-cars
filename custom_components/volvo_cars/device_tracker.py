"""Volvo Cars device tracker."""

from dataclasses import dataclass

from homeassistant.components.device_tracker.config_entry import (
    TrackerEntity,
    TrackerEntityDescription,
)
from homeassistant.const import ATTR_ENTITY_PICTURE, Platform
from homeassistant.core import Event, EventStateChangedData, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .config_flow import get_setting
from .const import ATTR_API_TIMESTAMP, ATTR_DIRECTION, OPT_DEVICE_TRACKER_PICTURE
from .coordinator import VolvoCarsConfigEntry, VolvoCarsDataCoordinator
from .entity import VolvoCarsEntity
from .entity_description import VolvoCarsDescription
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

        picture_entity_id: str | None = get_setting(
            self.coordinator.config_entry, OPT_DEVICE_TRACKER_PICTURE
        )

        if picture_entity_id:
            self.coordinator.config_entry.async_on_unload(
                async_track_state_change_event(
                    self.coordinator.hass, picture_entity_id, self._set_picture
                )
            )
        elif (
            self.coordinator.vehicle.images
            and self.coordinator.vehicle.images.exterior_image_url
        ):
            self._attr_extra_state_attributes[ATTR_ENTITY_PICTURE] = (
                self.coordinator.vehicle.images.exterior_image_url
            )

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

    def _set_picture(self, event: Event[EventStateChangedData]) -> None:
        state = event.data["new_state"]

        if state:
            url = state.attributes.get(ATTR_ENTITY_PICTURE, None)
            if url:
                self._attr_extra_state_attributes[ATTR_ENTITY_PICTURE] = url
                self.schedule_update_ha_state()
