# Phase 10C - Helm Guided Review and Apply/Revert UX Polish

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Scope: Helm assistant overlay UX/workflow polish only

## Summary

Phase 10C improves Helm's guided review, recommendation selection, apply, and revert flow. The assistant still launches from the top-right ASSISTANT cluster as a large overlay/modal and still uses the existing cards:

- What's wrong?
- What I'd change
- What I found
- Apply / Revert

The work keeps Helm deterministic, local, reversible, and in-memory only.

## Guided Review Flow

After analysis, Helm now shows a review summary with:

- symptom confidence;
- recommendation group count;
- selected-change count;
- affected axes;
- expected outcome summary;
- risk summary;
- in-memory-only reminder.

Example copy:

- `I found 2 tuning groups affecting 5 parameters.`
- `5 changes are selected.`
- `Expected result: smoother combat recovery with less sluggish yaw response.`
- `Risk: moderate; these are reversible and not saved yet.`
- `In-memory only. Save Workspace is still required to keep them.`

Recommendations are clearly staged before apply. Nothing is applied until the user presses Apply Selected Changes.

## Recommendation Selection

Recommendation group selection is now active:

- group checkboxes select or deselect every diff in the group;
- individual diff checkboxes remain available;
- selected counts update immediately;
- Apply Selected Changes is inactive when no diffs are selected.

Each group shows:

- title;
- confidence;
- selected state;
- affected parameter count;
- expected outcome;
- risk;
- compact `Why?` disclosure;
- list of diffs.

## Diff Display

Each diff row/card now shows:

- axis and parameter label;
- section/category;
- before value;
- after value;
- delta;
- reason;
- expected outcome;
- confidence;
- risk;
- selected state;
- applied state.

Values remain exact and human-readable. Helm does not show raw internal object dumps.

## Apply Behavior

Apply Selected Changes:

- applies selected diffs only;
- updates only the in-memory workspace draft;
- marks the workspace unsaved through the existing shell dirty-state path;
- records the applied batch for revert;
- never saves to `hotas_bridge_config_v3.json`;
- never claims runtime tuning or live output changes.

After apply, Helm uses truthful copy:

- `Applied N changes in memory.`
- `Save Workspace is still required to keep them.`
- `You can revert the last Helm batch.`

## Revert Behavior

Revert Last Helm Changes:

- restores exact before values from the most recent applied Helm batch;
- updates the workspace draft in memory;
- marks the workspace unsaved through the same draft path;
- is safe when no Helm batch exists.

Empty-state copy:

- `There isn't a Helm batch to revert yet.`

Successful copy:

- `Reverted the last Helm batch. The workspace is back to the prior draft values.`

Revert does not touch disk.

## Follow-Up UX

Follow-up-required symptoms now render deterministic answer choices before confident diffs are staged. The user can answer locally, press Analyze again, and Helm narrows the deterministic recommendation path.

No external AI, cloud service, or freeform chat path is used.

## Findings Display

The What I found card now reinforces the evidence boundary:

- Helm uses workspace values only.
- Live hardware analysis is not active.
- Findings are tuning/workspace-focused.
- Runtime truth is not inflated into output verification.

Examples:

- `Yaw combat scale is lower than pitch, so yaw may feel held back in combat.`
- `Yaw combat slew values are very low, so reversals and same-direction motion may both feel sticky.`
- `I'm using workspace values only; live hardware analysis is not active.`

## Preserved Boundaries

Phase 10C does not add:

- Help / Docs;
- Perf / Diagnostics;
- Live Overlay;
- Flight Recorder;
- real HOTAS polling;
- live physical input streaming;
- vJoy writes;
- output verification;
- automatic Bridge launch;
- UI-launched child process;
- service install;
- login auto-start;
- tray manager;
- installer launch;
- StartBridge/StopBridge/RestartBridge behavior;
- real process scanner;
- real runtime activation;
- cloud AI or LLM integration;
- conditional-rule auto-editing;
- auto-save.

Conditional rules remain untouched by Helm. Save Workspace remains the only persistence action.

## Current Runtime Truth

Current conservative runtime truth remains:

- Runtime truth: `blocked_missing_device`
- Bridge lifecycle: `Simulated`
- HOTAS discovery: `no_supported_device` unless read-only discovery sees a supported device
- `output_verified`: `false`
- Full Live Runtime Ready: `false`

## Verification

Phase 10C verification commands:

- `python -m pytest tests\test_phase10c_helm_guided_review_apply_revert.py` - 8 passed
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed
- `python -m pytest tests\test_phase10a_helm_overlay_foundation.py` - 6 passed
- `python -m pytest tests\test_phase10b_helm_intelligence_expansion.py` - 7 passed

Final verification was run after documentation updates:

- `python -m pytest` - 214 passed
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed
- `python -m pytest tests\test_phase10a_helm_overlay_foundation.py` - 6 passed
- `python -m pytest tests\test_phase10b_helm_intelligence_expansion.py` - 7 passed
- `python -m pytest tests\test_phase10c_helm_guided_review_apply_revert.py` - 8 passed
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed
- `python -m bridge_app.main --once` - passed
- `python -m bridge_app.main --run-for-ms 250` - passed
- `python -m bridge_app.main --status` - passed, `lifecycle=Simulated truth=blocked_missing_device output_verified=False`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; HOTAS Not Connected, vJoy Detected, Full Live Runtime Ready false
- `git diff --check` - passed

## Deferred

Deferred work remains:

- Help / Docs internals;
- Perf / Diagnostics;
- Live Overlay;
- Flight Recorder;
- live runtime analysis;
- live telemetry tuning;
- automatic profile optimization;
- cloud AI or LLM integration;
- voice interaction;
- conditional rule auto-editing;
- auto-save;
- real hardware observation;
- runtime process management.
