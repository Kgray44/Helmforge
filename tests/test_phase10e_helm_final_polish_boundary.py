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


def _workspace_with_final_helm_values() -> WorkspaceConfig:
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


def _shell(tmp_path, *, workspace: WorkspaceConfig | None = None):
    _app()
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=workspace or _workspace_with_final_helm_values(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )


def _all_label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def test_phase10e_helm_identity_remains_overlay_from_header_with_required_sections_and_chips(tmp_path):
    from PySide6.QtWidgets import QPushButton, QScrollArea
    from v3_app.helm.symptom_library import SYMPTOM_CHIPS

    shell = _shell(tmp_path)
    helm_button = shell.findChild(QPushButton, "helmButton")

    assert helm_button is not None
    assert helm_button.text() == "Helm"
    assert "helm" not in shell.page_widgets

    helm_button.click()
    overlay = shell.helm_overlay
    text = _all_label_text(overlay)
    button_text = {button.text() for button in overlay.findChildren(QPushButton)}

    assert overlay.objectName() == "helmOverlay"
    assert overlay.findChild(QScrollArea, "helmOverlayScrollArea") is not None
    for required in (
        "Helm",
        "Diagnosis-first tuning guidance for the current workspace.",
        "Helm is active",
        "Context-linked assistant",
        "In-memory only",
        "What's wrong?",
        "What I'd change",
        "What I found",
        "Apply / Revert",
    ):
        assert required in text
    for symptom in SYMPTOM_CHIPS:
        assert symptom in button_text


def test_phase10e_empty_and_ambiguous_states_are_polished_before_staging_diffs(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton

    shell = _shell(tmp_path)
    shell.open_helm_overlay()
    overlay = shell.helm_overlay

    overlay.findChild(QPushButton, "helmAnalyzeButton").click()
    no_symptom_text = _all_label_text(overlay)
    assert "Tell me what feels wrong and I'll compare it against the current workspace." in no_symptom_text
    assert "I'll propose draft-only changes before anything is applied." in no_symptom_text
    assert "I do not have safe diffs for that symptom yet." not in no_symptom_text
    assert overlay.findChild(QPushButton, "helmApplySelectedButton").isEnabled() is False

    overlay.symptom_input.setPlainText("Controls feel inconsistent")
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()
    ambiguous_text = _all_label_text(overlay)
    assert "Does the issue happen mostly near center?" in ambiguous_text
    assert "Answer these and I'll narrow the recommendation before staging changes." in ambiguous_text
    assert "Review these before applying." not in ambiguous_text
    assert "Nothing has been applied yet." in overlay.findChild(QLabel, "helmApplyStatus").text()


def test_phase10e_context_summary_and_findings_show_final_evidence_boundaries(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton

    shell = _shell(tmp_path)
    shell.open_helm_overlay()
    overlay = shell.helm_overlay
    overlay.symptom_input.setPlainText("Combat mode feels sluggish")
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()

    context_summary = overlay.findChild(QLabel, "helmContextSummary").text()
    text = _all_label_text(overlay)

    assert "Roll review using Workspace values, Mode settings, Conditional rules, Runtime diagnostics" in context_summary
    assert "output proof pending" in context_summary
    for group in ("Workspace findings", "Mode findings", "Rule findings", "Runtime boundary", "Recommendation summary"):
        assert group in text
    assert "Workspace-only review; live hardware analysis is not active." in text
    assert "Draft" in text
    assert "Full Live Runtime Ready true" not in text
    assert "Output verified true" not in text


def test_phase10e_group_and_individual_selection_apply_and_revert_stay_in_memory(tmp_path):
    from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton

    workspace_path = tmp_path / "hotas_bridge_config_v3.json"
    shell = _shell(tmp_path)
    original_rules = shell.workspace.rules
    shell.open_helm_overlay()
    overlay = shell.helm_overlay
    overlay.symptom_input.setPlainText("Combat mode feels sluggish")
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()

    overlay.findChild(QCheckBox, "helmGroupCheck_Fine_Aim_Control").setChecked(False)
    overlay.findChild(QCheckBox, "helmDiffCheck_Yaw_Combat_Scale").setChecked(False)
    assert "3 changes are selected across Yaw, Pitch." in overlay.findChild(QLabel, "helmReviewSummary").text()

    overlay.findChild(QPushButton, "helmApplySelectedButton").click()

    assert shell.workspace.combat.axes["yaw"].combat_center_alpha == 0.68
    assert shell.workspace.combat.axes["yaw"].combat_reverse_slew == 0.09
    assert shell.workspace.combat.axes["yaw"].combat_same_slew == 0.09
    assert shell.workspace.combat.axes["yaw"].combat_scale == 0.68
    assert shell.workspace.combat.axes["pitch"].combat_center_alpha == 0.56
    assert shell.workspace.rules == original_rules
    assert shell.state.saved is False
    assert not workspace_path.exists()
    assert "Applied 3 changes in memory." in _all_label_text(overlay)
    assert "Save Workspace is still required to keep them." in _all_label_text(overlay)

    overlay.findChild(QPushButton, "helmRevertLastButton").click()

    assert shell.workspace.combat.axes["yaw"].combat_center_alpha == 0.52
    assert shell.workspace.combat.axes["yaw"].combat_reverse_slew == 0.06
    assert shell.workspace.combat.axes["yaw"].combat_same_slew == 0.06
    assert shell.workspace.combat.axes["yaw"].combat_scale == 0.68
    assert shell.workspace.rules == original_rules
    assert not workspace_path.exists()
    assert "Reverted the last Helm batch. The workspace is back to the prior draft values." in _all_label_text(overlay)


def test_phase10e_apply_inactive_no_prior_revert_and_no_raw_object_dumps(tmp_path):
    from PySide6.QtWidgets import QCheckBox, QPushButton

    shell = _shell(tmp_path)
    shell.open_helm_overlay()
    overlay = shell.helm_overlay
    overlay.findChild(QPushButton, "helmRevertLastButton").click()
    assert "There isn't a Helm batch to revert yet." in _all_label_text(overlay)

    overlay.symptom_input.setPlainText("Combat mode feels sluggish")
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()
    for check in overlay.findChildren(QCheckBox):
        if check.objectName().startswith("helmGroupCheck_"):
            check.setChecked(False)

    assert overlay.findChild(QPushButton, "helmApplySelectedButton").isEnabled() is False
    assert "0 changes are selected across Yaw, Pitch." in _all_label_text(overlay)
    text = _all_label_text(overlay)
    for raw_dump in ("HelmRecommendationResult(", "HelmDiff(", "HelmFinding(", "MatchedSymptom("):
        assert raw_dump not in text


def test_phase10e_final_runtime_boundaries_and_forbidden_controls_remain_frozen(tmp_path):
    from PySide6.QtWidgets import QPushButton
    from shared_core.runtime.bridge_contracts import BridgeCommandType
    from v3_app.services.bridge_commands import BridgeCommandClient

    shell = _shell(tmp_path)
    shell.open_helm_overlay()
    overlay = shell.helm_overlay

    button_text = " ".join(button.text() for button in overlay.findChildren(QPushButton))
    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Verify Output",
        "Install Service",
        "Enable Auto Start",
        "Help / Docs",
        "Live Overlay",
        "Flight Recorder",
    ):
        assert forbidden not in button_text

    command_path = PROJECT_ROOT / ".tmp_phase10e_command.json"
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
        "auto_save",
    ):
        assert token not in helm_sources


def test_phase10e_documentation_records_final_phase10_boundary_freeze():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "phase-10e-helm-final-polish-boundary-freeze-report.md"
    assert report.exists()

    docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "docs" / "HelmForge" / "bridge-ui-architecture.md",
            report,
        )
    )
    for phrase in (
        "Phase 10E finalizes Helm for Phase 10",
        "Helm remains overlay/modal from the ASSISTANT cluster",
        "deterministic/local",
        "Apply Selected Changes modifies only the in-memory workspace draft",
        "Save Workspace remains the only persistence action",
        "Helm does not mutate conditional rules",
        "Helm does not use cloud AI or LLM behavior",
        "Phase 11: Help / Docs and Perf / Diagnostics",
    ):
        assert phrase in docs
