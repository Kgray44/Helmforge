from __future__ import annotations

import argparse
from pathlib import Path

from bridge_app import BRIDGE_NAME
from bridge_app.ipc import DEFAULT_COMMAND_PATH, DEFAULT_TELEMETRY_PATH
from bridge_app.service import BridgeService, BridgeServiceOptions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HelmForge Bridge background process skeleton.")
    parser.add_argument("--once", action="store_true", help="Run one simulation Bridge tick and exit.")
    parser.add_argument("--run", action="store_true", help="Run the Bridge continuously until interrupted or stopped.")
    parser.add_argument("--run-for-ms", type=int, default=None, help="Run the simulation Bridge loop for a bounded duration.")
    parser.add_argument("--telemetry-path", type=Path, default=DEFAULT_TELEMETRY_PATH, help="Telemetry JSON output path.")
    parser.add_argument("--command-path", type=Path, default=DEFAULT_COMMAND_PATH, help="Command JSON inbox path.")
    parser.add_argument("--config-path", type=Path, default=None, help="Workspace config path.")
    parser.add_argument("--simulate", action="store_true", help="Force simulation mode. Phase 9B is simulation-only.")
    parser.add_argument("--status", action="store_true", help="Print current Bridge state/truth and exit.")
    parser.add_argument("--telemetry-stream", dest="telemetry_stream", action="store_true", help="Enable the local-only telemetry WebSocket stream.")
    parser.add_argument("--no-telemetry-stream", dest="telemetry_stream", action="store_false", help="Disable the local telemetry stream.")
    parser.set_defaults(telemetry_stream=True)
    parser.add_argument("--telemetry-host", default="127.0.0.1", help="Telemetry stream bind host. HF-LRDC-3B supports 127.0.0.1 only.")
    parser.add_argument("--telemetry-port", type=int, default=8765, help="Telemetry stream bind port; use 0 for an ephemeral local port.")
    parser.add_argument("--telemetry-rate-hz", type=float, default=60.0, help="Maximum telemetry stream publish rate.")
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
            enable_telemetry_stream=bool(args.telemetry_stream),
            telemetry_stream_host=str(args.telemetry_host),
            telemetry_stream_port=int(args.telemetry_port),
            telemetry_stream_rate_hz=float(args.telemetry_rate_hz),
        )
    )
    try:
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

        if args.run:
            service.run_forever()
            return 0

        service.run_once()
        return 0
    finally:
        service.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
