from __future__ import annotations

from dataclasses import dataclass, replace

from shared_core.models.workspace import WorkspaceConfig, WorkspaceState, create_default_workspace
from v3_app.helm.diff_model import HelmDiff, apply_selected_diffs, revert_applied_diffs
from v3_app.helm.helm_engine import HelmEngine, HelmRecommendationResult
from v3_app.services.app_state import AppState


@dataclass(frozen=True)
class HelmFindingItem:
    title: str
    body: str
    evidence_source: str
    state_role: str


@dataclass(frozen=True)
class HelmProposedChangeItem:
    change_id: str
    title: str
    group_label: str
    axis: str
    section: str
    parameter: str
    value_text: str
    reason: str
    expected_outcome: str
    confidence: str
    risk_level: str
    evidence_source: str
    selected: bool
    truth_note: str


@dataclass(frozen=True)
class HelmApplyResult:
    valid: bool
    workspace: WorkspaceConfig
    message: str
    status_label: str
    applied_diffs: tuple[HelmDiff, ...] = ()
    validation_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class HelmCommandModel:
    status_label: str
    summary: str
    confidence_label: str
    symptom_text: str
    selected_axis: str
    evidence_labels: tuple[str, ...]
    findings: tuple[HelmFindingItem, ...]
    proposed_changes: tuple[HelmProposedChangeItem, ...]
    selected_change_count: int
    apply_available: bool
    revert_available: bool
    draft_state_label: str
    truth_source_notes: tuple[str, ...]
    result: HelmRecommendationResult
    signature: tuple[object, ...]


def build_helm_command_model(
    *,
    workspace: WorkspaceConfig | None = None,
    state: AppState | None = None,
    symptom_text: str = "Combat mode feels sluggish",
    selected_axis: str = "Yaw",
    last_apply_result: HelmApplyResult | None = None,
) -> HelmCommandModel:
    workspace = workspace or create_default_workspace()
    runtime_truth = state.runtime.truth.value if state is not None else "blocked_missing_device"
    output_verified = bool(state.runtime.output_verified) if state is not None else False
    result = HelmEngine().analyze(
        symptom_text,
        workspace,
        runtime_truth=runtime_truth,
        output_verified=output_verified,
        selected_axis=selected_axis,
    )
    proposed = tuple(_proposed_change(diff) for diff in result.diffs)
    findings = _finding_items(result)
    selected_count = sum(1 for change in proposed if change.selected)
    evidence_labels = result.context.evidence_labels if result.context is not None else ("Workspace values",)
    draft_label = (
        last_apply_result.status_label
        if last_apply_result is not None
        else "Recommendations ready for workspace draft" if proposed else "Review-only Helm status"
    )
    notes = (
        "Helm uses deterministic existing recommendation logic.",
        "Proposed changes are workspace draft changes only.",
        "Output proof unchanged.",
        "No live hardware action.",
    )
    signature = (
        result.status,
        result.confidence,
        result.summary,
        tuple(change.change_id for change in proposed),
        tuple((finding.title, finding.body) for finding in findings),
        draft_label,
        output_verified,
        runtime_truth,
    )
    return HelmCommandModel(
        status_label=_status_label(result),
        summary=result.summary,
        confidence_label=result.confidence,
        symptom_text=symptom_text,
        selected_axis=selected_axis,
        evidence_labels=evidence_labels,
        findings=findings,
        proposed_changes=proposed,
        selected_change_count=selected_count,
        apply_available=bool(proposed),
        revert_available=bool(last_apply_result and last_apply_result.applied_diffs),
        draft_state_label=draft_label,
        truth_source_notes=notes,
        result=result,
        signature=signature,
    )


def stage_selected_helm_changes(
    workspace: WorkspaceConfig,
    result: HelmRecommendationResult,
    *,
    selected_change_ids: tuple[str, ...] | None = None,
) -> HelmApplyResult:
    if not result.diffs:
        return HelmApplyResult(
            False,
            workspace,
            "No Helm recommendation is available to stage.",
            "Helm unavailable",
            validation_errors=("No proposed changes.",),
        )
    selected_ids = set(selected_change_ids or tuple(_change_id(diff) for diff in result.diffs))
    selected: list[HelmDiff] = []
    for diff in result.diffs:
        selected.append(replace(diff, selected=_change_id(diff) in selected_ids))
    if not any(diff.selected for diff in selected):
        return HelmApplyResult(
            False,
            workspace,
            "Select at least one Helm change before staging.",
            "Helm selection required",
            validation_errors=("No selected changes.",),
        )
    updated, applied = apply_selected_diffs(workspace, tuple(selected))
    applied_diffs = tuple(diff for diff in applied if diff.applied)
    updated = replace(updated, state=replace(updated.state, dirty=True, saved=False))
    count = len(applied_diffs)
    return HelmApplyResult(
        True,
        updated,
        f"Draft Helm change staged: {count} workspace recommendation{'s' if count != 1 else ''}. Output proof unchanged.",
        "Draft Helm change",
        applied_diffs=applied_diffs,
    )


def revert_helm_changes(
    workspace: WorkspaceConfig,
    applied_diffs: tuple[HelmDiff, ...],
    *,
    base_workspace: WorkspaceConfig | None = None,
) -> HelmApplyResult:
    if not applied_diffs:
        return HelmApplyResult(
            False,
            workspace,
            "There is no staged Helm batch to revert.",
            "Nothing to revert",
            validation_errors=("No applied Helm diffs.",),
        )
    reverted = base_workspace if base_workspace is not None else revert_applied_diffs(workspace, applied_diffs)
    if base_workspace is None:
        reverted = replace(reverted, state=WorkspaceState())
    return HelmApplyResult(
        True,
        reverted,
        "Reverted the last Helm draft batch. Output proof unchanged.",
        "Helm changes reverted",
    )


def _finding_items(result: HelmRecommendationResult) -> tuple[HelmFindingItem, ...]:
    items: list[HelmFindingItem] = []
    for finding in result.analysis_findings:
        items.append(
            HelmFindingItem(
                finding.title,
                finding.text,
                finding.evidence_source,
                "warning" if finding.severity == "warning" else "info",
            )
        )
    for index, text in enumerate(result.findings, start=1):
        items.append(HelmFindingItem(f"Finding {index}", text, "Recommendation analysis", "info"))
    if not items:
        items.append(
            HelmFindingItem(
                "Helm standby",
                "Tell Helm what feels wrong and it will compare that against workspace values.",
                "Workspace values",
                "info",
            )
        )
    return tuple(items)


def _proposed_change(diff: HelmDiff) -> HelmProposedChangeItem:
    return HelmProposedChangeItem(
        change_id=_change_id(diff),
        title=diff.label,
        group_label=diff.group_label,
        axis=diff.axis,
        section=diff.section,
        parameter=diff.parameter,
        value_text=diff.value_text,
        reason=diff.reason,
        expected_outcome=diff.expected_outcome,
        confidence=f"{diff.confidence_score:.2f}",
        risk_level=diff.risk_level,
        evidence_source=diff.evidence_source,
        selected=diff.selected,
        truth_note="Output proof unchanged. Workspace draft only.",
    )


def _status_label(result: HelmRecommendationResult) -> str:
    if result.status == "ready":
        return "Recommendations ready"
    if result.status == "needs_follow_up":
        return "More context needed"
    return "Helm standby"


def _change_id(diff: HelmDiff) -> str:
    return "_".join(
        part
        for part in (
            _safe(diff.axis),
            _safe(diff.section),
            _safe(diff.parameter),
        )
        if part
    )


def _safe(text: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in text.casefold()).strip("_")
