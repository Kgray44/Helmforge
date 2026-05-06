# Phase 3 Tuning Math and Signal Pipeline Report

Status: Phase 3 implemented and verified.

## Scope

Phase 3 adds the shared-core math and signal-processing foundation for HelmForge. It is UI-independent and runs without PySide6, HOTAS hardware, vJoy, or any driver installation.

Implemented modules:

- `shared_core/math/curves.py`
- `shared_core/math/deadzone.py`
- `shared_core/math/filtering.py`
- `shared_core/math/stack.py`

Phase 3 also wires the simulation runtime through the new stack so simulated raw values now produce processed final outputs while preserving the runtime truth labels from Phase 1.

## Pipeline Stages

The per-axis stack returns structured stage results using recovered Effective Response Stack names:

1. Raw Input
2. Center Conditioning
3. Curve / Shape
4. Base Output Limits
5. Filtering
6. Mode Modifiers
7. Rule Injections
8. Final Output

Each stage result includes:

- stage name,
- input value,
- output value,
- delta,
- active flag,
- explanation text,
- metadata,
- injected rule names where applicable.

## Formulas Used

Centered S-curve:

```text
y = (1-k)x + kx^3
```

This is implemented as an odd-symmetric cubic blend for centered axes. `k = 0` behaves like linear, and values are clamped to the normalized `-1..1` signal range.

Output limiting:

```text
limited = clamp(value * output_scale, -max_output, +max_output)
```

Linear reference data is generated independently as true `y=x` pairs and does not reuse transformed curve data. This specifically protects the recovered linear-reference bug.

## Deadzone and Hysteresis

Centered deadzone zeroes values inside the configured threshold. Values outside the threshold are remapped so full stick travel can still reach full output:

```text
remapped = (abs(x) - deadzone) / (1 - deadzone)
```

Anti-deadzone then lifts the first post-deadzone output:

```text
remapped = anti_deadzone + remapped * (1 - anti_deadzone)
```

Symmetric sign is restored after remapping. Edge cases such as `deadzone >= 1.0` safely produce zero output.

Hysteresis is represented as a state-aware threshold hook. When previous output is zero, the exit threshold can be raised by `hysteresis`; when previous output is nonzero, the return threshold can be lowered by `hysteresis`.

## Filtering and Slew

Filtering uses an alpha chosen from center/edge settings based on input magnitude:

```text
alpha = center_alpha + (edge_alpha - center_alpha) * abs(target)
smoothed = previous + (target - previous) * alpha
```

Then same-direction or reverse-direction slew limiting clamps the delta from the previous output. Reverse direction is detected when the previous output sign and requested delta oppose each other.

The filter step returns diagnostics including alpha, alpha region, slew path, slew limit, whether slew was applied, target, smoothed value, and previous output.

## Mode Modifiers

Phase 3 uses Phase 2 models:

- precision mode applies `AxisTuning.precision_scale`;
- combat mode applies combat S-curve and `AxisCombatProfile.combat_scale`;
- when precision and combat overlap, the recovered `multiply` stack mode multiplies the effects.

Exact future activation/gating remains a runtime/UI responsibility. Phase 3 only implements the math when a `ModeState` says precision or combat is active.

## Rule Injection Placeholder

The stack includes a `Rule Injections` stage. Disabled rules are reported in metadata and do not affect output. Enabled rule evaluation is intentionally deferred; the stage can carry enabled rule names later without pretending evaluation exists now.

## Simulation Integration

Simulation runtime is wired through the stack. Simulated raw axis values remain labeled simulated, but final output values now come from the same per-axis pipeline that future Live Monitor and Effective Response Stack views will inspect.

Runtime truth behavior is unchanged: missing HOTAS/vJoy still reports simulation fallback rather than fake live support.

## Assumptions

- Phase 2 numeric defaults remain conservative placeholders where recovered exact values were unknown.
- Combat mode math applies combat curve/scale after filtering as part of the Mode Modifiers stage.
- Hysteresis needs prior output state for full runtime behavior; Phase 3 exposes the hook and tests the center-exit behavior.
- One-sided/J-curve throttle support is exposed as a helper, but it is not wired into the default stack until throttle-specific UX/runtime requirements are reviewed.

## Deferred

- UI pages.
- Real HOTAS polling.
- Real vJoy writes.
- Driver installation.
- Full conditional rule evaluation.
- Profile-specific math presets beyond Phase 2 defaults.
- Graph rendering.
- Helm assistant analysis.

## Commands Run

- `git status --short`
- `git remote -v`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`
- recovered spec searches in documents 03 and 05
- `python -m pytest tests/test_phase3_tuning_math_pipeline.py`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`
- runtime preflight/setup-label smoke
- stack stage smoke

## Final Verification Results

- `python -m pytest tests/test_phase3_tuning_math_pipeline.py`: `13 passed`.
- `python -m pytest`: `40 passed`.
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`: exit code `0`.
- Runtime preflight/setup-label smoke:
  - mode: `simulated`
  - truth: `simulated`
  - input: `missing`
  - output: `vjoy_missing`
  - labels: `Thrustmaster Driver Unknown | HOTAS Not Connected | vJoy Missing | Simulation Mode Active`
- Stack stage smoke returned:
  - Raw Input
  - Center Conditioning
  - Curve / Shape
  - Base Output Limits
  - Filtering
  - Mode Modifiers
  - Rule Injections
  - Final Output

## Commit and Push

Performed after final verification; commit and push details are reported in the completion response.
