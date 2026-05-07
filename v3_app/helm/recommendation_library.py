from __future__ import annotations

from dataclasses import dataclass

from shared_core.models.axes import axis_by_name
from shared_core.models.workspace import WorkspaceConfig
from v3_app.helm.diff_model import HelmDiff


@dataclass(frozen=True)
class RecommendationSpec:
    axis: str
    section: str
    parameter: str
    after: float
    reason: str
    expected_outcome: str
    risk_level: str
    confidence_score: float
    group_id: str
    group_label: str
    evidence_source: str = "Workspace values"


PARAMETER_KEYS = {
    "Combat Profile": {
        "Combat Curve": "combat_curve",
        "Combat Center Alpha": "combat_center_alpha",
        "Combat Edge Alpha": "combat_edge_alpha",
        "Combat Reverse Slew": "combat_reverse_slew",
        "Combat Same Slew": "combat_same_slew",
        "Combat Scale": "combat_scale",
    },
    "Base Tuning": {
        "Curve Strength": "curve_strength",
        "Deadzone": "deadzone",
        "Anti Deadzone": "anti_deadzone",
        "Output Scale": "output_scale",
        "Precision Scale": "precision_scale",
    },
    "Filtering": {
        "Center Alpha": "center_alpha",
        "Edge Alpha": "edge_alpha",
        "Same Slew Limit": "same_slew_limit",
        "Reverse Slew Limit": "reverse_slew_limit",
    },
}


RECOMMENDATION_SPECS: dict[str, tuple[RecommendationSpec, ...]] = {
    "combat_sluggish": (
        RecommendationSpec(
            "Yaw",
            "Combat Profile",
            "Combat Center Alpha",
            0.68,
            "I would let yaw settle faster near center without making the full axis jumpy.",
            "Improved response during short target transitions.",
            "Low",
            0.86,
            "combat_responsiveness",
            "Combat Responsiveness",
        ),
        RecommendationSpec(
            "Pitch",
            "Combat Profile",
            "Combat Center Alpha",
            0.68,
            "I would bring pitch center damping up to match the yaw recovery change.",
            "More even pitch/yaw feel while tracking.",
            "Low",
            0.82,
            "fine_aim_control",
            "Fine Aim Control",
        ),
        RecommendationSpec(
            "Yaw",
            "Combat Profile",
            "Combat Reverse Slew",
            0.09,
            "I would loosen yaw reversals slightly so small corrections stop feeling stuck.",
            "Cleaner correction reversals without changing the base curve.",
            "Medium",
            0.84,
            "combat_responsiveness",
            "Combat Responsiveness",
        ),
        RecommendationSpec(
            "Yaw",
            "Combat Profile",
            "Combat Same Slew",
            0.09,
            "I would let same-direction yaw movement breathe a little more in combat.",
            "Less drag while following a moving target.",
            "Medium",
            0.83,
            "combat_responsiveness",
            "Combat Responsiveness",
        ),
        RecommendationSpec(
            "Yaw",
            "Combat Profile",
            "Combat Scale",
            0.79,
            "I would restore some yaw authority so the combat layer does not hold the axis back.",
            "Stronger yaw authority in combat without returning to full-scale movement.",
            "Medium",
            0.84,
            "combat_responsiveness",
            "Combat Responsiveness",
        ),
    ),
    "combat_overshoot": (
        RecommendationSpec(
            "Yaw",
            "Combat Profile",
            "Combat Scale",
            0.72,
            "I would trim yaw combat authority first because overshoot usually shows up there before pitch.",
            "Shorter stop distance after target snaps.",
            "Medium",
            0.78,
            "overshoot_mitigation",
            "Overshoot Mitigation",
        ),
        RecommendationSpec(
            "Pitch",
            "Combat Profile",
            "Combat Scale",
            0.78,
            "I would keep pitch slightly less aggressive so vertical corrections do not climb past the target.",
            "Smoother vertical tracking when the reticle crosses the target.",
            "Low",
            0.74,
            "overshoot_mitigation",
            "Overshoot Mitigation",
        ),
        RecommendationSpec(
            "Yaw",
            "Filtering",
            "Center Alpha",
            0.34,
            "I would add a little center filtering to slow the last part of the correction.",
            "More controlled stopping near center.",
            "Medium",
            0.72,
            "center_precision",
            "Center Precision",
        ),
    ),
    "aim_twitchy": (
        RecommendationSpec(
            "Yaw",
            "Filtering",
            "Center Alpha",
            0.38,
            "I would calm center jitter before changing the whole response curve.",
            "Less twitch around small aiming corrections.",
            "Low",
            0.77,
            "center_precision",
            "Center Precision",
        ),
        RecommendationSpec(
            "Yaw",
            "Base Tuning",
            "Deadzone",
            0.05,
            "I would add a small deadzone guard if the current center is too noisy.",
            "A quieter center with a modest cost to tiny inputs.",
            "Medium",
            0.70,
            "fine_aim_control",
            "Fine Aim Control",
        ),
    ),
    "tracking_unstable": (
        RecommendationSpec(
            "Yaw",
            "Filtering",
            "Center Alpha",
            0.36,
            "I would stabilize yaw near center because tracking instability usually starts there.",
            "Smoother sustained target following.",
            "Low",
            0.75,
            "stability",
            "Stability",
        ),
        RecommendationSpec(
            "Roll",
            "Base Tuning",
            "Curve Strength",
            0.50,
            "I would pull roll curve strength closer to yaw so the axes stop fighting each other.",
            "More predictable cross-axis tracking.",
            "Medium",
            0.72,
            "high_speed_tracking",
            "High-Speed Tracking",
        ),
    ),
    "small_movements_ignored": (
        RecommendationSpec(
            "Yaw",
            "Base Tuning",
            "Deadzone",
            0.035,
            "I would lower yaw deadzone so tiny corrections are not swallowed.",
            "Earlier response to small stick movements.",
            "Medium",
            0.73,
            "center_precision",
            "Center Precision",
        ),
        RecommendationSpec(
            "Yaw",
            "Base Tuning",
            "Anti Deadzone",
            0.02,
            "I would add a tiny anti-deadzone lift only if the center still feels absent.",
            "Small corrections become easier to start.",
            "Medium",
            0.68,
            "fine_aim_control",
            "Fine Aim Control",
        ),
    ),
    "recenter_aggressive": (
        RecommendationSpec(
            "Yaw",
            "Filtering",
            "Reverse Slew Limit",
            0.58,
            "I would soften reversal limiting so recentering does not snap or stick.",
            "Less abrupt direction changes.",
            "Low",
            0.72,
            "drift_reduction",
            "Drift Reduction",
        ),
    ),
    "roll_sensitive": (
        RecommendationSpec(
            "Roll",
            "Base Tuning",
            "Curve Strength",
            0.46,
            "I would lower roll curve strength so banking inputs do not jump ahead of yaw.",
            "A calmer roll response without changing the mapping.",
            "Low",
            0.76,
            "stability",
            "Stability",
        ),
        RecommendationSpec(
            "Roll",
            "Base Tuning",
            "Output Scale",
            0.92,
            "I would trim peak roll authority slightly because the current roll profile is very assertive.",
            "Less overshoot during bank corrections.",
            "Medium",
            0.71,
            "stability",
            "Stability",
        ),
    ),
    "pitch_inconsistent": (
        RecommendationSpec(
            "Pitch",
            "Base Tuning",
            "Curve Strength",
            0.38,
            "I would bring pitch shaping closer to roll so vertical response feels less separated.",
            "More consistent pitch response across small and medium inputs.",
            "Low",
            0.69,
            "stability",
            "Stability",
        ),
    ),
    "rudder_delayed": (
        RecommendationSpec(
            "Yaw",
            "Combat Profile",
            "Combat Scale",
            0.82,
            "I would restore yaw combat authority before touching the base axis.",
            "Less delay while preserving the combat layer.",
            "Medium",
            0.74,
            "combat_responsiveness",
            "Combat Responsiveness",
        ),
        RecommendationSpec(
            "Yaw",
            "Filtering",
            "Reverse Slew Limit",
            0.60,
            "I would loosen yaw reversals so rudder corrections respond sooner.",
            "Earlier response when changing yaw direction.",
            "Medium",
            0.72,
            "combat_responsiveness",
            "Combat Responsiveness",
        ),
    ),
    "hover_unstable": (
        RecommendationSpec(
            "Yaw",
            "Filtering",
            "Center Alpha",
            0.40,
            "I would stabilize the yaw center first because hover control depends on small corrections.",
            "Less drift during slow hover inputs.",
            "Low",
            0.73,
            "drift_reduction",
            "Drift Reduction",
        ),
    ),
    "steering_oscillates": (
        RecommendationSpec(
            "Roll",
            "Filtering",
            "Center Alpha",
            0.42,
            "I would add center smoothing so small steering corrections stop bouncing.",
            "Reduced oscillation around center.",
            "Low",
            0.74,
            "stability",
            "Stability",
        ),
        RecommendationSpec(
            "Roll",
            "Base Tuning",
            "Output Scale",
            0.90,
            "I would trim peak steering authority slightly to reduce overcorrection.",
            "Lower steering snap without changing route mappings.",
            "Medium",
            0.70,
            "stability",
            "Stability",
        ),
    ),
}


def diffs_for_symptom(workspace: WorkspaceConfig, symptom_id: str) -> tuple[HelmDiff, ...]:
    return tuple(_diff_from_spec(workspace, spec) for spec in RECOMMENDATION_SPECS.get(symptom_id, ()))


def combat_sluggish_diffs(workspace: WorkspaceConfig) -> tuple[HelmDiff, ...]:
    return diffs_for_symptom(workspace, "combat_sluggish")


def _diff_from_spec(workspace: WorkspaceConfig, spec: RecommendationSpec) -> HelmDiff:
    before = round(float(getattr(_axis_config(workspace, spec), PARAMETER_KEYS[spec.section][spec.parameter])), 2)
    return HelmDiff(
        axis=spec.axis,
        section=spec.section,
        parameter=spec.parameter,
        before=before,
        after=spec.after,
        reason=spec.reason,
        confidence_score=spec.confidence_score,
        expected_outcome=spec.expected_outcome,
        risk_level=spec.risk_level,
        group_id=spec.group_id,
        group_label=spec.group_label,
        evidence_source=spec.evidence_source,
    )


def _axis_config(workspace: WorkspaceConfig, spec: RecommendationSpec):
    axis_id = axis_by_name(spec.axis).axis_id.value
    if spec.section == "Combat Profile":
        return workspace.combat.axes[axis_id]
    if spec.section == "Base Tuning":
        return workspace.tuning.axes[axis_id]
    if spec.section == "Filtering":
        return workspace.filtering.axes[axis_id]
    raise ValueError(f"Unsupported recommendation section: {spec.section}")
