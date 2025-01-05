"""Data related to the entry."""

from __future__ import annotations

from typing import TypedDict, overload

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_MINOR_VERSION = 2


def create_store(hass: HomeAssistant, unique_id: str) -> VolvoCarsStore:
    """Create a VolvoCars store."""
    return VolvoCarsStore(
        hass,
        STORAGE_VERSION,
        f"{DOMAIN}.{unique_id}",
        minor_version=STORAGE_MINOR_VERSION,
    )


class StoreData(TypedDict):
    """Volvo Cars storage data."""

    access_token: str
    refresh_token: str
    data_update_interval: int


class VolvoCarsStore(Store[StoreData]):
    """Volvo Cars storage."""

    @overload
    async def async_update(self, data: StoreData) -> None: ...

    @overload
    async def async_update(
        self,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        data_update_interval: int | None = None,
    ) -> None: ...

    async def async_update(
        self,
        data: StoreData | None = None,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        data_update_interval: int | None = None,
    ) -> None:
        """Update the current store with given values."""

        if data:
            await self.async_save(data)
            return

        data = await self.async_load()

        if data:
            if access_token:
                data["access_token"] = access_token
            if refresh_token:
                data["refresh_token"] = refresh_token
            if data_update_interval:
                data["data_update_interval"] = data_update_interval

            await self.async_save(data)

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: StoreData | None,
    ) -> StoreData:
        if old_data is None:
            raise ValueError("old_data is required")

        if old_major_version > STORAGE_VERSION:
            # This means the user has downgraded from a future version
            return StoreData(**old_data)

        if STORAGE_VERSION == 1:
            if STORAGE_MINOR_VERSION < 3:
                return StoreData(**old_data, data_update_interval=135)

        return StoreData(**old_data)
