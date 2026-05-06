# Phase 6B Mapping Edit, Persistence, and Route Editor Polish Report

Status: Phase 6B implemented and verified.

## Scope

Phase 6B returned to the Mapping page after the core tuning pages and completed the deferred editor and persistence polish:

- combo-box-style route editors for axis, button, and hat routing;
- in-memory workspace/draft updates for safe mapping edits;
- dirty/unsaved state updates in header/footer;
- functional button route Add Route, Remove Selected, and Reset 1:1;
- functional hat route Add Hat and Remove Selected;
- shell-level Save Workspace and Revert wiring for the V3 config path;
- table row/column sizing improvements.

This phase did not implement real HOTAS polling, real vJoy writes, output verification, Bridge service/process work, driver installation, or installer launch.

## Screenshots Inspected

Primary recovered evidence:

- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/01 Mapping/v2-mapping_final-top-overview-live-route-summary-axis-routing.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/01 Mapping/v2-mapping_final-lower-axis-button-hat-routing.png`

These final/polished Mapping screenshots remained the visual target.

## Screenshot Fidelity Notes

Elements matched:

- Mapping title/copy/helper structure.
- Status chip row.
- Routing Overview and Live Route Summary cards.
- Axis Routing table with combo-like editors for Raw Axis, Logical Output, Runtime vJoy, and Invert.
- Button Routing and Hat Routing cards with compact action buttons.
- Lower table editor styling, spacing, and dark control-console tone.

Intentional deviations:

- HelmForge / HOTAS Control Panel V3 naming replaces recovered V2 naming.
- Runtime truth reflects the current machine, not the screenshot `Idle` state.
- `hotas_bridge_config_v3.json` replaces recovered V2 config naming.
- Runtime Setup / Preflight remains visible as a compact truth panel added in Phase 5.

Remaining visual gaps:

- Exact pixel parity for combo-box arrows and table scrollbars can be tuned further after visual review.
- Axis route rows remain fixed to the six recovered axes; add/remove axis routing is intentionally not exposed.
- Import Profile remains status-only until an explicit profile import/export phase.

## Editor Controls Added

Axis Routing:

- Raw Axis options: `Axis 1` through `Axis 8`.
- Logical Output options: `X`, `Y`, `Z`, `RX`, `RY`, `RZ`, `SL0`, `SL1`.
- Runtime vJoy options: `X(axis1)`, `Y(axis2)`, `Z(axis3)`, `RX(axis4)`, `RY(axis5)`, `RZ(axis6)`, `SL0`, `SL1`.
- Invert checkbox updates the workspace draft.

Button Routing:

- HOTAS button options: `B1` through `B15`.
- vJoy button options: `1` through `20`.

Hat Routing:

- HOTAS hat options: `1`, `2`.
- vJoy POV options: `1` through `4`.
- Direction button options: `None`, `0`, and `1` through `20`.

Option ranges are conservative UI-side assumptions based on the recovered schema and the Phase 2 defaults.

## Add, Remove, Reset Behavior

Button Routing:

- Add Route adds the next available unmapped HOTAS/vJoy button pair if a slot exists.
- Remove Selected removes the selected route and marks the workspace dirty.
- Reset 1:1 restores B1-B15 to vJoy 1-15.

Hat Routing:

- Add Hat restores the default HOTAS Hat 1 -> vJoy POV 1 route when no hat route exists.
- If the default hat route already exists, Add Hat reports that additional hats are deferred.
- Remove Selected removes the selected hat route and marks the workspace dirty.

Axis Routing:

- The six recovered core axis rows are preserved and cannot be deleted in this phase.

## Save/Revert Behavior

Save Workspace:

- Writes the current workspace draft to `hotas_bridge_config_v3.json`, or to the test-provided V3 path.
- Uses the existing JSON persistence layer with overwrite only through the explicit Save Workspace action.
- Marks the shell Saved on success.

Revert:

- Reloads the configured V3 workspace path when it exists.
- Otherwise restores the last saved/imported in-memory workspace.
- Rebuilds pages so Mapping editor controls reflect the reverted workspace.

Import Profile:

- Remains status-only and does not silently overwrite current edits.

## Recovered Defaults Preserved

Axis defaults remain:

- Roll: Raw axis 1 -> X -> X(axis1)
- Pitch: Raw axis 2 -> Y -> Y(axis2)
- Throttle: Raw axis 3 -> Z -> Z(axis3)
- Yaw: Raw axis 6 -> RZ -> RX(axis4)
- Aux 1: Raw axis 7 -> SL0 -> RY(axis5)
- Aux 2: Raw axis 8 -> RX -> RZ(axis6)

Route counts at default:

- Axis Routes: 6
- Button Routes: 15
- Hat Routes: 1

Routing note preserved:

`Battlefield-safe runtime routing still remaps RX / RY / RZ / SL0 behind the scenes when needed.`

## Runtime Truth During Implementation

Current machine state recorded during Phase 6B:

- Thrustmaster driver/software detected: yes, `T.Flight Hotas drivers`
- HOTAS detected: no, the controller is disconnected
- vJoy detected: yes, `C:\Program Files\vJoy\x64\vJoyInterface.dll`
- Runtime mode: `simulated`
- Runtime truth: `blocked_missing_device`
- Output writes verified: `false`
- Full Live Runtime Ready: false

## Commands Run

Prechecks:

- `git status --short`
- `git remote -v`
- `python -m pytest`
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- runtime truth probe via Python

Screenshot/design inspection:

- Direct inspection of the two final recovered Mapping screenshots listed above.

TDD:

- `python -m pytest tests\test_phase6b_mapping_editor_persistence.py`
- Initial result: 6 failed, 1 passed because shell save-path support and Mapping route editors/actions did not exist yet.
- Focused final result: 7 passed.

Compatibility checks:

- `python -m pytest tests\test_phase5_mapping_page.py tests\test_phase6b_mapping_editor_persistence.py`
- Result: 15 passed.
- `python -m pytest tests\test_phase6_core_tuning_pages.py`
- Result: 9 passed.

Verification:

- `python -m pytest`
- Result: 87 passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- Result: exit code 0.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- Result: completed, no installers launched.
- offscreen screenshot sanity render to `%TEMP%\helmforge_phase6b_mapping_editor.png`

Visual note:

- The offscreen Qt backend on this machine still renders text glyphs as boxes, but card/table/layout structure rendered. Screenshot fidelity assessment is based on direct recovered PNG inspection plus widget/action/persistence tests.

## Deferred

- Profile import/export and destructive overwrite protection UX.
- Live Bridge reload after saving a workspace.
- Real HOTAS polling and vJoy output writes.
- Conditional Rules page internals.
- More exact pixel tuning after visual review.
