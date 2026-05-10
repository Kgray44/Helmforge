# HF-LRDC-5A Runtime Acceptance Gates Report

## Problem Summary

HF-LRDC now has fast-loop separation, physical input diagnostics, Live Monitor frame dedupe, config handshake, persistent output-loop ownership, output cadence/safety telemetry, local telemetry stream support, fake/real bench artifacts, and a manual validation checklist. HF-LRDC-5A adds one deterministic acceptance layer over those facts so RC posture is based on evidence rather than scattered logs.

## Acceptance Model

Added `shared_core.runtime.runtime_acceptance` with:

- `AcceptanceGateStatus`
- `AcceptanceProofKind`
- `RuntimeAcceptanceGate`
- `RuntimeAcceptanceReport`
- `AcceptanceResult`
- `RuntimeAcceptanceOptions`
- `evaluate_runtime_acceptance`
- `export_acceptance_report`

The evaluator consumes telemetry, bench summary JSON, and manual validation JSON. It produces gate status, proof kind, blocking reasons, warnings, errors, release posture, and artifact paths.

## Gates Implemented

The required gates are:

- Bridge fast loop health
- Physical input fidelity
- Telemetry source truth
- Frame dedupe/cadence
- Workspace config sync
- Pipeline/output intent
- vJoy/output verification truth
- Persistent output loop
- Output cadence/safety
- Bench harness proof
- Manual validation proof
- Full Live Runtime Ready gate
- RC freeze gate

## Fake vs Real Mode Behavior

Fake mode can pass fake-path acceptance using fake bench evidence and generated fake acceptance telemetry. It keeps `full_live_runtime_ready` false unless existing runtime telemetry proves otherwise, and reports `fake_path_pass_real_path_unproven`.

Real mode blocks when required HOTAS, vJoy, real output, or manual-validation proof is missing. Fake bench evidence does not satisfy real-required proof gates.

## Acceptance CLI

Added:

```powershell
python scripts/run_hf_lrdc_acceptance.py --mode fake --output .artifacts/hf-lrdc/acceptance/fake-smoke
python scripts/run_hf_lrdc_acceptance.py --mode real --require-hotas --output .artifacts/hf-lrdc/acceptance/real
```

The CLI accepts:

- `--mode fake|real`
- `--require-hotas`
- `--require-vjoy`
- `--require-real-output`
- `--require-manual-validation`
- `--bench-artifact`
- `--manual-validation-artifact`
- `--telemetry-json`
- `--output`

If fake mode has no supplied bench artifact, it runs a short fake HF-LRDC-4A bench smoke and uses that evidence. Real mode does not fake missing hardware proof.

## Artifact Outputs

The acceptance writer creates:

```text
.artifacts/hf-lrdc/acceptance/<timestamp>-<mode>/
  acceptance_summary.md
  acceptance_summary.json
  gates.json
  evidence.json
```

The Markdown summary includes overall status, ready-for-RC state, proof kind, Full Live Runtime Ready truth, release posture, gate table, blocking reasons, and runtime-truth boundary notes.

## RC Freeze Criteria

RC freeze requires all required gates to pass for the selected proof path. Real-path RC freeze requires real hardware/output proof when those flags are selected. Fake-path acceptance is useful for CI and regression checks, but it is not real Full Live Runtime Ready.

## Tests Added

Added `tests/test_hf_lrdc_5a_runtime_acceptance_gates.py`, covering:

- gate model construction and summary counts;
- fake-mode acceptance without real readiness claims;
- real-mode blocking for missing HOTAS/vJoy/output proof;
- gate failures for missing timing, fidelity, config mismatch, stale telemetry, duplicate frame acceptance, and safety stop;
- artifact writer output;
- CLI parsing and exit behavior.

## Known Limitations

Real HOTAS/vJoy validation remains bench-only. The acceptance runner can consume real artifacts when supplied, but this pass did not exercise physical hardware.

## Runtime Truth Preservation

The acceptance system does not weaken the readiness gate. It does not convert physical input, telemetry freshness, stream connection, config match, manual confirmation, vJoy detection, or output intent into vJoy write proof. Fake backend evidence remains fake-path proof only.
