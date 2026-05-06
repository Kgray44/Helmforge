from __future__ import annotations

import argparse
import sys


APP_NAME = "HelmForge"
TECHNICAL_SUBTITLE = "HOTAS Control Panel V3"
WINDOW_TITLE = f"{APP_NAME} — {TECHNICAL_SUBTITLE}"
PHASE_NOTICE = (
    "Phase 0 foundation with Phase 1 runtime preflight only. "
    "No real HOTAS/vJoy runtime support is implemented yet. "
    "Simulation-first development scaffolding is present so future phases can "
    "proceed before hardware drivers are installed."
)
KNOWN_TARGET_HARDWARE = "Thrustmaster T-Flight HOTAS One"


def build_main_window():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget
    from shared_core.runtime.device_discovery import build_runtime_preflight_status

    window = QMainWindow()
    window.setWindowTitle(WINDOW_TITLE)
    window.resize(820, 420)
    runtime_status = build_runtime_preflight_status()

    central = QWidget()
    layout = QVBoxLayout(central)
    layout.setContentsMargins(36, 32, 36, 32)
    layout.setSpacing(14)

    title = QLabel(APP_NAME)
    title.setObjectName("appTitle")
    title.setAlignment(Qt.AlignmentFlag.AlignLeft)

    subtitle = QLabel(TECHNICAL_SUBTITLE)
    subtitle.setObjectName("appSubtitle")
    subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)

    notice = QLabel(PHASE_NOTICE)
    notice.setWordWrap(True)
    notice.setObjectName("phaseNotice")

    target = QLabel(f"Known target hardware: {KNOWN_TARGET_HARDWARE}. Real hardware support is not implemented in Phase 1.")
    target.setWordWrap(True)
    target.setObjectName("targetHardware")

    runtime = QLabel(
        "Runtime preflight: "
        f"{runtime_status.mode.value} / {runtime_status.truth.value}. "
        f"Input: {runtime_status.input.status.value}. "
        f"Output: {runtime_status.output.status.value}."
    )
    runtime.setWordWrap(True)
    runtime.setObjectName("runtimeStatus")

    runtime_detail = QLabel(" ".join((*runtime_status.messages, *runtime_status.warnings)))
    runtime_detail.setWordWrap(True)
    runtime_detail.setObjectName("runtimeDetail")

    layout.addWidget(title)
    layout.addWidget(subtitle)
    layout.addSpacing(10)
    layout.addWidget(notice)
    layout.addWidget(target)
    layout.addWidget(runtime)
    layout.addWidget(runtime_detail)
    layout.addStretch(1)

    window.setCentralWidget(central)
    window.setStyleSheet(
        """
        QMainWindow {
            background: #101418;
            color: #f3f7fb;
        }
        QWidget {
            background: #101418;
            color: #f3f7fb;
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 15px;
        }
        QLabel#appTitle {
            font-size: 34px;
            font-weight: 700;
            color: #f7fbff;
        }
        QLabel#appSubtitle {
            font-size: 18px;
            color: #9fb7c9;
        }
        QLabel#phaseNotice,
        QLabel#targetHardware,
        QLabel#runtimeStatus,
        QLabel#runtimeDetail {
            color: #d8e3ec;
            line-height: 1.35;
        }
        QLabel#runtimeStatus {
            color: #ffd28a;
        }
        """
    )
    return window


def run_app(smoke_exit_ms: int | None = None) -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = build_main_window()
    window.show()

    if smoke_exit_ms is not None:
        QTimer.singleShot(smoke_exit_ms, app.quit)

    return app.exec()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} - {TECHNICAL_SUBTITLE}")
    parser.add_argument(
        "--smoke-exit-ms",
        type=int,
        default=None,
        help="Exit automatically after this many milliseconds for launch smoke checks.",
    )
    args = parser.parse_args(argv)
    return run_app(smoke_exit_ms=args.smoke_exit_ms)


if __name__ == "__main__":
    raise SystemExit(main())
