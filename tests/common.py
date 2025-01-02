"""Common test utils for Volvo Cars."""

from functools import lru_cache
import pathlib

from homeassistant.util.json import JsonObjectType, json_loads_object


@lru_cache
def load_json_object_fixture(filename: str) -> JsonObjectType:
    """Load a JSON object from a fixture."""
    fixture_path = pathlib.Path().cwd().joinpath("tests", "fixtures", filename)
    fixture = fixture_path.read_text(encoding="utf8")

    return json_loads_object(fixture)
