from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


BUILT_IN_PROFILE_NAMES = (
    "Balanced Flight",
    "Precision Tracking",
    "Aggressive Combat",
    "Smooth Cinematic",
)
CURRENT_WORKSPACE_PROFILE_NAME = "Current Workspace"


class ProfileType(str, Enum):
    BUILT_IN = "built-in"
    PERSONAL = "personal"


@dataclass(frozen=True)
class Profile:
    profile_id: str
    name: str
    profile_type: ProfileType
    active: bool = False
    source_path: str | None = None
    description: str = ""


@dataclass(frozen=True)
class ProfilesConfig:
    profiles: tuple[Profile, ...] = field(default_factory=tuple)
    active_profile_id: str = "current-workspace"


def _slug(name: str) -> str:
    return name.casefold().replace(" ", "-")


def default_profiles() -> tuple[Profile, ...]:
    built_ins = tuple(
        Profile(
            profile_id=_slug(name),
            name=name,
            profile_type=ProfileType.BUILT_IN,
            description=f"Recovered built-in preset: {name}.",
        )
        for name in BUILT_IN_PROFILE_NAMES
    )
    current = Profile(
        profile_id="current-workspace",
        name=CURRENT_WORKSPACE_PROFILE_NAME,
        profile_type=ProfileType.PERSONAL,
        active=True,
        source_path="hotas_bridge_config_v3.json",
        description="Editable personal workspace copy.",
    )
    return (*built_ins, current)


def default_profiles_config() -> ProfilesConfig:
    return ProfilesConfig(profiles=default_profiles(), active_profile_id="current-workspace")

