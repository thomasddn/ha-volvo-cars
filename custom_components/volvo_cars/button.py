"""Volvo Cars button."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_API_TIMESTAMP, ATTR_LAST_RESULT
from .coordinator import VolvoCarsConfigEntry, VolvoCarsDataCoordinator
from .entity import VolvoCarsEntity
from .entity_description import VolvoCarsDescription
from .volvo.models import VolvoApiException

PARALLEL_UPDATES = 0
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class VolvoCarsButtonDescription(VolvoCarsDescription, ButtonEntityDescription):
    """Describes a Volvo Cars button entity."""

    api_field: str = ""
    api_command: str = ""
    required_command_key: str = ""
    non_api_command: bool = False
    data_fn: Callable[[VolvoCarsDataCoordinator], Awaitable[dict]] | None = None


async def _async_get_start_engine_data(coordinator: VolvoCarsDataCoordinator) -> dict:
    store_data = await coordinator.store.async_load()
    run_time = store_data["engine_run_time"] if store_data else 15

    return {"runtimeMinutes": run_time}


# pylint: disable=unexpected-keyword-arg
BUTTONS: tuple[VolvoCarsButtonDescription, ...] = (
    VolvoCarsButtonDescription(
        key="climatization_start",
        translation_key="climatization_start",
        api_command="climatization-start",
        required_command_key="CLIMATIZATION_START",
        icon="mdi:air-conditioner",
    ),
    VolvoCarsButtonDescription(
        key="climatization_stop",
        translation_key="climatization_stop",
        api_command="climatization-stop",
        required_command_key="CLIMATIZATION_STOP",
        icon="mdi:air-conditioner",
    ),
    VolvoCarsButtonDescription(
        key="engine_start",
        translation_key="engine_start",
        api_command="engine-start",
        required_command_key="ENGINE_START",
        icon="mdi:engine",
        data_fn=lambda coordinator: _async_get_start_engine_data(coordinator),
    ),
    VolvoCarsButtonDescription(
        key="engine_stop",
        translation_key="engine_stop",
        api_command="engine-stop",
        required_command_key="ENGINE_STOP",
        icon="mdi:engine-off",
    ),
    VolvoCarsButtonDescription(
        key="flash",
        translation_key="flash",
        api_command="flash",
        required_command_key="FLASH",
        icon="mdi:alarm-light-outline",
    ),
    VolvoCarsButtonDescription(
        key="honk",
        translation_key="honk",
        api_command="honk",
        required_command_key="HONK",
        icon="mdi:trumpet",
    ),
    VolvoCarsButtonDescription(
        key="honk_flash",
        translation_key="honk_flash",
        api_command="honk-flash",
        required_command_key="HONK_AND_FLASH",
        icon="mdi:alarm-light",
    ),
    VolvoCarsButtonDescription(
        key="update_data",
        translation_key="update_data",
        icon="mdi:cloud-refresh-outline",
        non_api_command=True,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    _: HomeAssistant,
    entry: VolvoCarsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button."""
    coordinator = entry.runtime_data.coordinator

    buttons = [
        VolvoCarsButton(coordinator, description)
        for description in BUTTONS
        if description.non_api_command
        or description.required_command_key in coordinator.commands
    ]

    async_add_entities(buttons)


# pylint: disable=abstract-method
class VolvoCarsButton(VolvoCarsEntity, ButtonEntity):
    """Representation of a Volvo Cars button."""

    entity_description: VolvoCarsButtonDescription

    def __init__(
        self,
        coordinator: VolvoCarsDataCoordinator,
        description: VolvoCarsButtonDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, Platform.BUTTON)

    async def async_press(self) -> None:
        """Handle the button press."""

        if self.entity_description.non_api_command:
            if self.entity_description.key == "update_data":
                _LOGGER.debug("Command update_data executing")
                await self.coordinator.async_refresh()
        else:
            try:
                _LOGGER.debug(
                    "Command %s executing", self.entity_description.api_command
                )

                data = (
                    await self.entity_description.data_fn(self.coordinator)
                    if self.entity_description.data_fn
                    else None
                )

                result = await self.coordinator.api.async_execute_command(
                    self.entity_description.api_command, data
                )

                status = result.invoke_status if result else ""

                _LOGGER.debug(
                    "Command %s result: %s",
                    self.entity_description.api_command,
                    status,
                )
                self._attr_extra_state_attributes[ATTR_LAST_RESULT] = status.lower()
                self._attr_extra_state_attributes[ATTR_API_TIMESTAMP] = datetime.now(
                    UTC
                ).isoformat()
                self.async_write_ha_state()

            except VolvoApiException as ex:
                _LOGGER.debug("Command %s error", self.entity_description.api_command)
                raise HomeAssistantError from ex
            finally:
                await self.coordinator.async_update_request_count(1)
                self.coordinator.async_update_listeners()
