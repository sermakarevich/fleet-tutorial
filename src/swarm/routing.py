"""Model routing: smart plans, cheap executes, per-task pick."""

import os
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class Harness(StrEnum):
    OPENCODE = "opencode"
    PI = "pi"


class Kind(StrEnum):
    PLAN = "plan"
    EXEC = "exec"


DEFAULT_HARNESS = Harness.OPENCODE.value
DEFAULT_KIND = Kind.EXEC.value
SMART_ENV = "SWARM_SMART_MODEL"
CHEAP_ENV = "SWARM_CHEAP_MODEL"
SMART_FALLBACK = "smart"
CHEAP_FALLBACK = "cheap"
KIND_KEY = "kind"
HARNESS_KEY = "harness"


@dataclass(frozen=True)
class Settings:
    smart_model: str
    cheap_model: str

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            smart_model=os.environ.get(SMART_ENV, SMART_FALLBACK),
            cheap_model=os.environ.get(CHEAP_ENV, CHEAP_FALLBACK),
        )


@dataclass(frozen=True)
class Route:
    harness: str
    model: str


def pick(meta: Mapping[str, str] | None = None, settings: Settings | None = None) -> Route:
    """Harness plus model for one bead from its metadata mapping."""
    active = settings or Settings.load()
    labels = dict(meta or {})
    kind = labels.get(KIND_KEY, DEFAULT_KIND)
    model = active.smart_model if kind == Kind.PLAN.value else active.cheap_model
    name = labels.get(HARNESS_KEY, DEFAULT_HARNESS)
    if name not in (Harness.OPENCODE.value, Harness.PI.value):
        warnings.warn(f"unknown harness {name!r}, using {DEFAULT_HARNESS}", stacklevel=2)
        name = DEFAULT_HARNESS
    return Route(harness=name, model=model)
