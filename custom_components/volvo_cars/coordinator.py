"""Volvo Cars Data Coordinator."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import cast

from requests import ConnectTimeout, HTTPError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_FRIENDLY_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DATA_BATTERY_CAPACITY, DATA_REQUEST_COUNT, DOMAIN, MANUFACTURER
from .entity_description import VolvoCarsDescription
from .store import StoreData, VolvoCarsStore
from .volvo.api import VolvoCarsApi
from .volvo.auth import VolvoCarsAuthApi
from .volvo.models import (
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
    store: VolvoCarsStore


type VolvoCarsConfigEntry = ConfigEntry[VolvoCarsData]
type CoordinatorData = dict[str, VolvoCarsApiBaseModel | None]


class VolvoCarsDataCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Volvo Cars Data Coordinator."""

    config_entry: VolvoCarsConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: VolvoCarsConfigEntry,
        update_interval: int,
        auth_api: VolvoCarsAuthApi,
        api: VolvoCarsApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.data.get(CONF_FRIENDLY_NAME) or entry.entry_id,
            update_interval=timedelta(seconds=update_interval),
        )

        self.api = api
        self._auth_api = auth_api

        self.vehicle: VolvoCarsVehicle
        self.device: DeviceInfo
        self.commands: list[str] = []

        self.supports_location: bool = False
        self.supports_doors: bool = False
        self.supports_tyres: bool = False
        self.supports_warnings: bool = False
        self.supports_windows: bool = False
        self.unsupported_keys: list[str] = []

    @property
    def store(self) -> VolvoCarsStore:
        """Return the store."""
        return self.config_entry.runtime_data.store

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
                _LOGGER.error("Unable to retrieve vehicle details.")
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
            commands = await self.api.async_get_commands()
            count += 1
            self.commands = [command.command for command in commands if command]

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

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            data: CoordinatorData = {}
            results = await asyncio.gather(*(call() for call in api_calls))

            for result in results:
                data |= cast(CoordinatorData, result)

            # Do not count API status
            calls_to_add = len(api_calls) - 1
            await self.async_update_request_count(calls_to_add, data)

            data[DATA_BATTERY_CAPACITY] = VolvoCarsValueField.from_dict(
                {
                    "value": self.vehicle.battery_capacity_kwh,
                    "timestamp": self.config_entry.modified_at,
                }
            )

        except VolvoAuthException as ex:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            _LOGGER.exception("Authentication failed")
            raise ConfigEntryAuthFailed("Authentication failed.") from ex
        else:
            return data

    def get_api_field(
        self, description: VolvoCarsDescription
    ) -> VolvoCarsApiBaseModel | None:
        """Get the API field based on the entity description."""

        return self.data.get(description.api_field) if description.api_field else None

    @callback
    async def async_refresh_token(self, _: datetime | None = None) -> None:
        """Refresh token."""
        storage_data = await self.store.async_load()

        if storage_data is None:
            return

        try:
            result = await self._auth_api.async_refresh_token(
                storage_data["refresh_token"]
            )
        except VolvoAuthException as ex:
            _LOGGER.exception("Authentication failed")
            raise ConfigEntryAuthFailed("Authentication failed.") from ex
        except (ConnectTimeout, HTTPError) as ex:
            _LOGGER.exception("Connection failed")
            raise ConfigEntryNotReady("Unable to connect to Volvo API.") from ex

        if result.token:
            await self.store.async_update(
                access_token=result.token.access_token,
                refresh_token=result.token.refresh_token,
            )
            self.api.update_access_token(result.token.access_token)

    async def async_update_request_count(
        self,
        calls_to_add: int,
        data: CoordinatorData | None = None,
    ) -> None:
        """Update the API request count."""
        store_data = await self.store.async_load()

        if not store_data:
            # There should be store_data
            raise UpdateFailed("Storage '%s' missing.", self.store.key)

        current_count = store_data["api_request_count"]
        request_count = current_count + calls_to_add

        data = data or self.data
        await self._async_set_request_count(request_count, data, store_data)

    async def async_reset_request_count(self, _: datetime | None = None) -> None:
        """Reset the API request count."""
        _LOGGER.debug("%s - Resetting API request count", self.config_entry.entry_id)
        await self._async_set_request_count(0, self.data, None, True)

    async def _async_set_request_count(
        self,
        count: int,
        data: CoordinatorData | None,
        store_data: StoreData | None,
        update_listeners: bool = False,
    ) -> None:
        if not store_data:
            store_data = await self.store.async_load()

        if not store_data:
            # There should be store_data
            raise UpdateFailed("Storage '%s' missing.", self.store.key)

        store_data["api_request_count"] = count
        await self.store.async_update(store_data)

        if data is not None:
            data[DATA_REQUEST_COUNT] = VolvoCarsValueField.from_dict(
                {
                    "value": count,
                    "timestamp": self.config_entry.modified_at,
                }
            )

        if update_listeners:
            self.async_update_listeners()

    def _is_all_unspecified(self, items: dict[str, VolvoCarsValueField | None]) -> bool:
        return all(
            item is None or item.value == "UNSPECIFIED" for item in items.values()
        )
