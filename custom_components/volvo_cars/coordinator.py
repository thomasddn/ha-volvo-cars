"""Volvo Cars Data Coordinator."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_FRIENDLY_NAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DATA_BATTERY_CAPACITY, DATA_REQUEST_COUNT, DOMAIN, MANUFACTURER
from .entity_description import VolvoCarsDescription
from .store import VolvoCarsStoreManager
from .volvo.api import VolvoCarsApi
from .volvo.auth import VolvoCarsAuthApi
from .volvo.models import (
    AuthorizationModel,
    VolvoApiException,
    VolvoAuthException,
    VolvoCarsApiBaseModel,
    VolvoCarsValueField,
    VolvoCarsVehicle,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class VolvoCarsData:
    """Data for Volvo Cars integration."""

    coordinator: VolvoCarsDataCoordinator
    token_coordinator: TokenCoordinator
    store: VolvoCarsStoreManager


type VolvoCarsConfigEntry = ConfigEntry[VolvoCarsData]
type CoordinatorData = dict[str, VolvoCarsApiBaseModel | None]


class VolvoCarsDataCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Volvo Cars Data Coordinator."""

    config_entry: VolvoCarsConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: VolvoCarsConfigEntry,
        store: VolvoCarsStoreManager,
        api: VolvoCarsApi,
    ) -> None:
        """Initialize the coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.data.get(CONF_FRIENDLY_NAME) or entry.entry_id,
            update_interval=timedelta(seconds=store.data["data_update_interval"]),
        )

        self.store = store
        self.api = api

        self.vehicle: VolvoCarsVehicle
        self.device: DeviceInfo
        self.commands: list[str] = []

        self.supports_location: bool = False
        self.supports_doors: bool = False
        self.supports_tyres: bool = False
        self.supports_warnings: bool = False
        self.supports_windows: bool = False
        self.unsupported_keys: list[str] = []

    async def _async_setup(self) -> None:
        """Set up the coordinator.

        This method is called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        _LOGGER.debug("%s - Setting up", self.config_entry.entry_id)

        try:
            count = 0
            vehicle = await self.api.async_get_vehicle_details()
            count += 1

            if vehicle is None:
                _LOGGER.error("Unable to retrieve vehicle details")
                raise VolvoApiException("Unable to retrieve vehicle details.")

            self.vehicle = vehicle

            device_name = (
                f"{MANUFACTURER} {vehicle.description.model} {vehicle.model_year}"
                if vehicle.fuel_type == "NONE"
                else f"{MANUFACTURER} {vehicle.description.model} {vehicle.fuel_type} {vehicle.model_year}"
            )

            self.device = DeviceInfo(
                identifiers={(DOMAIN, vehicle.vin)},
                manufacturer=MANUFACTURER,
                model=f"{vehicle.description.model} ({vehicle.model_year})",
                name=device_name,
                serial_number=vehicle.vin,
            )

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=f"{MANUFACTURER} {vehicle.description.model} ({vehicle.vin})",
            )

            # Check supported commands
            # We're unable to use the scope 'conve:climatization_start_stop' that
            # is required to use the "ENGINE_START" and "ENGINE_STOP" commands.
            commands = await self.api.async_get_commands()
            count += 1
            self.commands = [
                command.command
                for command in commands
                if command and command.command not in ("ENGINE_START", "ENGINE_STOP")
            ]

            # Check if location is supported
            location = await self.api.async_get_location()
            count += 1
            self.supports_location = location.get("location") is not None

            # Check if doors are supported
            doors = await self.api.async_get_doors_status()
            count += 1
            self.supports_doors = not self._is_all_unspecified(doors)

            # Check if tyres are supported
            tyres = await self.api.async_get_tyre_states()
            count += 1
            self.supports_tyres = not self._is_all_unspecified(tyres)

            # Check if warnings are supported
            warnings = await self.api.async_get_warnings()
            count += 1
            self.supports_warnings = not self._is_all_unspecified(warnings)

            # Check if windows are supported
            windows = await self.api.async_get_window_states()
            count += 1
            self.supports_windows = not self._is_all_unspecified(windows)

        finally:
            self.data = self.data or {}
            await self.async_update_request_count(count)

        # Keep track of unsupported keys
        self.unsupported_keys += [
            key
            for key, value in (doors | tyres | warnings | windows).items()
            if value is None or value.value == "UNSPECIFIED"
        ]

    async def _async_update_data(self) -> CoordinatorData:
        """Fetch data from API."""
        _LOGGER.debug("%s - Updating data", self.config_entry.entry_id)

        api_calls = self._get_api_calls()
        data: CoordinatorData = {}
        valid = 0
        exception: Exception | None = None

        try:
            results = await asyncio.gather(
                *(call() for call in api_calls), return_exceptions=True
            )

            for result in results:
                if isinstance(result, VolvoAuthException):
                    # If one result is a VolvoAuthException, then probably all requests
                    # will fail. In this case we can cancel everything to
                    # reauthenticate.
                    #
                    # Raising ConfigEntryAuthFailed will cancel future updates
                    # and start a config flow with SOURCE_REAUTH (async_step_reauth)
                    _LOGGER.exception(
                        "%s - Authentication failed. %s",
                        self.config_entry.entry_id,
                        result.message,
                    )
                    raise ConfigEntryAuthFailed(
                        f"Authentication failed. {result.message}"
                    ) from result

                if isinstance(result, VolvoApiException):
                    # Maybe it's just one call that fails. Log the error and
                    # continue processing the other calls.
                    _LOGGER.debug(
                        "%s - Error during data update: %s",
                        self.config_entry.entry_id,
                        result,
                    )
                    exception = exception or result
                    continue

                if isinstance(result, Exception):
                    # Something bad happened, raise immediately.
                    raise result

                data |= cast(CoordinatorData, result)
                valid += 1

            # Raise an error if not a single API call succeeded
            if valid == 0:
                message = "Unable to update data."

                if exception:
                    raise UpdateFailed(message) from exception

                raise UpdateFailed(message)

            # Add static values
            data[DATA_BATTERY_CAPACITY] = VolvoCarsValueField.from_dict(
                {
                    "value": self.vehicle.battery_capacity_kwh,
                    "timestamp": self.config_entry.modified_at,
                }
            )
        finally:
            # Save number of API requests made (excluding API status)
            calls_to_add = len(api_calls) - 1
            await self.async_update_request_count(calls_to_add, data)

        return data

    def get_api_field(
        self, description: VolvoCarsDescription
    ) -> VolvoCarsApiBaseModel | None:
        """Get the API field based on the entity description."""

        return self.data.get(description.api_field) if description.api_field else None

    async def async_update_request_count(
        self,
        calls_to_add: int,
        data: CoordinatorData | None = None,
    ) -> None:
        """Update the API request count."""
        current_count = self.store.data["api_request_count"]
        request_count = current_count + calls_to_add

        data = data or self.data
        await self._async_set_request_count(request_count, data)

    async def async_reset_request_count(self, _: datetime | None = None) -> None:
        """Reset the API request count."""
        _LOGGER.debug("%s - Resetting API request count", self.config_entry.entry_id)
        await self._async_set_request_count(
            0, self.data, update_listeners=True, set_reset_timestamp=True
        )

    async def _async_set_request_count(
        self,
        count: int,
        data: CoordinatorData | None,
        *,
        update_listeners: bool = False,
        set_reset_timestamp: bool = False,
    ) -> None:
        reset_time = datetime.now(UTC).isoformat() if set_reset_timestamp else None
        await self.store.async_update(
            api_request_count=count, api_requests_reset_time=reset_time
        )

        if data is not None:
            data[DATA_REQUEST_COUNT] = VolvoCarsValueField.from_dict(
                {
                    "value": count,
                    "timestamp": datetime.now(UTC),
                }
            )

        if update_listeners:
            self.async_update_listeners()

    def _get_api_calls(
        self,
    ) -> list[Callable[[], Coroutine[Any, Any, Any]]]:
        api_calls = [
            self.api.async_get_api_status,
            self.api.async_get_availability_status,
            self.api.async_get_brakes_status,
            self.api.async_get_diagnostics,
            self.api.async_get_engine_status,
            self.api.async_get_engine_warnings,
            self.api.async_get_odometer,
            self.api.async_get_statistics,
        ]

        if self.supports_doors:
            api_calls.append(self.api.async_get_doors_status)

        if self.vehicle.has_combustion_engine():
            api_calls.append(self.api.async_get_fuel_status)

        if self.supports_location:
            api_calls.append(self.api.async_get_location)

        if self.vehicle.has_battery_engine():
            api_calls.append(self.api.async_get_recharge_status)

        if self.supports_tyres:
            api_calls.append(self.api.async_get_tyre_states)

        if self.supports_warnings:
            api_calls.append(self.api.async_get_warnings)

        if self.supports_windows:
            api_calls.append(self.api.async_get_window_states)

        return api_calls

    def _is_all_unspecified(self, items: dict[str, VolvoCarsValueField | None]) -> bool:
        return all(
            item is None or item.value == "UNSPECIFIED" for item in items.values()
        )


class TokenCoordinator:
    """Coordinator for handling refresh tokens."""

    _RETRY_AT_PERCENTAGES = [0.65, 0.8, 0.90]

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: VolvoCarsStoreManager,
        auth_api: VolvoCarsAuthApi,
    ) -> None:
        """Initialize the coordinator."""

        self._hass = hass
        self._entry = entry
        self._store = store
        self._auth_api = auth_api

        entry_name = entry.data.get(CONF_FRIENDLY_NAME) or entry.entry_id
        self._name = f"{entry_name} - refresh token"

        self._delays: deque[int] = deque()
        self._unsub_refresh: CALLBACK_TYPE | None = None

    async def async_schedule_refresh(self, init: bool = False) -> None:
        """Schedule the token refresher."""
        self.cancel_refresh()

        if init:
            await self._async_refresh_token(raise_on_auth_failed=True)
            return

        if not self._delays:
            _LOGGER.debug("%s - No token refresh schedule found", self._entry.entry_id)
            return

        delay = self._delays.popleft()
        _LOGGER.debug("%s - Next token refresh in %ss", self._entry.entry_id, delay)

        loop = self._hass.loop
        next_refresh = int(loop.time()) + delay

        self._unsub_refresh = loop.call_at(
            next_refresh, self.__wrap_handle_refresh_interval
        ).cancel

    def cancel_refresh(self) -> None:
        """Cancel any scheduled call."""
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

    async def _async_refresh_token(self, raise_on_auth_failed: bool = False) -> None:
        """Refresh token."""
        _LOGGER.debug("%s - Refreshing token", self._entry.entry_id)

        self.cancel_refresh()

        if self._hass.is_stopping:
            return

        result: AuthorizationModel | None = None

        try:
            result = await self._auth_api.async_refresh_token(
                self._store.data["refresh_token"]
            )
        except VolvoAuthException as ex:
            if raise_on_auth_failed:
                _LOGGER.exception("Authentication failed: %s", ex.message)
                raise ConfigEntryAuthFailed(
                    f"Authentication failed. {ex.message}"
                ) from ex

            if self._delays:
                _LOGGER.exception(
                    "Authentication failed: %s. Trying again in %ss",
                    ex.message,
                    self._delays[0],
                )
            else:
                _LOGGER.exception(
                    "Authentication failed: %s. Starting reauth flow", ex.message
                )
                self._entry.async_start_reauth(self._hass)

        if result and result.token:
            await self._store.async_update(
                access_token=result.token.access_token,
                refresh_token=result.token.refresh_token,
            )

            self._set_delays(result.token.expires_in)

        if self._delays and not self._hass.is_stopping:
            await self.async_schedule_refresh()

    def _set_delays(self, expiry: int) -> None:
        percentages = self._RETRY_AT_PERCENTAGES

        self._delays = deque(
            [int(percentages[0] * expiry)]
            + [
                int((percentages[i] - percentages[i - 1]) * expiry)
                for i in range(1, len(percentages))
            ]
        )

    @callback
    def __wrap_handle_refresh_interval(self) -> None:
        self._entry.async_create_background_task(
            self._hass,
            self._handle_refresh_interval(),
            name=self._name,
            eager_start=True,
        )

    async def _handle_refresh_interval(self, _now: datetime | None = None) -> None:
        self._unsub_refresh = None
        await self._async_refresh_token()
