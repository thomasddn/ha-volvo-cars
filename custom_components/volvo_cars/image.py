"""Volvo Cars images."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging
from urllib import parse

from httpx import AsyncClient, HTTPStatusError, RequestError

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.util.color import color_rgb_to_hex

from .const import OPT_IMG_BG_COLOR, OPT_IMG_TRANSPARENT
from .coordinator import VolvoCarsConfigEntry, VolvoCarsDataCoordinator
from .entity import VolvoCarsEntity
from .entity_description import VolvoCarsDescription
from .volvo.models import VolvoCarsApiBaseModel

_LOGGER = logging.getLogger(__name__)
_HEADERS = {
    "Accept-Language": "en-GB",
    "Sec-Fetch-User": "?1",
    "User-Agent": "PostmanRuntime/7.43.0",
}
_IMAGE_ANGLE_MAP = {
    "1": "right",
    "3": "front",
    "4": "threeQuartersFrontLeft",
    "5": "threeQuartersRearLeft",
    "6": "rear",
    "7": "left",
}

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class VolvoCarsImageDescription(VolvoCarsDescription, ImageEntityDescription):
    """Describes a Volvo Cars image entity."""

    api_field: str = ""
    image_url_fn: Callable[[VolvoCarsDataCoordinator], str]


def _exterior_image_url(
    exterior_url: str, angle: str, entry: VolvoCarsConfigEntry
) -> str:
    if not exterior_url:
        return ""

    url_parts = parse.urlparse(exterior_url)

    if url_parts.netloc.startswith("wizz"):
        if new_angle := _IMAGE_ANGLE_MAP.get(angle):
            current_angle = url_parts.path.split("/")[-2]
            return exterior_url.replace(current_angle, new_angle)

        return ""

    query = parse.parse_qs(url_parts.query, keep_blank_values=True)
    query["angle"] = [angle]

    if not entry.options.get(OPT_IMG_TRANSPARENT, True):
        rgb_color = entry.options.get(OPT_IMG_BG_COLOR, [255, 255, 255])
        color = color_rgb_to_hex(*rgb_color).lstrip("#")
        query["bg"] = [color]

    return url_parts._replace(query=parse.urlencode(query, doseq=True)).geturl()


async def _async_image_exists(client: AsyncClient, url: str) -> bool:
    if not url:
        return False

    try:
        response = await client.get(url, timeout=10, follow_redirects=True)
        response.raise_for_status()
    except (RequestError, HTTPStatusError):
        _LOGGER.debug("Image does not exist: %s", url)
        return False
    else:
        return True


# pylint: disable=unexpected-keyword-arg
IMAGES: tuple[VolvoCarsImageDescription, ...] = (
    VolvoCarsImageDescription(
        key="exterior",
        translation_key="exterior",
        image_url_fn=lambda coordinator: _exterior_image_url(
            coordinator.vehicle.images.exterior_image_url, "1", coordinator.config_entry
        ),
    ),
    VolvoCarsImageDescription(
        key="exterior_back",
        translation_key="exterior_back",
        image_url_fn=lambda coordinator: _exterior_image_url(
            coordinator.vehicle.images.exterior_image_url, "6", coordinator.config_entry
        ),
    ),
    VolvoCarsImageDescription(
        key="exterior_back_driver",
        translation_key="exterior_back_driver",
        image_url_fn=lambda coordinator: _exterior_image_url(
            coordinator.vehicle.images.exterior_image_url, "5", coordinator.config_entry
        ),
    ),
    VolvoCarsImageDescription(
        key="exterior_back_passenger",
        translation_key="exterior_back_passenger",
        image_url_fn=lambda coordinator: _exterior_image_url(
            coordinator.vehicle.images.exterior_image_url, "2", coordinator.config_entry
        ),
    ),
    VolvoCarsImageDescription(
        key="exterior_front",
        translation_key="exterior_front",
        image_url_fn=lambda coordinator: _exterior_image_url(
            coordinator.vehicle.images.exterior_image_url, "3", coordinator.config_entry
        ),
    ),
    VolvoCarsImageDescription(
        key="exterior_front_driver",
        translation_key="exterior_front_driver",
        image_url_fn=lambda coordinator: _exterior_image_url(
            coordinator.vehicle.images.exterior_image_url, "4", coordinator.config_entry
        ),
    ),
    VolvoCarsImageDescription(
        key="exterior_front_passenger",
        translation_key="exterior_front_passenger",
        image_url_fn=lambda coordinator: _exterior_image_url(
            coordinator.vehicle.images.exterior_image_url, "0", coordinator.config_entry
        ),
    ),
    VolvoCarsImageDescription(
        key="exterior_side_driver",
        translation_key="exterior_side_driver",
        image_url_fn=lambda coordinator: _exterior_image_url(
            coordinator.vehicle.images.exterior_image_url, "7", coordinator.config_entry
        ),
    ),
    VolvoCarsImageDescription(
        key="interior",
        translation_key="interior",
        image_url_fn=lambda coordinator: coordinator.vehicle.images.internal_image_url,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VolvoCarsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up images."""
    coordinator = entry.runtime_data.coordinator
    client = get_async_client(hass, False)
    client.headers.update(_HEADERS)

    images = [
        VolvoCarsImage(coordinator, description)
        for description in IMAGES
        if (await _async_image_exists(client, description.image_url_fn(coordinator)))
        is True
    ]

    async_add_entities(images)


# pylint: disable=abstract-method
class VolvoCarsImage(VolvoCarsEntity, ImageEntity):
    """Representation of a Volvo Cars image."""

    entity_description: VolvoCarsImageDescription

    def __init__(
        self,
        coordinator: VolvoCarsDataCoordinator,
        description: VolvoCarsImageDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, Platform.IMAGE)
        ImageEntity.__init__(self, coordinator.hass)

        self._client.headers.update(_HEADERS)

    def _update_state(self, api_field: VolvoCarsApiBaseModel | None) -> None:
        url = self.entity_description.image_url_fn(self.coordinator)

        if self._attr_image_url != url:
            self._attr_image_url = url
            self._attr_image_last_updated = datetime.now()
