from __future__ import annotations

import os

from shared_core.models.runtime import (
    InputDeviceDetection,
    InputStatus,
    OutputBackendDetection,
    OutputStatus,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _runtime_status(
    *,
    truth: RuntimeTruth,
    input_status: InputStatus = InputStatus.MISSING,
    output_status: OutputStatus = OutputStatus.VJOY_DETECTED,
    output_verified: bool = False,
) -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=truth,
        input=InputDeviceDetection(status=input_status),
        output=OutputBackendDetection(
            status=output_status,
            backend_name="vJoy" if output_status is not OutputStatus.VJOY_MISSING else None,
            live_output_writes_verified=output_verified,
        ),
        messages=("Simulation mode selected because live output is not verified.",),
    )


def test_phase4_main_window_title_and_shell_constructs():
    _app()

    from PySide6.QtWidgets import QPushButton, QWidget
    from v3_app.main import WINDOW_TITLE, build_main_window

    window = build_main_window()

    assert WINDOW_TITLE == "HelmForge — HOTAS Control Panel V3"
    assert window.windowTitle() == WINDOW_TITLE
    assert window.findChild(QWidget, "helmforgeShell") is not None
    assert window.findChild(QWidget, "appSidebar") is not None
    assert window.findChild(QWidget, "appHeader") is not None
    assert window.findChild(QWidget, "appFooter") is not None
    assert any(button.text() == "Helm" for button in window.findChildren(QPushButton))


def test_phase4_all_placeholder_pages_are_registered_and_reused():
    _app()

    from v3_app.pages.placeholders import PAGE_DEFINITIONS
    from v3_app.services.app_state import PAGE_IDS
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell()

    assert tuple(page.page_id for page in PAGE_DEFINITIONS) == PAGE_IDS
    assert len(PAGE_DEFINITIONS) == 12
    assert set(shell.page_widgets) == set(PAGE_IDS)

    original_page = shell.page_widgets["live_monitor"]
    shell.switch_page("live_monitor")
    shell.switch_page("mapping")
    shell.switch_page("live_monitor")

    assert shell.active_page_id == "live_monitor"
    assert shell.page_widgets["live_monitor"] is original_page


def test_phase4_sidebar_switching_updates_active_state_and_footer():
    _app()

    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell()
    shell.switch_page("flight_recorder")

    active_button = shell.findChild(QPushButton, "nav_flight_recorder")
    inactive_button = shell.findChild(QPushButton, "nav_mapping")
    footer_page = shell.findChild(QLabel, "footerPageDetail")

    assert shell.active_page_id == "flight_recorder"
    assert active_button.property("active") is True
    assert inactive_button.property("active") is False
    assert "Flight Recorder" in footer_page.text()


def test_phase4_runtime_status_surfaces_do_not_claim_live_when_unverified():
    _app()

    from PySide6.QtWidgets import QLabel
    from v3_app.services.app_state import AppState
    from v3_app.ui.shell import HelmForgeShell

    for truth, expected in (
        (RuntimeTruth.BLOCKED_MISSING_DEVICE, "HOTAS Not Connected"),
        (RuntimeTruth.DETECTED_UNVERIFIED, "Output Unverified"),
        (RuntimeTruth.SIMULATED, "Simulated"),
    ):
        shell = HelmForgeShell(
            AppState.from_runtime_status(
                _runtime_status(
                    truth=truth,
                    input_status=InputStatus.DETECTED
                    if truth is RuntimeTruth.DETECTED_UNVERIFIED
                    else InputStatus.MISSING,
                    output_status=OutputStatus.VJOY_DETECTED,
                    output_verified=False,
                )
            )
        )
        labels_text = " ".join(label.text() for label in shell.findChildren(QLabel))

        assert expected in labels_text
        assert "Full Live Runtime Ready" not in labels_text
        assert "Output Verified" not in labels_text


def test_phase4_status_chips_and_action_buttons_are_distinguishable():
    _app()

    from PySide6.QtWidgets import QLabel, QPushButton
    from v3_app.ui.shell import HelmForgeShell

    shell = HelmForgeShell()
    status_chips = [
        label for label in shell.findChildren(QLabel) if label.property("uiRole") == "statusChip"
    ]
    action_buttons = [
        button for button in shell.findChildren(QPushButton) if button.property("uiRole") == "actionButton"
    ]

    assert {chip.text() for chip in status_chips} >= {"Workspace Copy", "Saved"}
    assert {button.text() for button in action_buttons} >= {
        "Helm",
        "Import Profile",
        "Revert",
        "Save Workspace",
    }
    assert all(not isinstance(chip, QPushButton) for chip in status_chips)


def test_phase4_shared_core_boundary_still_excludes_ui_imports():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    shared_core_sources = list((project_root / "shared_core").rglob("*.py"))
    joined = "\n".join(path.read_text(encoding="utf-8") for path in shared_core_sources)

    assert "from v3_app" not in joined
    assert "import v3_app" not in joined
    assert "PySide6" not in joined
