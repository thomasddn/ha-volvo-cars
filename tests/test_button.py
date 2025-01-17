"""Test Volvo Cars buttons."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant


@pytest.mark.use_model("xc90_ice")
async def test_engine_buttons_disabled(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test if engine buttons are not added."""

    with patch("custom_components.volvo_cars.PLATFORMS", [Platform.BUTTON]):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert hass.states.get("button.volvo_myvolvo_engine_start") is None
        assert hass.states.get("button.volvo_myvolvo_engine_stop") is None
