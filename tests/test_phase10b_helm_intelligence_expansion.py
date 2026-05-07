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


def _workspace_with_diagnostic_values() -> WorkspaceConfig:
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
    tuning_axes["roll"] = replace(tuning_axes["roll"], curve_strength=0.72, output_scale=1.0)
    tuning_axes["yaw"] = replace(tuning_axes["yaw"], deadzone=0.08, curve_strength=0.62)
    filtering_axes = dict(workspace.filtering.axes)
    filtering_axes["yaw"] = replace(filtering_axes["yaw"], center_alpha=0.22, reverse_slew_limit=0.42)
    return replace(
        workspace,
        combat=replace(workspace.combat, axes=combat_axes),
        tuning=replace(workspace.tuning, axes=tuning_axes),
        filtering=replace(workspace.filtering, axes=filtering_axes),
    )


def test_phase10b_combat_sluggish_path_has_rich_grouped_recommendations():
    from v3_app.helm.helm_engine import HelmEngine

    result = HelmEngine().analyze("Combat mode feels sluggish", _workspace_with_diagnostic_values())

    assert result.status == "ready"
    assert result.confidence == "High"
    assert result.confidence_score == 0.84
    assert [group.label for group in result.groups] == ["Combat Responsiveness", "Fine Aim Control"]
    assert sum(group.affected_count for group in result.groups) == 5
    assert result.groups[0].confidence == "High"
    assert result.groups[0].confidence_score == 0.84

    yaw_scale = next(diff for diff in result.diffs if diff.axis == "Yaw" and diff.parameter == "Combat Scale")
    assert yaw_scale.before == 0.68
    assert yaw_scale.after == 0.79
    assert yaw_scale.delta_amount == 0.11
    assert yaw_scale.expected_outcome
    assert yaw_scale.risk_level == "Medium"
    assert yaw_scale.reversibility == "In-memory reversible"
    assert yaw_scale.confidence_score == 0.84
    assert yaw_scale.group_label == "Combat Responsiveness"


def test_phase10b_multiple_symptom_paths_are_deterministic_and_local():
    from v3_app.helm.helm_engine import HelmEngine

    engine = HelmEngine()
    workspace = _workspace_with_diagnostic_values()
    symptoms = {
        "Combat aim overshoots": "Overshoot Mitigation",
        "Aim feels twitchy": "Center Precision",
        "Roll feels too sensitive": "Stability",
        "Rudder feels delayed": "Combat Responsiveness",
        "Steering oscillates": "Stability",
    }

    first_pass = {symptom: engine.analyze(symptom, workspace) for symptom in symptoms}
    second_pass = {symptom: engine.analyze(symptom, workspace) for symptom in symptoms}

    for symptom, expected_group in symptoms.items():
        assert first_pass[symptom].status == "ready"
        assert expected_group in {group.label for group in first_pass[symptom].groups}
        assert [(diff.axis, diff.section, diff.parameter, diff.before, diff.after) for diff in first_pass[symptom].diffs] == [
            (diff.axis, diff.section, diff.parameter, diff.before, diff.after) for diff in second_pass[symptom].diffs
        ]


def test_phase10b_follow_up_questions_refine_ambiguous_symptom_confidence():
    from v3_app.helm.helm_engine import HelmEngine

    engine = HelmEngine()
    workspace = _workspace_with_diagnostic_values()
    first = engine.analyze("Controls feel inconsistent", workspace)

    assert first.status == "needs_follow_up"
    assert first.confidence == "Low"
    assert len(first.follow_up_questions) >= 2
    assert any("near center" in question.prompt for question in first.follow_up_questions)
    assert first.diffs == ()

    refined = engine.analyze(
        "Controls feel inconsistent",
        workspace,
        answers={
            "movement_zone": "near_center",
            "mode_scope": "combat",
            "motion_style": "tracking",
        },
    )

    assert refined.status == "ready"
    assert refined.confidence == "Medium"
    assert refined.confidence_score > first.confidence_score
    assert "Center Precision" in {group.label for group in refined.groups}
    assert refined.diffs


def test_phase10b_workspace_analysis_reports_findings_and_warnings_without_runtime_claims():
    from v3_app.helm.helm_engine import HelmEngine

    workspace = _workspace_with_diagnostic_values()
    result = HelmEngine().analyze("Hard to track smoothly", workspace)

    finding_text = "\n".join(finding.text for finding in result.analysis_findings)
    warning_text = "\n".join(result.warnings)

    assert "deadzone" in finding_text.casefold()
    assert "Roll response is significantly more aggressive than yaw" in finding_text
    assert "Extreme values" in warning_text
    assert "live" not in result.summary.casefold()
    assert "output verified" not in result.summary.casefold()


def test_phase10b_apply_and_revert_grouped_diffs_stays_in_memory_and_preserves_rules():
    from v3_app.helm.diff_model import apply_selected_diffs, revert_applied_diffs
    from v3_app.helm.helm_engine import HelmEngine

    workspace = _workspace_with_diagnostic_values()
    original_rules = workspace.rules
    result = HelmEngine().analyze("Combat aim overshoots", workspace)

    updated, applied = apply_selected_diffs(workspace, result.diffs)

    assert updated.rules == original_rules
    assert updated is not workspace
    assert all(diff.applied for diff in applied if diff.selected)
    assert updated.combat.axes["yaw"].combat_scale != workspace.combat.axes["yaw"].combat_scale
    assert updated.filtering.axes["yaw"].center_alpha != workspace.filtering.axes["yaw"].center_alpha

    reverted = revert_applied_diffs(updated, applied)
    assert reverted.combat.axes["yaw"].combat_scale == workspace.combat.axes["yaw"].combat_scale
    assert reverted.filtering.axes["yaw"].center_alpha == workspace.filtering.axes["yaw"].center_alpha
    assert reverted.rules == original_rules


def test_phase10b_overlay_renders_groups_confidence_and_why_sections(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    _app()
    status = RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
    )
    shell = HelmForgeShell(
        AppState.from_runtime_status(status, driver_detected=True),
        workspace=_workspace_with_diagnostic_values(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )
    shell.open_helm_overlay()
    overlay = shell.helm_overlay

    overlay.findChild(QPushButton, "helmSymptom_Combat_mode_feels_sluggish").click()
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()

    text = "\n".join(label.text() for label in overlay.findChildren(QLabel))
    assert "Combat Responsiveness" in text
    assert "Fine Aim Control" in text
    assert "Confidence: High" in text
    assert "Risk: Medium" in text
    assert "Expected:" in text
    assert overlay.findChild(QPushButton, "helmWhy_Combat_Responsiveness") is not None


def test_phase10b_preserves_phase9k_runtime_boundary_and_rejects_unsafe_commands():
    from shared_core.runtime.bridge_contracts import BridgeCommandType
    from v3_app.services.bridge_commands import BridgeCommandClient

    command_path = PROJECT_ROOT / ".tmp_phase10b_command.json"
    client = BridgeCommandClient(command_path=command_path)
    try:
        for command in (
            BridgeCommandType.START_BRIDGE,
            BridgeCommandType.STOP_BRIDGE,
            BridgeCommandType.RESTART_BRIDGE,
            BridgeCommandType.SUSPEND_BRIDGE,
            BridgeCommandType.VERIFY_OUTPUT,
        ):
            result = client.write_command(command)
            assert result.success is False
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
    ):
        assert token not in helm_sources
