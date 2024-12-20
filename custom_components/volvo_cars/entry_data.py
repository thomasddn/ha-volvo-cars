"""Data related to the entry."""

from __future__ import annotations

from typing import TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1


def create_store(hass: HomeAssistant, unique_id: str) -> VolvoCarsStore:
    """Create a VolvoCars store."""
    return VolvoCarsStore(hass, STORAGE_VERSION, f"{DOMAIN}.{unique_id}")


class StoreData(TypedDict):
    """Volvo Cars storage data."""

    access_token: str
    refresh_token: str


class VolvoCarsStore(Store[StoreData]):
    """Volvo Cars storage."""
