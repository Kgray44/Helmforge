# Phase 3 Tuning Math and Signal Pipeline Report

Status: Phase 3 implemented, refreshed after Phase 2B, and verified.

## Scope

Phase 3 provides the shared-core math and signal-processing foundation for HelmForge - HOTAS Control Panel V3. The pipeline is UI-independent, Bridge-ready, and runs without PySide6, HOTAS hardware, vJoy writes, or driver installation.

Implemented modules:

- `shared_core/math/curves.py`
- `shared_core/math/deadzone.py`
- `shared_core/math/filtering.py`
- `shared_core/math/stack.py`
- `shared_core/math/pipeline.py`

Phase 3 does not implement real HOTAS polling, real vJoy writes, output verification, UI pages, overlays, recorder logic, Helm assistant logic, or installer actions.

## Current Runtime Truth

Precheck before this Phase 3 refresh:

- Thrustmaster driver/software detected: yes, `T.Flight Hotas drivers`
- vJoy detected: yes, `C:\Program Files\vJoy\x64\vJoyInterface.dll`
- HOTAS device detected: no, because the controller is currently disconnected
- Runtime mode: `simulated`
- Runtime truth: `blocked_missing_device`
- Output writes verified: `false`
- Full Live Runtime Ready: false

Post-implementation truth remains the same. Phase 3 does not poll hardware or verify/write vJoy output.

If the HOTAS is later plugged in while output writes remain unverified, the expected runtime truth is `detected_unverified`.

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

Each stage result includes stage name, input value, output value, delta, active flag, explanation text, metadata, and injected rule names where applicable.

## Formulas Used

Centered S-curve:

```text
y = (1-k)x + kx^3
```

`k = 0` behaves like a linear pass-through. The helper clamps inputs to the normalized `-1..1` signal range and preserves odd symmetry for centered axes.

Output limiting:

```text
limited = clamp(value * output_scale, -max_output, +max_output)
```

Linear reference data is generated independently as true `y=x` pairs and does not reuse transformed curve data. Tests protect this graph-reference behavior.

One-sided/J-curve throttle support exists as `one_sided_curve()`, but it is not wired into default stack behavior until throttle-specific runtime/UI requirements are reviewed.

## Deadzone and Hysteresis

Centered deadzone zeroes values inside the configured threshold. Values outside the threshold are remapped so full stick travel can still reach full output:

```text
remapped = (abs(x) - deadzone) / (1 - deadzone)
```

Anti-deadzone then lifts the first post-deadzone output:

```text
remapped = anti_deadzone + remapped * (1 - anti_deadzone)
```

The original sign is restored after remapping. Edge cases such as `deadzone >= 1.0` safely produce zero output.

Hysteresis is represented as a state-aware threshold hook. When previous output is zero, the exit threshold can be raised by `hysteresis`; when previous output is nonzero, the return threshold can be lowered by `hysteresis`.

## Filtering and Slew

Filtering chooses alpha from center/edge settings based on input magnitude:

```text
alpha = center_alpha + (edge_alpha - center_alpha) * abs(target)
smoothed = previous + (target - previous) * alpha
```

Then same-direction or reverse-direction slew limiting clamps the delta from the previous output. Reverse direction is detected when the previous output sign and requested delta oppose each other.

Diagnostics include alpha, alpha region, slew path, slew limit, whether slew was applied, target, smoothed value, and previous output.

## Mode Modifiers

Phase 3 uses Phase 2 models:

- precision mode applies `AxisTuning.precision_scale`;
- combat mode applies combat S-curve and `AxisCombatProfile.combat_scale`;
- precision + combat overlap uses the recovered `multiply` stack mode.

Exact button activation and gating remain runtime/UI responsibilities. Phase 3 only implements the math when `ModeState` marks precision or combat active.

## Rule Injection Placeholder

The stack includes a `Rule Injections` stage. Disabled rules are reported in metadata and do not affect output. Enabled rule evaluation remains deferred; the stage can carry enabled rule names later without pretending evaluation exists now.

## Bridge Seam

`shared_core/math/pipeline.py` adds the explicit future-Bridge seam:

- `WorkspaceSignalPipeline`
- `SignalPipelineState`
- `WorkspaceSignalPipelineResult`

The future Bridge can hold a `WorkspaceSignalPipeline`, keep a `SignalPipelineState` between samples, and call:

```python
result = pipeline.process(raw_axis_values, mode_state=mode_state, state=previous_state)
next_state = result.state
final_axes = result.final_output_values
```

This seam imports no PySide6, no `v3_app`, no vJoy adapter, and no hardware discovery code.

## Simulation Integration

Simulation runtime is wired through `WorkspaceSignalPipeline`. Simulated raw axis values remain labeled simulated, and final output values now come through the same shared-core stack that the future Bridge can call.

Runtime truth behavior is unchanged: missing HOTAS/vJoy or unverified output still reports truthful simulation/detected-unverified states rather than fake live support.

## Assumptions

- Phase 2 numeric defaults remain conservative placeholders where recovered exact values were unknown.
- Combat mode math applies combat curve/scale after filtering as part of the Mode Modifiers stage.
- Hysteresis needs prior output state for full runtime behavior; Phase 3 exposes the hook and tests center-exit behavior.
- The future Bridge will own real-time mode-state derivation from buttons/hats. Phase 3 only consumes a `ModeState`.

## Deferred

- Real HOTAS polling.
- Real vJoy writes.
- Output write verification.
- Driver installation or installer launch.
- Full conditional rule evaluation.
- UI pages and graph rendering.
- Telemetry streaming from a real Bridge process.
- Helm assistant analysis.
- Flight Recorder and Live Overlay behavior.

## Commands Run

Prechecks:

- `git status --short`
- `git remote -v`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- runtime truth probe via Python

TDD and implementation:

- `python -m pytest .\tests\test_phase3_tuning_math_pipeline.py -k workspace_signal_pipeline`
- `python -m pytest .\tests\test_phase3_tuning_math_pipeline.py`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- final runtime truth probe via Python

## Verification Results

Red test check:

- `python -m pytest .\tests\test_phase3_tuning_math_pipeline.py -k workspace_signal_pipeline`
- Initial result before implementation: failed because `shared_core.math.pipeline` did not exist.

Focused Phase 3 test:

- `python -m pytest .\tests\test_phase3_tuning_math_pipeline.py`
- Result: `15 passed`

Full suite:

- `python -m pytest`
- Result: `57 passed`

Minimal app smoke:

- `python -m v3_app.main --smoke-exit-ms 250`
- Result: exit code `0`

Runtime setup dry-run:

- Thrustmaster driver/software detected.
- vJoy detected.
- HOTAS not connected.
- No installers launched.
- Full Live Runtime Ready remains false.

Final runtime truth probe:

- Driver detected: true, `T.Flight Hotas drivers`
- Mode: `simulated`
- Truth: `blocked_missing_device`
- Input: `missing`
- Output: `vjoy_detected`
- Output backend: `C:\Program Files\vJoy\x64\vJoyInterface.dll`
- Output writes verified: `false`
- Labels: `Thrustmaster Driver Detected | HOTAS Not Connected | vJoy Detected | Simulation Mode Active`
