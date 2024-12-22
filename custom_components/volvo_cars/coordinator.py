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

from .const import DATA_BATTERY_CAPACITY, DOMAIN, MANUFACTURER
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


class VolvoCarsDataCoordinator(
    DataUpdateCoordinator[dict[str, VolvoCarsApiBaseModel | None]]
):
    """Volvo Cars Data Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: VolvoCarsConfigEntry,
        auth_api: VolvoCarsAuthApi,
        api: VolvoCarsApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.data.get(CONF_FRIENDLY_NAME) or entry.entry_id,
            update_interval=timedelta(minutes=2, seconds=15),
        )

        self.config_entry: VolvoCarsConfigEntry = entry
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

    def get_api_field(
        self, description: VolvoCarsDescription
    ) -> VolvoCarsApiBaseModel | None:
        """Get the API field based on the entity description."""

        if isinstance(description.api_field, str):
            return (
                self.data.get(description.api_field) if description.api_field else None
            )

        if isinstance(description.api_field, list):
            for key in description.api_field:
                if (field := self.data.get(key)) is not None:
                    return field

        return None

    async def _async_setup(self) -> None:
        """Set up the coordinator.

        This method is called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        vehicle = await self.api.async_get_vehicle_details()

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
        self.commands = [command.command for command in commands if command]

        # Check if location is supported
        location = await self.api.async_get_location()
        self.supports_location = location.get("location") is not None

        # Check if doors are supported
        doors = await self.api.async_get_doors_status()
        self.supports_doors = not self._is_all_unspecified(doors)

        # Check if tyres are supported
        tyres = await self.api.async_get_tyre_states()
        self.supports_tyres = not self._is_all_unspecified(tyres)

        # Check if warnings are supported
        warnings = await self.api.async_get_warnings()
        self.supports_warnings = not self._is_all_unspecified(warnings)

        # Check if windows are supported
        windows = await self.api.async_get_window_states()
        self.supports_windows = not self._is_all_unspecified(windows)

        # Keep track of unsupported keys
        self.unsupported_keys.append("location")
        self.unsupported_keys += [
            key
            for key, value in (doors | tyres | warnings | windows).items()
            if value is None or value.value == "UNSPECIFIED"
        ]

    async def _async_update_data(self) -> dict[str, VolvoCarsApiBaseModel | None]:
        """Fetch data from API."""
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
            async with asyncio.timeout(30):
                data: dict[str, VolvoCarsApiBaseModel | None] = {}
                results = await asyncio.gather(*(call() for call in api_calls))

                for result in results:
                    data |= cast(dict[str, VolvoCarsApiBaseModel | None], result)

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
        except (ConnectTimeout, HTTPError) as ex:
            _LOGGER.exception("Connection failed")
            raise UpdateFailed("Unable to connect to Volvo API.") from ex
        else:
            return data

    @callback
    async def async_refresh_token(self, _: datetime | None = None) -> None:
        """Refresh token."""
        store = self.config_entry.runtime_data.store
        storage_data = await store.async_load()

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
            await store.async_save(
                StoreData(
                    access_token=result.token.access_token,
                    refresh_token=result.token.refresh_token,
                )
            )
            self.api.update_access_token(result.token.access_token)

    def _is_all_unspecified(self, items: dict[str, VolvoCarsValueField | None]) -> bool:
        return all(
            item is None or item.value == "UNSPECIFIED" for item in items.values()
        )
