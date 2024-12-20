"""Volvo Cars base entity."""

from custom_components.volvo_cars.entity_description import VolvoCarsDescription
from homeassistant.const import CONF_FRIENDLY_NAME, Platform
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_API_TIMESTAMP, MANUFACTURER
from .coordinator import VolvoCarsDataCoordinator
from .volvo.models import VolvoCarsApiBaseModel, VolvoCarsValueField


def get_entity_id(
    coordinator: VolvoCarsDataCoordinator, platform: Platform, key: str
) -> str:
    """Get the entity ID."""
    friendly_name = coordinator.entry.data.get(CONF_FRIENDLY_NAME)

    if friendly_name:
        return f"{platform}.{MANUFACTURER}_{friendly_name}_{key}".lower()

    return f"{platform}.{MANUFACTURER}_{coordinator.vehicle.vin}_{key}".lower()


def get_unique_id(vin: str, key: str) -> str:
    """Get the unique ID."""
    return f"{MANUFACTURER}_{vin}_{key}".lower()


def value_to_translation_key(value: str) -> str:
    """Make sure the translation key is valid."""
    return value.lower()


class VolvoCarsEntity(CoordinatorEntity[VolvoCarsDataCoordinator]):
    """Volvo Cars base entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VolvoCarsDataCoordinator,
        description: VolvoCarsDescription,
        platform: Platform,
    ) -> None:
        """Initialize entity."""
        super().__init__(coordinator)

        self.entity_description: VolvoCarsDescription = description
        self.entity_id = get_entity_id(coordinator, platform, description.key)
        self._attr_unique_id = get_unique_id(coordinator.vehicle.vin, description.key)
        self._attr_device_info = coordinator.device
        self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        api_field = self.coordinator.get_api_field(self.entity_description)

        if isinstance(api_field, VolvoCarsValueField):
            self._attr_extra_state_attributes[ATTR_API_TIMESTAMP] = api_field.timestamp

        self._update_state(api_field)
        super()._handle_coordinator_update()

    def _update_state(self, api_field: VolvoCarsApiBaseModel | None) -> None:
        pass
