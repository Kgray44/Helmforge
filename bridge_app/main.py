from __future__ import annotations

import argparse
from pathlib import Path

from bridge_app import BRIDGE_NAME
from bridge_app.ipc import DEFAULT_COMMAND_PATH, DEFAULT_TELEMETRY_PATH
from bridge_app.service import BridgeService, BridgeServiceOptions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HelmForge Bridge background process skeleton.")
    parser.add_argument("--once", action="store_true", help="Run one simulation Bridge tick and exit.")
    parser.add_argument("--run-for-ms", type=int, default=None, help="Run the simulation Bridge loop for a bounded duration.")
    parser.add_argument("--telemetry-path", type=Path, default=DEFAULT_TELEMETRY_PATH, help="Telemetry JSON output path.")
    parser.add_argument("--command-path", type=Path, default=DEFAULT_COMMAND_PATH, help="Command JSON inbox path.")
    parser.add_argument("--config-path", type=Path, default=None, help="Workspace config path.")
    parser.add_argument("--simulate", action="store_true", help="Force simulation mode. Phase 9B is simulation-only.")
    parser.add_argument("--status", action="store_true", help="Print current Bridge state/truth and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = BridgeService(
        BridgeServiceOptions(
            telemetry_path=args.telemetry_path,
            command_path=args.command_path,
            config_path=args.config_path,
            simulate=bool(args.simulate),
            enable_live_input=not bool(args.simulate),
            enable_output_verification=not bool(args.simulate),
            enable_output_loop=not bool(args.simulate),
        )
    )

    if args.status:
        telemetry = service.status()
        print(
            f"{BRIDGE_NAME}: lifecycle={telemetry.lifecycle_state.value} "
            f"truth={telemetry.runtime_truth.value} output_verified={telemetry.output_verified}"
        )
        print(f"telemetry_path={args.telemetry_path}")
        return 0

    if args.run_for_ms is not None:
        service.run_for_ms(args.run_for_ms)
        return 0

    service.run_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
