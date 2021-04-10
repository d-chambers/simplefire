"""
Dataclasses configured in a sensible way
"""
import functools
from pydantic.dataclasses import dataclass


class Config:
    """Config for base model."""

    extra = "forbid"
    validate_assignment = True
    arbitrary_types_allowed = True


dataclass = functools.partial(dataclass, config=Config)
