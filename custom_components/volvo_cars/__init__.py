"""The Volvo Cars integration."""

import logging

from requests import ConnectTimeout, HTTPError

from homeassistant.const import CONF_ACCESS_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import async_get

from .const import CONF_REFRESH_TOKEN, PLATFORMS
from .coordinator import VolvoCarsConfigEntry, VolvoCarsData, VolvoCarsDataCoordinator
from .entity import get_entity_id
from .volvo.auth import VolvoCarsAuthApi
from .volvo.models import VolvoAuthException

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: VolvoCarsConfigEntry) -> bool:
    """Set up Volvo Cars integration."""
    _LOGGER.debug("Loading entry %s", entry.entry_id)

    try:
        client = async_get_clientsession(hass)
        auth_api = VolvoCarsAuthApi(client)
        result = await auth_api.async_refresh_token(
            entry.data.get(CONF_REFRESH_TOKEN, "")
        )
    except VolvoAuthException as ex:
        _LOGGER.exception("Authentication failed")
        raise ConfigEntryAuthFailed("Authentication failed.") from ex
    except (ConnectTimeout, HTTPError) as ex:
        _LOGGER.exception("Connection failed")
        raise ConfigEntryNotReady("Unable to connect to Volvo API.") from ex

    if result.token is not None:
        data = entry.data | {
            CONF_ACCESS_TOKEN: result.token.access_token,
            CONF_REFRESH_TOKEN: result.token.refresh_token,
        }
        hass.config_entries.async_update_entry(entry, data=data)

    coordinator = VolvoCarsDataCoordinator(hass, entry, auth_api)
    entry.runtime_data = VolvoCarsData(coordinator)

    await coordinator.async_config_entry_first_refresh()
    _remove_old_entities(hass, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: VolvoCarsConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading entry %s", entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _remove_old_entities(
    hass: HomeAssistant, coordinator: VolvoCarsDataCoordinator
) -> None:
    old_entities: tuple[tuple[Platform, str], ...] = (
        #
        # v0.2
        #
        (Platform.BINARY_SENSOR, "availability"),
        (Platform.BINARY_SENSOR, "front_left_door"),
        (Platform.BINARY_SENSOR, "front_right_door"),
        (Platform.BINARY_SENSOR, "rear_left_door"),
        (Platform.BINARY_SENSOR, "rear_right_door"),
        (Platform.BINARY_SENSOR, "front_left_tyre"),
        (Platform.BINARY_SENSOR, "front_right_tyre"),
        (Platform.BINARY_SENSOR, "rear_left_tyre"),
        (Platform.BINARY_SENSOR, "rear_right_tyre"),
        (Platform.BINARY_SENSOR, "front_left_window"),
        (Platform.BINARY_SENSOR, "front_right_window"),
        (Platform.BINARY_SENSOR, "rear_left_window"),
        (Platform.BINARY_SENSOR, "rear_right_window"),
        (Platform.SENSOR, "engine_hours_to_service"),
    )

    er = async_get(hass)

    for old_entity in old_entities:
        old_id = get_entity_id(coordinator, old_entity[0], old_entity[1])
        entry = er.async_get(old_id)

        if entry:
            _LOGGER.debug("Removing %s", entry.entity_id)
            er.async_remove(entry.entity_id)
