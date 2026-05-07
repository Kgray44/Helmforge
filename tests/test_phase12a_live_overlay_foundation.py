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


def test_phase12a_axis_colors_and_config_defaults_are_stable():
    from v3_app.overlay.axis_colors import DEFAULT_AXIS_COLORS, color_for_axis
    from v3_app.overlay.overlay_config import LiveOverlayConfig

    assert DEFAULT_AXIS_COLORS == {
        "Roll": "#58B8FF",
        "Pitch": "#6FDB9F",
        "Throttle": "#F0C46A",
        "Yaw": "#CF95FF",
        "Aux 1": "#FF9B6B",
        "Aux 2": "#6ED9D0",
    }
    assert color_for_axis("Yaw") == "#CF95FF"

    config = LiveOverlayConfig.defaults()
    assert config.preset == "Custom"
    assert config.visible is False
    assert config.source == "Final output"
    assert config.history_seconds == 7.5
    assert config.position == "Bottom strip"
    assert config.margin_px == 18
    assert config.attach_mode == "Attach to display"
    assert config.width == "Standard"
    assert config.height == 0.6
    assert config.display_label == "Current display"
    assert config.opacity == 0.66
    assert config.background == 0.82
    assert config.line_thickness == 2.8
    assert config.show_legend is True
    assert config.show_live_values is True
    assert config.auto_hide_when_target_loses_focus is False
    assert config.always_on_top is True
    assert config.click_through is False
    assert config.click_through_supported == "unknown"
    assert config.fps_cap == 60
    assert config.toggle_hotkey == "Ctrl+Shift+F9"
    assert config.hotkey_registered is False
    assert tuple(config.axes) == ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
    assert all(axis.include for axis in config.axes.values())
    assert {axis: value.color for axis, value in config.axes.items()} == DEFAULT_AXIS_COLORS


def test_phase12a_overlay_config_roundtrip_restore_and_validation_clamps():
    from v3_app.overlay.overlay_config import LiveOverlayConfig

    config = LiveOverlayConfig.defaults()
    payload = config.to_dict()
    roundtrip = LiveOverlayConfig.from_dict(payload)
    assert roundtrip == config
    assert LiveOverlayConfig.from_json(config.to_json()) == config

    dirty = LiveOverlayConfig.from_dict(
        {
            **payload,
            "opacity": 4,
            "background": -1,
            "line_thickness": 99,
            "fps_cap": 1000,
            "height": -5,
            "margin_px": -30,
            "history_seconds": 999,
        }
    )
    assert dirty.opacity == 1.0
    assert dirty.background == 0.0
    assert dirty.line_thickness == 8.0
    assert dirty.fps_cap == 144
    assert dirty.height == 0.2
    assert dirty.margin_px == 0
    assert dirty.history_seconds == 60.0
    assert dirty.restore_defaults() == LiveOverlayConfig.defaults()


def test_phase12a_telemetry_buffer_trims_by_history_and_trace_builder_is_pure():
    from v3_app.overlay.overlay_config import LiveOverlayConfig
    from v3_app.overlay.telemetry_buffer import OverlayTelemetryBuffer, OverlayTelemetrySample
    from v3_app.overlay.trace_builder import build_overlay_traces

    config = LiveOverlayConfig.defaults()
    buffer = OverlayTelemetryBuffer(history_seconds=2.0)
    for second in (0.0, 1.0, 3.0):
        buffer.append(
            OverlayTelemetrySample(
                timestamp=second,
                axes={
                    "Roll": second - 1.5,
                    "Pitch": 0.25,
                    "Throttle": 2.0,
                    "Yaw": -2.0,
                    "Aux 1": 0.0,
                    "Aux 2": 0.5,
                },
                source="Final output",
            )
        )

    samples = buffer.samples()
    assert [sample.timestamp for sample in samples] == [1.0, 3.0]

    traces = build_overlay_traces(config, samples)
    assert [trace.axis for trace in traces.series] == ["Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2"]
    assert traces.series[0].color == "#58B8FF"
    assert traces.source == "Final output"
    assert traces.series[0].points == ((-2.0, -0.5), (0.0, 1.0))
    assert traces.series[2].points[-1] == (0.0, 1.0)
    assert traces.series[3].points[-1] == (0.0, -1.0)

    filtered = LiveOverlayConfig.from_dict(
        {
            **config.to_dict(),
            "axes": {
                axis: {"include": axis == "Roll", "color": axis_config.color}
                for axis, axis_config in config.axes.items()
            },
        }
    )
    assert [trace.axis for trace in build_overlay_traces(filtered, samples).series] == ["Roll"]


def test_phase12a_live_monitor_has_live_overlay_card_without_fake_active_claims(tmp_path):
    from PySide6.QtWidgets import QPushButton

    shell = _shell(tmp_path)
    page = shell.page_widgets["live_monitor"].widget()
    text = _label_text(page)
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}

    assert "Live Overlay" in text
    assert "Launch the detached telemetry strip, choose a preset, and adjust advanced behavior only when needed." in text
    assert "Preset\nCustom" in text
    assert "Status\nInactive" in text
    assert "Attached display\nCurrent display" in text
    assert "Toggle\nCtrl+Shift+F9" in text
    assert "Summary\nCustom | Bottom strip | 66% opacity | Final output" in text
    assert "Runtime truth\nblocked_missing_device" in text
    assert "Output verified\nfalse" in text
    assert "Full Live Runtime Ready\nfalse" in text
    assert buttons["Show Overlay"].isEnabled() in {False, True}
    assert "Configure" in buttons
    assert "overlay active" not in text.lower()
    assert "hotkey armed" not in text.lower()
    assert "click-through active" not in text.lower()


def test_phase12a_live_overlay_configuration_dialog_contains_required_fields_and_applies_only_on_ok(tmp_path):
    from PySide6.QtWidgets import QCheckBox, QDialogButtonBox, QDoubleSpinBox, QLabel, QSpinBox

    shell = _shell(tmp_path)
    page = shell.page_widgets["live_monitor"].widget()

    dialog = page.create_live_overlay_config_dialog()
    text = _label_text(dialog)
    assert dialog.windowTitle() == "Live Overlay Configuration - HOTAS Control Panel V3"
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
        "Ctrl+Shift+F9",
        "Hotkey status\nNot registered",
        "Click-through support\nNot verified",
        "Final output",
        "7.50 s",
    ):
        assert expected in text
    for axis in ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2"):
        assert axis in text
        assert dialog.findChild(QCheckBox, f"overlayAxisInclude_{axis.replace(' ', '_')}") is not None
        assert dialog.findChild(QLabel, f"overlayAxisColor_{axis.replace(' ', '_')}") is not None

    opacity = dialog.findChild(QDoubleSpinBox, "overlayOpacityField")
    opacity.setValue(0.4)
    dialog.reject()
    assert page.overlay_config.opacity == 0.66

    dialog = page.create_live_overlay_config_dialog()
    dialog.findChild(QDoubleSpinBox, "overlayOpacityField").setValue(0.4)
    dialog.findChild(QSpinBox, "overlayFpsCapField").setValue(48)
    dialog.accept()
    assert page.overlay_config.opacity == 0.4
    assert page.overlay_config.fps_cap == 48
    assert "40% opacity" in _label_text(page)

    dialog = page.create_live_overlay_config_dialog()
    dialog.findChild(QDoubleSpinBox, "overlayOpacityField").setValue(0.33)
    dialog.restore_defaults()
    assert dialog.findChild(QDoubleSpinBox, "overlayOpacityField").value() == 0.66
    assert dialog.findChild(QDialogButtonBox, "overlayDialogButtons") is not None


def test_phase12a_no_forbidden_runtime_or_phase13_authority_was_introduced(tmp_path):
    from PySide6.QtWidgets import QPushButton

    shell = _shell(tmp_path)
    page = shell.page_widgets["live_monitor"].widget()
    button_text = " ".join(button.text() for button in page.findChildren(QPushButton))
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
