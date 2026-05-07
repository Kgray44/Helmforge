from __future__ import annotations

import os
from pathlib import Path


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


def _shell(tmp_path):
    _app()
    from shared_core.models.workspace import create_default_workspace
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell(
        AppState.from_runtime_status(_status(), driver_detected=True),
        workspace=create_default_workspace(),
        workspace_path=tmp_path / "hotas_bridge_config_v3.json",
    )
    shell.switch_page("live_monitor")
    return shell


def _label_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def _buttons(widget):
    from PySide6.QtWidgets import QPushButton

    return {button.text(): button for button in widget.findChildren(QPushButton)}


def test_phase12c_live_overlay_card_truth_labels_and_close_updates_status(tmp_path):
    app = _app()
    shell = _shell(tmp_path)
    page = shell.page_widgets["live_monitor"].widget()
    text = _label_text(page)

    assert "Live Overlay" in text
    assert "Launch the detached telemetry strip, choose a preset, and adjust advanced behavior only when needed." in text
    assert "Preset\nCustom" in text
    assert "Status\nInactive" in text
    assert "Attached display\nCurrent display" in text
    assert "Toggle\nCtrl+Shift+F9" in text
    assert "Hotkey status\nNot registered" in text
    assert "Click-through\nNot enabled - not verified" in text
    assert "Summary\nCustom | Bottom strip | 66% opacity | Final output" in text
    assert "Output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text

    for unsupported in (
        "hotkey armed",
        "click-through active",
        "attached to game",
        "live hardware overlay",
        "output verified\ntrue",
        "Full Live Runtime Ready\ntrue",
    ):
        assert unsupported not in text.lower()

    _buttons(page)["Show Overlay"].click()
    app.processEvents()
    assert page.live_overlay_window is not None
    assert page.live_overlay_window.is_overlay_active() is True
    assert "Status\nActive" in _label_text(page)

    page.live_overlay_window.close()
    app.processEvents()
    assert page.live_overlay_window.is_overlay_active() is False
    assert "Status\nInactive" in _label_text(page)
    assert "Show Overlay" in _buttons(page)


def test_phase12c_configuration_dialog_copy_and_draft_rules_are_finalized(tmp_path):
    from PySide6.QtWidgets import QDialogButtonBox, QDoubleSpinBox

    shell = _shell(tmp_path)
    page = shell.page_widgets["live_monitor"].widget()
    dialog = page.create_live_overlay_config_dialog()
    text = _label_text(dialog)

    assert dialog.windowTitle() == "Live Overlay Configuration - HOTAS Control Panel V3"
    assert (
        "Fine-tune placement, appearance, and data behavior for the detached live telemetry overlay. "
        "Axis colors are shared with Flight Recorder so replays and live telemetry stay consistent."
    ) in text
    for section in ("Placement", "Appearance", "Behavior", "Data", "Axes"):
        assert section in text
    for expected in (
        "Bottom strip",
        "18 px",
        "Attach to display",
        "Standard",
        "0.60",
        "0.66",
        "0.82",
        "2.80",
        "Show legend",
        "Show live values",
        "60 fps",
        "Ctrl+Shift+F9",
        "Hotkey status\nNot registered",
        "Click-through support\nNot verified",
        "Final output",
        "7.50 s",
    ):
        assert expected in text
    assert "Phase 12A" not in text
    assert "hotkey armed" not in text.lower()
    assert "click-through active" not in text.lower()

    dialog.findChild(QDoubleSpinBox, "overlayOpacityField").setValue(0.4)
    dialog.restore_defaults()
    assert dialog.findChild(QDoubleSpinBox, "overlayOpacityField").value() == 0.66
    dialog.reject()
    assert page.overlay_config.opacity == 0.66

    dialog = page.create_live_overlay_config_dialog()
    dialog.findChild(QDoubleSpinBox, "overlayOpacityField").setValue(0.4)
    dialog.accept()
    assert page.overlay_config.opacity == 0.4
    assert dialog.findChild(QDialogButtonBox, "overlayDialogButtons") is not None


def test_phase12c_renderer_handles_edge_states_without_debug_or_placeholder_text():
    _app()
    from v3_app.overlay.overlay_config import LiveOverlayConfig
    from v3_app.overlay.overlay_renderer import OverlayRenderer
    from v3_app.overlay.telemetry_buffer import OverlayTelemetrySample
    from v3_app.overlay.trace_builder import build_overlay_traces

    config = LiveOverlayConfig.defaults()
    renderer = OverlayRenderer(config=config)
    renderer.set_runtime_truth(
        runtime_truth="blocked_missing_device",
        output_verified=False,
        full_live_runtime_ready=False,
        source="Final output",
    )
    renderer.set_trace_set(build_overlay_traces(config, ()))
    assert "Waiting for overlay telemetry samples." in renderer.status_text()

    one_axis = LiveOverlayConfig.from_dict(
        {
            **config.to_dict(),
            "show_legend": False,
            "show_live_values": False,
            "axes": {
                axis: {"include": axis == "Yaw", "color": axis_config.color}
                for axis, axis_config in config.axes.items()
            },
        }
    )
    samples = (
        OverlayTelemetrySample(
            timestamp=1.0,
            axes={"Roll": -5.0, "Pitch": 5.0, "Throttle": 0.0, "Yaw": -1.4, "Aux 1": 0.0, "Aux 2": 0.0},
            source="Final output",
        ),
        OverlayTelemetrySample(
            timestamp=2.0,
            axes={"Roll": -5.0, "Pitch": 5.0, "Throttle": 0.0, "Yaw": 1.4, "Aux 1": 0.0, "Aux 2": 0.0},
            source="Final output",
        ),
    )
    renderer.set_config(one_axis)
    renderer.set_trace_set(build_overlay_traces(one_axis, samples))
    assert renderer.included_axes() == ("Yaw",)
    assert renderer.axis_colors()["Yaw"] == "#CF95FF"
    assert "Rendering 1 overlay axes." in renderer.status_text()
    assert "Waiting for overlay telemetry samples." not in renderer.status_text()
    assert "OverlayTrace" not in renderer.status_text()
    assert "dataclass" not in renderer.status_text()


def test_phase12c_overlay_timer_stops_on_hide_and_close():
    app = _app()
    from v3_app.overlay.live_overlay_window import LiveOverlayWindow
    from v3_app.overlay.overlay_config import LiveOverlayConfig

    window = LiveOverlayWindow(
        config=LiveOverlayConfig.defaults(),
        runtime_truth="blocked_missing_device",
        output_verified=False,
        full_live_runtime_ready=False,
    )
    assert window.hotkey_status_text() == "Not registered"
    assert window.click_through_status_text() == "Not enabled - not verified"
    assert window.always_on_top_status_text() in {"Enabled", "Disabled", "Unavailable"}

    window.show_overlay()
    app.processEvents()
    assert window.refresh_timer.isActive() is True
    window.hide_overlay()
    app.processEvents()
    assert window.refresh_timer.isActive() is False

    window.show_overlay()
    app.processEvents()
    assert window.refresh_timer.isActive() is True
    window.close()
    app.processEvents()
    assert window.refresh_timer.isActive() is False


def test_phase12c_docs_and_static_boundaries_freeze_phase12_scope(tmp_path):
    shell = _shell(tmp_path)
    page = shell.page_widgets["live_monitor"].widget()
    button_text = " ".join(_buttons(page))
    for forbidden in (
        "StartBridge",
        "StopBridge",
        "RestartBridge",
        "Install Service",
        "Enable Auto Start",
        "VerifyOutput",
        "Verify Output",
        "Ctrl+Shift+F10",
    ):
        assert forbidden not in button_text

    recorder_page = PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py"
    if recorder_page.exists():
        recorder_text = recorder_page.read_text(encoding="utf-8")
        assert "Capture backend missing" in recorder_text
        assert "Recording backend is not active in this phase" in recorder_text
    assert not (PROJECT_ROOT / "v3_app" / "flight_recorder").exists()

    docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "docs" / "HelmForge" / "bridge-ui-architecture.md",
        )
    )
    help_docs = (PROJECT_ROOT / "v3_app" / "services" / "help_docs.py").read_text(encoding="utf-8")
    assert "does not inject into games" in docs
    assert "graphics API hooking" in docs
    assert "app-owned detached overlay" in help_docs
    assert "does not inject into games" in help_docs
    assert "does not use graphics API hooking" in help_docs

    phase12_sources = [
        PROJECT_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
    ]
    overlay_root = PROJECT_ROOT / "v3_app" / "overlay"
    if overlay_root.exists():
        phase12_sources.extend(overlay_root.rglob("*.py"))
    sources = "\n".join(path.read_text(encoding="utf-8") for path in phase12_sources)
    for token in (
        "UpdateVJD",
        "SetAxis",
        "SetBtn",
        "AcquireVJD",
        "subprocess.Popen",
        "QProcess",
        "startDetached",
        "Start-Process",
        "RegisterHotKey",
        "SetWindowLong",
        "Ctrl+Shift+F10",
        "DirectX",
        "Vulkan",
        "OpenGL hook",
        "pystray",
        "openai",
        "anthropic",
        "auto_save",
    ):
        assert token not in sources
