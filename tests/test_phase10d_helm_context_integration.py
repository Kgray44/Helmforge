from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from shared_core.models.workspace import WorkspaceConfig, create_default_workspace


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status():
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )

    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
    )


def _workspace_with_context_values() -> WorkspaceConfig:
    workspace = create_default_workspace()
    combat_axes = dict(workspace.combat.axes)
    combat_axes["yaw"] = replace(
        combat_axes["yaw"],
        combat_center_alpha=0.52,
        combat_reverse_slew=0.06,
        combat_same_slew=0.06,
        combat_scale=0.68,
    )
    combat_axes["pitch"] = replace(combat_axes["pitch"], combat_center_alpha=0.56, combat_scale=0.84)
    tuning_axes = dict(workspace.tuning.axes)
    tuning_axes["yaw"] = replace(tuning_axes["yaw"], deadzone=0.08, output_scale=1.0)
    filtering_axes = dict(workspace.filtering.axes)
    filtering_axes["yaw"] = replace(filtering_axes["yaw"], center_alpha=0.22, reverse_slew_limit=0.42)
    return replace(
        workspace,
        combat=replace(workspace.combat, axes=combat_axes),
        tuning=replace(workspace.tuning, axes=tuning_axes),
        filtering=replace(workspace.filtering, axes=filtering_axes),
    )


def _stack_snapshot(workspace: WorkspaceConfig):
    from shared_core.math.pipeline import WorkspaceSignalPipeline
    from shared_core.math.stack import ModeState

    pipeline = WorkspaceSignalPipeline(workspace)
    return pipeline.process(
        {axis: 0.0 for axis in ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")} | {"Yaw": 0.42},
        mode_state=ModeState(combat_active=True, zoom_active=True),
    )


def test_phase10d_context_includes_workspace_modes_rules_runtime_and_evidence_labels():
    from v3_app.helm.context import HelmEvidenceSource, build_helm_context

    workspace = _workspace_with_context_values()
    context = build_helm_context(
        workspace,
        runtime_status=_runtime_status(),
        selected_axis="Yaw",
    )

    assert context.selected_axis == "Yaw"
    assert context.axis_contexts["Yaw"].tuning.deadzone == 0.08
    assert context.axis_contexts["Yaw"].filtering.center_alpha == 0.22
    assert context.axis_contexts["Yaw"].combat.combat_scale == 0.68
    assert context.mode.stack_mode == "multiply"
    assert context.mode.precision_hold_buttons == (0,)
    assert context.mode.combat_zoom_aim_buttons == (5,)
    assert context.rules.total_count == 1
    assert context.rules.disabled_count == 1
    assert context.rules.target_axes == ("Yaw",)
    assert context.runtime.runtime_truth == "blocked_missing_device"
    assert context.runtime.lifecycle_state == "Simulated"
    assert context.runtime.output_verified is False
    assert context.runtime.full_live_runtime_ready is False
    assert context.runtime.device_discovery_status == "no_supported_device"
    assert HelmEvidenceSource.WORKSPACE_VALUES.value in context.evidence_labels
    assert HelmEvidenceSource.MODE_SETTINGS.value in context.evidence_labels
    assert HelmEvidenceSource.CONDITIONAL_RULES.value in context.evidence_labels
    assert HelmEvidenceSource.RUNTIME_DIAGNOSTICS.value in context.evidence_labels


def test_phase10d_stack_context_consumes_snapshot_and_handles_unavailable_gracefully():
    from v3_app.helm.context import build_helm_context

    workspace = _workspace_with_context_values()
    unavailable = build_helm_context(workspace, runtime_status=_runtime_status(), selected_axis="Yaw")
    available = build_helm_context(
        workspace,
        runtime_status=_runtime_status(),
        selected_axis="Yaw",
        stack_snapshot=_stack_snapshot(workspace),
    )

    assert unavailable.stack.available is False
    assert unavailable.stack.evidence_source == "Unavailable"
    assert available.stack.available is True
    assert available.stack.selected_axis == "Yaw"
    assert available.stack.raw_input == 0.42
    assert isinstance(available.stack.final_output, float)
    assert available.stack.stage_count == 8
    assert available.stack.largest_stage_name
    assert "Response stack snapshot" in available.evidence_labels


def test_phase10d_engine_groups_findings_by_source_and_adds_context_cautions():
    from v3_app.helm.helm_engine import HelmEngine

    workspace = _workspace_with_context_values()
    result = HelmEngine().analyze(
        "Combat mode feels sluggish",
        workspace,
        runtime_truth="blocked_missing_device",
        output_verified=False,
        selected_axis="Yaw",
        stack_snapshot=_stack_snapshot(workspace),
    )

    grouped = {(finding.source_group, finding.evidence_source) for finding in result.analysis_findings}
    assert ("Workspace findings", "Workspace values") in grouped
    assert ("Mode findings", "Mode settings") in grouped
    assert ("Rule findings", "Conditional rules") in grouped
    assert ("Stack findings", "Response stack snapshot") in grouped
    assert ("Runtime boundary", "Runtime diagnostics") in grouped

    text = "\n".join((*result.findings, *(finding.text for finding in result.analysis_findings), *result.warnings))
    assert "Precision and combat stack by multiplication" in text
    assert "disabled yaw rule targets output scale" in text.casefold()
    assert "output_verified false" in text
    assert "No physical HOTAS is currently available for live validation" in text
    assert "live hardware analysis is not active" in text
    assert "output verified true" not in text.casefold()

    yaw_scale = next(diff for diff in result.diffs if diff.axis == "Yaw" and diff.parameter == "Combat Scale")
    assert yaw_scale.evidence_source == "Mode settings and combat profile"
    assert "multiply" in yaw_scale.reason.casefold()
    assert yaw_scale.risk_level == "Medium"


def test_phase10d_rules_are_read_only_and_apply_revert_still_preserves_them():
    from v3_app.helm.diff_model import apply_selected_diffs, revert_applied_diffs
    from v3_app.helm.helm_engine import HelmEngine

    workspace = _workspace_with_context_values()
    original_rules = workspace.rules
    result = HelmEngine().analyze("Combat aim overshoots", workspace, selected_axis="Yaw")

    updated, applied = apply_selected_diffs(workspace, result.diffs)
    reverted = revert_applied_diffs(updated, applied)

    assert updated.rules == original_rules
    assert reverted.rules == original_rules
    assert result.context.rules.total_count == len(original_rules.rules)


def test_phase10d_overlay_shows_compact_context_summary_without_sidebar_or_runtime_claims(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    _app()
    shell = HelmForgeShell(
        AppState.from_runtime_status(_runtime_status(), driver_detected=True),
        workspace=_workspace_with_context_values(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )
    shell.open_helm_overlay()
    overlay = shell.helm_overlay
    overlay.symptom_input.setPlainText("Combat mode feels sluggish")
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()

    context_summary = overlay.findChild(QLabel, "helmContextSummary")
    text = "\n".join(label.text() for label in overlay.findChildren(QLabel))

    assert context_summary is not None
    assert "Axis context: Roll" in context_summary.text()
    assert "Evidence: Workspace values, Mode settings, Conditional rules, Runtime diagnostics" in context_summary.text()
    assert "Runtime: blocked_missing_device" in context_summary.text()
    assert "Output verified: false" in context_summary.text()
    assert "Live analysis: not active" in context_summary.text()
    assert "Discovery-only status: no_supported_device" in context_summary.text()
    assert "helm" not in shell.page_widgets
    assert "Full Live Runtime Ready true" not in text
    assert "Output verified true" not in text


def test_phase10d_runtime_boundary_static_checks_and_unsafe_commands_remain_rejected():
    from shared_core.runtime.bridge_contracts import BridgeCommandType
    from v3_app.services.bridge_commands import BridgeCommandClient

    command_path = PROJECT_ROOT / ".tmp_phase10d_command.json"
    client = BridgeCommandClient(command_path=command_path)
    try:
        for command in (
            BridgeCommandType.START_BRIDGE,
            BridgeCommandType.STOP_BRIDGE,
            BridgeCommandType.RESTART_BRIDGE,
            BridgeCommandType.SUSPEND_BRIDGE,
            BridgeCommandType.VERIFY_OUTPUT,
        ):
            assert client.write_command(command).success is False
    finally:
        if command_path.exists():
            command_path.unlink()

    helm_sources = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "v3_app" / "helm").rglob("*.py"))
    for token in (
        "UpdateVJD",
        "SetAxis",
        "SetBtn",
        "AcquireVJD",
        "subprocess.Popen",
        "QProcess",
        "startDetached",
        "Start-Process",
        "win32serviceutil",
        "schtasks",
        "pystray",
        "openai",
        "anthropic",
    ):
        assert token not in helm_sources
