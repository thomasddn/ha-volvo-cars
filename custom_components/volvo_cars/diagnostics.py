"""Diagnostics for Volvo Cars integration."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_REFRESH_TOKEN, CONF_VCC_API_KEY, CONF_VIN
from .coordinator import VolvoCarsConfigEntry

TO_REDACT_ENTRY = [
    CONF_ACCESS_TOKEN,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_USERNAME,
    CONF_VCC_API_KEY,
    CONF_VIN,
]

TO_REDACT_DATA = [
    "coordinates",
    "heading",
    "vin",
]


async def async_get_config_entry_diagnostics(
    _: HomeAssistant, config_entry: VolvoCarsConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data.coordinator

    entry_diagnostics = async_redact_data(config_entry.data, TO_REDACT_ENTRY)
    entry_diagnostics["entry_id"] = config_entry.entry_id

    return {
        "entry": entry_diagnostics,
        "vehicle": async_redact_data(coordinator.vehicle.dict(), TO_REDACT_DATA),
        "state": async_redact_data(coordinator.data, TO_REDACT_DATA),
    }
