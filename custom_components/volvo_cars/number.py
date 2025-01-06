"""Volvo Cars number."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import Platform, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VolvoCarsConfigEntry, VolvoCarsDataCoordinator
from .entity import VolvoCarsEntity
from .entity_description import VolvoCarsDescription
from .store import StoreData
from .volvo.models import VolvoCarsVehicle

PARALLEL_UPDATES = 0
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class VolvoCarsNumberDescription(VolvoCarsDescription, NumberEntityDescription):
    """Describes a Volvo Cars number entity."""

    api_field: str = ""
    get_value_fn: Callable[[StoreData], float]
    set_value_fn: Callable[[VolvoCarsDataCoordinator, float], Awaitable[None]]
    available_fn: Callable[[VolvoCarsVehicle], bool] = lambda vehicle: True


def _get_update_interval(data: StoreData) -> float:
    return round(data["data_update_interval"])


async def _set_update_interval(
    coordinator: VolvoCarsDataCoordinator, value: float
) -> None:
    value = round(value)
    await coordinator.store.async_update(data_update_interval=value)
    coordinator.update_interval = timedelta(seconds=value)


def _get_engine_run_time(data: StoreData) -> float:
    return round(data["engine_run_time"])


async def _set_engine_run_time(
    coordinator: VolvoCarsDataCoordinator, value: float
) -> None:
    value = round(value)
    await coordinator.store.async_update(engine_run_time=value)


NUMBERS: tuple[VolvoCarsNumberDescription, ...] = (
    VolvoCarsNumberDescription(
        key="data_update_interval",
        translation_key="data_update_interval",
        icon="mdi:timer-sync-outline",
        native_min_value=60,
        native_max_value=3600,
        native_step=5,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        mode=NumberMode.SLIDER,
        get_value_fn=_get_update_interval,
        set_value_fn=_set_update_interval,
    ),
    VolvoCarsNumberDescription(
        key="engine_run_time",
        translation_key="engine_run_time",
        icon="mdi:timelapse",
        native_min_value=1,
        native_max_value=15,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        mode=NumberMode.SLIDER,
        get_value_fn=_get_engine_run_time,
        set_value_fn=_set_engine_run_time,
        available_fn=lambda vehicle: vehicle.has_combustion_engine(),
    ),
)


async def async_setup_entry(
    _: HomeAssistant,
    entry: VolvoCarsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number."""
    coordinator = entry.runtime_data.coordinator

    numbers = [VolvoCarsNumber(coordinator, description) for description in NUMBERS]

    async_add_entities(numbers)


# pylint: disable=abstract-method
class VolvoCarsNumber(VolvoCarsEntity, NumberEntity):
    """Representation of a Volvo Cars number."""

    entity_description: VolvoCarsNumberDescription

    def __init__(
        self,
        coordinator: VolvoCarsDataCoordinator,
        description: VolvoCarsNumberDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, Platform.NUMBER)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        store_data = await self.coordinator.store.async_load()

        if store_data:
            self._attr_native_value = self.entity_description.get_value_fn(store_data)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.debug("Updating %s to %s", self.entity_description.key, value)
        await self.entity_description.set_value_fn(self.coordinator, value)
        self._attr_native_value = value
        self.async_write_ha_state()
