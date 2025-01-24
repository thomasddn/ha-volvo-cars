"""Test Volvo Cars sensors."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.volvo_cars.const import (
    OPT_FUEL_CONSUMPTION_UNIT,
    OPT_UNIT_LITER_PER_100KM,
    OPT_UNIT_MPG_UK,
    OPT_UNIT_MPG_US,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import (
    METRIC_SYSTEM as METRIC,
    US_CUSTOMARY_SYSTEM as IMPERIAL,
    UnitSystem,
)


@pytest.mark.parametrize(
    ("entity_id", "unit", "value", "unit_of_measurement"),
    [
        ("sensor.volvo_myvolvo_average_speed_automatic", METRIC, "26", "km/h"),
        ("sensor.volvo_myvolvo_average_speed_automatic", IMPERIAL, "16", "mph"),
    ],
)
async def test_ha_unit_conversion(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    entity_id: str,
    unit: UnitSystem,
    value: str,
    unit_of_measurement: str,
) -> None:
    """Test if automatic conversion by HA is still applied."""

    with patch("custom_components.volvo_cars.PLATFORMS", [Platform.SENSOR]):
        hass.config.units = unit

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        entity = hass.states.get(entity_id)
        assert entity
        assert entity.state == value
        assert entity.attributes.get("unit_of_measurement") == unit_of_measurement


@pytest.mark.parametrize(
    ("entity_id", "unit", "value", "unit_of_measurement"),
    [
        (
            "sensor.volvo_myvolvo_average_fuel_consumption",
            OPT_UNIT_LITER_PER_100KM,
            "7.2",
            "L/100 km",
        ),
        (
            "sensor.volvo_myvolvo_average_fuel_consumption",
            OPT_UNIT_MPG_UK,
            "39.07",
            "mpg",
        ),
        (
            "sensor.volvo_myvolvo_average_fuel_consumption",
            OPT_UNIT_MPG_US,
            "32.53",
            "mpg",
        ),
    ],
)
@pytest.mark.use_model("xc90_ice")
async def test_fuel_unit_conversion(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_config_entry: MockConfigEntry,
    entity_id: str,
    unit: str,
    value: str,
    unit_of_measurement: str,
) -> None:
    """Test fuel unit conversion."""

    with patch("custom_components.volvo_cars.PLATFORMS", [Platform.SENSOR]):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        hass.config_entries.async_update_entry(
            mock_config_entry,
            options={OPT_FUEL_CONSUMPTION_UNIT: unit},
        )
        await hass.async_block_till_done()

        entity = hass.states.get(entity_id)
        assert entity
        assert entity.state == value
        assert entity.attributes.get("unit_of_measurement") == unit_of_measurement
