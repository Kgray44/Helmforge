from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from shared_core.models.combat import AxisCombatProfile
from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.bridge_contracts import BridgeCommandType


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _status() -> RuntimePreflightStatus:
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


def _workspace_with_recovered_combat_values() -> WorkspaceConfig:
    workspace = create_default_workspace()
    axes = dict(workspace.combat.axes)
    axes["yaw"] = replace(
        axes["yaw"],
        combat_center_alpha=0.52,
        combat_reverse_slew=0.06,
        combat_same_slew=0.06,
        combat_scale=0.68,
    )
    axes["pitch"] = replace(axes["pitch"], combat_center_alpha=0.56)
    return replace(workspace, combat=replace(workspace.combat, axes=axes))


def _shell(*, workspace=None, workspace_path=None):
    _app()
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=workspace or _workspace_with_recovered_combat_values(),
        workspace_path=workspace_path,
    )


def test_phase10a_helm_button_exists_opens_and_closes_overlay_from_header(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton

    shell = _shell(workspace_path=tmp_path / "hotas_bridge_config_v3.json")
    helm_button = shell.findChild(QPushButton, "helmButton")

    assert helm_button is not None
    assert helm_button.text() == "Helm"
    assert "helm" not in shell.page_widgets

    helm_button.click()
    overlay = shell.helm_overlay

    assert overlay is not None
    assert overlay.isVisible()
    assert overlay.objectName() == "helmOverlay"
    assert overlay.windowModality().name.endswith("ApplicationModal")
    assert overlay.width() >= int(shell.width() * 0.60)
    assert shell.active_page_id != "helm"

    text = " ".join(label.text() for label in overlay.findChildren(QLabel))
    assert "Helm" in text
    assert "Diagnosis-first tuning guidance for the current workspace." in text
    assert "Helm is active" in text
    assert "Context-linked assistant" in text
    assert "In-memory only" in text

    overlay.findChild(QPushButton, "helmCloseButton").click()
    assert not overlay.isVisible()


def test_phase10a_overlay_contains_required_cards_chips_and_actions(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton, QPlainTextEdit

    shell = _shell(workspace_path=tmp_path / "hotas_bridge_config_v3.json")
    shell.open_helm_overlay()
    overlay = shell.helm_overlay

    labels = " ".join(label.text() for label in overlay.findChildren(QLabel))
    buttons = {button.text(): button for button in overlay.findChildren(QPushButton)}
    input_box = overlay.findChild(QPlainTextEdit, "helmSymptomInput")

    for expected in ("What's wrong?", "What I'd change", "What I found", "Apply / Revert"):
        assert expected in labels
    assert input_box is not None
    assert input_box.placeholderText() == "Example: Can't hold aim steady on target."

    for chip in (
        "Can't hold aim steady",
        "Too twitchy near center",
        "Overshoots target",
        "Combat mode feels sluggish",
        "Reversals feel sticky",
        "Hard to track smoothly",
    ):
        assert chip in buttons

    for action in ("Analyze", "Review Changes", "Cancel", "Apply Selected Changes", "Revert Last Helm Changes"):
        assert action in buttons

    buttons["Combat mode feels sluggish"].click()
    assert input_box.toPlainText() == "Combat mode feels sluggish"


def test_phase10a_combat_sluggish_engine_produces_exact_recovered_style_diffs():
    from v3_app.helm.helm_engine import HelmEngine

    workspace = _workspace_with_recovered_combat_values()
    result = HelmEngine().analyze("Combat mode feels sluggish", workspace)

    assert result.status == "ready"
    assert result.confidence == "High"
    assert "I'd soften yaw recovery" in result.summary
    assert len(result.diffs) == 5
    assert [(diff.axis, diff.parameter, diff.before, diff.after) for diff in result.diffs] == [
        ("Yaw", "Combat Center Alpha", 0.52, 0.68),
        ("Pitch", "Combat Center Alpha", 0.56, 0.68),
        ("Yaw", "Combat Reverse Slew", 0.06, 0.09),
        ("Yaw", "Combat Same Slew", 0.06, 0.09),
        ("Yaw", "Combat Scale", 0.68, 0.79),
    ]
    assert all(diff.selected and not diff.applied for diff in result.diffs)
    assert all(diff.section == "Combat Profile" for diff in result.diffs)


def test_phase10a_overlay_analyze_apply_and_revert_are_in_memory_only(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton

    workspace_path = tmp_path / "hotas_bridge_config_v3.json"
    shell = _shell(workspace_path=workspace_path)
    original_rules = shell.workspace.rules

    shell.open_helm_overlay()
    overlay = shell.helm_overlay
    overlay.findChild(QPushButton, "helmSymptom_Combat_mode_feels_sluggish").click()
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()

    text_after_analyze = " ".join(label.text() for label in overlay.findChildren(QLabel))
    assert "Yaw Combat Center Alpha" in text_after_analyze
    assert "0.52 -> 0.68" in text_after_analyze
    assert "I found the combat layer" in text_after_analyze
    assert "5 changes ready" in text_after_analyze
    assert shell.workspace.combat.axes["yaw"].combat_center_alpha == 0.52
    assert shell.state.saved is True
    assert not workspace_path.exists()

    overlay.findChild(QPushButton, "helmApplySelectedButton").click()

    assert shell.workspace.combat.axes["yaw"].combat_center_alpha == 0.68
    assert shell.workspace.combat.axes["pitch"].combat_center_alpha == 0.68
    assert shell.workspace.combat.axes["yaw"].combat_reverse_slew == 0.09
    assert shell.workspace.combat.axes["yaw"].combat_same_slew == 0.09
    assert shell.workspace.combat.axes["yaw"].combat_scale == 0.79
    assert shell.workspace.rules == original_rules
    assert shell.state.saved is False
    assert "Helm staged 5 in-memory changes" in shell.state.status_message
    assert not workspace_path.exists()

    overlay.findChild(QPushButton, "helmRevertLastButton").click()

    assert shell.workspace.combat.axes["yaw"].combat_center_alpha == 0.52
    assert shell.workspace.combat.axes["pitch"].combat_center_alpha == 0.56
    assert shell.workspace.combat.axes["yaw"].combat_reverse_slew == 0.06
    assert shell.workspace.combat.axes["yaw"].combat_same_slew == 0.06
    assert shell.workspace.combat.axes["yaw"].combat_scale == 0.68
    assert shell.workspace.rules == original_rules
    assert not workspace_path.exists()


def test_phase10a_cancel_clears_draft_without_navigation_change(tmp_path):
    from PySide6.QtWidgets import QLabel, QPushButton, QPlainTextEdit

    shell = _shell(workspace_path=tmp_path / "hotas_bridge_config_v3.json")
    start_page = shell.active_page_id
    shell.open_helm_overlay()
    overlay = shell.helm_overlay
    overlay.findChild(QPushButton, "helmSymptom_Combat_mode_feels_sluggish").click()
    overlay.findChild(QPushButton, "helmAnalyzeButton").click()
    overlay.findChild(QPushButton, "helmCancelButton").click()

    assert shell.active_page_id == start_page
    assert overlay.findChild(QPlainTextEdit, "helmSymptomInput").toPlainText() == ""
    labels = " ".join(label.text() for label in overlay.findChildren(QLabel))
    assert "Nothing has been applied yet." in labels


def test_phase10a_boundaries_remain_frozen():
    from v3_app.services.bridge_commands import BridgeCommandClient

    command_path = PROJECT_ROOT / ".tmp_phase10a_command.json"
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

    production_sources = {
        path: path.read_text(encoding="utf-8")
        for root in ("bridge_app", "shared_core", "v3_app")
        for path in (PROJECT_ROOT / root).rglob("*.py")
    }
    combined = "\n".join(production_sources.values())
    bridge_sources = "\n".join(text for path, text in production_sources.items() if "bridge_app" in path.parts)
    helm_sources = "\n".join(
        text
        for path, text in production_sources.items()
        if "v3_app" in path.parts and ("helm" in path.parts or path.name in {"shell.py", "header.py"})
    )

    shared_vjoy_source = (PROJECT_ROOT / "shared_core" / "runtime" / "vjoy_output.py").read_text(encoding="utf-8")
    for token in ("SetAxis", "SetBtn", "AcquireVJD"):
        assert token in shared_vjoy_source
        assert token not in bridge_sources
        assert token not in helm_sources
    assert "UpdateVJD" not in combined
    for token in ("subprocess.Popen", "QProcess", "startDetached", "Start-Process"):
        assert token not in helm_sources
    for token in ("win32serviceutil", "schtasks", "pystray"):
        assert token not in combined
    assert "from v3_app" not in bridge_sources
    assert "import v3_app" not in bridge_sources
    assert "PySide6" not in bridge_sources
