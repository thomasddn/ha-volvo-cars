"""Test Volvo API models."""

from datetime import UTC, datetime

import pytest

from custom_components.volvo_cars.volvo.models import (
    VolvoCarsLocation,
    VolvoCarsValueField,
)

from .common import load_json_object_fixture


@pytest.mark.parametrize(("has_timestamp"), [(True), (False)])
def test_create_value_field(has_timestamp: bool) -> None:
    """Test deserialization of VolvoCarsValueField."""

    data = (
        load_json_object_fixture("engine_status.json")
        if has_timestamp
        else load_json_object_fixture("engine_status_no_timestamp.json")
    )

    field = VolvoCarsValueField.from_dict(data["engineStatus"])

    assert field
    assert field.value == "STOPPED"

    if has_timestamp:
        date = datetime(2024, 12, 30, 15, 0, 0, 0, UTC)
        assert field.timestamp == date
    else:
        assert field.timestamp is None


@pytest.mark.parametrize(("has_timestamp"), [(True), (False)])
def test_create_location(has_timestamp: bool) -> None:
    """Test deserialization of VolvoCarsLocation."""

    data = (
        load_json_object_fixture("location.json")
        if has_timestamp
        else load_json_object_fixture("location_no_timestamp.json")
    )

    location = VolvoCarsLocation.from_dict(data)

    assert location
    assert location.properties
    assert location.properties.heading == "90"
    assert location.geometry
    assert len(location.geometry.coordinates) == 3

    if has_timestamp:
        date = datetime(2024, 12, 30, 15, 0, 0, 0, UTC)
        assert location.properties.timestamp == date
    else:
        assert location.properties.timestamp is None
