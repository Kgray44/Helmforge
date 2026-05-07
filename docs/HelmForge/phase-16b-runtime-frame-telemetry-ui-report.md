# Phase 16B Runtime Frame Telemetry UI Report

Phase 16B adds runtime_frame telemetry and UI surfaces for the Runtime End-to-End Live Mode line.

## Summary

- Bridge telemetry now includes a compact `runtime_frame` section produced from the Phase 16A runtime orchestrator.
- The UI telemetry client parses `runtime_frame` safely and treats missing, malformed, or stale runtime-frame telemetry as fallback-safe.
- Mapping, Live Monitor, Perf / Diagnostics, and Copy Diagnostics can surface runtime frame source, pipeline status, output intent readiness, output backend, output loop state, output verification truth, runtime truth, blocked reason, warnings, and errors.
- Help / Docs now explains that `runtime_frame` is compact telemetry for the orchestrated runtime path.

## Runtime Frame Truth

`runtime_frame` can be simulation-backed. A simulation frame proves the simulation pipeline and output-intent path only.

output intent is not output write proof. Output loop state must be read separately from output intent readiness. output_verified requires the Phase 15 output verification semantics. Full Live Runtime Ready remains false unless the full proof chain is explicitly met and tested.

## Boundary

Phase 16B does not add automatic output enablement, unsupported real vJoy writes, Bridge lifecycle management, automatic Bridge launch, UI-launched child process, service install, login auto-start, tray manager, installer launch, Start/Stop/Restart behavior, real process scanner, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or unsupported runtime activation.

## Verification

Verification completed on May 7, 2026:

- `python -m pytest` - 352 passed.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - 7 passed.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - 6 passed.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - 5 passed.
- `python -m pytest tests\test_phase13d_flight_recorder_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase14d_input_boundary_freeze.py` - 4 passed.
- `python -m pytest tests\test_phase15d_output_boundary_freeze.py` - 4 passed.
- `python -m pytest tests\test_phase16a_runtime_orchestrator_simulation_path.py` - 5 passed.
- `python -m pytest tests\test_phase16b_runtime_frame_telemetry_ui.py` - 4 passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed with `truth=blocked_missing_device` and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; dry-run reported HOTAS Not Connected, vJoy Detected, Full Live Runtime Ready false.
- `git diff --check` - passed.
