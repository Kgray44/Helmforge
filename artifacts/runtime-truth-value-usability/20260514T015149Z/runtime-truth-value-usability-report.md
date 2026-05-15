# Runtime Truth Value Usability Report

Generated: `2026-05-14T01:52:43.789926+00:00`
Overall status: `passed`
Artifact directory: `artifacts\runtime-truth-value-usability\20260514T015149Z`

## Executive Findings
- No value-truth failures were detected in this probe.

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
| Hysteresis | `True` | Stress workspace sets hysteresis=0.04; coverage requires an active hysteresis transition. |
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
| `axis_sine_fake` | `fake` | 180 | 61 | 1.0 | 21.803 | 65.679 | 0.337 | 4.584 | 0.081 | 2.1e-05 | 2.1e-05 |
| `axis_sharp_step_sine_fake` | `fake` | 180 | 61 | 1.0 | 22.135 | 68.495 | 0.34 | 4.181 | 0.075 | 2.6e-05 | 2.6e-05 |
| `buttons_toggle_fake` | `fake` | 45 | 46 | 1.0 | 23.002 | 67.534 | 0.367 | 5.008 | 0.059 | 0.053974 | 0.053974 |
| `math_stage_stress_fake` | `fake` | 96 | 97 | 1.0 | 19.879 | 41.247 | 0.256 | 3.696 | 0.068 | 1e-05 | 1e-05 |
| `mapping_variant_fake` | `fake` | 2 | 3 | 1.0 | 23.745 | 30.416 | 0.173 | 2.324 | 0.044 | 1e-05 | 1e-05 |
| `axis_sine_real_vjoy` | `real_vjoy` | 72 | 73 | 1.0 | 31.628 | 65.213 | 0.267 | 9.66 | 2.787 | 2e-05 | 2e-05 |
| `buttons_toggle_real_vjoy` | `real_vjoy` | 45 | 46 | 1.0 | 33.443 | 94.478 | 0.305 | 11.237 | 4.076 | 0.053974 | 0.053974 |

## Axis Proof
### axis_sine_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 2e-05 | 2e-05 | 21.803 | 60 |
| Pitch | 2.1e-05 | 2.1e-05 | 21.803 | 60 |
| Throttle | 8e-06 | 8e-06 | 21.803 | 60 |
| Yaw | 2e-05 | 2e-05 | 21.803 | 60 |
| Aux 1 | 1.7e-05 | 1.7e-05 | 21.803 | 60 |
| Aux 2 | 1.6e-05 | 1.6e-05 | 21.803 | 60 |
### axis_sharp_step_sine_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 1.7e-05 | 1.7e-05 | 22.135 | 60 |
| Pitch | 2.2e-05 | 2.2e-05 | 22.135 | 60 |
| Throttle | 8e-06 | 8e-06 | 22.135 | 60 |
| Yaw | 2.6e-05 | 2.6e-05 | 22.135 | 60 |
| Aux 1 | 1.3e-05 | 1.3e-05 | 22.135 | 60 |
| Aux 2 | 1.4e-05 | 1.4e-05 | 22.135 | 60 |
### math_stage_stress_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 1e-05 | 1e-05 | 19.879 | 96 |
| Pitch | 1e-05 | 1e-05 | 19.879 | 96 |
| Throttle | 6e-06 | 6e-06 | 19.879 | 96 |
| Yaw | 9e-06 | 9e-06 | 19.879 | 96 |
| Aux 1 | 1e-05 | 1e-05 | 19.879 | 96 |
| Aux 2 | 1e-05 | 1e-05 | 19.879 | 96 |
### mapping_variant_fake
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 9e-06 | 9e-06 | 23.745 | 2 |
| Pitch | 4e-06 | 4e-06 | 23.745 | 2 |
| Throttle | 4e-06 | 4e-06 | 23.745 | 2 |
| Yaw | 1e-05 | 1e-05 | 23.745 | 2 |
| Aux 1 | 3e-06 | 3e-06 | 23.745 | 2 |
| Aux 2 | 5e-06 | 5e-06 | 23.745 | 2 |
### axis_sine_real_vjoy
| Axis | Max final diff vs stateful intended | Max output diff vs mapped intended | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|
| Roll | 1.7e-05 | 1.7e-05 | 31.628 | 72 |
| Pitch | 1.7e-05 | 1.7e-05 | 31.628 | 72 |
| Throttle | 7e-06 | 7e-06 | 31.628 | 72 |
| Yaw | 2e-05 | 2e-05 | 31.628 | 72 |
| Aux 1 | 1.5e-05 | 1.5e-05 | 31.628 | 72 |
| Aux 2 | 1.6e-05 | 1.6e-05 | 31.628 | 72 |

## Button Proof
### buttons_toggle_fake
| Button | Expected output button | Input true observed | Output true observed | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|---:|
| B1 | Out1 | 1 | 1 | 23.002 | 45 |
| B2 | Out2 | 1 | 1 | 23.002 | 45 |
| B3 | Out3 | 1 | 1 | 23.002 | 45 |
| B4 | Out4 | 1 | 1 | 23.002 | 45 |
| B5 | Out5 | 1 | 1 | 23.002 | 45 |
| B6 | Out6 | 1 | 1 | 23.002 | 45 |
| B7 | Out7 | 1 | 1 | 23.002 | 45 |
| B8 | Out8 | 1 | 1 | 23.002 | 45 |
| B9 | Out9 | 1 | 1 | 23.002 | 45 |
| B10 | Out10 | 1 | 1 | 23.002 | 45 |
| B11 | Out11 | 1 | 1 | 23.002 | 45 |
| B12 | Out12 | 1 | 1 | 23.002 | 45 |
| B13 | Out13 | 1 | 1 | 23.002 | 45 |
| B14 | Out14 | 1 | 1 | 23.002 | 45 |
| B15 | Out15 | 1 | 1 | 23.002 | 45 |
### mapping_variant_fake
| Button | Expected output button | Input true observed | Output true observed | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|---:|
| B1 | Out2 | 1 | 1 | 23.745 | 2 |
| B2 | Out1 | 0 | 0 | 23.745 | 2 |
| B3 | Out3 | 0 | 0 | 23.745 | 2 |
| B4 | Out4 | 0 | 0 | 23.745 | 2 |
| B5 | Out5 | 0 | 0 | 23.745 | 2 |
| B6 | Out6 | 0 | 0 | 23.745 | 2 |
| B7 | Out7 | 0 | 0 | 23.745 | 2 |
| B8 | Out8 | 0 | 0 | 23.745 | 2 |
| B9 | Out9 | 0 | 0 | 23.745 | 2 |
| B10 | Out10 | 0 | 0 | 23.745 | 2 |
| B11 | Out11 | 0 | 0 | 23.745 | 2 |
| B12 | Out12 | 0 | 0 | 23.745 | 2 |
| B13 | Out13 | 0 | 0 | 23.745 | 2 |
| B14 | Out14 | 0 | 0 | 23.745 | 2 |
| B15 | Out15 | 0 | 0 | 23.745 | 2 |
### buttons_toggle_real_vjoy
| Button | Expected output button | Input true observed | Output true observed | Avg total latency ms | Writes observed |
|---|---:|---:|---:|---:|---:|
| B1 | Out1 | 1 | 1 | 33.443 | 45 |
| B2 | Out2 | 1 | 1 | 33.443 | 45 |
| B3 | Out3 | 1 | 1 | 33.443 | 45 |
| B4 | Out4 | 1 | 1 | 33.443 | 45 |
| B5 | Out5 | 1 | 1 | 33.443 | 45 |
| B6 | Out6 | 1 | 1 | 33.443 | 45 |
| B7 | Out7 | 1 | 1 | 33.443 | 45 |
| B8 | Out8 | 1 | 1 | 33.443 | 45 |
| B9 | Out9 | 1 | 1 | 33.443 | 45 |
| B10 | Out10 | 1 | 1 | 33.443 | 45 |
| B11 | Out11 | 1 | 1 | 33.443 | 45 |
| B12 | Out12 | 1 | 1 | 33.443 | 45 |
| B13 | Out13 | 1 | 1 | 33.443 | 45 |
| B14 | Out14 | 1 | 1 | 33.443 | 45 |
| B15 | Out15 | 1 | 1 | 33.443 | 45 |

## Graphs
![Sine measured vs intended](runtime-truth-value-usability-assets/axis-sine-measured-vs-intended.svg)
![Sharp-step sine measured vs intended](runtime-truth-value-usability-assets/axis-sharp-step-measured-vs-intended.svg)
![Math-stage stress measured vs intended](runtime-truth-value-usability-assets/axis-math-stage-stress-measured-vs-intended.svg)

## Interpretation
- Stage values are now present in `runtime_frame.axis_stage_values` and are generated from the existing `AxisStackResult`; the focused regression verifies no second pipeline pass.
- Axis value truth is available at Raw Input, Center Conditioning, Curve / Shape, Base Output Limits, Filtering, Mode Modifiers, Rule Injections, and Final Output for every axis.
- Stable-config simulated scenarios preserved one orchestrator context; filtering, slew, and hysteresis state carried across samples.
- Workspace axis mappings are applied to output intent; the temporary Roll/Pitch swap moved values to the swapped vJoy axes without changing the values.
- Button mappings are applied to output intent and writer payloads; B1-B15 press/release checks drive only their mapped output buttons.
- The dedicated stress input covers every named math parameter, including at least one active hysteresis transition.
- Real vJoy write calls can be accepted when enabled, but the current product path does not expose a vJoy readback channel; this report distinguishes write-call proof from readback proof.

