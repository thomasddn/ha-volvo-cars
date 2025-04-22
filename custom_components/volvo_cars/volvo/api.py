"""Volvo API."""

import logging
from typing import Any, cast

from aiohttp import (
    ClientError,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    RequestInfo,
    hdrs,
)
from yarl import URL

from .models import (
    TokenResponse,
    VolvoApiException,
    VolvoAuthException,
    VolvoCarsAvailableCommand,
    VolvoCarsCommandResult,
    VolvoCarsErrorResult,
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
_API_REQUEST_TIMEOUT = ClientTimeout(total=30)

_DATA_TO_REDACT = [
    "coordinates",
    "heading",
    "href",
    "vin",
]

_LOGGER = logging.getLogger(__name__)


class VolvoCarsApi:
    """Volvo Cars API."""

    def __init__(self, client: ClientSession, vin: str, api_key: str) -> None:
        """Initialize Volvo Cars API."""
        self._client = client
        self._vin = vin
        self._api_key = api_key

    def update_access_token(self, token: TokenResponse) -> None:
        """Update the access token."""
        self._access_token = token.access_token

    async def async_get_api_status(self) -> dict[str, VolvoCarsValue]:
        """Check the API status."""
        try:
            _LOGGER.debug("Request [API status]")
            async with self._client.get(
                _API_STATUS_URL, timeout=_API_REQUEST_TIMEOUT
            ) as response:
                _LOGGER.debug("Request [API status] status: %s", response.status)
                response.raise_for_status()
                json = await response.json()
                data = cast(dict[str, Any], json)
                _LOGGER.debug("Request [API status] response: %s", data)

                message = data.get("message") or "OK"

        except (ClientError, TimeoutError) as ex:
            _LOGGER.debug("Request [API status] error: %s", ex)
            message = "Unknown"

        return {"apiStatus": VolvoCarsValue(message)}

    async def async_get_availability_status(
        self,
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get availability status."""
        return await self._async_get_field(
            _API_CONNECTED_ENDPOINT, "command-accessibility"
        )

    async def async_get_brakes_status(self) -> dict[str, VolvoCarsValueField | None]:
        """Get brakes status."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "brakes")

    async def async_get_commands(self) -> list[VolvoCarsAvailableCommand | None]:
        """Get available commands."""
        items = await self._async_get_data_list(_API_CONNECTED_ENDPOINT, "commands")
        return [VolvoCarsAvailableCommand.from_dict(item) for item in items]

    async def async_get_diagnostics(self) -> dict[str, VolvoCarsValueField | None]:
        """Get diagnostics."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "diagnostics")

    async def async_get_doors_status(self) -> dict[str, VolvoCarsValueField | None]:
        """Get doors status."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "doors")

    async def async_get_engine_status(self) -> dict[str, VolvoCarsValueField | None]:
        """Get engine status."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "engine-status")

    async def async_get_engine_warnings(self) -> dict[str, VolvoCarsValueField | None]:
        """Get engine warnings."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "engine")

    async def async_get_fuel_status(self) -> dict[str, VolvoCarsValueField | None]:
        """Get fuel status."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "fuel")

    async def async_get_location(self) -> dict[str, VolvoCarsLocation | None]:
        """Get location."""
        data = await self._async_get_data_dict(_API_LOCATION_ENDPOINT, "location")
        return {"location": VolvoCarsLocation.from_dict(data)}

    async def async_get_odometer(self) -> dict[str, VolvoCarsValueField | None]:
        """Get odometer."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "odometer")

    async def async_get_recharge_status(self) -> dict[str, VolvoCarsValueField | None]:
        """Get recharge status."""
        return await self._async_get_field(_API_ENERGY_ENDPOINT, "recharge-status")

    async def async_get_statistics(self) -> dict[str, VolvoCarsValueField | None]:
        """Get statistics."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "statistics")

    async def async_get_tyre_states(self) -> dict[str, VolvoCarsValueField | None]:
        """Get tyre states."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "tyres")

    async def async_get_vehicle_details(self) -> VolvoCarsVehicle | None:
        """Get vehicle details."""
        data = await self._async_get_data_dict(_API_CONNECTED_ENDPOINT, "")
        return VolvoCarsVehicle.from_dict(data)

    async def async_get_warnings(self) -> dict[str, VolvoCarsValueField | None]:
        """Get warnings."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "warnings")

    async def async_get_window_states(self) -> dict[str, VolvoCarsValueField | None]:
        """Get window states."""
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "windows")

    async def async_execute_command(
        self, command: str, body: dict[str, Any] | None = None
    ) -> VolvoCarsCommandResult | None:
        """Execute a command."""
        body = await self._async_post(
            _API_CONNECTED_ENDPOINT, f"commands/{command}", body
        )
        data: dict = body.get("data", {})
        data["invoke_status"] = data.pop("invokeStatus", None)
        return VolvoCarsCommandResult.from_dict(data)

    async def _async_get_field(
        self, endpoint: str, operation: str
    ) -> dict[str, VolvoCarsValueField | None]:
        body = await self._async_get(endpoint, operation)
        data: dict = body.get("data", {})
        return {
            key: VolvoCarsValueField.from_dict(value) for key, value in data.items()
        }

    async def _async_get_data_dict(
        self, endpoint: str, operation: str
    ) -> dict[str, Any]:
        body = await self._async_get(endpoint, operation)
        return cast(dict[str, Any], body.get("data", {}))

    async def _async_get_data_list(self, endpoint: str, operation: str) -> list[Any]:
        body = await self._async_get(endpoint, operation)
        return cast(list[Any], body.get("data", []))

    async def _async_get(self, endpoint: str, operation: str) -> dict[str, Any]:
        return await self._async_request(hdrs.METH_GET, endpoint, operation)

    async def _async_post(
        self, endpoint: str, operation: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return await self._async_request(hdrs.METH_POST, endpoint, operation, body=body)

    async def _async_request(
        self,
        method: str,
        endpoint: str,
        operation: str,
        *,
        body: dict[str, Any] | None = None,
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

        data: dict[str, Any] = {}

        try:
            _LOGGER.debug(
                "Request [%s]: %s %s",
                operation,
                method,
                redact_url(url, self._vin),
            )
            async with self._client.request(
                method, url, headers=headers, json=body, timeout=_API_REQUEST_TIMEOUT
            ) as response:
                _LOGGER.debug("Request [%s] status: %s", operation, response.status)
                json = await response.json()
                data = cast(dict[str, Any], json)
                _LOGGER.debug(
                    "Request [%s] response: %s",
                    operation,
                    redact_data(data, _DATA_TO_REDACT),
                )
                response.raise_for_status()
                return data
        except ClientResponseError as ex:
            if ex.status == 404:
                return {}

            _LOGGER.debug("Request [%s] error: %s", operation, ex.message)

            if ex.status == 422 and "commands" in operation:
                return {
                    "data": {
                        "vin": self._vin,
                        "invokeStatus": "UNKNOWN",
                        "message": "",
                    }
                }

            redacted_exception = RedactedClientResponseError(ex, self._vin)
            message = redacted_exception.message

            if data and (error_data := data.get("error")):
                error = VolvoCarsErrorResult.from_dict(error_data)

                if error is not None:
                    message = f"{error.message}. {error.description}".strip()

            if ex.status in (401, 403):
                raise VolvoAuthException(message) from redacted_exception

            raise VolvoApiException(message) from redacted_exception

        except (ClientError, TimeoutError) as ex:
            _LOGGER.debug("Request [%s] error: %s", operation, ex.__class__.__name__)
            raise VolvoApiException(ex.__class__.__name__) from ex


class RedactedClientResponseError(ClientResponseError):
    """Exception class that redacts sensitive data."""

    def __init__(self, exception: ClientResponseError, vin: str) -> None:
        """Initialize class."""

        redacted_url = self._redact_url(exception.request_info.url, vin)
        redacted_real_url = self._redact_url(exception.request_info.real_url, vin)
        redacted_request_info = RequestInfo(
            redacted_url,
            exception.request_info.method,
            exception.request_info.headers,
            redacted_real_url,
        )

        super().__init__(
            redacted_request_info,
            exception.history,
            status=exception.status,
            message=exception.message,
            headers=exception.headers,
        )

    def _redact_url(self, url: URL, vin: str) -> URL:
        redacted_url = redact_url(str(url), vin)
        return URL(redacted_url)
