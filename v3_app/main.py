from __future__ import annotations

import argparse
import sys


APP_NAME = "HelmForge"
TECHNICAL_SUBTITLE = "HOTAS Control Panel V3"
WINDOW_TITLE = f"{APP_NAME} — {TECHNICAL_SUBTITLE}"
KNOWN_TARGET_HARDWARE = "Thrustmaster T-Flight HOTAS One"


def build_main_window():
    from v3_app.app import build_window

    return build_window(title=WINDOW_TITLE)


def run_app(smoke_exit_ms: int | None = None) -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(WINDOW_TITLE)
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
