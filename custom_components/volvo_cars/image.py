"""Volvo Cars images."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VolvoCarsConfigEntry, VolvoCarsDataCoordinator
from .entity import VolvoCarsDescription, VolvoCarsEntity
from .volvo.models import VolvoCarsApiBaseModel, VolvoCarsVehicle

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class VolvoCarsImageDescription(VolvoCarsDescription, ImageEntityDescription):
    """Describes a Volvo Cars image entity."""

    api_field: str = ""
    image_url_fn: Callable[[VolvoCarsVehicle], str]


# pylint: disable=unexpected-keyword-arg
IMAGES: tuple[VolvoCarsImageDescription, ...] = (
    VolvoCarsImageDescription(
        key="exterior",
        translation_key="exterior",
        image_url_fn=lambda vehicle: vehicle.images.exterior_image_url,
    ),
    VolvoCarsImageDescription(
        key="interior",
        translation_key="interior",
        image_url_fn=lambda vehicle: vehicle.images.internal_image_url,
    ),
)


async def async_setup_entry(
    _: HomeAssistant,
    entry: VolvoCarsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up images."""
    coordinator = entry.runtime_data.coordinator
    images = [VolvoCarsImage(coordinator, description) for description in IMAGES]

    async_add_entities(images)


# pylint: disable=abstract-method
class VolvoCarsImage(VolvoCarsEntity, ImageEntity):
    """Representation of a Volvo Cars image."""

    entity_description: VolvoCarsImageDescription

    def __init__(
        self,
        coordinator: VolvoCarsDataCoordinator,
        description: VolvoCarsImageDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, Platform.IMAGE)
        ImageEntity.__init__(self, coordinator.hass)

        self._client.headers.update(
            {"Accept-Language": "en-GB", "Sec-Fetch-User": "?1"}
        )

    def _update_state(self, api_field: VolvoCarsApiBaseModel | None) -> None:
        url = self.entity_description.image_url_fn(self.coordinator.vehicle)

        if self._attr_image_url != url:
            self._attr_image_url = url
            self._attr_image_last_updated = datetime.now()
