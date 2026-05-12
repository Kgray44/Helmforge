from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROUTES = (
    ("01-preflight-command-readiness.png", "preflight.command_readiness", "Preflight / Command Readiness"),
    ("02-mapping-hotas-map.png", "mapping.hotas_map", "Mapping / HOTAS Map"),
    ("03-mapping-route-details.png", "mapping.route_details", "Mapping / Route Details"),
    ("04-mapping-advanced-route-tables.png", "mapping.advanced_route_tables", "Mapping / Advanced Route Tables"),
    ("05-tuning-base-tuning.png", "tuning.base_tuning", "Tuning / Base Tuning"),
    ("06-tuning-filtering.png", "tuning.filtering", "Tuning / Filtering"),
    ("07-tuning-combat-profile.png", "tuning.combat_profile", "Tuning / Combat Profile"),
    ("08-tuning-conditional-rules.png", "tuning.conditional_rules", "Tuning / Conditional Rules"),
    ("09-tuning-profiles-library.png", "tuning.profiles_library", "Tuning / Profiles Library"),
    ("10-analysis-effective-response-stack.png", "analysis.effective_response_stack", "Analysis / Effective Response Stack"),
    ("11-analysis-live-monitor.png", "analysis.live_monitor", "Analysis / Live Monitor"),
)

SUPPORTED_PHASES = ("lcd-7u", "lcd-7v", "lcd-7w")
DEFAULT_PHASE = "lcd-7w"


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture deterministic Liquid UI screenshots.")
    parser.add_argument("--phase", default=DEFAULT_PHASE, help="Artifact phase id.")
    parser.add_argument("--width", type=int, default=1500)
    parser.add_argument("--height", type=int, default=1000)
    args = parser.parse_args()
    if args.phase not in SUPPORTED_PHASES:
        raise SystemExit(f"Unsupported Liquid UI screenshot phase: {args.phase}")

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))

    from PySide6.QtWidgets import QApplication, QPushButton
    from v3_app.liquid.app_shell import LiquidCommandShell

    app = QApplication.instance() or QApplication([])
    shell = LiquidCommandShell()
    shell.resize(args.width, args.height)
    shell.show()
    app.processEvents()

    out_dir = project_root / "artifacts" / "liquid-ui" / args.phase
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []

    for filename, route_key, title in ROUTES:
        shell.switch_route(route_key)
        for _ in range(6):
            app.processEvents()
        screenshot = shell.grab()
        path = out_dir / filename
        if not screenshot.save(str(path), "PNG"):
            manifest.append(
                {
                    "route": route_key,
                    "title": title,
                    "file": filename,
                    "status": "failed",
                    "note": "Qt screenshot save returned false.",
                }
            )
            continue
        manifest.append(
            {
                "route": route_key,
                "title": title,
                "file": filename,
                "status": "captured",
                "note": "Top-of-route Liquid command surface screenshot.",
            }
        )

    shell.switch_route("mapping.hotas_map")
    for _ in range(4):
        app.processEvents()
    marker = shell.page_widgets["mapping.hotas_map"].widget().findChild(QPushButton, "liquidMappingMarker_axis_yaw")
    if marker is not None:
        marker.click()
        for _ in range(6):
            app.processEvents()
        filename = "mapping-editor-overlay-open.png"
        screenshot = shell.grab()
        path = out_dir / filename
        status = "captured" if screenshot.save(str(path), "PNG") else "failed"
        manifest.append(
            {
                "route": "mapping.hotas_map",
                "title": "Mapping / Editor Overlay Open",
                "file": filename,
                "status": status,
                "note": f"{args.phase.upper()} required HOTAS route editor overlay screenshot.",
            }
        )
    else:
        manifest.append(
            {
                "route": "mapping.hotas_map",
                "title": "Mapping / Editor Overlay Open",
                "file": "mapping-editor-overlay-open.png",
                "status": "failed",
                "note": "Marker liquidMappingMarker_axis_yaw was unavailable.",
            }
        )

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    shell.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
