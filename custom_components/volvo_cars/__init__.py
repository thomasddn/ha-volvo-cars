"""The Volvo Cars integration."""

from datetime import timedelta
import logging

from requests import ConnectTimeout, HTTPError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.event import (
    async_track_time_interval,
    async_track_utc_time_change,
)

from .config_flow import VolvoCarsFlowHandler
from .const import (
    CONF_VCC_API_KEY,
    CONF_VIN,
    OPT_FUEL_CONSUMPTION_UNIT,
    OPT_UNIT_LITER_PER_100KM,
    PLATFORMS,
)
from .coordinator import VolvoCarsConfigEntry, VolvoCarsData, VolvoCarsDataCoordinator
from .entity import get_entity_id
from .store import create_store
from .volvo.api import VolvoCarsApi
from .volvo.auth import VolvoCarsAuthApi
from .volvo.models import VolvoAuthException

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: VolvoCarsConfigEntry) -> bool:
    """Set up Volvo Cars integration."""
    _LOGGER.debug("%s - Loading entry", entry.entry_id)

    assert entry.unique_id is not None
    store = create_store(hass, entry.unique_id)
    store_data = await store.async_load()

    if store_data is None:
        _LOGGER.exception("Storage %s missing.", store.key)
        raise ConfigEntryNotReady(f"Storage {store.key} missing.")

    client = async_get_clientsession(hass)
    auth_api = VolvoCarsAuthApi(client)

    # Try to refresh authentication token
    try:
        result = await auth_api.async_refresh_token(store_data["refresh_token"])
    except VolvoAuthException as ex:
        _LOGGER.exception("Authentication failed")
        raise ConfigEntryAuthFailed("Authentication failed.") from ex
    except (ConnectTimeout, HTTPError) as ex:
        _LOGGER.exception("Connection failed")
        raise ConfigEntryNotReady("Unable to connect to Volvo API.") from ex

    if result.token is None:
        _LOGGER.exception("Authentication token is None")
        raise ConfigEntryAuthFailed("Authentication token is None.")

    # Save tokens
    await store.async_update(
        access_token=result.token.access_token,
        refresh_token=result.token.refresh_token,
    )

    # Create api
    api = VolvoCarsApi(
        client,
        entry.data[CONF_VIN],
        entry.data[CONF_VCC_API_KEY],
        result.token.access_token,
    )

    # Setup coordinator
    coordinator = VolvoCarsDataCoordinator(
        hass, entry, store_data["data_update_interval"], auth_api, api
    )
    entry.runtime_data = VolvoCarsData(coordinator, store)

    # Setup entities
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register events
    entry.async_on_unload(entry.add_update_listener(_options_update_listener))
    entry.async_on_unload(
        async_track_time_interval(
            hass, coordinator.async_refresh_token, timedelta(minutes=25)
        )
    )
    entry.async_on_unload(
        async_track_utc_time_change(
            hass, coordinator.async_reset_request_count, hour=0, minute=0, second=0
        )
    )

    return True


async def async_migrate_entry(hass: HomeAssistant, entry: VolvoCarsConfigEntry) -> bool:
    """Migrate entry."""
    _LOGGER.debug(
        "%s - Migrating configuration from version %s.%s",
        entry.entry_id,
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
            _remove_old_entities(hass, entry.runtime_data.coordinator)

        if entry.minor_version < 3:
            if CONF_ACCESS_TOKEN in new_data and "refresh_token" in new_data:
                assert entry.unique_id is not None
                store = create_store(hass, entry.unique_id)
                await store.async_update(
                    access_token=new_data.pop(CONF_ACCESS_TOKEN),
                    refresh_token=new_data.pop("refresh_token"),
                )

            if CONF_PASSWORD in new_data:
                new_data.pop(CONF_PASSWORD)

        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            options=new_options,
            version=VolvoCarsFlowHandler.VERSION,
            minor_version=VolvoCarsFlowHandler.MINOR_VERSION,
        )

    _LOGGER.debug(
        "%s - Migration to configuration version %s.%s successful",
        entry.entry_id,
        entry.version,
        entry.minor_version,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VolvoCarsConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("%s - Unloading entry", entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    _LOGGER.debug("%s - Removing entry", entry.entry_id)

    # entry.runtime_data does not exist at this time. Creating a new
    # store manager to delete it the storage data.
    store = create_store(hass, entry.unique_id)
    await store.async_remove()


async def _options_update_listener(
    hass: HomeAssistant, entry: VolvoCarsConfigEntry
) -> None:
    """Reload entry after config changes."""
    await hass.config_entries.async_reload(entry.entry_id)


def _remove_old_entities(
    hass: HomeAssistant, coordinator: VolvoCarsDataCoordinator
) -> None:
    old_entities: tuple[tuple[Platform, str], ...] = (
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
