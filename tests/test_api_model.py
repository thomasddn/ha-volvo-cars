"""Test Volvo API models."""

from datetime import UTC, datetime

import pytest

from custom_components.volvo_cars.volvo.models import (
    VolvoCarsErrorResult,
    VolvoCarsLocation,
    VolvoCarsValueField,
    VolvoCarsVehicle,
)

from .common import load_json_object_fixture


@pytest.mark.parametrize(("has_timestamp"), [(True), (False)])
def test_create_value_field(has_timestamp: bool) -> None:
    """Test deserialization of VolvoCarsValueField."""

    data = (
        load_json_object_fixture("engine_status")
        if has_timestamp
        else load_json_object_fixture("engine_status_no_timestamp")
    )

    field = VolvoCarsValueField.from_dict(data["engineStatus"])  # type: ignore[arg-type]
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
        load_json_object_fixture("location")
        if has_timestamp
        else load_json_object_fixture("location_no_timestamp")
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


@pytest.mark.parametrize(("has_colour"), [(True), (False)])
def test_create_vehicle(has_colour: bool) -> None:
    """Test deserialization of VolvoCarsVehicle."""

    data = (
        load_json_object_fixture("ex30_bev/vehicle")
        if has_colour
        else load_json_object_fixture("ex30_bev_no_colour/vehicle")
    )

    vehicle = VolvoCarsVehicle.from_dict(data)

    assert vehicle
    assert vehicle.vin == "YV1ABCDEFG1234567"
    assert vehicle.model_year == 2024
    assert vehicle.gearbox == "AUTOMATIC"

    if has_colour:
        assert vehicle.external_colour == "Crystal White Pearl"
    else:
        assert vehicle.external_colour is None


@pytest.mark.parametrize(("has_description"), [(True), (False)])
def test_error_parsing(has_description: bool) -> None:
    """Test parsing an error message."""

    message = "Something went wrong."
    description = "More details about the error."

    error_data = {"message": message}

    if has_description:
        error_data["description"] = description

    error = VolvoCarsErrorResult.from_dict(error_data)

    assert error
    assert error.message == message

    if has_description:
        assert error.description == description
    else:
        assert error.description is None
