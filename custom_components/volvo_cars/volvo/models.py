"""Volvo API models."""

from dataclasses import KW_ONLY, dataclass, field, is_dataclass
from datetime import datetime
import inspect
from typing import Any

# pylint: disable-next=no-name-in-module
from pydantic import BaseModel, Field


class VolvoCarsModel(BaseModel):
    """Representation of a Volvo Cars model."""

    model: str
    upholstery: str | None
    steering: str


class VolvoCarsImages(BaseModel):
    """Representation of Volvo Cars images."""

    exterior_image_url: str = Field(..., alias="exteriorImageUrl")
    internal_image_url: str = Field(..., alias="internalImageUrl")


class VolvoCarsVehicle(BaseModel):
    """Representation of a Volvo Cars vehicle."""

    vin: str
    model_year: int = Field(..., alias="modelYear")
    gearbox: str
    fuel_type: str = Field(..., alias="fuelType")
    external_colour: str = Field(..., alias="externalColour")
    battery_capacity_kwh: float | None = Field(None, alias="batteryCapacityKWH")
    images: VolvoCarsImages
    description: VolvoCarsModel = Field(..., alias="descriptions")

    def has_battery_engine(self) -> bool:
        """Determine if vehicle has a battery engine."""
        return self.fuel_type in ("ELECTRIC", "PETROL/ELECTRIC")

    def has_combustion_engine(self) -> bool:
        """Determine if vehicle has a combustion engine."""
        return self.fuel_type in ("DIESEL", "PETROL", "PETROL/ELECTRIC")


@dataclass
class VolvoCarsApiBaseModel:
    """Base API model."""

    _: KW_ONLY
    extra_data: dict[str, Any] = field(default_factory=dict[str, Any])

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """Create instance from json dict."""
        parameters = inspect.signature(cls).parameters
        class_data: dict[str, Any] = {}
        extra_data: dict[str, Any] = {}

        for key, value in data.items():
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
                else:
                    class_data[key] = value
            else:
                extra_data[key] = value

        class_data["extra_data"] = extra_data
        return cls(**class_data)

    def get(self, key: str) -> Any:
        """Get a specific key from the API field."""
        return self.extra_data.get(key)


@dataclass
class VolvoCarsValue(VolvoCarsApiBaseModel):
    """API value model."""

    value: Any


@dataclass
class VolvoCarsValueField(VolvoCarsValue):
    """API value field model."""

    timestamp: datetime
    unit: str | None = None

    def __post_init__(self):
        """Post initialization."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class VolvoCarsGeometry(VolvoCarsApiBaseModel):
    """API geometry model."""

    coordinates: list[float] = field(default_factory=list[float])


@dataclass
class VolvoCarsLocationProperties(VolvoCarsApiBaseModel):
    """API location properties model."""

    heading: str
    timestamp: datetime

    def __post_init__(self):
        """Post initialization."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


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


class TokenResponse(BaseModel):
    """Authorization response model."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    id_token: str | None


@dataclass
class AuthorizationModel:
    """Authorization wrapper model."""

    status: str
    _: KW_ONLY
    next_url: str | None = None
    token: TokenResponse | None = None


class VolvoApiException(Exception):
    """Thrown when an API request fails."""


class VolvoAuthException(VolvoApiException):
    """Thrown when the authentication fails."""
