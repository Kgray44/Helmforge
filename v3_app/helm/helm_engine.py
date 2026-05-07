from __future__ import annotations

from dataclasses import dataclass, replace

from shared_core.models.workspace import WorkspaceConfig
from v3_app.helm.context import HelmContext, build_helm_context
from v3_app.helm.diff_model import HelmDiff
from v3_app.helm.recommendation_library import diffs_for_symptom
from v3_app.helm.symptom_library import MatchedSymptom, match_symptom


@dataclass(frozen=True)
class HelmFinding:
    title: str
    text: str
    severity: str = "info"
    evidence_source: str = "Workspace values"
    source_group: str = "Workspace findings"


@dataclass(frozen=True)
class HelmFollowUpQuestion:
    question_id: str
    prompt: str
    options: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class HelmRecommendationGroup:
    group_id: str
    label: str
    confidence_score: float
    summary: str
    diffs: tuple[HelmDiff, ...]
    selected: bool = True
    expanded: bool = True

    @property
    def confidence(self) -> str:
        return confidence_label(self.confidence_score)

    @property
    def affected_count(self) -> int:
        return len(self.diffs)


@dataclass(frozen=True)
class HelmRecommendationResult:
    symptom: MatchedSymptom | None
    status: str
    confidence: str
    summary: str
    findings: tuple[str, ...]
    diffs: tuple[HelmDiff, ...]
    confidence_score: float = 0.0
    groups: tuple[HelmRecommendationGroup, ...] = ()
    follow_up_questions: tuple[HelmFollowUpQuestion, ...] = ()
    analysis_findings: tuple[HelmFinding, ...] = ()
    warnings: tuple[str, ...] = ()
    context: HelmContext | None = None


FOLLOW_UP_QUESTIONS = (
    HelmFollowUpQuestion(
        "movement_zone",
        "Does the issue happen mostly near center?",
        ("near_center", "mid_throw", "edge"),
        "Center-heavy symptoms call for smaller filtering and deadzone changes before scale changes.",
    ),
    HelmFollowUpQuestion(
        "mode_scope",
        "Does the issue occur in all modes or only combat?",
        ("combat", "all_modes", "precision"),
        "Mode scope tells me whether to stay inside the combat profile or touch base tuning.",
    ),
    HelmFollowUpQuestion(
        "motion_style",
        "Is the issue more noticeable during tracking or snapping?",
        ("tracking", "snapping", "both"),
        "Tracking and snapping failures usually need different slew and scale changes.",
    ),
)


class HelmEngine:
    def analyze(
        self,
        symptom_text: str,
        workspace: WorkspaceConfig,
        *,
        runtime_truth: str = "blocked_missing_device",
        output_verified: bool = False,
        answers: dict[str, str] | None = None,
        selected_axis: str | None = None,
        stack_snapshot: object | None = None,
        runtime_diagnostics: object | None = None,
    ) -> HelmRecommendationResult:
        symptom = match_symptom(symptom_text)
        context = build_helm_context(
            workspace,
            runtime_truth=runtime_truth,
            output_verified=output_verified,
            selected_axis=selected_axis,
            stack_snapshot=stack_snapshot,
            runtime_diagnostics=runtime_diagnostics,
        )
        workspace_findings, warnings = analyze_workspace(workspace, context=context)
        if symptom is None:
            return HelmRecommendationResult(
                symptom=None,
                status="idle",
                confidence="None",
                confidence_score=0.0,
                summary="Tell me what feels wrong and I'll compare it against the current workspace.",
                findings=(
                    "I have not applied anything.",
                    "I'll propose draft-only changes before anything is applied.",
                ),
                diffs=(),
                analysis_findings=workspace_findings,
                warnings=warnings,
                context=context,
            )

        answer_map = answers or {}
        if symptom.needs_follow_up and not _has_useful_answers(answer_map):
            return HelmRecommendationResult(
                symptom=symptom,
                status="needs_follow_up",
                confidence="Low",
                confidence_score=0.42,
                summary="I need one more bit of context before I stage tuning changes.",
                findings=(
                    "This symptom can come from center damping, curve shape, or mode scaling.",
                    "Answer the short follow-up questions and I'll keep the recommendation narrow.",
                ),
                diffs=(),
                follow_up_questions=FOLLOW_UP_QUESTIONS,
                analysis_findings=workspace_findings,
                warnings=warnings,
                context=context,
            )

        symptom_id = _refine_symptom_id(symptom.symptom_id, answer_map)
        diffs = _contextualize_diffs(diffs_for_symptom(workspace, symptom_id), context)
        if diffs:
            confidence_score = _confidence_score(symptom_id, answer_map)
            groups = group_diffs(diffs)
            findings = _findings_for(symptom_id, context)
            context_findings, context_warnings = analyze_context(context)
            return HelmRecommendationResult(
                symptom=symptom,
                status="ready",
                confidence=confidence_label(confidence_score),
                confidence_score=confidence_score,
                summary=_summary_for(symptom_id, answer_map),
                findings=findings,
                diffs=diffs,
                groups=groups,
                follow_up_questions=(),
                analysis_findings=(*workspace_findings, *context_findings),
                warnings=(*warnings, *context_warnings),
                context=context,
            )

        return HelmRecommendationResult(
            symptom=symptom,
            status="needs_follow_up",
            confidence=symptom.confidence_hint,
            confidence_score=0.50,
            summary="I can read this symptom, but I need narrower context before I stage safe changes.",
            findings=(
                "I did not stage tuning changes.",
                "I can stay deterministic if you narrow the symptom with a follow-up answer.",
            ),
            diffs=(),
            follow_up_questions=FOLLOW_UP_QUESTIONS,
            analysis_findings=workspace_findings,
            warnings=warnings,
            context=context,
        )


def extract_context(
    workspace: WorkspaceConfig,
    *,
    runtime_truth: str,
    output_verified: bool,
) -> HelmContext:
    return build_helm_context(workspace, runtime_truth=runtime_truth, output_verified=output_verified)


def analyze_workspace(workspace: WorkspaceConfig, *, context: HelmContext | None = None) -> tuple[tuple[HelmFinding, ...], tuple[str, ...]]:
    findings: list[HelmFinding] = []
    warnings: list[str] = []
    yaw_tuning = workspace.tuning.axes["yaw"]
    roll_tuning = workspace.tuning.axes["roll"]
    yaw_combat = workspace.combat.axes["yaw"]
    pitch_combat = workspace.combat.axes["pitch"]

    if yaw_tuning.deadzone >= 0.07:
        findings.append(
            HelmFinding(
                "Yaw center gate",
                f"Yaw deadzone is {yaw_tuning.deadzone:.2f}, which can make small corrections feel ignored.",
                "warning",
                "Workspace values",
                "Workspace findings",
            )
        )
        warnings.append("Extreme values are present in the current workspace; I would apply changes in small batches.")
    if roll_tuning.curve_strength - yaw_tuning.curve_strength >= 0.08:
        findings.append(
            HelmFinding(
                "Cross-axis mismatch",
                "Roll response is significantly more aggressive than yaw, so combined aiming can feel uneven.",
                "info",
                "Workspace values",
                "Workspace findings",
            )
        )
    if yaw_combat.combat_scale < 0.72 and pitch_combat.combat_scale >= 0.80:
        findings.append(
            HelmFinding(
                "Combat yaw authority",
                "Yaw combat scale is lower than pitch, so yaw may feel held back in combat.",
                "info",
                "Workspace values",
                "Workspace findings",
            )
        )
    if yaw_combat.combat_same_slew < 0.10 and yaw_combat.combat_reverse_slew < 0.10:
        findings.append(
            HelmFinding(
                "Combat slew gate",
                "Yaw combat slew values are very low, so reversals and same-direction motion may both feel sticky.",
                "warning",
                "Workspace values",
                "Workspace findings",
            )
        )
    if not findings:
        findings.append(
            HelmFinding(
                "Workspace check",
                "I did not find an extreme tuning conflict in the current workspace.",
                "info",
                "Workspace values",
                "Workspace findings",
            )
        )
    return tuple(findings), tuple(dict.fromkeys(warnings))


def analyze_context(context: HelmContext) -> tuple[tuple[HelmFinding, ...], tuple[str, ...]]:
    findings: list[HelmFinding] = []
    warnings: list[str] = []
    if context.mode.stack_mode == "multiply":
        message = "Precision and combat stack by multiplication, so aggressive scaling can compound."
        findings.append(HelmFinding("Mode stack", message, "warning", "Mode settings", "Mode findings"))
        warnings.append(message)

    if context.rules.disabled_rule_summaries:
        for summary in context.rules.disabled_rule_summaries:
            findings.append(
                HelmFinding(
                    "Rule context",
                    f"{summary} I'm not changing rules in Helm v1.",
                    "info",
                    "Conditional rules",
                    "Rule findings",
                )
            )

    if context.stack.available:
        findings.append(
            HelmFinding(
                "Response stack snapshot",
                (
                    f"{context.stack.selected_axis} stack snapshot reports {context.stack.largest_stage_name} "
                    "as the largest observed stage delta."
                ),
                "info",
                "Response stack snapshot",
                "Stack findings",
            )
        )
    else:
        findings.append(
            HelmFinding(
                "Response stack snapshot",
                "Response stack context is unavailable here; I will not pretend stage evidence exists.",
                "info",
                "Unavailable",
                "Stack findings",
            )
        )

    runtime_lines = [
        f"Bridge telemetry says runtime truth is {context.runtime.runtime_truth}.",
        f"output_verified {str(context.runtime.output_verified).lower()}; changes are draft tuning only.",
    ]
    if context.runtime.device_discovery_status == "no_supported_device":
        runtime_lines.append("No physical HOTAS is currently available for live validation.")
    elif context.runtime.device_discovery_status == "supported_device_detected":
        runtime_lines.append("Supported HOTAS detected; discovery-only status, polling not active.")
    runtime_lines.append("I'm using workspace/simulation context only; live hardware analysis is not active.")
    findings.append(
        HelmFinding(
            "Runtime boundary",
            " ".join(runtime_lines),
            "warning",
            "Runtime diagnostics",
            "Runtime boundary",
        )
    )
    return tuple(findings), tuple(dict.fromkeys(warnings))


def group_diffs(diffs: tuple[HelmDiff, ...]) -> tuple[HelmRecommendationGroup, ...]:
    groups: dict[str, list[HelmDiff]] = {}
    labels: dict[str, str] = {}
    for diff in diffs:
        groups.setdefault(diff.group_id, []).append(diff)
        labels[diff.group_id] = diff.group_label
    ordered: list[HelmRecommendationGroup] = []
    for group_id, group_diffs_ in groups.items():
        confidence = round(sum(diff.confidence_score for diff in group_diffs_) / len(group_diffs_), 2)
        ordered.append(
            HelmRecommendationGroup(
                group_id=group_id,
                label=labels[group_id],
                confidence_score=confidence,
                summary=_group_summary(labels[group_id]),
                diffs=tuple(group_diffs_),
            )
        )
    return tuple(ordered)


def confidence_label(score: float) -> str:
    if score >= 0.80:
        return "High"
    if score >= 0.60:
        return "Medium"
    if score > 0.0:
        return "Low"
    return "None"


def _has_useful_answers(answers: dict[str, str]) -> bool:
    return bool(answers.get("movement_zone") or answers.get("mode_scope") or answers.get("motion_style"))


def _refine_symptom_id(symptom_id: str, answers: dict[str, str]) -> str:
    if symptom_id in {"controls_inconsistent", "general"}:
        if answers.get("mode_scope") == "combat" and answers.get("movement_zone") == "near_center":
            return "aim_twitchy"
        if answers.get("motion_style") == "tracking":
            return "tracking_unstable"
        return "small_movements_ignored"
    return symptom_id


def _confidence_score(symptom_id: str, answers: dict[str, str]) -> float:
    base_scores = {
        "combat_sluggish": 0.84,
        "combat_overshoot": 0.76,
        "aim_twitchy": 0.70,
        "tracking_unstable": 0.72,
        "small_movements_ignored": 0.68,
        "recenter_aggressive": 0.66,
        "roll_sensitive": 0.73,
        "pitch_inconsistent": 0.64,
        "rudder_delayed": 0.70,
        "hover_unstable": 0.68,
        "steering_oscillates": 0.71,
    }
    score = base_scores.get(symptom_id, 0.55)
    if answers:
        score = min(0.79, score + 0.08)
    return round(score, 2)


def _contextualize_diffs(diffs: tuple[HelmDiff, ...], context: HelmContext) -> tuple[HelmDiff, ...]:
    contextualized: list[HelmDiff] = []
    for diff in diffs:
        reason = diff.reason
        evidence = diff.evidence_source
        risk = diff.risk_level
        if diff.section == "Combat Profile":
            evidence = "Mode settings and combat profile"
        if context.mode.stack_mode == "multiply" and diff.section == "Combat Profile":
            reason = f"{reason} Because precision and combat use multiply stacking, I would keep this change moderate."
            if diff.risk_level == "Low" and abs(diff.delta_amount) >= 0.10:
                risk = "Medium"
        if any(rule_axis.casefold() == diff.axis.casefold() for rule_axis in context.rules.target_axes):
            reason = f"{reason} I also see rule context on {diff.axis}, so I would review rules before larger tuning moves."
        contextualized.append(replace(diff, reason=reason, risk_level=risk, evidence_source=evidence))
    return tuple(contextualized)


def _summary_for(symptom_id: str, answers: dict[str, str]) -> str:
    summaries = {
        "combat_sluggish": "I'd soften yaw recovery slightly and raise combat center damping.",
        "combat_overshoot": "I'd reduce combat overshoot by trimming authority first, then adding light center control.",
        "aim_twitchy": "I'd calm the center before touching the full travel of the axis.",
        "tracking_unstable": "I'd stabilize sustained tracking by evening out yaw filtering and roll shaping.",
        "small_movements_ignored": "I'd open the center just enough for small corrections to register.",
        "recenter_aggressive": "I'd loosen reversal behavior so recentering feels controlled instead of abrupt.",
        "roll_sensitive": "I'd take the edge off roll without changing your route mapping.",
        "pitch_inconsistent": "I'd bring pitch shaping closer to the rest of the workspace.",
        "rudder_delayed": "I'd restore yaw authority and loosen the reversal gate in a small, reversible step.",
        "hover_unstable": "I'd stabilize center yaw first because hover control depends on tiny corrections.",
        "steering_oscillates": "I'd reduce steering bounce with center smoothing and a small peak authority trim.",
    }
    if answers:
        return f"{summaries.get(symptom_id, 'I found a narrow deterministic tuning path.')} Your answers keep this scoped."
    return summaries.get(symptom_id, "I found a narrow deterministic tuning path.")


def _findings_for(symptom_id: str, context: HelmContext) -> tuple[str, ...]:
    return (
        "I checked the current workspace values before proposing changes.",
        f"Runtime truth is {context.runtime.runtime_truth}; I am not treating this as hardware evidence.",
        f"I see {context.rules.total_count} conditional rule entries, but I won't create or edit rules.",
        "I'll keep this in memory until you save the workspace.",
        _diagnostic_sentence(symptom_id),
    )


def _diagnostic_sentence(symptom_id: str) -> str:
    sentences = {
        "combat_sluggish": "I found the combat layer is probably holding yaw back more than pitch.",
        "combat_overshoot": "I found the safest first move is reducing combat authority before changing base tuning.",
        "aim_twitchy": "I found a center-noise pattern, so I am keeping the changes near center.",
        "tracking_unstable": "I found a likely cross-axis mismatch that can make tracking feel unsettled.",
        "small_movements_ignored": "I found a center-entry issue that can hide small corrections.",
        "roll_sensitive": "I found roll shaping is more assertive than the rest of the workspace.",
        "rudder_delayed": "I found yaw combat authority and reversal limiting are the likely first suspects.",
        "steering_oscillates": "I found a stability-first path that avoids route changes.",
    }
    return sentences.get(symptom_id, "I found a conservative tuning path for this symptom.")


def _group_summary(label: str) -> str:
    summaries = {
        "Fine Aim Control": "Small movement behavior and center feel.",
        "Combat Responsiveness": "Combat-layer authority, damping, and slew response.",
        "Stability": "Smoothing and scale changes intended to reduce oscillation.",
        "Center Precision": "Near-center filtering and deadzone behavior.",
        "High-Speed Tracking": "Cross-axis behavior under larger motion.",
        "Drift Reduction": "Slow correction stability and reversal behavior.",
        "Overshoot Mitigation": "Scale and stop-distance changes for target transitions.",
    }
    return summaries.get(label, "Related deterministic tuning changes.")
