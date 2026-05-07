from __future__ import annotations

import os
from dataclasses import replace
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


def test_phase12b_renderer_handles_empty_and_axis_traces_without_raw_debug():
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

    assert renderer.included_axes() == ()
    assert "Waiting for overlay telemetry samples." in renderer.status_text()
    assert "Runtime truth: blocked_missing_device" in renderer.status_text()
    assert "Output verified: false" in renderer.status_text()
    assert "Full Live Runtime Ready: false" in renderer.status_text()
    assert "OverlayTrace" not in renderer.status_text()
    assert "dataclass" not in renderer.status_text()

    samples = (
        OverlayTelemetrySample(
            timestamp=1.0,
            axes={"Roll": -0.25, "Pitch": 0.5, "Throttle": 1.0, "Yaw": -1.0, "Aux 1": 0.0, "Aux 2": 0.25},
            source="Final output",
        ),
        OverlayTelemetrySample(
            timestamp=2.0,
            axes={"Roll": 0.25, "Pitch": 0.75, "Throttle": 0.5, "Yaw": -0.5, "Aux 1": 0.2, "Aux 2": 0.4},
            source="Final output",
        ),
    )
    renderer.set_trace_set(build_overlay_traces(config, samples))
    assert renderer.included_axes() == ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
    assert renderer.axis_colors()["Roll"] == "#58B8FF"
    assert renderer.axis_colors()["Yaw"] == "#CF95FF"

    filtered = LiveOverlayConfig.from_dict(
        {
            **config.to_dict(),
            "axes": {
                axis: {"include": axis in {"Roll", "Yaw"}, "color": axis_config.color}
                for axis, axis_config in config.axes.items()
            },
        }
    )
    renderer.set_config(filtered)
    renderer.set_trace_set(build_overlay_traces(filtered, samples))
    assert renderer.included_axes() == ("Roll", "Yaw")


def test_phase12b_detached_overlay_window_constructs_and_show_hide_is_truthful():
    app = _app()
    from PySide6.QtCore import Qt
    from v3_app.overlay.live_overlay_window import LiveOverlayWindow
    from v3_app.overlay.overlay_config import LiveOverlayConfig

    config = LiveOverlayConfig.defaults()
    window = LiveOverlayWindow(
        config=config,
        runtime_truth="blocked_missing_device",
        output_verified=False,
        full_live_runtime_ready=False,
    )
    flags = window.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert window.hotkey_status_text() == "Not registered"
    assert window.click_through_status_text() == "Not enabled - not verified"

    window.show_overlay()
    app.processEvents()
    assert window.is_overlay_active() is True
    assert window.refresh_timer.isActive() is True

    window.hide_overlay()
    app.processEvents()
    assert window.is_overlay_active() is False
    assert window.refresh_timer.isActive() is False


def test_phase12b_live_monitor_show_hide_overlay_card_tracks_real_window_visibility(tmp_path):
    app = _app()
    shell = _shell(tmp_path)
    page = shell.page_widgets["live_monitor"].widget()
    buttons = _buttons(page)

    assert buttons["Show Overlay"].isEnabled() is True
    assert "Status\nInactive" in _label_text(page)
    buttons["Show Overlay"].click()
    app.processEvents()

    assert page.live_overlay_window is not None
    assert page.live_overlay_window.is_overlay_active() is True
    assert "Status\nActive" in _label_text(page)
    assert "Hide Overlay" in _buttons(page)
    assert "Hotkey status\nNot registered" in _label_text(page)
    assert "Click-through\nNot enabled - not verified" in _label_text(page)
    assert "hotkey armed" not in _label_text(page).lower()
    assert "click-through active" not in _label_text(page).lower()

    _buttons(page)["Hide Overlay"].click()
    app.processEvents()
    assert page.live_overlay_window.is_overlay_active() is False
    assert "Status\nInactive" in _label_text(page)


def test_phase12b_config_dialog_updates_visible_overlay_only_on_ok(tmp_path):
    from PySide6.QtWidgets import QDialogButtonBox, QDoubleSpinBox, QSpinBox

    app = _app()
    shell = _shell(tmp_path)
    page = shell.page_widgets["live_monitor"].widget()
    page.show_live_overlay()
    app.processEvents()
    assert page.live_overlay_window is not None

    dialog = page.create_live_overlay_config_dialog()
    dialog.findChild(QDoubleSpinBox, "overlayOpacityField").setValue(0.4)
    dialog.reject()
    assert page.overlay_config.opacity == 0.66
    assert page.live_overlay_window.config.opacity == 0.66

    dialog = page.create_live_overlay_config_dialog()
    dialog.findChild(QDoubleSpinBox, "overlayOpacityField").setValue(0.4)
    dialog.findChild(QSpinBox, "overlayFpsCapField").setValue(48)
    dialog.accept()
    assert page.overlay_config.opacity == 0.4
    assert page.overlay_config.fps_cap == 48
    assert page.live_overlay_window.config.opacity == 0.4
    assert page.live_overlay_window.refresh_timer.interval() == 20
    assert "Custom | Bottom strip | 40% opacity | Final output" in _label_text(page)

    dialog = page.create_live_overlay_config_dialog()
    dialog.findChild(QDoubleSpinBox, "overlayOpacityField").setValue(0.33)
    dialog.restore_defaults()
    assert dialog.findChild(QDoubleSpinBox, "overlayOpacityField").value() == 0.66
    assert dialog.findChild(QDialogButtonBox, "overlayDialogButtons") is not None
    dialog.accept()
    assert page.overlay_config == page.overlay_config.restore_defaults()
    assert page.live_overlay_window.config == page.overlay_config.restore_defaults()


def test_phase12b_overlay_window_applies_config_and_preserves_truth_states():
    app = _app()
    from v3_app.overlay.live_overlay_window import LiveOverlayWindow
    from v3_app.overlay.overlay_config import LiveOverlayConfig

    config = LiveOverlayConfig.defaults()
    window = LiveOverlayWindow(
        config=config,
        runtime_truth="blocked_missing_device",
        output_verified=False,
        full_live_runtime_ready=False,
    )
    window.show_overlay()
    app.processEvents()

    updated = replace(config, opacity=0.5, background=0.6, fps_cap=30, show_legend=False, show_live_values=False)
    window.apply_config(updated)
    assert window.config == updated
    assert window.refresh_timer.interval() == 33
    assert window.renderer.config == updated
    assert "Output verified: false" in window.renderer.status_text()
    assert "Full Live Runtime Ready: false" in window.renderer.status_text()
    assert window.always_on_top_status_text() in {"Enabled", "Unavailable"}

    window.hide_overlay()
    app.processEvents()
    assert window.refresh_timer.isActive() is False


def test_phase12b_no_forbidden_runtime_or_phase13_authority_was_introduced(tmp_path):
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
    ):
        assert forbidden not in button_text

    recorder_page = PROJECT_ROOT / "v3_app" / "pages" / "flight_recorder_page.py"
    if recorder_page.exists():
        recorder_text = recorder_page.read_text(encoding="utf-8")
        assert "Capture backend missing" in recorder_text
        assert "Recording backend is not active in this phase" in recorder_text

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
        "DirectX",
        "Vulkan",
        "OpenGL hook",
        "pystray",
        "openai",
        "anthropic",
        "auto_save",
    ):
        assert token not in sources
