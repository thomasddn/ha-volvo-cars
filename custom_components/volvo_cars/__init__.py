"""The Volvo Cars integration."""

from datetime import UTC, date, datetime, time
import logging
from typing import cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.event import async_track_utc_time_change
from homeassistant.helpers.service import ServiceCall
from homeassistant.helpers.typing import ConfigType

from .config_flow import VolvoCarsFlowHandler, get_setting
from .const import (
    CONF_VCC_API_KEY,
    CONF_VIN,
    DOMAIN,
    OPT_FUEL_CONSUMPTION_UNIT,
    OPT_UNIT_LITER_PER_100KM,
    PLATFORMS,
    SERVICE_PARAM_DATA,
    SERVICE_PARAM_ENTRY,
    SERVICE_REFRESH_DATA,
)
from .coordinator import (
    TokenCoordinator,
    VolvoCarsConfigEntry,
    VolvoCarsData,
    VolvoCarsDataCoordinator,
)
from .data_manager import VOLVO_CARS_KEY
from .entity import get_entity_id
from .factory import async_create_auth_api
from .store import VolvoCarsStoreManager
from .volvo.api import VolvoCarsApi

_LOGGER = logging.getLogger(__name__)

_SERVICE_REFRESH_SCHEMA = vol.Schema(
    {
        vol.Optional(SERVICE_PARAM_ENTRY): str,
        vol.Optional(SERVICE_PARAM_DATA): list[str],
    }
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Volvo Cars integration."""
    _LOGGER.debug("Loading integration")

    # Register services
    async def refresh_data(call: ServiceCall) -> None:
        entry_id = call.data.get(SERVICE_PARAM_ENTRY)
        data = call.data.get(SERVICE_PARAM_DATA)

        # Remove duplicates
        data = list(set(data)) if data else []

        entries = (
            [hass.config_entries.async_get_entry(entry_id)]
            if entry_id
            else hass.config_entries.async_entries(DOMAIN)
        )

        for entry in entries:
            if entry and (entry := cast(VolvoCarsConfigEntry, entry)):
                await entry.runtime_data.coordinator.async_partial_refresh(data)

    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH_DATA, refresh_data, schema=_SERVICE_REFRESH_SCHEMA
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: VolvoCarsConfigEntry) -> bool:
    """Set up Volvo Cars entry."""
    _LOGGER.debug("%s - Loading entry", entry.entry_id)

    # Load store
    assert entry.unique_id is not None
    store = VolvoCarsStoreManager(hass, entry.unique_id)
    await store.async_load()

    # Create APIs
    client = async_get_clientsession(hass)
    api = VolvoCarsApi(
        client,
        get_setting(entry, CONF_VIN),
        get_setting(entry, CONF_VCC_API_KEY),
    )
    auth_api = await async_create_auth_api(hass, client, api.update_access_token)

    # Setup token refresh
    token_coordinator = TokenCoordinator(hass, entry, store, auth_api)
    await token_coordinator.async_schedule_refresh(True)

    # Setup data coordinator
    coordinator = VolvoCarsDataCoordinator(hass, entry, store, api)

    # Reset API count if it the auto-reset was missed
    await _async_reset_request_count_if_missed(
        store.data["api_requests_reset_time"], coordinator
    )

    # Setup entry
    entry.runtime_data = VolvoCarsData(coordinator, token_coordinator, store)
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register events
    entry.async_on_unload(entry.add_update_listener(_options_update_listener))
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
                store = VolvoCarsStoreManager(hass, entry.unique_id)
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

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry.runtime_data.token_coordinator.cancel_refresh()

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    _LOGGER.debug("%s - Removing entry", entry.entry_id)

    # entry.runtime_data does not exist at this time. Creating a new
    # store manager to delete it the storage data.
    if entry.unique_id:
        store = VolvoCarsStoreManager(hass, entry.unique_id)
        await store.async_remove()

    cleanup(hass, entry)


async def _async_reset_request_count_if_missed(
    last_reset_time: str | None, coordinator: VolvoCarsDataCoordinator
) -> None:
    if not last_reset_time:
        return

    now = datetime.now(UTC)
    most_recent_midnight = datetime.combine(
        date(now.year, now.month, now.day), time(0, 0, 0, tzinfo=UTC)
    )
    reset_time = datetime.fromisoformat(last_reset_time)

    if reset_time < most_recent_midnight:
        await coordinator.async_reset_request_count()


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


def cleanup(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove data file if no more entries are loaded."""

    if (data_manager := hass.data.get(VOLVO_CARS_KEY)) is None:
        return

    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    count = len(entries)

    # During unloading of the entry, it is not marked as unloaded yet. So
    # count can be 1 if it is the last one.
    if count == 0 or (count == 1 and entries[0].entry_id == entry.entry_id):
        data_manager.shutdown()
