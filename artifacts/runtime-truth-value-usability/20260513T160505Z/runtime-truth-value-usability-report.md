# Runtime Truth Value Usability Report

Generated: `2026-05-13T16:05:21.162963+00:00`
Overall status: `failures_detected`
Artifact directory: `artifacts\runtime-truth-value-usability\20260513T160505Z`

## Executive Findings
- `workspace_mapping_not_applied_to_output_intent`
- `button_mapping_not_applied_to_output_intent`
- `bridge_step_response_does_not_match_stateful_filter_intent`
- `math_stage_probe_coverage_incomplete`

## Live Environment Truth
- Bridge status: `HelmForge Bridge: lifecycle=LiveVerified truth=live_verified output_verified=True`
- Runtime setup HOTAS PID proof: `HOTAS match: HID-compliant game controller HID\VID_044F&PID_B68D\8&39EC0CDD&0&0000`
- Real vJoy available: `True`
- Real vJoy status: `backend_available`

## Simulated Inputs
- Axis test 1: 180-frame two-cycle sine input across all six axes. Roll/Pitch/Yaw/Aux axes use signed -1..1 normalization; Throttle uses the current one-sided 0..1 physical normalization.
- Axis test 2: the same sine structure with abrupt injected step offsets at quarter intervals for step-response verification.
- Button test: B1 through B15 are each driven false -> true -> false with all other buttons false.
- Mapping test: a temporary workspace swaps Roll/Pitch output axes and B1/B2 output buttons, then the current workspace copy is used again. The repository workspace file is not modified.
- Math-stage stress test: 96-frame composite input with center, below-deadzone, anti-deadzone, edge, same-direction slew, reverse-direction slew, max-output clamp, and conditional-rule threshold crossings. It uses an artifact-only workspace with curve_strength=0.64, deadzone=0.12, anti_deadzone=0.18, hysteresis=0.04, output_scale=1.35, max_output=0.72, center_alpha=0.18, edge_alpha=0.82, same_slew_limit=0.24, reverse_slew_limit=0.11, and one enabled Yaw output-scale rule.

## Math Parameter Probe Coverage
| Parameter family | Runtime stage payload | Proof field |
|---|---|---|
| Curve Mode | Curve / Shape | `metadata.curve_mode` |
| Curve Strength | Curve / Shape | `metadata.curve_strength` |
| Deadzone | Center Conditioning | `metadata.deadzone` |
| Anti-Deadzone | Center Conditioning | `metadata.anti_deadzone` |
| Hysteresis | Center Conditioning | `metadata.hysteresis`, `metadata.hysteresis_active` |
| Output Scale | Base Output Limits | `metadata.output_scale`, `metadata.configured_output_scale` |
| Max Output | Base Output Limits and Final Output | `metadata.max_output` plus final clamp value |
| Center Alpha | Filtering | `metadata.center_alpha` and computed `metadata.alpha` |
| Edge Alpha | Filtering | `metadata.edge_alpha` and computed `metadata.alpha_region` |
| Same Slew Limit | Filtering | `metadata.same_slew_limit`, `metadata.slew_path`, `metadata.slew_limit` |
| Reverse Slew Limit | Filtering | `metadata.reverse_slew_limit`, `metadata.slew_path`, `metadata.slew_limit` |
| Conditional Rules | Rule Injections and Base Output Limits | `metadata.evaluations`, `metadata.active_rules`, `metadata.injected_rules` |

## Math-Stage Stress Coverage Result
| Parameter family | Covered | Evidence |
|---|---:|---|
| Curve Mode | `True` | Curve / Shape exposes curve_mode. |
| Curve Strength | `True` | Stress workspace sets curve_strength=0.64 on every axis. |
| Deadzone | `True` | Center Conditioning exposes deadzone=0.12 and samples below/above the threshold. |
| Anti-Deadzone | `True` | Center Conditioning exposes anti_deadzone=0.18. |
| Hysteresis | `False` | Stress workspace sets hysteresis=0.04; coverage requires an active hysteresis transition. |
| Output Scale | `True` | Base Output Limits exposes configured_output_scale=1.35. |
| Max Output | `True` | Base Output Limits exposes max_output=0.72 and edge samples drive clamping. |
| Center Alpha | `True` | Filtering exposes center_alpha=0.18 on center-region samples. |
| Edge Alpha | `True` | Filtering exposes edge_alpha=0.82 on edge-region samples. |
| Same Slew Limit | `True` | Filtering exposes same_slew_limit=0.24 and same-direction limited deltas. |
| Reverse Slew Limit | `True` | Filtering exposes reverse_slew_limit=0.11 and reverse-direction limited deltas in stateful intent. |
| Conditional Rules | `True` | Stress workspace enables a Yaw output-scale rule gated by Roll final output. |

## Current Mapping
| Function/Button | Source | Output |
|---|---|---|
| Roll | Axis 1 | X(axis1) |
| Pitch | Axis 2 | Y(axis2) |
| Throttle | Axis 3 | Z(axis3) |
| Yaw | Axis 6 | RX(axis4) |
| Aux 1 | Axis 7 | RY(axis5) |
| Aux 2 | Axis 8 | RZ(axis6) |
| B1 | HOTAS B1 | Out1 |
| B2 | HOTAS B2 | Out2 |
| B3 | HOTAS B3 | Out3 |
| B4 | HOTAS B4 | Out4 |
| B5 | HOTAS B5 | Out5 |
| B6 | HOTAS B6 | Out6 |
| B7 | HOTAS B7 | Out7 |
| B8 | HOTAS B8 | Out8 |
| B9 | HOTAS B9 | Out9 |
| B10 | HOTAS B10 | Out10 |
| B11 | HOTAS B11 | Out11 |
| B12 | HOTAS B12 | Out12 |
| B13 | HOTAS B13 | Out13 |
| B14 | HOTAS B14 | Out14 |
| B15 | HOTAS B15 | Out15 |

## Temporary Mapping Variant
| Function/Button | Source | Output |
|---|---|---|
| Roll | Axis 1 | Y(axis2) |
| Pitch | Axis 2 | X(axis1) |
| Throttle | Axis 3 | Z(axis3) |
| Yaw | Axis 6 | RX(axis4) |
| Aux 1 | Axis 7 | RY(axis5) |
| Aux 2 | Axis 8 | RZ(axis6) |
| B1 | HOTAS B1 | Out2 |
| B2 | HOTAS B2 | Out1 |
| B3 | HOTAS B3 | Out3 |
| B4 | HOTAS B4 | Out4 |
| B5 | HOTAS B5 | Out5 |
| B6 | HOTAS B6 | Out6 |
| B7 | HOTAS B7 | Out7 |
| B8 | HOTAS B8 | Out8 |
| B9 | HOTAS B9 | Out9 |
| B10 | HOTAS B10 | Out10 |
| B11 | HOTAS B11 | Out11 |
| B12 | HOTAS B12 | Out12 |
| B13 | HOTAS B13 | Out13 |
| B14 | HOTAS B14 | Out14 |
| B15 | HOTAS B15 | Out15 |

## Latency Summary
| Scenario | Backend | Frames | Writes | Avg total ms | Max total ms | Avg input ms | Avg pipeline ms | Avg output ms | Max final diff | Max output diff |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `axis_sine_fake` | `fake` | 180 | 61 | 9.56 | 28.297 | 0.134 | 1.276 | 0.025 | 0.388807 | 0.388807 |
| `axis_sharp_step_sine_fake` | `fake` | 180 | 61 | 8.192 | 34.626 | 0.131 | 1.124 | 0.022 | 0.548801 | 0.548801 |
| `buttons_toggle_fake` | `fake` | 45 | 46 | 6.796 | 24.26 | 0.127 | 1.076 | 0.02 | 0.152445 | 0.152445 |
| `math_stage_stress_fake` | `fake` | 96 | 97 | 9.31 | 29.194 | 0.128 | 1.233 | 0.023 | 0.455031 | 0.455031 |
| `mapping_variant_fake` | `fake` | 2 | 3 | 6.194 | 6.233 | 0.099 | 1.433 | 0.035 | 0.182346 | 0.234595 |

## Axis Proof
### axis_sine_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 0.31009 | 0.31009 | 9.56 | 60 |
| Pitch | 0.30944 | 0.30944 | 9.56 | 60 |
| Throttle | 0.208188 | 0.208188 | 9.56 | 60 |
| Yaw | 0.388807 | 0.388807 | 9.56 | 60 |
| Aux 1 | 0.310953 | 0.310953 | 9.56 | 60 |
| Aux 2 | 0.310942 | 0.310942 | 9.56 | 60 |
### axis_sharp_step_sine_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 0.495853 | 0.495853 | 8.192 | 60 |
| Pitch | 0.442498 | 0.442498 | 8.192 | 60 |
| Throttle | 0.246266 | 0.246266 | 8.192 | 60 |
| Yaw | 0.548801 | 0.548801 | 8.192 | 60 |
| Aux 1 | 0.240356 | 0.240356 | 8.192 | 60 |
| Aux 2 | 0.269495 | 0.269495 | 8.192 | 60 |
### math_stage_stress_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 0.381232 | 0.381232 | 9.31 | 96 |
| Pitch | 0.381232 | 0.381232 | 9.31 | 96 |
| Throttle | 0.455031 | 0.455031 | 9.31 | 96 |
| Yaw | 0.422205 | 0.422205 | 9.31 | 96 |
| Aux 1 | 0.3936 | 0.3936 | 9.31 | 96 |
| Aux 2 | 0.381232 | 0.381232 | 9.31 | 96 |
### mapping_variant_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 0.072061 | 0.212268 | 6.194 | 2 |
| Pitch | 0.041882 | 0.234595 | 6.194 | 2 |
| Throttle | 0.182346 | 0.182346 | 6.194 | 2 |
| Yaw | 0.092408 | 0.092408 | 6.194 | 2 |
| Aux 1 | 0.047421 | 0.047421 | 6.194 | 2 |
| Aux 2 | 0.026255 | 0.026255 | 6.194 | 2 |

## Button Proof
### buttons_toggle_fake
| Button | Expected output button | Input true observed | Output true observed |
|---|---:|---:|---:|
| B1 | Out1 | 1 | 0 |
| B2 | Out2 | 1 | 0 |
| B3 | Out3 | 1 | 0 |
| B4 | Out4 | 1 | 0 |
| B5 | Out5 | 1 | 0 |
| B6 | Out6 | 1 | 0 |
| B7 | Out7 | 1 | 0 |
| B8 | Out8 | 1 | 0 |
| B9 | Out9 | 1 | 0 |
| B10 | Out10 | 1 | 0 |
| B11 | Out11 | 1 | 0 |
| B12 | Out12 | 1 | 0 |
| B13 | Out13 | 1 | 0 |
| B14 | Out14 | 1 | 0 |
| B15 | Out15 | 1 | 0 |

## Graphs
![Sine measured vs intended](runtime-truth-value-usability-assets/axis-sine-measured-vs-intended.svg)
![Sharp-step sine measured vs intended](runtime-truth-value-usability-assets/axis-sharp-step-measured-vs-intended.svg)

## Interpretation
- Stage values are now present in `runtime_frame.axis_stage_values` and are generated from the existing `AxisStackResult`; the focused regression verifies no second pipeline pass.
- Axis value truth is available at Raw Input, Center Conditioning, Curve / Shape, Base Output Limits, Filtering, Mode Modifiers, Rule Injections, and Final Output for every axis.
- The current output intent path still uses recovered static axis routing; the temporary mapping swap did not move output intent values to the swapped targets.
- Button input telemetry sees B1-B15, but the runtime output intent does not drive mapped output buttons true.
- The dedicated stress input covers every named math parameter except active hysteresis transitions; the stack reports hysteresis configuration, but this run did not observe `hysteresis_active=true`.
- Real vJoy write calls can be accepted when enabled, but the current product path does not expose a vJoy readback channel; this report distinguishes write-call proof from readback proof.

