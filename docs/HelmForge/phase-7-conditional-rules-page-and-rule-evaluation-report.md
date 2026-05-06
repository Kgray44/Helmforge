# Phase 7 Conditional Rules Page And Rule Evaluation Report

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Config schema: `hotas_bridge_config_v3.json`

## Scope

Phase 7 replaces the Conditional Rules placeholder with a screenshot-guided rules page and adds UI-independent shared-core rule evaluation for the recovered default rule. It does not implement real HOTAS polling, vJoy output writes, output verification, installer launch, Bridge service behavior, Effective Response Stack internals, Live Monitor internals, overlays, or Helm automation.

## Precheck Runtime Truth

Current local precheck state:

- Thrustmaster driver/software: detected.
- HOTAS device: not connected.
- vJoy backend: detected.
- Runtime mode: `simulated`.
- Runtime truth: `blocked_missing_device`.
- Output writes verified: `false`.

## Screenshots Inspected

- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/07 Conditional Rules/v2-conditional-rules_final-rule-list-detail-disabled-rule.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/07 Conditional Rules/legacy-conditional-rules_initial-v2-draft-disabled-rule-detail.png`
- `HOTAS Control Panel Forensic Spec Set/04-conditional-rules-system.md`

## Screenshot Fidelity Notes

Matched elements:

- Page title: `Conditional Rules`.
- Recovered copy: `Build responsive modifier rules, track their live state, and see exactly where they inject into the response stack.`
- Four status chips: total rules, active, blocked, disabled.
- Action row: `Add Rule`, `Edit Selected`, `Duplicate`, `Enable`, `Delete`.
- Left `Rule List` card.
- Right `Rule Detail` card.
- Lower `Rule Logic` card with recovered explanatory copy.
- Recovered default rule: `Yaw 0.75 | Roll > 0.35`.
- Recovered detail sentence: `Targets Yaw. Watches Roll Final Output > 0.35. Set Output Scale.`

Intentional deviations:

- Branding stays HelmForge / HOTAS Control Panel V3 instead of the recovered V2 window title.
- The detail card includes grouped editable fields for `Action`, `When`, and `Condition` so Phase 7 is functional rather than read-only.
- Runtime labels show simulated/blocked truth and output verification status instead of any live claim.

Remaining visual gaps:

- The final pixel tuning of row widths, detail-card scroll behavior, and editor density can be refined during later page polish.
- Future active/inactive live animation is deferred until the Bridge publishes live rule telemetry.

## Rule Model And Evaluation Decisions

Added `shared_core/rules/evaluator.py` with UI-independent models and helpers:

- `RuleStatus`: `Disabled`, `Inactive`, `Active`, `Blocked`.
- `RuleEvaluationContext`: stage/axis signal values for evaluator input.
- `RuleEvaluationResult`: status, applies flag, blocked reason, target/action fields, injection stage, summary, and metadata.

Supported in Phase 7:

- Measure: `absolute`, `signed`, `raw`.
- Comparators: `greater than`, `less than`, `equal`, `approximately`, `between`, `range`.
- Operations represented: `Set`, `Add`, `Multiply`.
- Implemented stack effect: `Output Scale` at `Base Output Limits`.

Unsupported or invalid rules report `Blocked` and do not apply.

## Example Rule Behavior

Recovered default rule:

- Title: `Yaw 0.75 | Roll > 0.35`
- Enabled by default: `False`
- Target axis: `Yaw`
- Parameter: `Output Scale`
- Operation: `Set`
- Value: `0.75`
- Injects at: `Base Output Limits`
- Reference axis/stage: `Roll` / `Final Output`
- Measure/comparator/threshold: `absolute` / `greater than` / `0.35`

Behavior:

- Disabled: reports `Disabled`, does not change output.
- Enabled and absolute Roll final output `> 0.35`: reports `Active` and can set Yaw output scale to `0.75`.
- Enabled and absolute Roll final output `<= 0.35`: reports `Inactive`, does not change output.
- Invalid axis/parameter/comparator/stage/value: reports `Blocked`, does not crash.

## Pipeline And Stack Injection Seam

The shared-core workspace pipeline now evaluates rules in a baseline pass, then passes evaluation results into each target axis stack. The recovered example is applied at the `Base Output Limits` stage for Yaw and the `Rule Injections` stage carries metadata for future Effective Response Stack display.

This remains a Bridge-ready pure shared-core seam:

- no PySide6 imports,
- no vJoy imports,
- no direct hardware access,
- deterministic tests.

## Conditional Rules UI Behavior

The page is registered in the Phase 4 shell and replaces the placeholder. Actions now behave as follows:

- `Add Rule`: creates a disabled safe draft rule.
- `Edit Selected`: focuses the grouped detail editor.
- `Duplicate`: duplicates selected rule and keeps the copy disabled.
- `Enable` / `Disable`: toggles the selected rule enabled state.
- `Delete`: removes the selected rule.

Editable fields update the in-memory workspace draft and mark the shell unsaved:

- title,
- target axis,
- parameter,
- operation,
- value,
- injection stage,
- mode gate,
- buttons,
- button test,
- reference axis,
- reference stage,
- measure,
- comparator,
- threshold,
- threshold high.

## Workspace Save/Revert Behavior

Rule edits are staged in memory through the existing shell workspace draft. `Save Workspace` writes to the configured V3 path, and `Revert` restores the last saved/imported workspace. Tests cover round-trip rule persistence through a temp `hotas_bridge_config_v3.json`.

## Deferred

- Full advanced conflict ordering semantics.
- Full mode/button gate runtime evaluation.
- UI confirmation dialog for delete.
- Effective Response Stack page rendering of rule injection cards.
- Bridge-published live active/inactive rule telemetry.
- Helm rule-context analysis.
- Real HOTAS polling and vJoy writes.

## Commands Run

- `git status --short`
- `git remote -v`
- `python -m pytest`
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- runtime truth probe via `build_runtime_preflight_status()`
- `Get-ChildItem -Path 'HOTAS Control Panel Forensic Spec Set\Recovered PNG Evidence' -Recurse -File ...`
- `Get-Content -Path 'HOTAS Control Panel Forensic Spec Set\04-conditional-rules-system.md'`
- `python -m pytest tests\test_phase7_rule_evaluation.py tests\test_phase7_conditional_rules_page.py`
- `python -m pytest tests\test_phase3_tuning_math_pipeline.py tests\test_phase4_app_shell.py tests\test_phase6b_mapping_editor_persistence.py tests\test_phase7_rule_evaluation.py tests\test_phase7_conditional_rules_page.py`

## Verification Results

Pre-implementation:

- Full suite before changes: `87 passed`.
- Smoke launch before changes: exited cleanly.
- Runtime setup dry run: HOTAS not connected, vJoy detected, no installers launched.

Phase 7 focused verification:

- New tests were first run before implementation and failed on missing `shared_core.rules`.
- Rule/page focused tests after implementation: `14 passed`.
- Focused integration slice after implementation: `42 passed`.

Final verification:

- Full suite after implementation: `102 passed`.
- Minimal app smoke after implementation: exited cleanly with `python -m v3_app.main --smoke-exit-ms 250` and `QT_QPA_PLATFORM=offscreen`.
- Runtime setup dry run after implementation: HOTAS not connected, vJoy detected, no installers launched.
- Runtime truth after implementation: `blocked_missing_device`.
- Output writes verified after implementation: `false`.
