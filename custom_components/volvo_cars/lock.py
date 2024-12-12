"""Volvo Cars lock."""

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from typing import Any, cast

from homeassistant.components.lock import LockEntity, LockEntityDescription
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_API_TIMESTAMP, ATTR_LAST_RESULT, DOMAIN
from .coordinator import VolvoCarsConfigEntry, VolvoCarsDataCoordinator
from .entity import VolvoCarsDescription, VolvoCarsEntity
from .volvo.models import VolvoApiException, VolvoCarsApiBaseModel, VolvoCarsValue

PARALLEL_UPDATES = 0
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class VolvoCarsLockDescription(VolvoCarsDescription, LockEntityDescription):
    """Describes a Volvo Cars lock entity."""

    api_lock_value: str = "LOCKED"
    api_unlock_value: str = "UNLOCKED"
    lock_command: str
    unlock_command: str
    required_command_key: str


# pylint: disable=unexpected-keyword-arg
LOCKS: tuple[VolvoCarsLockDescription, ...] = (
    VolvoCarsLockDescription(
        key="lock",
        translation_key="lock",
        api_field="centralLock",
        lock_command="lock",
        unlock_command="unlock",
        required_command_key="LOCK",
    ),
    VolvoCarsLockDescription(
        key="lock_reduced_guard",
        translation_key="lock_reduced_guard",
        api_field="centralLock",
        lock_command="lock-reduced-guard",
        unlock_command="unlock",
        required_command_key="LOCK_REDUCED_GUARD",
    ),
)


async def async_setup_entry(
    _: HomeAssistant,
    entry: VolvoCarsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up lock."""
    coordinator = entry.runtime_data.coordinator

    locks = [
        VolvoCarsLock(coordinator, description)
        for description in LOCKS
        if description.required_command_key in coordinator.commands
    ]

    async_add_entities(locks)


# pylint: disable=abstract-method
class VolvoCarsLock(VolvoCarsEntity, LockEntity):
    """Representation of a Volvo Cars lock."""

    entity_description: VolvoCarsLockDescription

    def __init__(
        self,
        coordinator: VolvoCarsDataCoordinator,
        description: VolvoCarsLockDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, Platform.LOCK)

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the car."""
        await self._async_handle_command(self.entity_description.lock_command, True)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the car."""
        await self._async_handle_command(self.entity_description.unlock_command, False)

    def _update_state(self, api_field: VolvoCarsApiBaseModel | None) -> None:
        if not isinstance(api_field, VolvoCarsValue):
            return

        self._attr_is_locked = api_field.value == "LOCKED"

    async def _async_handle_command(self, command: str, locked: bool) -> None:
        try:
            _LOGGER.debug(
                "Lock '%s' is %s", command, "locked" if locked else "unlocked"
            )
            if locked:
                self._attr_is_locking = True
            else:
                self._attr_is_unlocking = True
            self.async_write_ha_state()

            result = await self.coordinator.api.async_execute_command(command)
            status = result.invoke_status.lower() if result else "<none>"

            _LOGGER.debug("Lock '%s' result: %s", command, status)
            self._attr_extra_state_attributes[ATTR_LAST_RESULT] = status
            self._attr_extra_state_attributes[ATTR_API_TIMESTAMP] = datetime.now(
                UTC
            ).isoformat()

            if status not in ("COMPLETED", "DELIVERED"):
                self._attr_is_locking = False
                self._attr_is_unlocking = False
                self.async_write_ha_state()

                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="lock_failure",
                    translation_placeholders={
                        "command": command,
                        "status": status,
                        "message": result.message if result else "",
                    },
                )

            api_field = cast(
                VolvoCarsValue, self.coordinator.data[self.entity_description.api_field]
            )

            if locked:
                self._attr_is_locking = False
                api_field.value = self.entity_description.api_lock_value
            else:
                self._attr_is_unlocking = False
                api_field.value = self.entity_description.api_unlock_value

            self._attr_is_locked = locked
            self.async_write_ha_state()
            self.coordinator.async_update_listeners()

        except VolvoApiException as ex:
            _LOGGER.debug("Lock '%s' error", command)
            raise HomeAssistantError from ex
