# Phase 16C Verified Runtime Path Report

Status: implemented for Phase 16C only.

## Summary

Phase 16C connects verified input/output runtime path semantics in the shared runtime orchestrator and UI truth surfaces. It does not add Bridge lifecycle management or unsupported runtime authority.

The runtime frame now separates proof into four lanes:

- input proof;
- pipeline proof;
- output verification proof;
- output-loop proof.

## Verified Runtime Path Policy

Phase 16C uses Policy B for Full Live Runtime Ready. A frame may report `verified_runtime_candidate` when a fresh physical input sample, successful pipeline result, guarded real output verification, enabled/running output loop, and successful write are all present. Full Live Runtime Ready remains false because Phase 16D owns the final readiness gate.

Blocked states include missing input, stale input, input error, pipeline error, unverified output, disabled output loop, and output safety stop. Output intent remains separate from output write proof.

## Runtime Frame Proof Fields

`runtime_frame` now includes compact proof fields:

- `input_verified_for_runtime`;
- `output_verified_for_runtime`;
- `output_loop_enabled`;
- `output_loop_running`;
- `output_loop_safety_stopped`;
- `pipeline_ready`;
- `verified_runtime_candidate`;
- `input_proof`;
- `pipeline_proof`;
- `output_proof`;
- `proof_summary`.

The proof summary stays compact and does not dump full internal pipeline objects.

## UI Behavior

Mapping, Live Monitor, Perf / Diagnostics, and Copy Diagnostics can display input proof, pipeline proof, output proof, runtime candidate, blocked reason, and proof summary. Simulated or fake/test paths remain clearly distinct from real readiness. Fake/test path is not real readiness and cannot set real output verified.

## Current Runtime Truth

Simulation mode remains available. Physical input, pipeline success, output verification, and output loop state are separate proofs. A fresh physical input sample alone cannot set `output_verified`. Output verification alone cannot set `Full Live Runtime Ready`. Output intent alone is not output write proof.

## Boundary

Phase 16C does not add automatic output enablement, unsupported real vJoy writes, automatic Bridge launch, UI-launched child process, service install, login auto-start, tray manager, installer launch, Start/Stop/Restart behavior, real process scanner, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or unsupported runtime activation.

## Verification

Executed on 2026-05-07:

- `python -m pytest` - 356 passed.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - 7 passed.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - 6 passed.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - 5 passed.
- `python -m pytest tests\test_phase13d_flight_recorder_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase14d_input_boundary_freeze.py` - 4 passed.
- `python -m pytest tests\test_phase15d_output_boundary_freeze.py` - 4 passed.
- `python -m pytest tests\test_phase16a_runtime_orchestrator_simulation_path.py` - 5 passed.
- `python -m pytest tests\test_phase16b_runtime_frame_telemetry_ui.py` - 4 passed.
- `python -m pytest tests\test_phase16c_verified_runtime_path.py` - 4 passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed; reported `lifecycle=Simulated`, `truth=blocked_missing_device`, `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; reported HOTAS Not Connected, vJoy Detected, and Full Live Runtime Ready false.
- `git diff --check` - passed.

## Phase 16D Readiness

Phase 16D should freeze the final readiness policy. It may build on the Phase 16C proof summary but must preserve simulation fallback, keep output writes safety-gated, require real input and real output proof, and avoid fake readiness from detection-only or fake/test signals.
