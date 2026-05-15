# Runtime Usability 1D Physical HOTAS Live Smoke Report

Generated: `2026-05-15T17:11:46.719317+00:00`
Artifact directory: `artifacts\runtime-physical-hotas-smoke\20260515T171133Z`
Overall status: `passed`

## Executive Result
- Guided physical probe status: `passed`
- Aux 1 focused retest status: `passed`
- The Thrustmaster manual states that, on PC, the Xbox button light off is the independent 5/8 axes mode. The rear-throttle rocking control was therefore treated as an independent physical axis, not a device-mode failure.
- Direct physical diagnostics showed the rear-throttle control on WinMM raw `V`; the runtime now maps WinMM `V` to user-facing `Aux 1` for this HOTAS path.
- This phase does not implement device hiding/direct physical HOTAS filtering.
- Game-level verification remains manual unless an external game/controller observer is tested.

## Aux 1 Focused Finding
- Manual checked: `https://ts.thrustmaster.com/download/accessories/Manuals/TFHOne/T-Flight_HO_Manual.pdf`
- User hardware state: Xbox button light off, matching the manual's PC 5/8 axes independent-axis mode.
- Focused raw-axis diagnostic found the rear-throttle axis on WinMM `V`.
- The uncalibrated Windows Raw Input decoder produced multi-axis movement from the same control and is now kept behind WinMM priority for guided physical smoke tests.
- Final Aux 1-only guided proof artifact: `artifacts\runtime-physical-hotas-smoke\20260515T171133Z`

## Hardware State
- Physical HOTAS proof: `detected`
- VID/PID: `VID_044F&PID_B68D`
- vJoy detected: `True`
- vJoy write-call proof: `passed`
- vJoy readback: `not_implemented`
- Bridge status: `HelmForge Bridge: lifecycle=LiveVerified truth=live_verified output_verified=True`

## Guided Probe Procedure
- Each requested physical control waits up to the configured timeout.
- After detection, the probe collects the configured settle window before judging the step.
- Timeouts are recorded per control. `--skip-on-timeout` continues after a failed step.

## Axis Test Table
| Step | Status | Evidence |
|---|---|---|
| `Aux 1` | `passed` | Aux 1 changed raw input and mapped output RY. |

Aux 1 focused values:

| Field | Value |
|---|---|
| Raw delta | `1.000015` |
| Largest raw-axis delta | `Aux 1` |
| Final runtime value | `1.0` |
| Output intent target | `RY` |
| Output intent value | `1.0` |
| Writer value | `1.0` |
| Writer status | `real_write_succeeded` |

## Button Test Table
No steps recorded.

## Hat/POV Test Table
No steps recorded.

## Mode Activation Table
No steps recorded.

## Conditional Rule Activation Table
No steps recorded.

## Mapping Variant Table
No steps recorded.

## Game-Readiness Checklist Path
- `artifacts\runtime-physical-hotas-smoke\20260515T171133Z\game-readiness-checklist.md`

## Known Gaps After 1D
- vJoy readback remains not implemented.
- Automated game-level verification remains not implemented.
- Direct physical HOTAS hiding/filtering is intentionally deferred.
- Any timeout/unavailable physical step remains listed in the artifact step files.

## Files Changed
- `scripts/runtime_physical_hotas_smoke_probe.py`
- `shared_core/runtime/hotas_input.py`
- `shared_core/runtime/vjoy_output.py`
- `tests/test_hf_lrdc_6a_native_raw_input_backend.py`
- `tests/test_runtime_usability_1d_aux1_physical_backend.py`
- `tests/test_runtime_usability_1d_physical_hotas_smoke_probe.py`
- `docs/HelmForge/runtime-usability-1d-physical-hotas-live-smoke-report.md`

## Runtime Truth Preservation Statement
- vJoy write-call proof is not readback proof.
- Game-level proof is not claimed without external observation.
- Full Live Runtime Ready semantics were not loosened.
- No UI redesign, Live Monitor performance work, animations, Flight Recorder work, device hiding/filtering, game injection, graphics hooking, cloud AI/LLM behavior, or auto-save behavior was added.

## Explicit Deferred Items
- vJoy readback/device-state verification.
- Automated game-level verification.
- Device hiding/direct physical HOTAS filtering.
