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
    engine_run_time: int
    api_request_count: int


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
        engine_run_time: int | None = None,
        api_request_count: int | None = None,
    ) -> None: ...

    async def async_update(
        self,
        data: StoreData | None = None,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        data_update_interval: int | None = None,
        engine_run_time: int | None = None,
        api_request_count: int | None = None,
    ) -> None:
        """Update the current store with given values."""

        if data:
            await self.async_save(data)
            return

        data = await self.async_load()

        if not data:
            data = self._create_default()

        self._merge_data(
            data,
            access_token,
            refresh_token,
            data_update_interval,
            engine_run_time,
            api_request_count,
        )
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

        if old_major_version == 1:
            if old_minor_version < 2:
                return self._merge_data(
                    old_data,
                    data_update_interval=135,
                    engine_run_time=15,
                    api_request_count=0,
                )

        return StoreData(**old_data)

    def _merge_data(
        self,
        data: StoreData,
        access_token: str | None = None,
        refresh_token: str | None = None,
        data_update_interval: int | None = None,
        engine_run_time: int | None = None,
        api_request_count: int | None = None,
    ) -> StoreData:
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

    def _create_default(self) -> StoreData:
        return StoreData(
            access_token="",
            refresh_token="",
            data_update_interval=135,
            engine_run_time=15,
            api_request_count=0,
        )
