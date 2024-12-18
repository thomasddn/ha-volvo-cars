"""Config flow for Volvo Cars integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any, Self

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry, ConfigFlowResult
from homeassistant.const import CONF_FRIENDLY_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import selector

from .const import (
    CONF_OTP,
    CONF_VCC_API_KEY,
    CONF_VIN,
    DOMAIN,
    MANUFACTURER,
    OPT_FUEL_CONSUMPTION_UNIT,
    OPT_UNIT_LITER_PER_100KM,
    OPT_UNIT_MPG_UK,
    OPT_UNIT_MPG_US,
)
from .entry_data import StoreData, create_store
from .volvo.auth import VolvoCarsAuthApi
from .volvo.models import AuthorizationModel, VolvoAuthException

_LOGGER = logging.getLogger(__name__)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(OPT_FUEL_CONSUMPTION_UNIT): selector(
            {
                "select": {
                    "options": [
                        OPT_UNIT_LITER_PER_100KM,
                        OPT_UNIT_MPG_UK,
                        OPT_UNIT_MPG_US,
                    ],
                    "translation_key": OPT_FUEL_CONSUMPTION_UNIT,
                }
            }
        )
    }
)


class VolvoCarsFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Volvo Cars config flow."""

    VERSION = 1
    MINOR_VERSION = 3

    def __init__(self) -> None:
        """Initialize Volvo Cars config flow."""
        self._username: str | None = None
        self._password: str | None = None
        self._vin: str | None = None
        self._api_key: str | None = None
        self._friendly_name: str | None = None

        self._auth_result: AuthorizationModel | None = None

    # Overridden method
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            flow = await self._async_authenticate(
                user_input[CONF_VIN], user_input, errors
            )

            if flow is not None:
                return flow

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=self._username or ""): str,
                vol.Required(CONF_PASSWORD, default=self._password or ""): str,
                vol.Required(CONF_VIN, default=self._vin or ""): str,
                vol.Required(CONF_VCC_API_KEY, default=self._api_key or ""): str,
                vol.Optional(
                    CONF_FRIENDLY_NAME, default=self._friendly_name or ""
                ): str,
            },
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle OTP step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                client = async_get_clientsession(self.hass)
                api = VolvoCarsAuthApi(client)

                if self._auth_result and self._auth_result.next_url:
                    self._auth_result = await api.async_request_token(
                        self._auth_result.next_url, user_input[CONF_OTP]
                    )
            except VolvoAuthException:
                _LOGGER.exception("Authentication failed")
                errors["base"] = "invalid_auth"

            if not errors:
                return await self._async_create_or_update_entry()

        schema = vol.Schema({vol.Required(CONF_OTP, default=""): str})
        return self.async_show_form(step_id="otp", data_schema=schema, errors=errors)

    # By convention method
    async def async_step_reauth(self, _: Mapping[str, Any]) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            flow = await self._async_authenticate(
                reauth_entry.data[CONF_VIN], user_input, errors
            )

            if flow is not None:
                return flow

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME, default=reauth_entry.data.get(CONF_USERNAME)
                ): str,
                vol.Required(CONF_PASSWORD, default=""): str,
                vol.Required(
                    CONF_VCC_API_KEY, default=reauth_entry.data.get(CONF_VCC_API_KEY)
                ): str,
            },
        )

        return self.async_show_form(
            step_id="reauth_confirm", data_schema=schema, errors=errors
        )

    # Overridden method
    def is_matching(self, other_flow: Self) -> bool:
        """Return True if other_flow is matching this flow."""
        return other_flow._vin == self._vin  # noqa: SLF001 # pylint: disable=protected-access

    # Overridden method
    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()

    async def _async_authenticate(
        self, vin: str, user_input: dict[str, Any], errors: dict[str, str]
    ) -> ConfigFlowResult | None:
        await self.async_set_unique_id(vin)

        if self.source == SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch()
        else:
            self._abort_if_unique_id_configured()

        try:
            client = async_get_clientsession(self.hass)
            api = VolvoCarsAuthApi(client)

            result = await api.async_authenticate(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
        except VolvoAuthException:
            _LOGGER.exception("Authentication failed")
            errors["base"] = "invalid_auth"

        self._vin = vin
        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]
        self._api_key = user_input[CONF_VCC_API_KEY]
        self._friendly_name = user_input[CONF_FRIENDLY_NAME]

        if not errors:
            self._auth_result = result

            if result.status == "OTP_REQUIRED":
                return await self.async_step_otp()

            if result.status == "COMPLETED":
                return await self._async_create_or_update_entry()

        return None

    async def _async_create_or_update_entry(self) -> ConfigFlowResult:
        data = {
            CONF_USERNAME: self._username,
            CONF_VIN: self._vin,
            CONF_VCC_API_KEY: self._api_key,
            CONF_FRIENDLY_NAME: self._friendly_name,
        }

        if self._auth_result and self._auth_result.token:
            if self.unique_id is None:
                raise ConfigEntryError("Config entry has no unique_id")

            store = create_store(self.hass, self.unique_id)
            await store.async_save(
                StoreData(
                    access_token=self._auth_result.token.access_token,
                    refresh_token=self._auth_result.token.refresh_token,
                )
            )

        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates=data,
            )

        return self.async_create_entry(
            title=f"{MANUFACTURER} {self._vin}",
            data=data,
            options={OPT_FUEL_CONSUMPTION_UNIT: OPT_UNIT_LITER_PER_100KM},
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Class to handle the options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=OPTIONS_SCHEMA,
        )
