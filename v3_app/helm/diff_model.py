from __future__ import annotations

from dataclasses import dataclass, replace

from shared_core.models.axes import axis_by_name
from shared_core.models.workspace import WorkspaceConfig


COMBAT_PARAMETER_KEYS = {
    "Combat Curve": "combat_curve",
    "Combat Center Alpha": "combat_center_alpha",
    "Combat Edge Alpha": "combat_edge_alpha",
    "Combat Reverse Slew": "combat_reverse_slew",
    "Combat Same Slew": "combat_same_slew",
    "Combat Scale": "combat_scale",
}

TUNING_PARAMETER_KEYS = {
    "Curve Strength": "curve_strength",
    "Deadzone": "deadzone",
    "Anti Deadzone": "anti_deadzone",
    "Output Scale": "output_scale",
    "Precision Scale": "precision_scale",
}

FILTERING_PARAMETER_KEYS = {
    "Center Alpha": "center_alpha",
    "Edge Alpha": "edge_alpha",
    "Same Slew Limit": "same_slew_limit",
    "Reverse Slew Limit": "reverse_slew_limit",
}

PARAMETER_KEYS_BY_SECTION = {
    "Combat Profile": COMBAT_PARAMETER_KEYS,
    "Base Tuning": TUNING_PARAMETER_KEYS,
    "Filtering": FILTERING_PARAMETER_KEYS,
}


@dataclass(frozen=True)
class HelmDiff:
    axis: str
    section: str
    parameter: str
    before: float
    after: float
    reason: str
    selected: bool = True
    applied: bool = False
    confidence_score: float = 0.72
    expected_outcome: str = "A small, reversible tuning change in the current workspace draft."
    risk_level: str = "Low"
    reversibility: str = "In-memory reversible"
    group_id: str = "general"
    group_label: str = "General"

    @property
    def parameter_key(self) -> str:
        try:
            return PARAMETER_KEYS_BY_SECTION[self.section][self.parameter]
        except KeyError as exc:
            raise ValueError(f"Unsupported Helm diff parameter: {self.section} / {self.parameter}") from exc

    @property
    def label(self) -> str:
        return f"{self.axis} {self.parameter}"

    @property
    def value_text(self) -> str:
        return f"{_fmt(self.before)} -> {_fmt(self.after)}"

    @property
    def delta_amount(self) -> float:
        return round(float(self.after) - float(self.before), 3)


def apply_selected_diffs(workspace: WorkspaceConfig, diffs: tuple[HelmDiff, ...]) -> tuple[WorkspaceConfig, tuple[HelmDiff, ...]]:
    updated = workspace
    applied: list[HelmDiff] = []
    for diff in diffs:
        if not diff.selected:
            applied.append(diff)
            continue
        updated = _apply_value(updated, diff, diff.after)
        applied.append(replace(diff, applied=True))
    return updated, tuple(applied)


def revert_applied_diffs(workspace: WorkspaceConfig, diffs: tuple[HelmDiff, ...]) -> WorkspaceConfig:
    updated = workspace
    for diff in reversed(diffs):
        if diff.applied:
            updated = _apply_value(updated, diff, diff.before)
    return updated


def _apply_value(workspace: WorkspaceConfig, diff: HelmDiff, value: float) -> WorkspaceConfig:
    axis_id = axis_by_name(diff.axis).axis_id.value
    if diff.section == "Combat Profile":
        axes = dict(workspace.combat.axes)
        axes[axis_id] = replace(axes[axis_id], **{diff.parameter_key: float(value)})
        return replace(workspace, combat=replace(workspace.combat, axes=axes))
    if diff.section == "Base Tuning":
        axes = dict(workspace.tuning.axes)
        axes[axis_id] = replace(axes[axis_id], **{diff.parameter_key: float(value)})
        return replace(workspace, tuning=replace(workspace.tuning, axes=axes))
    if diff.section == "Filtering":
        axes = dict(workspace.filtering.axes)
        axes[axis_id] = replace(axes[axis_id], **{diff.parameter_key: float(value)})
        return replace(workspace, filtering=replace(workspace.filtering, axes=axes))
    raise ValueError(f"Unsupported Helm diff section: {diff.section}")


def _fmt(value: float) -> str:
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text if text else "0"
