# HF-LRDC-4B Manual Bench Validation Report

Unique repair track: HF-LRDC, HelmForge Live Runtime Data Chain.

## Problem Summary

HF-LRDC-4A added a bench harness for fake CI validation and optional real bench artifacts. HF-LRDC-4B adds an operator-facing manual validation model and compact Live Monitor surface so a person can plug in the HOTAS, move controls, watch telemetry truth, mark results, and export a clear report without hunting through logs.

## Manual Validation Model

Added `shared_core/runtime/manual_bench_validation.py`.

The model defines:

- `ManualValidationStepStatus`
- `ManualValidationStep`
- `ManualValidationSession`
- `ManualValidationResult`
- `create_manual_validation_session`
- `export_manual_validation_session`

The model is UI-independent and evaluates only existing telemetry evidence. Operator notes and manual pass/fail/skip marks are stored as bench evidence, not runtime authority.

## Steps Included

The session includes:

- Bridge / telemetry readiness
- Config sync
- HOTAS detection
- Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2 axis checks
- B1, B2, B15 button checks
- Hat up/right/down/left/center checks
- Pipeline / output intent
- vJoy / output proof status
- Final readiness truth

Axis movement uses a configurable normalized threshold, default `0.20`.

## Telemetry Evidence Sources

Evaluation uses:

- telemetry source label and age
- `raw_axes`
- `final_axes`
- `buttons`
- `hats`
- `bridge_workspace`
- UI workspace hash
- `device_discovery`
- `physical_input_fidelity`
- `physical_input_backend_choice`
- `runtime_frame`
- `output_loop_runtime`
- `output_verified`

It does not invent proof.

## UI Behavior Added

Live Monitor now includes a compact `Manual Bench Validation` card with:

- session status;
- current step;
- instruction text;
- evidence text;
- Start Validation;
- Next Step;
- Mark Passed;
- Mark Failed;
- Skip;
- Export Report.

The card observes accepted Live Monitor telemetry state and does not append duplicate graph frames or treat UI timer ticks as movement proof.

## Artifact Export

Model-level export writes:

```text
manual_validation.json
manual_validation.md
```

The Live Monitor export button writes under:

```text
.artifacts/hf-lrdc/manual-validation/<timestamp>/
```

Reports include session summary, step statuses, observed evidence, notes, warnings, and the explicit reminder that manual confirmation does not prove vJoy writes by itself.

## Pass / Fail / Block Rules

- Telemetry readiness passes only for fresh non-simulation Bridge telemetry.
- Config sync passes only when Bridge/UI hashes match.
- Axis steps pass only when the target logical axis changes above threshold.
- Button steps pass on false -> true -> false.
- Hat steps pass when the expected direction appears.
- Pipeline/output intent step can pass on output intent telemetry, but says this is not output write proof.
- Output proof blocks unless telemetry reports real output verification.
- Final readiness passes only if `runtime_frame.full_live_runtime_ready` is true.

## Tests Added

Added `tests/test_hf_lrdc_4b_manual_bench_validation.py`.

Coverage includes model creation, step transitions, operator notes, axis/button/hat evaluation, config/telemetry readiness, output proof truth, export artifacts, and offscreen Live Monitor card construction/start behavior.

## Real Hardware Limitations

Real Windows/HOTAS/vJoy validation remains manual bench-only. This phase makes the operator workflow repeatable, but it does not add a new physical input backend, does not enable vJoy writes, and does not bypass existing output-loop safety gates.

## Runtime Truth Preservation

Manual operator confirmation does not prove vJoy writes by itself. HOTAS detection does not prove physical sampling. Physical sampling does not prove output writes. vJoy detected is not output verification. Output intent is not output write proof. Stream connected does not prove output writes. Config match does not prove output writes. Full Live Runtime Ready remains gated by real input proof, pipeline proof, real output verification, output loop running, and real write proof.

HF-LRDC-4B adds no fake output verification, no fake Full Live Runtime Ready claim, no game injection, no graphics hooking, no cloud behavior, and no auto-save.
