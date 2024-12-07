"""Volvo API."""

import logging
from typing import Any, cast

from aiohttp import ClientResponseError, ClientSession, hdrs

from .models import (
    VolvoApiException,
    VolvoAuthException,
    VolvoCarsAvailableCommand,
    VolvoCarsCommandResult,
    VolvoCarsLocation,
    VolvoCarsValue,
    VolvoCarsValueField,
    VolvoCarsVehicle,
)
from .util import redact_data, redact_url

_API_CONNECTED_ENDPOINT = "/connected-vehicle/v2/vehicles"
_API_ENERGY_ENDPOINT = "/energy/v1/vehicles"
_API_LOCATION_ENDPOINT = "/location/v1/vehicles"
_API_URL = "https://api.volvocars.com"
_API_STATUS_URL = "https://public-developer-portal-bff.weu-prod.ecpaz.volvocars.biz/api/v1/backend-status"

_LOGGER = logging.getLogger(__name__)
_DATA_TO_REDACT = [
    "coordinates",
    "heading",
    "href",
    "vin",
]


class VolvoCarsApi:
    """Volvo Cars API."""

    def __init__(
        self, client: ClientSession, vin: str, api_key: str, access_token: str
    ) -> None:
        """Initialize Volvo Cars API."""
        self._client = client
        self._vin = vin
        self._api_key = api_key
        self._access_token = access_token

    def update_access_token(self, access_token: str) -> None:
        """Update the access token."""
        self._access_token = access_token

    async def async_get_api_status(self) -> dict[str, VolvoCarsValue]:
        """Check the API status."""
        try:
            _LOGGER.debug("Request [API status]")
            async with self._client.get(_API_STATUS_URL) as response:
                _LOGGER.debug("Request [API status] status: %s", response.status)
                response.raise_for_status()
                json = await response.json()
                data = cast(dict[str, Any], json)
                _LOGGER.debug("Request [API status] body: %s", data)

                message = data.get("message")

                if not message:
                    message = "OK"

                return {"apiStatus": VolvoCarsValue(message)}
        except ClientResponseError as ex:
            _LOGGER.debug("Request [API status] error: %s", ex.message)
            raise VolvoApiException from ex

    async def async_get_availability_status(self) -> dict[str, VolvoCarsValueField]:
        """Get availability status."""
        return await self._async_get_field(
            _API_CONNECTED_ENDPOINT, "command-accessibility"
        )

    async def async_get_brakes_status(self) -> dict[str, VolvoCarsValueField]:
        """Get brakes status."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "brakes")

    async def async_get_commands(self) -> list[VolvoCarsAvailableCommand]:
        """Get available commands."""
        items = await self._async_get_data_list(_API_CONNECTED_ENDPOINT, "commands")
        return [VolvoCarsAvailableCommand.from_dict(item) for item in items]

    async def async_get_diagnostics(self) -> dict[str, VolvoCarsValueField]:
        """Get diagnostics."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "diagnostics")

    async def async_get_doors_status(self) -> dict[str, VolvoCarsValueField]:
        """Get doors status."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "doors")

    async def async_get_engine_status(self) -> dict[str, VolvoCarsValueField]:
        """Get engine status."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "engine-status")

    async def async_get_engine_warnings(self) -> dict[str, VolvoCarsValueField]:
        """Get engine warnings."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "engine")

    async def async_get_fuel_status(self) -> dict[str, VolvoCarsValueField]:
        """Get fuel status."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "fuel")

    async def async_get_location(self) -> dict[str, VolvoCarsLocation]:
        """Get location."""
        data = await self._async_get_data_dict(_API_LOCATION_ENDPOINT, "location")
        return {"location": VolvoCarsLocation.from_dict(data)}

    async def async_get_odometer(self) -> dict[str, VolvoCarsValueField]:
        """Get odometer."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "odometer")

    async def async_get_recharge_status(self) -> dict[str, VolvoCarsValueField]:
        """Get recharge status."""
        return await self._async_get_field(_API_ENERGY_ENDPOINT, "recharge-status")

    async def async_get_statistics(self) -> dict[str, VolvoCarsValueField]:
        """Get statistics."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "statistics")

    async def async_get_tyre_states(self) -> dict[str, VolvoCarsValueField]:
        """Get tyre states."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "tyres")

    async def async_get_vehicle_details(self) -> VolvoCarsVehicle:
        """Get vehicle details."""
        data = await self._async_get_data_dict(_API_CONNECTED_ENDPOINT, "")
        return VolvoCarsVehicle.parse_obj(data)

    async def async_get_warnings(self) -> dict[str, VolvoCarsValueField]:
        """Get warnings."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "warnings")

    async def async_get_window_states(self) -> dict[str, VolvoCarsValueField]:
        """Get window states."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "windows")

    async def async_execute_command(self, command: str) -> VolvoCarsCommandResult:
        """Execute a command."""
        body = await self._async_post(_API_CONNECTED_ENDPOINT, f"commands/{command}")
        data: dict = body.get("data", {})
        data["invoke_status"] = data.pop("invokeStatus")
        return VolvoCarsCommandResult.from_dict(data)

    async def _async_get_field(
        self, endpoint: str, operation: str
    ) -> dict[str, VolvoCarsValueField]:
        body = await self._async_get(endpoint, operation)
        data: dict = body.get("data", {})
        return {
            key: VolvoCarsValueField.from_dict(value) for key, value in data.items()
        }

    async def _async_get_data_dict(
        self, endpoint: str, operation: str
    ) -> dict[str, Any]:
        body = await self._async_get(endpoint, operation)
        return body.get("data", {})

    async def _async_get_data_list(self, endpoint: str, operation: str) -> list[Any]:
        body = await self._async_get(endpoint, operation)
        return body.get("data", [])

    async def _async_get(self, endpoint: str, operation: str) -> dict[str, Any]:
        return await self._async_request(hdrs.METH_GET, endpoint, operation)

    async def _async_post(self, endpoint: str, operation: str) -> dict[str, Any]:
        return await self._async_request(hdrs.METH_POST, endpoint, operation)

    async def _async_request(
        self, method: str, endpoint: str, operation: str
    ) -> dict[str, Any]:
        url = (
            f"{_API_URL}{endpoint}/{self._vin}/{operation}"
            if operation
            else f"{_API_URL}{endpoint}/{self._vin}"
        )

        headers = {
            hdrs.AUTHORIZATION: f"Bearer {self._access_token}",
            "vcc-api-key": self._api_key,
        }

        if method == hdrs.METH_POST:
            headers[hdrs.CONTENT_TYPE] = "application/json"

        try:
            _LOGGER.debug(
                "Request [%s]: %s %s",
                operation,
                method,
                redact_url(url, self._vin),
            )
            async with self._client.request(method, url, headers=headers) as response:
                _LOGGER.debug("Request [%s] status: %s", operation, response.status)
                json = await response.json()
                data = cast(dict[str, Any], json)
                _LOGGER.debug(
                    "Request [%s] body: %s",
                    operation,
                    redact_data(data, _DATA_TO_REDACT),
                )
                response.raise_for_status()
                return data
        except ClientResponseError as ex:
            _LOGGER.debug("Request [%s] error: %s", operation, ex.message)
            if ex.status in (401, 403):
                raise VolvoAuthException from ex

            raise VolvoApiException from ex
