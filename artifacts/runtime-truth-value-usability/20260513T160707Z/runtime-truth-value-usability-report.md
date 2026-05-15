# Runtime Truth Value Usability Report

Generated: `2026-05-13T16:07:25.567079+00:00`
Overall status: `failures_detected`
Artifact directory: `artifacts\runtime-truth-value-usability\20260513T160707Z`

## Executive Findings
- `bridge_continuous_axis_response_does_not_match_stateful_filter_intent`
- `workspace_mapping_not_applied_to_output_intent`
- `button_mapping_not_applied_to_output_intent`
- `bridge_step_response_does_not_match_stateful_filter_intent`
- `runtime_orchestrator_rebuilds_each_sample`
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
| Scenario | Backend | Frames | Writes | Rebuilds | Avg total ms | Max total ms | Avg input ms | Avg pipeline ms | Avg output ms | Max final diff | Max output diff |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `axis_sine_fake` | `fake` | 180 | 61 | 181.0 | 5.83 | 25.5 | 0.098 | 0.887 | 0.018 | 0.388807 | 0.388807 |
| `axis_sharp_step_sine_fake` | `fake` | 180 | 61 | 181.0 | 5.788 | 27.183 | 0.089 | 0.714 | 0.016 | 0.548801 | 0.548801 |
| `buttons_toggle_fake` | `fake` | 45 | 46 | 46.0 | 6.087 | 25.588 | 0.088 | 0.755 | 0.015 | 0.152445 | 0.152445 |
| `math_stage_stress_fake` | `fake` | 96 | 97 | 97.0 | 6.569 | 28.989 | 0.099 | 0.817 | 0.015 | 0.455031 | 0.455031 |
| `mapping_variant_fake` | `fake` | 2 | 3 | 3.0 | 7.811 | 12.208 | 0.085 | 0.809 | 0.019 | 0.182346 | 0.234595 |
| `axis_sine_real_vjoy` | `real_vjoy` | 72 | 73 | 73.0 | 10.484 | 25.739 | 0.117 | 2.469 | 0.791 | 0.388807 | 0.388807 |
| `buttons_toggle_real_vjoy` | `real_vjoy` | 45 | 46 | 46.0 | 13.077 | 37.582 | 0.141 | 3.277 | 1.05 | 0.152445 | 0.152445 |

## Axis Proof
### axis_sine_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 0.31009 | 0.31009 | 5.83 | 60 |
| Pitch | 0.30944 | 0.30944 | 5.83 | 60 |
| Throttle | 0.208188 | 0.208188 | 5.83 | 60 |
| Yaw | 0.388807 | 0.388807 | 5.83 | 60 |
| Aux 1 | 0.310953 | 0.310953 | 5.83 | 60 |
| Aux 2 | 0.310942 | 0.310942 | 5.83 | 60 |
### axis_sharp_step_sine_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 0.495853 | 0.495853 | 5.788 | 60 |
| Pitch | 0.442498 | 0.442498 | 5.788 | 60 |
| Throttle | 0.246266 | 0.246266 | 5.788 | 60 |
| Yaw | 0.548801 | 0.548801 | 5.788 | 60 |
| Aux 1 | 0.240356 | 0.240356 | 5.788 | 60 |
| Aux 2 | 0.269495 | 0.269495 | 5.788 | 60 |
### math_stage_stress_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 0.381232 | 0.381232 | 6.569 | 96 |
| Pitch | 0.381232 | 0.381232 | 6.569 | 96 |
| Throttle | 0.455031 | 0.455031 | 6.569 | 96 |
| Yaw | 0.422205 | 0.422205 | 6.569 | 96 |
| Aux 1 | 0.3936 | 0.3936 | 6.569 | 96 |
| Aux 2 | 0.381232 | 0.381232 | 6.569 | 96 |
### mapping_variant_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 0.072061 | 0.212268 | 7.811 | 2 |
| Pitch | 0.041882 | 0.234595 | 7.811 | 2 |
| Throttle | 0.182346 | 0.182346 | 7.811 | 2 |
| Yaw | 0.092408 | 0.092408 | 7.811 | 2 |
| Aux 1 | 0.047421 | 0.047421 | 7.811 | 2 |
| Aux 2 | 0.026255 | 0.026255 | 7.811 | 2 |
### axis_sine_real_vjoy
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 0.31009 | 0.31009 | 10.484 | 72 |
| Pitch | 0.30942 | 0.30942 | 10.484 | 72 |
| Throttle | 0.208188 | 0.208188 | 10.484 | 72 |
| Yaw | 0.388807 | 0.388807 | 10.484 | 72 |
| Aux 1 | 0.310842 | 0.310842 | 10.484 | 72 |
| Aux 2 | 0.310942 | 0.310942 | 10.484 | 72 |

## Button Proof
### buttons_toggle_fake
| Button | Expected output button | Input true observed | Output true observed | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|---:|
| B1 | Out1 | 1 | 0 | 6.087 | 45 |
| B2 | Out2 | 1 | 0 | 6.087 | 45 |
| B3 | Out3 | 1 | 0 | 6.087 | 45 |
| B4 | Out4 | 1 | 0 | 6.087 | 45 |
| B5 | Out5 | 1 | 0 | 6.087 | 45 |
| B6 | Out6 | 1 | 0 | 6.087 | 45 |
| B7 | Out7 | 1 | 0 | 6.087 | 45 |
| B8 | Out8 | 1 | 0 | 6.087 | 45 |
| B9 | Out9 | 1 | 0 | 6.087 | 45 |
| B10 | Out10 | 1 | 0 | 6.087 | 45 |
| B11 | Out11 | 1 | 0 | 6.087 | 45 |
| B12 | Out12 | 1 | 0 | 6.087 | 45 |
| B13 | Out13 | 1 | 0 | 6.087 | 45 |
| B14 | Out14 | 1 | 0 | 6.087 | 45 |
| B15 | Out15 | 1 | 0 | 6.087 | 45 |
### mapping_variant_fake
| Button | Expected output button | Input true observed | Output true observed | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|---:|
| B1 | Out2 | 1 | 0 | 7.811 | 2 |
| B2 | Out1 | 0 | 0 | 7.811 | 2 |
| B3 | Out3 | 0 | 0 | 7.811 | 2 |
| B4 | Out4 | 0 | 0 | 7.811 | 2 |
| B5 | Out5 | 0 | 0 | 7.811 | 2 |
| B6 | Out6 | 0 | 0 | 7.811 | 2 |
| B7 | Out7 | 0 | 0 | 7.811 | 2 |
| B8 | Out8 | 0 | 0 | 7.811 | 2 |
| B9 | Out9 | 0 | 0 | 7.811 | 2 |
| B10 | Out10 | 0 | 0 | 7.811 | 2 |
| B11 | Out11 | 0 | 0 | 7.811 | 2 |
| B12 | Out12 | 0 | 0 | 7.811 | 2 |
| B13 | Out13 | 0 | 0 | 7.811 | 2 |
| B14 | Out14 | 0 | 0 | 7.811 | 2 |
| B15 | Out15 | 0 | 0 | 7.811 | 2 |
### buttons_toggle_real_vjoy
| Button | Expected output button | Input true observed | Output true observed | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|---:|
| B1 | Out1 | 1 | 0 | 13.077 | 45 |
| B2 | Out2 | 1 | 0 | 13.077 | 45 |
| B3 | Out3 | 1 | 0 | 13.077 | 45 |
| B4 | Out4 | 1 | 0 | 13.077 | 45 |
| B5 | Out5 | 1 | 0 | 13.077 | 45 |
| B6 | Out6 | 1 | 0 | 13.077 | 45 |
| B7 | Out7 | 1 | 0 | 13.077 | 45 |
| B8 | Out8 | 1 | 0 | 13.077 | 45 |
| B9 | Out9 | 1 | 0 | 13.077 | 45 |
| B10 | Out10 | 1 | 0 | 13.077 | 45 |
| B11 | Out11 | 1 | 0 | 13.077 | 45 |
| B12 | Out12 | 1 | 0 | 13.077 | 45 |
| B13 | Out13 | 1 | 0 | 13.077 | 45 |
| B14 | Out14 | 1 | 0 | 13.077 | 45 |
| B15 | Out15 | 1 | 0 | 13.077 | 45 |

## Graphs
![Sine measured vs intended](runtime-truth-value-usability-assets/axis-sine-measured-vs-intended.svg)
![Sharp-step sine measured vs intended](runtime-truth-value-usability-assets/axis-sharp-step-measured-vs-intended.svg)
![Math-stage stress measured vs intended](runtime-truth-value-usability-assets/axis-math-stage-stress-measured-vs-intended.svg)

## Interpretation
- Stage values are now present in `runtime_frame.axis_stage_values` and are generated from the existing `AxisStackResult`; the focused regression verifies no second pipeline pass.
- Axis value truth is available at Raw Input, Center Conditioning, Curve / Shape, Base Output Limits, Filtering, Mode Modifiers, Rule Injections, and Final Output for every axis.
- The bridge reports `runtime_context_changed` rebuilds on every simulated sample, so stateful filtering diverges from the expected continuous pipeline response during sine and step tests.
- The current output intent path still uses recovered static axis routing; the temporary mapping swap did not move output intent values to the swapped targets.
- Button input telemetry sees B1-B15, but the runtime output intent does not drive mapped output buttons true.
- The dedicated stress input covers every named math parameter except active hysteresis transitions; the stack reports hysteresis configuration, but this run did not observe `hysteresis_active=true`.
- Real vJoy write calls can be accepted when enabled, but the current product path does not expose a vJoy readback channel; this report distinguishes write-call proof from readback proof.

