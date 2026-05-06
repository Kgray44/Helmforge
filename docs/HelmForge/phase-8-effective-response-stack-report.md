# Phase 8 Effective Response Stack Report

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Config schema: `hotas_bridge_config_v3.json`

## Scope

Phase 8 replaces the Effective Response Stack placeholder with a screenshot-guided diagnostic page that visualizes one selected axis through the shared-core signal pipeline. It uses Phase 3 stack stages, Phase 7 rule injection metadata, pyqtgraph Raw vs Final data, and simulation/runtime snapshots when live hardware is not active.

This phase does not implement real HOTAS polling, real vJoy writes, output verification, driver installation, installer launch, Bridge service behavior, Live Monitor internals, overlays, or Helm automation.

## Precheck Runtime Truth

Current local precheck state:

- Thrustmaster driver/software: detected.
- HOTAS device: not connected.
- vJoy backend: detected.
- Runtime mode: `simulated`.
- Runtime truth: `blocked_missing_device`.
- Output writes verified: `false`.

## Screenshots And Documents Inspected

- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/08 Effective Response Stack/v2-effective-response-stack_final-stage-cards-raw-center-conditioning.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/08 Effective Response Stack/legacy-effective-response-stack_initial-v2-draft-wide-signal-chain-raw-vs-final.png`
- `HOTAS Control Panel Forensic Spec Set/05-graphs-and-effective-response-stack.md`

## Screenshot Fidelity Notes

Matched elements:

- Page title: `Effective Response Stack`.
- Recovered copy about inspecting one selected axis through shaping, filtering, modes, rule injections, and final output.
- Top control row with axis selector, live/runtime truth pill, Freeze/Resume, Copy Snapshot, and Show All chip.
- Left `Signal Chain` panel with vertical stage cards.
- Stage cards for all recovered stages: Raw Input, Center Conditioning, Curve / Shape, Base Output Limits, Filtering, Mode Modifiers, Rule Injections, Final Output.
- Stage-card values: `IN`, `OUT`, `DELTA`, input/output bars, status chip, explanation line.
- Right `Raw vs Final` graph card with recovered title, copy, and caption.
- Supporting cards: Mode State, Current Stack Summary, Selected Stage, and Rule Driver Values.

Intentional deviations:

- Branding remains HelmForge / HOTAS Control Panel V3 instead of the recovered V2 title.
- The signal flow arrows are simple text arrows for Phase 8; animated flow/pinning is deferred.
- The page uses a low-frequency in-place refresh and hidden-page guard instead of constant animation.

Remaining visual gaps:

- More distinctive flow connectors, green pulse, rule-card styling, and final-output emphasis can be refined later.
- More advanced Show All / Changed Only filtering is not implemented yet.

## Stage Card Implementation

The page creates all eight stage widgets once during construction. Routine refreshes update label text, progress bars, selected-state properties, and graph data in place. Tests verify the stage widget identities remain stable after refresh.

The recovered stages are rendered in shared-core order:

1. Raw Input
2. Center Conditioning
3. Curve / Shape
4. Base Output Limits
5. Filtering
6. Mode Modifiers
7. Rule Injections
8. Final Output

## Graph Implementation

Added `effective_response_stack_graph_data()` in `v3_app/pages/graph_data.py`.

Graph behavior:

- `Raw vs Final` uses raw input on X and effective output on Y.
- The true linear reference is generated independently as `y=x`.
- The effective curve samples the shared-core workspace pipeline for the selected axis.
- The live/simulated marker is plotted at the current selected-axis raw/final pair.
- pyqtgraph updates are scoped to the graph widget.

Tests verify the linear reference remains true `y=x`.

## Rule Injection Metadata Usage

The page does not invent a separate rules path. It reads stack stage metadata produced from Phase 7 evaluator results:

- Disabled rules do not appear as applied.
- Active recovered example rule appears inline when selected axis is Yaw and Roll driver value crosses the threshold.
- Base Output Limits and Rule Injections stage text can show `Yaw 0.75 | Roll > 0.35` and `Set Yaw Output Scale to 0.75`.
- Rule Driver Values shows supporting reference/measured/threshold information without rendering another full axis stack.

## Freeze / Resume Behavior

Freeze captures the current raw values and processed stack result, then keeps rendering that captured result even if refresh is requested. Resume clears the frozen result and returns to simulated/runtime refresh.

Copy Snapshot copies a readable summary to the clipboard with selected axis, runtime truth, output verification state, and stage values.

## Performance / Twitch Prevention

Implemented safeguards:

- Stage widgets are reused and updated in place.
- The page does not rebuild the shell or recreate stage cards during refresh.
- Refresh timer skips work while frozen.
- Refresh timer skips expensive graph/stack work when the page is hidden.
- Graph updates are local to the graph widget.

## Deferred

- Real Bridge telemetry subscription.
- Real HOTAS polling.
- Real vJoy output writes.
- Output verification.
- Animated flow/pulse connectors.
- Stage pinning.
- Changed-only view.
- More detailed rule execution-order labeling.

## Commands Run

- `git status --short`
- `git remote -v`
- `python -m pytest`
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- runtime truth probe via `build_runtime_preflight_status()`
- `Get-ChildItem -Path 'HOTAS Control Panel Forensic Spec Set\Recovered PNG Evidence' -Recurse -File ...`
- `Get-Content -Path 'HOTAS Control Panel Forensic Spec Set\05-graphs-and-effective-response-stack.md'`
- `python -m pytest tests\test_phase8_effective_response_stack_page.py`
- `python -m pytest tests\test_phase7_rule_evaluation.py tests\test_phase8_effective_response_stack_page.py`

## Verification Results

Pre-implementation:

- Full suite before changes: `102 passed`.
- Smoke launch before changes: exited cleanly.
- Runtime setup dry run: HOTAS not connected, vJoy detected, no installers launched.

Focused Phase 8 verification:

- Phase 8 tests first failed on the missing page/helper.
- Phase 8 focused tests after implementation: `9 passed`.
- Phase 7/8 focused slice after implementation: `16 passed`.

Final verification:

- Full suite after implementation: `111 passed`.
- Minimal app smoke after implementation: exited cleanly with `python -m v3_app.main --smoke-exit-ms 250` and `QT_QPA_PLATFORM=offscreen`.
- Runtime setup dry run after implementation: HOTAS not connected, vJoy detected, no installers launched.
- Runtime truth after implementation: `blocked_missing_device`.
- Output writes verified after implementation: `false`.
