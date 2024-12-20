"""Diagnostics for Volvo Cars integration."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_VCC_API_KEY, CONF_VIN
from .coordinator import VolvoCarsConfigEntry

TO_REDACT_DATA = [
    "coordinates",
    "heading",
    "vin",
]

TO_REDACT_ENTRY = [
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VCC_API_KEY,
    CONF_VIN,
]

TO_REDACT_STORE = [
    CONF_ACCESS_TOKEN,
    "refresh_token",
]


async def async_get_config_entry_diagnostics(
    _: HomeAssistant, config_entry: VolvoCarsConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data.coordinator
    store = config_entry.runtime_data.store

    entry_diagnostics = async_redact_data(config_entry.data, TO_REDACT_ENTRY)
    entry_diagnostics["entry_id"] = config_entry.entry_id

    vehicle_data = _to_dict(coordinator.vehicle)
    coordinator_data = _to_dict(coordinator.data)
    store_data = await store.async_load()

    return {
        "entry": entry_diagnostics,
        "vehicle": async_redact_data(vehicle_data, TO_REDACT_DATA),
        "coordinator": async_redact_data(coordinator_data, TO_REDACT_DATA),
        "store": async_redact_data(store_data, TO_REDACT_STORE),
    }


def _to_dict(obj: Any) -> Any:
    if isinstance(obj, dict):
        data = {}
        for k, v in obj.items():
            data[k] = _to_dict(v)
        return data

    if hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [_to_dict(v) for v in obj]

    if hasattr(obj, "__dict__"):
        return {
            key: _to_dict(value)
            for key, value in obj.__dict__.items()
            if not callable(value) and not key.startswith("_")
        }

    return obj
