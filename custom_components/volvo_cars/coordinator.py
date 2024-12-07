"""Volvo Cars Data Coordinator."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from requests import ConnectTimeout, HTTPError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_FRIENDLY_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_REFRESH_TOKEN, CONF_VCC_API_KEY, CONF_VIN, DOMAIN, MANUFACTURER
from .volvo.api import VolvoCarsApi
from .volvo.auth import VolvoCarsAuthApi
from .volvo.models import VolvoAuthException, VolvoCarsApiBaseModel, VolvoCarsVehicle

_LOGGER = logging.getLogger(__name__)


@dataclass
class VolvoCarsData:
    """Data for Volvo Cars integration."""

    coordinator: VolvoCarsDataCoordinator


type VolvoCarsConfigEntry = ConfigEntry[VolvoCarsData]


class VolvoCarsDataCoordinator(DataUpdateCoordinator[dict[str, VolvoCarsApiBaseModel]]):
    """Volvo Cars Data Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        auth_api: VolvoCarsAuthApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.data.get(CONF_FRIENDLY_NAME) or entry.entry_id,
            update_interval=timedelta(minutes=2, seconds=15),
        )

        self.entry = entry
        self._auth_api = auth_api
        self.api = VolvoCarsApi(
            async_get_clientsession(hass),
            entry.data[CONF_VIN],
            entry.data[CONF_VCC_API_KEY],
            entry.data[CONF_ACCESS_TOKEN],
        )

        entry.async_on_unload(
            async_track_time_interval(
                self.hass, self.async_refresh_token, timedelta(minutes=25)
            )
        )

        self.vehicle: VolvoCarsVehicle
        self.device: DeviceInfo
        self.commands: list[str]

    async def _async_setup(self) -> None:
        """Set up the coordinator.

        This method is called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        self.vehicle = await self.api.async_get_vehicle_details()
        self.device = DeviceInfo(
            identifiers={(DOMAIN, self.vehicle.vin)},
            manufacturer=MANUFACTURER,
            model=f"{self.vehicle.description.model} ({self.vehicle.model_year})",
            name=f"{MANUFACTURER} {self.vehicle.description.model} {self.vehicle.fuel_type} {self.vehicle.model_year}",
            serial_number=self.vehicle.vin,
        )

        commands = await self.api.async_get_commands()
        self.commands = [command.command for command in commands]

        self.hass.config_entries.async_update_entry(
            self.entry,
            title=f"{MANUFACTURER} {self.vehicle.description.model} ({self.vehicle.vin})",
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with asyncio.timeout(30):
                data: dict[str, VolvoCarsApiBaseModel] = {}

                results = await asyncio.gather(
                    self.api.async_get_api_status(),
                    self.api.async_get_availability_status(),
                    self.api.async_get_brakes_status(),
                    self.api.async_get_diagnostics(),
                    self.api.async_get_doors_status(),
                    self.api.async_get_engine_status(),
                    self.api.async_get_engine_warnings(),
                    self.api.async_get_location(),
                    self.api.async_get_odometer(),
                    self.api.async_get_statistics(),
                    self.api.async_get_tyre_states(),
                    self.api.async_get_warnings(),
                    self.api.async_get_window_states(),
                )

                for result in results:
                    data |= result

                if self.vehicle.has_combustion_engine():
                    data |= await self.api.async_get_fuel_status()

                if self.vehicle.has_battery_engine():
                    data |= await self.api.async_get_recharge_status()

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
        try:
            result = await self._auth_api.async_refresh_token(
                self.entry.data.get(CONF_REFRESH_TOKEN, "")
            )
        except VolvoAuthException as ex:
            _LOGGER.exception("Authentication failed")
            raise ConfigEntryAuthFailed("Authentication failed.") from ex
        except (ConnectTimeout, HTTPError) as ex:
            _LOGGER.exception("Connection failed")
            raise ConfigEntryNotReady("Unable to connect to Volvo API.") from ex

        if result.token:
            data = self.entry.data | {
                CONF_ACCESS_TOKEN: result.token.access_token,
                CONF_REFRESH_TOKEN: result.token.refresh_token,
            }
            self.hass.config_entries.async_update_entry(self.entry, data=data)
            self.api.update_access_token(result.token.access_token)
