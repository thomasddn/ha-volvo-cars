"""Factory methods."""

from collections.abc import Callable

from aiohttp import ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .data_manager import ApiDataManager
from .volvo.auth import VolvoCarsAuthApi
from .volvo.models import TokenResponse


async def async_create_auth_api(
    hass: HomeAssistant,
    client: ClientSession | None = None,
    on_token_refresh: Callable[[TokenResponse], None] | None = None,
) -> VolvoCarsAuthApi:
    """Create a new instance of VolvoCarsAuthApi."""

    data_manager = ApiDataManager.get_or_create(hass)
    client = client or async_get_clientsession(hass)

    api_data = await data_manager.async_get_api_data(client)

    return VolvoCarsAuthApi(
        client,
        client_id=api_data.client_id,
        auth_header=api_data.auth_header,
        default_headers=api_data.default_headers,
        on_token_refresh=on_token_refresh,
    )
