"""Common test utils for Volvo Cars."""

from functools import lru_cache
import pathlib

from homeassistant.util.json import JsonObjectType, json_loads_object


@lru_cache
def load_json_object_fixture(name: str, model: str | None = None) -> JsonObjectType:
    """Load a JSON object from a fixture."""

    name = f"{name}.json"

    fixtures_path = pathlib.Path().cwd().joinpath("tests", "fixtures")

    # If a model is given, check if there is the requested data
    # is available. If not, fallback to the fixtures root.
    path = fixtures_path.joinpath(model) if model else fixtures_path
    data_path = path.joinpath(name)

    if data_path.exists():
        fixture = data_path.read_text(encoding="utf8")
    else:
        fixture = fixtures_path.joinpath(name).read_text(encoding="utf8")

    return json_loads_object(fixture)
