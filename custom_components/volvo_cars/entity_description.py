"""Volvo Cars entity description."""

from dataclasses import dataclass

from homeassistant.helpers.entity import EntityDescription


@dataclass(frozen=True, kw_only=True)
class VolvoCarsDescription(EntityDescription):
    """Describes a Volvo Cars entity."""

    api_field: str
