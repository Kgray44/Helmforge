# Runtime Usability 1C Close Known Runtime Gaps Report

Generated: 2026-05-13

Branch: `runtime-usability-1c-close-known-runtime-gaps`

## 1. Executive Result

Runtime Usability 1C passed.

This phase closed the two runtime gaps reported by 1B:

- `combat_filter_parameters`: now covered.
- `hat_button_mapping`: now covered.

No UI calculation authority was added. The fixes live in the shared runtime math and output intent paths.

Latest matrix artifact:

- `artifacts/runtime-tuning-matrix/20260513T222654Z`

Latest runtime truth artifact with real-vJoy write-call option:

- `artifacts/runtime-truth-value-usability/20260513T222631Z`

## 2. Hardware State

| Item | Status | Evidence |
|---|---|---|
| Physical HOTAS | Deferred / unplugged | Setup dry run reported `HOTAS Not Connected`. |
| vJoy detection | Detected | Setup dry run found vJoy driver, device, and `vJoyInterface.dll`. |
| Optional real-vJoy write-call proof | Passed | Matrix probe requested real writes, found `vJoy Device 1`, attempted 3 writes, 3 succeeded. |
| vJoy readback | Not implemented | `readback_verified=false`; accepted write calls are not device readback proof. |
| Bridge status | LiveVerified with missing physical input | `HelmForge Bridge: lifecycle=LiveVerified truth=blocked_missing_device output_verified=True`. |

## 3. Runtime Authority Boundary

The UI remains a configuration and telemetry surface only.

Runtime calculation authority remains in:

- `shared_core/math/stack.py`
- `shared_core/math/pipeline.py`
- `shared_core/runtime/runtime_orchestrator.py`
- `shared_core/runtime/vjoy_output.py`
- shared workspace/config models

The 1C authority test scans `shared_core/math`, `shared_core/runtime`, `shared_core/rules`, and `bridge_app` and fails on UI page/widget imports. It passed.

## 4. Combat Filter Policy

Combat inactive:

- `center_alpha`, `edge_alpha`, `same_slew_limit`, and `reverse_slew_limit` come from base `AxisFiltering`.
- Combat filter parameters have no effect.

Combat active:

- `combat_center_alpha` overrides effective center alpha.
- `combat_edge_alpha` overrides effective edge alpha.
- `combat_same_slew` overrides effective same-direction slew.
- `combat_reverse_slew` overrides effective reverse-direction slew.

Invalid combat filter values:

- Fall back to the corresponding base filtering value.
- Outputs remain finite and bounded.
- UI validation is not required for runtime safety.

## 5. Combat Filter Implementation Summary

`shared_core/math/stack.py` now resolves effective filter settings before the existing `step_filter()` call. This preserves the existing single pipeline pass and keeps stateful filtering in the normal runtime path.

Filtering stage telemetry now reports:

- base filter values
- combat-active state
- effective filter values
- active combat filter values when combat is active

## 6. Combat Filter Test Table

| Case | Combat Active | Base Filter | Combat Filter | Expected Runtime Effect | Result |
|---|---:|---|---|---|---|
| Inactive no effect | false | center/edge `0.20`, slew `10.0` | alpha `1.0`, slew `0.01` | Output uses base filter: `0.40 -> 0.08` | Pass |
| Center alpha active | true | center/edge `0.05` | center/edge `0.80` | Output uses combat alpha: `0.25 -> 0.20` | Pass |
| Edge alpha active | true | center/edge `0.05` | center `0.20`, edge `1.0` | Edge-region alpha is effective combat alpha blend | Pass |
| Same slew active | true | same slew `10.0` | same slew `0.10` | First positive step limited to `0.10` | Pass |
| Reverse slew active | true | reverse slew `10.0` | reverse slew `0.05` | Reversal limited to `0.05` | Pass |
| Mode transition | false, true, false | center/edge `0.20` | center/edge `1.0` | State preserved, combat does not latch after release | Pass |
| Per-axis independence | true | shared base values | per-axis combat values | Roll, Pitch, Yaw report distinct effective values | Pass |
| Invalid combat values | true | finite base fallback | NaN/string/None/inf | No crash, finite output, effective values fall back to base | Pass |

## 7. Hat-To-Button Policy

POV passthrough remains supported.

Hat-to-button mappings are additive and optional:

- `Up`, `Right`, `Down`, and `Left` can drive configured output buttons.
- `Centered` releases hat-derived output buttons.
- Hat-derived button routes OR with normal button routes.
- Invalid output button targets are skipped safely.
- Diagonal hat values decompose to cardinal routes, for example `UpRight` drives both `Up` and `Right` mapped buttons.
- POV output remains emitted as `POV1`.

## 8. Hat-To-Button Implementation Summary

`shared_core/runtime/vjoy_output.py` now maps normalized hat state through workspace `HatMapping` button fields while building output intent.

The fake writer and real writer paths still use the same `VirtualOutputIntent` source of truth. The implementation does not claim vJoy readback.

## 9. Hat-To-Button Test Table

| Case | POV Output | Button Mapping | Expected Button State | Writer Payload | Result |
|---|---|---|---|---|---|
| No hat mapping | normalized `POV1` | none | no output buttons true | unchanged | Pass |
| Up | `Up` | Up -> Out9 | Out9 true only | fake writer matches | Pass |
| Right | `Right` | Right -> Out10 | Out10 true only | fake writer matches | Pass |
| Down | `Down` | Down -> Out11 | Out11 true only | fake writer matches | Pass |
| Left | `Left` | Left -> Out12 | Out12 true only | fake writer matches | Pass |
| Neutral release | `Centered` | Up -> Out9 | Out9 false | fake writer matches | Pass |
| Duplicate OR | `Up` plus B5 route | Hat Up -> Out9, B5 -> Out9 | Out9 true while either source true | fake writer matches | Pass |
| Invalid target | `Up` | Up -> 999 | skipped safely | no crash | Pass |
| Diagonal | `UpRight` | Up -> Out9, Right -> Out10 | Out9 and Out10 true | fake writer matches | Pass |

## 10. Updated Coverage Summary

Latest matrix coverage:

| Family | Status |
|---|---|
| base_tuning | covered |
| filtering | covered |
| combat_curve_scale | covered |
| combat_filter_parameters | covered |
| modes | covered |
| conditional_rules | covered |
| axis_mapping | covered |
| button_mapping | covered |
| hat_pov | pov_passthrough_and_hat_button_mapping_covered |

Generated case counts from `artifacts/runtime-tuning-matrix/20260513T222654Z`:

| Area | Count |
|---|---:|
| runtime_authority_boundary | 1 |
| curve_mode_cases | 67 |
| numeric_boundary_cases | 238 |
| combat_filter_cases | 8 |
| axis_mapping_cases | 6 |
| button_behavior_cases | 52 |
| hat_pov_cases | 10 |
| hat_button_mapping_cases | 15 |
| mode_cases | 4 |
| conditional_rule_cases | 16 |
| stage_telemetry_cases | 6 |
| pairwise_cases | 78 |
| seeded_fuzz_property_cases | 252 |
| real_vjoy_optional_cases | 3 |

## 11. Known Gaps After 1C

- `vjoy_readback`: no readback channel exists. Accepted write calls are not vJoy device-state proof.
- Physical HOTAS proof: deferred while the HOTAS is unplugged.

No combat filter parameter gap remains in the runtime matrix.

No hat-to-button mapping gap remains in the runtime matrix.

## 12. Matrix Artifact Path

Latest fake-only matrix run:

- `artifacts/runtime-tuning-matrix/20260513T222559Z`

Latest real-vJoy optional matrix run:

- `artifacts/runtime-tuning-matrix/20260513T222654Z`

New 1C artifact files include:

- `known-gaps.json`
- `combat-filter-table.md`
- `hat-button-mapping-table.md`

## 13. Files Changed

Runtime:

- `shared_core/math/stack.py`
- `shared_core/runtime/vjoy_output.py`

Tests and probes:

- `tests/test_runtime_usability_1c_close_known_gaps.py`
- `scripts/runtime_tuning_matrix_probe.py`

Report:

- `docs/HelmForge/runtime-usability-1c-close-known-runtime-gaps-report.md`

Existing 1A/1B files and artifacts remain part of this dirty worktree from prior phases.

## 14. Tests Run

| Command | Result |
|---|---|
| `python -m pytest tests/test_runtime_usability_1c_close_known_gaps.py -q` | 14 passed |
| `python -m pytest tests/test_runtime_usability_1b_full_tuning_matrix.py -q` | 19 passed |
| `python -m pytest tests/test_runtime_usability_1a_control_chain_correctness.py -q` | 6 passed |
| `python -m pytest tests/test_phase16b_runtime_frame_telemetry_ui.py -q` | 6 passed |
| `python -m pytest tests/test_phase3_tuning_math_pipeline.py -q` | 17 passed |
| `python scripts/runtime_truth_value_probe.py` | passed |
| `python scripts/runtime_tuning_matrix_probe.py` | passed |
| `python -m py_compile scripts/runtime_truth_value_probe.py scripts/runtime_tuning_matrix_probe.py v3_app/services/bridge_client.py shared_core/runtime/runtime_orchestrator.py shared_core/math/filtering.py shared_core/math/curves.py shared_core/math/deadzone.py shared_core/math/stack.py shared_core/math/pipeline.py shared_core/runtime/vjoy_output.py` | passed |
| `python -m bridge_app.main --status` | passed, LiveVerified with missing HOTAS truth |
| `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` | passed, HOTAS Not Connected, vJoy Detected |
| `git diff --check` | passed |
| `python scripts/runtime_truth_value_probe.py --real-vjoy-writes` | passed |
| `python scripts/runtime_tuning_matrix_probe.py --real-vjoy-writes` | passed, 3 write calls accepted |

## 15. Full Pytest Result

`python -m pytest`

Result:

- `909 passed in 261.03s (0:04:21)`

## 16. Runtime Truth Preservation Statement

This phase did not loosen Full Live Runtime Ready semantics.

This phase did not treat missing HOTAS hardware as a pass for physical sampling proof.

This phase did not claim vJoy readback.

This phase did not add UI redesign, Live Monitor performance work, animations, Bridge lifecycle behavior changes, unsupported runtime readiness claims, Flight Recorder work, Help/Docs behavior, game injection, graphics hooking, cloud AI/LLM behavior, or auto-save behavior.

The deterministic no-hardware runtime proof passes. Physical HOTAS sampling remains deferred until the device is plugged in.

## 17. Explicit Deferred Items

- vJoy readback/device-state verification.
- Physical HOTAS VID/PID sampling proof while the HOTAS is unplugged.
- Real physical HOTAS input -> vJoy write-call proof.
