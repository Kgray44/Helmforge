from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QPoint, QSize

from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _blocked_runtime_status() -> RuntimePreflightStatus:
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


def _live_verified_runtime_status() -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.FULL_LIVE,
        truth=RuntimeTruth.LIVE_VERIFIED,
        input=InputDeviceDetection(
            status=InputStatus.DETECTED,
            detected_device_names=("Thrustmaster T-Flight HOTAS One",),
        ),
        output=OutputBackendDetection(
            status=OutputStatus.OUTPUT_VERIFIED,
            backend_name="vJoy",
            live_output_writes_verified=True,
        ),
    )


def _state(runtime_status: RuntimePreflightStatus):
    from v3_app.services.app_state import AppState

    state = AppState.from_runtime_status(runtime_status)
    state.active_profile = "LCD-2F Test Workspace"
    state.source_config = "hotas_bridge_config_v3.json"
    state.saved = True
    state.status_message = "LCD-2F layout fit smoke; footer actions remain placeholders."
    return state


def _texts(widget) -> list[str]:
    from PySide6.QtWidgets import QLabel, QPushButton

    return [label.text() for label in widget.findChildren(QLabel)] + [
        button.text() for button in widget.findChildren(QPushButton)
    ]


def _text_blob(widget) -> str:
    return "\n".join(_texts(widget))


def _rect_in_shell(widget, shell):
    top_left = widget.mapTo(shell, QPoint(0, 0))
    return widget.geometry().translated(top_left - widget.geometry().topLeft())


def test_lcd_2f_liquid_window_size_uses_larger_clamped_defaults_without_changing_legacy():
    _app()

    from v3_app.app import LEGACY_UI_SHELL, LIQUID_UI_SHELL, window_sizes_for_shell
    from v3_app.liquid.theme_tokens import LiquidLayout
    from v3_app.theme.tokens import Layout

    legacy_min, legacy_default = window_sizes_for_shell(LEGACY_UI_SHELL, available_size=QSize(1920, 1080))
    liquid_min, liquid_default = window_sizes_for_shell(LIQUID_UI_SHELL, available_size=QSize(1920, 1080))
    small_min, small_default = window_sizes_for_shell(LIQUID_UI_SHELL, available_size=QSize(1280, 760))

    assert legacy_default == QSize(Layout.window_width, Layout.window_height)
    assert legacy_min == QSize(Layout.window_min_width, Layout.window_min_height)

    assert liquid_default == QSize(LiquidLayout.window_width, LiquidLayout.window_height)
    assert liquid_min == QSize(LiquidLayout.window_min_width, LiquidLayout.window_min_height)
    assert liquid_default.width() >= int(Layout.window_width * 1.3)
    assert liquid_default.height() >= int(Layout.window_height * 1.25)

    assert small_default.width() <= 1280
    assert small_default.height() <= 760
    assert small_min.width() <= small_default.width()
    assert small_min.height() <= small_default.height()


def test_lcd_2f_liquid_build_window_applies_liquid_size_contract_and_preserves_launch_path():
    _app()

    from v3_app.app import build_window

    window = build_window(title="HelmForge LCD-2F", state=_state(_blocked_runtime_status()), ui_shell="liquid")

    assert window.ui_shell == "liquid"
    assert window.property("requestedDefaultSize").width() >= 1280
    assert window.property("requestedMinimumSize").height() >= 760
    assert window.findChild(type(window.shell), "liquidCommandShell") is not None


def test_lcd_2f_placeholder_header_uses_separate_title_subtitle_and_chip_regions():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(_blocked_runtime_status()))
    shell.switch_mode("preflight")
    page = shell.page_host.currentWidget()

    for object_name in (
        "liquidPlaceholderHeaderTitleRegion_preflight",
        "liquidPlaceholderHeaderSubtitleRegion_preflight",
        "liquidPlaceholderHeaderChipRegion_preflight",
    ):
        widget = page.findChild(QWidget, object_name)
        assert widget is not None, object_name
        assert widget.property("liquidRole") in {
            "liquid_placeholder_header_title_region",
            "liquid_placeholder_header_subtitle_region",
            "liquid_placeholder_header_chip_region",
        }


def test_lcd_2f_geometry_smoke_has_footer_clearance_and_nonempty_major_regions():
    app = _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell
    from v3_app.liquid.navigation import LIQUID_MODE_IDS

    shell = LiquidCommandShell(state=_state(_blocked_runtime_status()))
    shell.resize(1360, 800)
    shell.show()
    app.processEvents()

    footer = shell.findChild(QWidget, "liquid_floating_footer_strip")
    clearance = shell.findChild(QWidget, "liquid_footer_clearance")
    assert footer is not None
    assert clearance is not None
    assert clearance.property("footerClearance") is True
    assert clearance.height() >= 80

    page_host = shell.findChild(QWidget, "liquid_page_host")
    footer_rect = _rect_in_shell(footer, shell)
    page_host_rect = _rect_in_shell(page_host, shell)
    assert page_host_rect.bottom() <= footer_rect.top() + 4

    for mode_id in LIQUID_MODE_IDS:
        shell.switch_mode(mode_id)
        app.processEvents()
        page = shell.page_host.currentWidget()
        for object_name in (
            f"liquidHeroRegion_{mode_id}",
            f"liquidContextInspectorRegion_{mode_id}",
            f"liquidDetailActionRegion_{mode_id}",
            f"liquidAdvancedRegion_{mode_id}",
        ):
            widget = page.findChild(QWidget, object_name)
            assert widget is not None, object_name
            assert widget.geometry().width() > 0, object_name
            assert widget.geometry().height() > 0, object_name


def test_lcd_2f_live_verified_top_truth_does_not_conflict_with_static_demo_chips():
    _app()

    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(_live_verified_runtime_status()))
    labels = _texts(shell)
    assert "Live Verified" in labels

    shell.switch_mode("preflight")
    page_labels = _texts(shell.page_host.currentWidget())

    contradictory_samples = [
        label
        for label in page_labels
        if any(phrase in label for phrase in ("Runtime blocked", "Output proof missing", "Telemetry stale"))
    ]
    assert contradictory_samples
    for label in contradictory_samples:
        lowered = label.casefold()
        assert any(marker in lowered for marker in ("demo", "example", "static", "placeholder")), label

    page_text = "\n".join(page_labels)
    for forbidden in (
        "Live Output Active",
        "Full Live Runtime Ready",
        "Recording Ready",
        "vJoy writing",
        "Bridge managed",
        "auto-save",
    ):
        assert forbidden.casefold() not in page_text.casefold()


def test_lcd_2f_preserves_floating_shell_no_legacy_stack_or_forbidden_features():
    _app()

    from PySide6.QtWidgets import QWidget
    from v3_app.liquid.app_shell import LiquidCommandShell

    shell = LiquidCommandShell(state=_state(_blocked_runtime_status()))

    for object_name in (
        "liquid_command_surface",
        "liquid_surface_glass_field",
        "liquid_floating_mode_dock",
        "liquid_floating_footer_strip",
        "liquid_page_host",
    ):
        assert shell.findChild(QWidget, object_name) is not None

    assert shell.findChild(QWidget, "appSidebar") is None
    assert shell.findChild(QWidget, "pageStack") is None

    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "v3_app" / "liquid").rglob("*.py")
    )
    for forbidden in (
        "QPropertyAnimation",
        "QGraphicsBlurEffect",
        "QGraphicsOpacityEffect",
        "open_radial",
        "radial_menu",
        "EmbeddedBridgeRuntime",
        "BridgeCommandClient",
        "save_workspace(",
        "build_runtime_preflight_status(",
        "start_recording",
        "VideoWriter",
        "OpenAI(",
        "auto_save",
    ):
        assert forbidden.casefold() not in source_text.casefold()


def test_lcd_2f_report_documents_layout_fit_scope_and_deferred_work():
    report = PROJECT_ROOT / "docs" / "HelmForge" / "lcd-2f-layout-fit-window-scaling-report.md"

    assert report.exists()
    text = report.read_text(encoding="utf-8")

    for required in (
        "LCD-2F Layout Fit",
        "previous layout issue",
        "default window size",
        "minimum size",
        "Liquid and Legacy",
        "overlap fixes",
        "footer clearance",
        "header/chip wrapping",
        "runtime truth preservation",
        "LCD-3",
        "no LCD-3 navigation was implemented",
        "no real page rebuilds were implemented",
        "no animations were added",
        "no radial menu behavior was added",
        "no real blur/distortion was added",
        "no runtime authority was changed",
        "no hardware polling was changed",
        "no vJoy/output behavior was changed",
        "no output verification behavior was changed",
        "no Bridge lifecycle management was added",
        "no recorder capture/encoding was added",
        "no cloud AI/LLM behavior was added",
        "no auto-save was added",
    ):
        assert required in text
