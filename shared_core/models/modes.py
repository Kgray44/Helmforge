from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StackMode(str, Enum):
    MULTIPLY = "multiply"


@dataclass(frozen=True)
class ModeConfig:
    precision_hold_buttons: tuple[int, ...] = (0,)
    combat_trigger_buttons: tuple[int, ...] = ()
    combat_zoom_aim_buttons: tuple[int, ...] = (5,)
    combat_extra_buttons: tuple[int, ...] = ()
    precision_combat_stack_mode: StackMode = StackMode.MULTIPLY


def default_mode_config() -> ModeConfig:
    return ModeConfig()

