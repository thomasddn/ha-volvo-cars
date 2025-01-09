"""Volvo Auth API."""

import logging
from typing import Any, cast

from aiohttp import ClientSession

from .data import DataCache
from .models import AuthorizationModel, TokenResponse, VolvoAuthException
from .util import redact_data

_AUTH_URL = "https://volvoid.eu.volvocars.com/as/authorization.oauth2"
_TOKEN_URL = "https://volvoid.eu.volvocars.com/as/token.oauth2"
_SCOPE = [
    "openid",
    "conve:brake_status",
    "conve:climatization_start_stop",
    "conve:command_accessibility",
    "conve:commands",
    "conve:diagnostics_engine_status",
    "conve:diagnostics_workshop",
    "conve:doors_status",
    "conve:engine_status",
    "conve:environment",
    "conve:fuel_status",
    "conve:honk_flash",
    "conve:lock",
    "conve:lock_status",
    "conve:navigation",
    "conve:odometer_status",
    "conve:trip_statistics",
    "conve:tyre_status",
    "conve:unlock",
    "conve:vehicle_relation",
    "conve:warnings",
    "conve:windows_status",
    "energy:battery_charge_level",
    "energy:charging_connection_status",
    "energy:charging_system_status",
    "energy:electric_range",
    "energy:estimated_charging_time",
    "energy:recharge_status",
]

_LOGGER = logging.getLogger(__name__)
_DATA_TO_REDACT = [
    "access_token",
    "code",
    "id",
    "id_token",
    "href",
    "refresh_token",
    "target",
    "username",
]


class VolvoCarsAuthApi:
    """Volvo Cars Authentication API."""

    def __init__(self, client: ClientSession) -> None:
        """Initialize Volvo Cars Authentication API."""
        self._client = client

    async def async_authenticate(
        self, username: str, password: str
    ) -> AuthorizationModel:
        """Request OTP to authenticate user."""

        try:
            data = await self._async_auth_init()
            status = data.get("status")

            if status == "USERNAME_PASSWORD_REQUIRED":
                url = data["_links"]["checkUsernamePassword"]["href"]

                data = await self._async_username_pass(url, username, password)
                status = data.get("status")

            if status == "OTP_REQUIRED":
                url = data["_links"]["checkOtp"]["href"] + "?action=checkOtp"
                return AuthorizationModel(status, next_url=url)

            if status == "COMPLETED":
                return await self._handle_status_completed(data, status)
        except Exception as ex:
            raise VolvoAuthException from ex

        raise VolvoAuthException(f"Unhandled status: {status}")

    async def async_request_token(self, url: str, otp: str) -> AuthorizationModel:
        """Request token."""

        try:
            data = await self._async_send_otp(url, otp)
            status = data.get("status")

            if status == "OTP_VERIFIED":
                url = (
                    data["_links"]["continueAuthentication"]["href"]
                    + "?action=continueAuthentication"
                )

                data = await self._async_continue_auth(url)
                status = data.get("status")

                if status == "COMPLETED":
                    return await self._handle_status_completed(data, status)
        except Exception as ex:
            raise VolvoAuthException from ex

        raise VolvoAuthException(f"Unhandled status: {status}")

    async def async_refresh_token(self, refresh_token: str) -> AuthorizationModel:
        """Refresh token."""

        try:
            auth = await self._async_refresh_token(refresh_token)
            return AuthorizationModel("COMPLETED", token=auth)
        except Exception as ex:
            raise VolvoAuthException from ex

    async def _async_auth_init(self) -> dict[str, Any]:
        helper_data = await DataCache.async_get_data(self._client)
        client_id = DataCache.deobfuscate_str(
            helper_data["h"]["a"]["value"].split(" ")[1]
        ).split(":")[0]

        headers = await self._async_get_default_headers()
        payload = {
            "client_id": client_id,
            "response_type": "code",
            "response_mode": "pi.flow",
            "acr_values": "urn:volvoid:aal:bronze:2sv",
            "scope": " ".join(_SCOPE),
        }

        _LOGGER.debug("Request [auth init]")
        async with self._client.post(
            _AUTH_URL,
            headers=headers,
            data=payload,
        ) as response:
            _LOGGER.debug("Request [auth init] status: %s", response.status)
            json = await response.json()
            data = cast(dict[str, Any], json)
            _LOGGER.debug(
                "Request [auth init] response: %s", redact_data(data, _DATA_TO_REDACT)
            )
            response.raise_for_status()
            return data

    async def _async_username_pass(
        self, url: str, username: str, password: str
    ) -> dict[str, Any]:
        headers = await self._async_get_default_headers()
        params = {"action": "checkUsernamePassword"}
        payload = {"username": username, "password": password}

        _LOGGER.debug("Request [credentials]")
        async with self._client.post(
            url, headers=headers, params=params, json=payload
        ) as response:
            _LOGGER.debug("Request [credentials] status: %s", response.status)
            json = await response.json()
            data = cast(dict[str, Any], json)
            _LOGGER.debug(
                "Request [credentials] response: %s", redact_data(data, _DATA_TO_REDACT)
            )
            response.raise_for_status()
            return data

    async def _async_send_otp(self, url: str, otp: str) -> dict[str, Any]:
        headers = await self._async_get_default_headers()
        payload = {"otp": otp}

        _LOGGER.debug("Request [OTP]")
        async with self._client.post(url, headers=headers, json=payload) as response:
            _LOGGER.debug("Request [OTP] status: %s", response.status)
            json = await response.json()
            data = cast(dict[str, Any], json)
            _LOGGER.debug(
                "Request [OTP] response: %s", redact_data(data, _DATA_TO_REDACT)
            )
            response.raise_for_status()
            return data

    async def _async_continue_auth(self, url: str) -> dict[str, Any]:
        _LOGGER.debug("Request [auth cont]")
        headers = await self._async_get_default_headers()
        async with self._client.get(url, headers=headers) as response:
            _LOGGER.debug("Request [auth cont] status: %s", response.status)
            json = await response.json()
            data = cast(dict[str, Any], json)
            _LOGGER.debug(
                "Request [auth cont] response: %s", redact_data(data, _DATA_TO_REDACT)
            )
            response.raise_for_status()
            return data

    async def _async_request_token(self, code: str) -> TokenResponse | None:
        headers = await self._async_get_all_headers()
        payload = {"code": code, "grant_type": "authorization_code"}

        _LOGGER.debug("Request [tokens]")
        async with self._client.post(
            _TOKEN_URL, headers=headers, data=payload
        ) as response:
            _LOGGER.debug("Request [tokens] status: %s", response.status)
            json = await response.json()
            _LOGGER.debug(
                "Request [tokens] response: %s", redact_data(json, _DATA_TO_REDACT)
            )
            response.raise_for_status()
            return TokenResponse.from_dict(json)

    async def _async_refresh_token(self, refresh_token: str) -> TokenResponse | None:
        headers = await self._async_get_all_headers()
        payload = {"refresh_token": refresh_token, "grant_type": "refresh_token"}

        _LOGGER.debug("Request [token refresh]")
        async with self._client.post(
            _TOKEN_URL, headers=headers, data=payload
        ) as response:
            _LOGGER.debug("Request [token refresh] status: %s", response.status)
            json = await response.json()
            _LOGGER.debug(
                "Request [token refresh] response: %s",
                redact_data(json, _DATA_TO_REDACT),
            )
            response.raise_for_status()
            return TokenResponse.from_dict(json)

    async def _handle_status_completed(
        self, data: dict, status: str
    ) -> AuthorizationModel:
        code = data["authorizeResponse"]["code"]
        auth = await self._async_request_token(code)
        return AuthorizationModel(status, token=auth)

    async def _async_get_default_headers(self) -> dict[str, str]:
        helper_data = await DataCache.async_get_data(self._client)
        p = helper_data["h"]["p"]
        return {p["key"]: p["value"]}

    async def _async_get_all_headers(self) -> dict[str, str]:
        helper_data = await DataCache.async_get_data(self._client)
        p = helper_data["h"]["p"]
        a = helper_data["h"]["a"]

        return {
            p["key"]: p["value"],
            a["key"]: a["value"],
        }
