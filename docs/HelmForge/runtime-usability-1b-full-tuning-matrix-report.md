# Runtime Usability 1B Full Tuning Matrix Report

Generated: `20260515T162543Z`
Artifact directory: `artifacts\runtime-tuning-matrix\20260515T162543Z`
Overall status: `passed`

## Executive Result
- Matrix status: passed. No deterministic runtime matrix failures were detected.
- Physical HOTAS proof: deferred/unplugged; this phase intentionally uses simulated/fake input.
- Bridge status: `HelmForge Bridge: lifecycle=LiveVerified truth=live_verified output_verified=True`
- vJoy optional write-call requested: `False`
- vJoy optional write-call available: `True`
- vJoy readback status: not implemented; accepted write calls are not readback proof.

## Runtime Authority Boundary
- UI pages/widgets are not used as runtime calculation authority.
- Bridge/shared_core owns runtime math, rule evaluation, output intent, and writer payload construction.
- v3_app telemetry parsing may display Bridge values, but this probe does not use UI pages as expected-value calculators.

## Parameter Inventory
- Curve modes tested: `s`
- Numeric tuning parameters: `curve_strength, deadzone, anti_deadzone, hysteresis, output_scale, max_output, precision_scale`
- Numeric filtering parameters: `center_alpha, edge_alpha, same_slew_limit, reverse_slew_limit`
- Numeric combat parameters inventoried: `combat_curve, combat_scale, combat_center_alpha, combat_edge_alpha, combat_same_slew, combat_reverse_slew`
- Conditional rule comparators: `greater than, less than, equal, approximately, between, range`
- Conditional rule operations: `Set, Add, Multiply`
- Conditional rule injection targets currently supported: `Output Scale` at `Base Output Limits`

## Generated Counts
| Area | Cases |
|---|---:|
| `runtime_authority_boundary` | 1 |
| `curve_mode_cases` | 67 |
| `numeric_boundary_cases` | 238 |
| `combat_filter_cases` | 8 |
| `axis_mapping_cases` | 6 |
| `button_behavior_cases` | 52 |
| `hat_pov_cases` | 10 |
| `hat_button_mapping_cases` | 15 |
| `mode_cases` | 4 |
| `conditional_rule_cases` | 16 |
| `stage_telemetry_cases` | 6 |
| `pairwise_cases` | 78 |
| `seeded_fuzz_property_cases` | 252 |
| `real_vjoy_optional_cases` | 0 |

## Coverage Summary
| Family | Status |
|---|---|
| `base_tuning` | `covered` |
| `filtering` | `covered` |
| `combat_curve_scale` | `covered` |
| `combat_filter_parameters` | `covered` |
| `modes` | `covered` |
| `conditional_rules` | `covered` |
| `axis_mapping` | `covered` |
| `button_mapping` | `covered` |
| `hat_pov` | `pov_passthrough_and_hat_button_mapping_covered` |

## Known Gaps / Deferred Items
- `vjoy_readback`: No vJoy readback channel exists; accepted write calls are not readback proof.

## Evidence Tables
- `parameter-inventory.json`
- `coverage-summary.json`
- `matrix-results.json`
- `generated-case-counts.json`
- `known-gaps.json`
- `tuning-boundary-table.md`
- `rule-matrix-table.md`
- `mode-matrix-table.md`
- `combat-filter-table.md`
- `hat-button-mapping-table.md`

## Runtime Truth Preservation Statement
- Missing HOTAS does not fail this phase; physical sampling proof remains deferred.
- Real vJoy write-call proof, when requested and available, remains separate from readback proof.
- Full Live Runtime Ready and Bridge lifecycle semantics were not loosened.
- No UI redesign, Live Monitor performance work, animations, Flight Recorder work, game injection, graphics hooking, cloud AI/LLM behavior, or auto-save behavior was added by this probe.
