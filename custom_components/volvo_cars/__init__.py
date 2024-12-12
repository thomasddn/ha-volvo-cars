"""The Volvo Cars integration."""

from datetime import timedelta
import logging

from requests import ConnectTimeout, HTTPError

from homeassistant.const import CONF_ACCESS_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.event import async_track_time_interval

from .config_flow import VolvoCarsFlowHandler
from .const import (
    CONF_REFRESH_TOKEN,
    OPT_FUEL_CONSUMPTION_UNIT,
    OPT_UNIT_LITER_PER_100KM,
    PLATFORMS,
)
from .coordinator import VolvoCarsConfigEntry, VolvoCarsData, VolvoCarsDataCoordinator
from .entity import get_entity_id
from .volvo.auth import VolvoCarsAuthApi
from .volvo.models import VolvoAuthException

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: VolvoCarsConfigEntry) -> bool:
    """Set up Volvo Cars integration."""
    _LOGGER.debug("Loading entry %s", entry.entry_id)

    # Try to refresh authentication token
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

    # Setup coordinator
    coordinator = VolvoCarsDataCoordinator(hass, entry, auth_api)
    entry.runtime_data = VolvoCarsData(coordinator)

    # Setup entities
    await coordinator.async_config_entry_first_refresh()
    _remove_old_entities(hass, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register events
    entry.async_on_unload(entry.add_update_listener(options_update_listener))
    entry.async_on_unload(
        async_track_time_interval(
            hass, coordinator.async_refresh_token, timedelta(minutes=25)
        )
    )

    return True


async def async_migrate_entry(hass: HomeAssistant, entry: VolvoCarsConfigEntry) -> bool:
    """Migrate entry."""
    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        entry.version,
        entry.minor_version,
    )

    if entry.version > VolvoCarsFlowHandler.VERSION:
        # This means the user has downgraded from a future version
        return False

    if entry.version == 1:
        new_data = {**entry.data}
        new_options = {**entry.options}

        if entry.minor_version < 2:
            new_options[OPT_FUEL_CONSUMPTION_UNIT] = OPT_UNIT_LITER_PER_100KM

        hass.config_entries.async_update_entry(
            entry, data=new_data, options=new_options, version=1, minor_version=2
        )

    _LOGGER.debug(
        "Migration to configuration version %s.%s successful",
        entry.version,
        entry.minor_version,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VolvoCarsConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading entry %s", entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def options_update_listener(
    hass: HomeAssistant, entry: VolvoCarsConfigEntry
) -> None:
    """Reload entry after config changes."""
    await hass.config_entries.async_reload(entry.entry_id)


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
