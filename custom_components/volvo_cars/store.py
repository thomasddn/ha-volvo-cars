"""Data related to the entry."""

from __future__ import annotations

from typing import TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_MINOR_VERSION = 2


class StoreData(TypedDict):
    """Volvo Cars storage data."""

    access_token: str
    refresh_token: str
    data_update_interval: int
    engine_run_time: int
    api_request_count: int


class VolvoCarsStore(Store[StoreData]):
    """Volvo Cars storage."""

    def merge_data(
        self,
        data: StoreData,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        data_update_interval: int | None = None,
        engine_run_time: int | None = None,
        api_request_count: int | None = None,
    ) -> StoreData:
        """Merge new values into the data."""

        if access_token is not None:
            data["access_token"] = access_token
        if refresh_token is not None:
            data["refresh_token"] = refresh_token
        if data_update_interval is not None:
            data["data_update_interval"] = data_update_interval
        if engine_run_time is not None:
            data["engine_run_time"] = engine_run_time
        if api_request_count is not None:
            data["api_request_count"] = api_request_count

        return data

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

        if old_major_version == 1:
            if old_minor_version < 2:
                return self.merge_data(
                    old_data,
                    data_update_interval=135,
                    engine_run_time=15,
                    api_request_count=0,
                )

        return StoreData(**old_data)


class VolvoCarsStoreManager:
    """Class to handle store access."""

    def __init__(self, hass: HomeAssistant, unique_id: str) -> None:
        """Initialize class."""
        self._store = VolvoCarsStore(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{unique_id}",
            minor_version=STORAGE_MINOR_VERSION,
        )

        self._data: StoreData | None = None

    @property
    def data(self) -> StoreData:
        """Return the store data."""
        assert self._data is not None
        return self._data

    async def async_load(self) -> StoreData:
        """Load store data."""
        self._data = await self._store.async_load()

        if not self._data:
            self._data = self._create_default()

        return self._data

    async def async_update(
        self,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        data_update_interval: int | None = None,
        engine_run_time: int | None = None,
        api_request_count: int | None = None,
    ) -> None:
        """Update the current store with given values."""

        self._data = self._data or await self.async_load()

        self._store.merge_data(
            self._data,
            access_token=access_token,
            refresh_token=refresh_token,
            data_update_interval=data_update_interval,
            engine_run_time=engine_run_time,
            api_request_count=api_request_count,
        )

        await self._store.async_save(self._data)

    async def async_remove(self) -> None:
        """Remove store data."""
        self._data = None
        await self._store.async_remove()

    def _create_default(self) -> StoreData:
        return StoreData(
            access_token="",
            refresh_token="",
            data_update_interval=135,
            engine_run_time=15,
            api_request_count=0,
        )
