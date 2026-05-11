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


def _status():
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
        messages=("Simulation mode selected because live output is not verified.",),
    )


def _shell(tmp_path, *, workspace=None):
    _app()
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=workspace or _workspace_with_diagnostic_values(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )


def _overlay_after_analysis(tmp_path, symptom: str = "Combat mode feels sluggish"):
    from PySide6.QtWidgets import QPushButton

    shell = _shell(tmp_path)
    shell.open_helm_overlay()
    overlay = shell.helm_overlay
    chip_name = f"helmSymptom_{symptom.replace("'", "").replace('/', '_').replace(' ', '_')}"
    chip = overlay.findChild(QPushButton, chip_name)
    if chip is not None:
        chip.click()
    else:
        overlay.symptom_input.setPlainText(symptom)
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()
    return shell, overlay


def _all_label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_phase10c_analysis_shows_guided_review_summary_counts_risk_and_outcome(tmp_path):
    from PySide6.QtWidgets import QLabel

    _shell, overlay = _overlay_after_analysis(tmp_path)
    summary = overlay.findChild(QLabel, "helmReviewSummary")

    assert summary is not None
    assert "5 changes are selected across Yaw, Pitch." in summary.text()
    assert "Expected result:" in summary.text()
    assert "Risk is moderate." in summary.text()
    assert "staged in memory" in summary.text()


def test_phase10c_group_selection_updates_diff_selection_and_selected_counts(tmp_path):
    from PySide6.QtWidgets import QCheckBox, QLabel

    _shell, overlay = _overlay_after_analysis(tmp_path)
    group_check = overlay.findChild(QCheckBox, "helmGroupCheck_Combat_Responsiveness")
    yaw_scale_check = overlay.findChild(QCheckBox, "helmDiffCheck_Yaw_Combat_Scale")
    yaw_center_check = overlay.findChild(QCheckBox, "helmDiffCheck_Yaw_Combat_Center_Alpha")
    pitch_center_check = overlay.findChild(QCheckBox, "helmDiffCheck_Pitch_Combat_Center_Alpha")
    summary = overlay.findChild(QLabel, "helmReviewSummary")

    assert group_check.isChecked()
    assert yaw_scale_check.isChecked()
    assert yaw_center_check.isChecked()

    group_check.setChecked(False)
    assert not yaw_scale_check.isChecked()
    assert not yaw_center_check.isChecked()
    assert pitch_center_check.isChecked()
    assert "1 change is selected across Yaw, Pitch." in summary.text()

    group_check.setChecked(True)
    assert yaw_scale_check.isChecked()
    assert yaw_center_check.isChecked()
    assert "5 changes are selected across Yaw, Pitch." in summary.text()


def test_phase10c_apply_button_is_inactive_when_no_diffs_are_selected(tmp_path):
    from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton

    _shell, overlay = _overlay_after_analysis(tmp_path)
    for group_check in overlay.findChildren(QCheckBox):
        if group_check.objectName().startswith("helmGroupCheck_"):
            group_check.setChecked(False)

    apply_button = overlay.findChild(QPushButton, "helmApplySelectedButton")
    status = overlay.findChild(QLabel, "helmApplyStatus")
    summary = overlay.findChild(QLabel, "helmReviewSummary")

    assert not apply_button.isEnabled()
    assert "0 changes are selected across Yaw, Pitch." in summary.text()
    apply_button.click()
    assert "Select at least one change before applying." in status.text()


def test_phase10c_apply_selected_changes_only_in_memory_then_revert_exact_batch(tmp_path):
    from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton

    workspace_path = tmp_path / "hotas_bridge_config_v3.json"
    shell = _shell(tmp_path)
    shell.workspace_path = workspace_path
    original_rules = shell.workspace.rules
    shell.open_helm_overlay()
    overlay = shell.helm_overlay
    overlay.symptom_input.setPlainText("Combat mode feels sluggish")
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()

    overlay.findChild(QCheckBox, "helmGroupCheck_Fine_Aim_Control").setChecked(False)
    overlay.findChild(QPushButton, "helmApplySelectedButton").click()

    assert shell.workspace.combat.axes["yaw"].combat_center_alpha == 0.68
    assert shell.workspace.combat.axes["yaw"].combat_reverse_slew == 0.09
    assert shell.workspace.combat.axes["yaw"].combat_same_slew == 0.09
    assert shell.workspace.combat.axes["yaw"].combat_scale == 0.79
    assert shell.workspace.combat.axes["pitch"].combat_center_alpha == 0.56
    assert shell.workspace.rules == original_rules
    assert shell.state.saved is False
    assert not workspace_path.exists()

    text_after_apply = _all_label_text(overlay)
    assert "Applied 4 changes in memory." in text_after_apply
    assert "Save Workspace is still required to keep them." in text_after_apply
    assert "You can revert the last Helm batch." in text_after_apply

    overlay.findChild(QPushButton, "helmRevertLastButton").click()

    assert shell.workspace.combat.axes["yaw"].combat_center_alpha == 0.52
    assert shell.workspace.combat.axes["yaw"].combat_reverse_slew == 0.06
    assert shell.workspace.combat.axes["yaw"].combat_same_slew == 0.06
    assert shell.workspace.combat.axes["yaw"].combat_scale == 0.68
    assert shell.workspace.combat.axes["pitch"].combat_center_alpha == 0.56
    assert shell.workspace.rules == original_rules
    assert not workspace_path.exists()
    assert "Reverted the last Helm batch. The workspace is back to the prior draft values." in _all_label_text(overlay)


def test_phase10c_revert_without_prior_batch_is_safe(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton

    shell = _shell(tmp_path)
    shell.open_helm_overlay()
    overlay = shell.helm_overlay
    overlay.findChild(QPushButton, "helmRevertLastButton").click()

    assert "There isn't a Helm batch to revert yet." in overlay.findChild(QLabel, "helmApplyStatus").text()
    assert not (tmp_path / "hotas_bridge_config_v3.json").exists()


def test_phase10c_follow_up_questions_render_answer_choices_before_confident_diffs(tmp_path):
    from PySide6.QtWidgets import QPushButton

    shell = _shell(tmp_path)
    shell.open_helm_overlay()
    overlay = shell.helm_overlay
    overlay.symptom_input.setPlainText("Controls feel inconsistent")
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()

    text = _all_label_text(overlay)
    assert "Does the issue happen mostly near center?" in text
    assert "Does the issue occur in all modes or only combat?" in text
    assert "Review these before applying." not in text
    assert overlay.findChild(QPushButton, "helmFollowUp_movement_zone_near_center") is not None
    assert overlay.findChild(QPushButton, "helmFollowUp_mode_scope_combat") is not None

    overlay.findChild(QPushButton, "helmFollowUp_movement_zone_near_center").click()
    overlay.findChild(QPushButton, "helmFollowUp_mode_scope_combat").click()
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()

    refined_text = _all_label_text(overlay)
    assert "I found" in refined_text
    assert "changes are selected across" in refined_text
    assert "Review these before applying." in refined_text


def test_phase10c_findings_are_workspace_focused_without_fake_live_claims(tmp_path):
    _shell, overlay = _overlay_after_analysis(tmp_path, "Hard to track smoothly")

    text = _all_label_text(overlay)
    assert "Workspace-only review; live hardware analysis is not active." in text
    assert "Yaw deadzone is 0.08" in text
    assert "Roll Curve Strength" in text
    assert "Full Live Runtime Ready" not in text
    assert "output verified true" not in text.casefold()


def test_phase10c_overlay_identity_and_runtime_boundaries_remain_frozen(tmp_path):
    from PySide6.QtWidgets import QPushButton
    from shared_core.runtime.bridge_contracts import BridgeCommandType
    from v3_app.services.bridge_commands import BridgeCommandClient

    shell = _shell(tmp_path)
    shell.open_helm_overlay()
    overlay = shell.helm_overlay

    assert overlay.objectName() == "helmOverlay"
    assert overlay.property("paneMode") == "in-app-slide"
    assert overlay.parentWidget() is shell
    assert "helm" not in shell.page_widgets

    button_text = " ".join(button.text() for button in overlay.findChildren(QPushButton))
    for forbidden in ("StartBridge", "StopBridge", "RestartBridge", "Verify Output", "Install Service"):
        assert forbidden not in button_text

    command_path = PROJECT_ROOT / ".tmp_phase10c_command.json"
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
