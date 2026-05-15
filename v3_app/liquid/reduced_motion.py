from __future__ import annotations

from collections.abc import Mapping

from v3_app.liquid.motion import MotionSettings, motion_settings_from_mapping


def motion_settings_from_environment(values: Mapping[str, str] | None = None) -> MotionSettings:
    return motion_settings_from_mapping(values)

