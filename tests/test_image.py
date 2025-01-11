"""Test Volvo Cars images."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant


async def test_has_images(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_image_client,
) -> None:
    """Test vehicle with images."""

    with patch("custom_components.volvo_cars.PLATFORMS", [Platform.IMAGE]):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        entity_id = "image.volvo_myvolvo_exterior"
        entity = hass.states.get(entity_id)

        assert entity


@pytest.mark.use_model("s90_diesel")
async def test_no_images(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_image_client,
) -> None:
    """Test vehicle without images."""

    with patch("custom_components.volvo_cars.PLATFORMS", [Platform.IMAGE]):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        entity_id = "image.volvo_myvolvo_exterior"
        entity = hass.states.get(entity_id)

        assert entity is None
