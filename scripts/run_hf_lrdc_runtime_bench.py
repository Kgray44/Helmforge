from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge_app.runtime_bench import RuntimeBenchOptions, run_runtime_bench


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the HF-LRDC runtime bench harness.")
    parser.add_argument("--mode", choices=("fake", "real"), default="fake")
    parser.add_argument("--scenario", default="axis_sweep_roll")
    parser.add_argument("--duration-ms", type=int, default=3000)
    parser.add_argument("--output", type=Path, default=Path(".artifacts") / "hf-lrdc" / "runtime-bench")
    parser.add_argument("--require-hotas", action="store_true")
    parser.add_argument("--require-vjoy", action="store_true")
    parser.add_argument("--allow-real-output-writes", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_runtime_bench(
        RuntimeBenchOptions(
            mode=args.mode,
            scenario=args.scenario,
            duration_ms=args.duration_ms,
            output_dir=args.output,
            require_hotas=bool(args.require_hotas),
            require_vjoy=bool(args.require_vjoy),
            allow_real_output_writes=bool(args.allow_real_output_writes),
        )
    )
    summary = result.summary
    print(f"artifact_path={result.artifact_dir}")
    print(f"pass={summary.get('pass')}")
    print(f"mode={summary.get('mode')} scenario={summary.get('scenario')}")
    print(f"runtime_truth={summary.get('runtime_truth')}")
    print(f"warnings={'; '.join(str(item) for item in summary.get('warnings', ()) or ())}")
    errors = tuple(summary.get("errors", ()) or ())
    if errors:
        print(f"errors={'; '.join(str(item) for item in errors)}")
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
