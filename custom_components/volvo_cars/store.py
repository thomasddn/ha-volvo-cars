"""Data related to the entry."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypedDict, Unpack

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_MINOR_VERSION = 3


class StoreData(TypedDict, total=False):
    """Volvo Cars storage data."""

    access_token: str
    refresh_token: str
    data_update_interval: int
    engine_run_time: int
    api_request_count: int
    api_requests_reset_time: str | None


class VolvoCarsStore(Store[StoreData]):
    """Volvo Cars storage."""

    def merge_data(self, data: StoreData, **kwargs: Unpack[StoreData]) -> StoreData:
        """Merge new values into the data."""

        for key, value in kwargs.items():
            if value is not None and key in StoreData.__annotations__:
                data[key] = value  # type: ignore[literal-required]

        return data

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: StoreData | None,
    ) -> StoreData:
        if old_data is None:
            raise ValueError("old_data is required")

        data = StoreData(**old_data)

        if old_major_version > STORAGE_VERSION:
            # This means the user has downgraded from a future version
            return data

        if old_major_version == 1:
            if old_minor_version < 2:
                self.merge_data(
                    data,
                    data_update_interval=135,
                    engine_run_time=15,
                    api_request_count=0,
                )

            if old_minor_version < 3:
                self.merge_data(
                    data,
                    api_requests_reset_time=datetime.now(UTC).isoformat(),
                )

        return data


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

    async def async_update(self, **kwargs: Unpack[StoreData]) -> None:
        """Update the current store with given values."""

        self._data = self._data or await self.async_load()

        self._store.merge_data(self._data, **kwargs)
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
            api_requests_reset_time=datetime.now(UTC).isoformat(),
        )
