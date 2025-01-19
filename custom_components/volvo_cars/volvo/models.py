"""Volvo API models."""

from dataclasses import KW_ONLY, dataclass, field, is_dataclass
from datetime import datetime
import inspect
import re
from typing import Any, TypeVar

T = TypeVar("T", bound="VolvoCarsApiBaseModel")
_TO_SNAKE_CASE_REGEX = re.compile(r"(?<=[a-z0-9])([A-Z])")


def _sanitize_json_key(key: str) -> str:
    key = "description" if key == "descriptions" else key
    key = _TO_SNAKE_CASE_REGEX.sub(r"_\1", key)
    return key.lower()


@dataclass
class VolvoCarsApiBaseModel:
    """Base API model."""

    _: KW_ONLY
    extra_data: dict[str, Any] = field(default_factory=dict[str, Any])

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T | None:
        """Create instance from json dict."""
        parameters = inspect.signature(cls).parameters
        class_data: dict[str, Any] = {}
        extra_data: dict[str, Any] = {}

        for key, value in data.items():
            key = _sanitize_json_key(key)
            if key in parameters:
                # Check if the field is a dataclass and the value is a dict
                param_type = parameters[key].annotation
                if (
                    is_dataclass(param_type)
                    and isinstance(param_type, type)
                    and issubclass(param_type, VolvoCarsApiBaseModel)
                    and isinstance(value, dict)
                ):
                    # Recursive call for nested dataclasses
                    class_data[key] = param_type.from_dict(value)
                elif key == "timestamp" and isinstance(value, str):
                    if value:
                        class_data[key] = datetime.fromisoformat(value)
                else:
                    class_data[key] = value
            else:
                extra_data[key] = value

        if len(class_data) == 0:
            return None

        class_data["extra_data"] = extra_data
        return cls(**class_data)

    def get(self, key: str) -> Any:
        """Get a specific key from the API field."""
        return self.extra_data.get(key)


@dataclass
class VolvoCarsModel(VolvoCarsApiBaseModel):
    """Representation of a Volvo Cars model."""

    model: str
    steering: str
    upholstery: str | None = None


@dataclass
class VolvoCarsImages(VolvoCarsApiBaseModel):
    """Representation of Volvo Cars images."""

    exterior_image_url: str
    internal_image_url: str


@dataclass
class VolvoCarsVehicle(VolvoCarsApiBaseModel):
    """Representation of a Volvo Cars vehicle."""

    vin: str
    model_year: int
    gearbox: str
    fuel_type: str
    external_colour: str
    images: VolvoCarsImages
    description: VolvoCarsModel
    battery_capacity_kwh: float | None = None

    def has_battery_engine(self) -> bool:
        """Determine if vehicle has a battery engine."""
        return self.fuel_type in ("ELECTRIC", "PETROL/ELECTRIC", "NONE")

    def has_combustion_engine(self) -> bool:
        """Determine if vehicle has a combustion engine."""
        return self.fuel_type in ("DIESEL", "PETROL", "PETROL/ELECTRIC")


@dataclass
class VolvoCarsValue(VolvoCarsApiBaseModel):
    """API value model."""

    value: Any


@dataclass
class VolvoCarsValueField(VolvoCarsValue):
    """API value field model."""

    timestamp: datetime | None = None
    unit: str | None = None


@dataclass
class VolvoCarsGeometry(VolvoCarsApiBaseModel):
    """API geometry model."""

    coordinates: list[float] = field(default_factory=list[float])


@dataclass
class VolvoCarsLocationProperties(VolvoCarsApiBaseModel):
    """API location properties model."""

    heading: str
    timestamp: datetime | None = None


@dataclass
class VolvoCarsLocation(VolvoCarsApiBaseModel):
    """API location model."""

    type: str
    properties: VolvoCarsLocationProperties
    geometry: VolvoCarsGeometry


@dataclass
class VolvoCarsAvailableCommand(VolvoCarsApiBaseModel):
    """Available command model."""

    command: str
    href: str


@dataclass
class VolvoCarsCommandResult(VolvoCarsApiBaseModel):
    """Command result model."""

    vin: str
    invoke_status: str
    message: str


@dataclass
class TokenResponse(VolvoCarsApiBaseModel):
    """Authorization response model."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    id_token: str | None = None


@dataclass
class AuthorizationModel:
    """Authorization wrapper model."""

    status: str
    _: KW_ONLY
    next_url: str | None = None
    token: TokenResponse | None = None


class VolvoApiException(Exception):
    """Thrown when an API request fails."""

    def __init__(self, message: str = "") -> None:
        """Initialize exception."""
        self.message = message


class VolvoAuthException(VolvoApiException):
    """Thrown when the authentication fails."""
