# Phase 5 Mapping Page Report

Status: Phase 5 implemented and verified.

## Scope

Phase 5 replaces the Mapping placeholder with a screenshot-guided Mapping page for HelmForge - HOTAS Control Panel V3.

Implemented in scope:

- Mapping page title, copy, helper text, and status chips.
- Routing Overview card with recovered route counts.
- Live Route Summary card with recovered axis route text.
- Axis Routing table sourced from the Phase 2 workspace defaults.
- Button Routing table sourced from the Phase 2 workspace defaults.
- Hat Routing table sourced from the Phase 2 workspace defaults.
- Runtime Setup / Preflight card with truthful current runtime status.
- Safe Mapping page registration in the Phase 4 shell.
- Dirty-state wiring for invert checkbox edits.

Not implemented in this phase:

- real HOTAS polling;
- real vJoy writes;
- output write verification;
- driver or installer launch;
- full route editing widgets;
- saving edited mappings to disk;
- detailed internals for pages other than Mapping.

## Screenshot Fidelity Notes

Screenshots inspected:

- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/01 Mapping/v2-mapping_final-top-overview-live-route-summary-axis-routing.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/01 Mapping/v2-mapping_final-lower-axis-button-hat-routing.png`

Elements matched:

- Mapping title and page-level structure.
- Recovered page copy and helper-copy meaning, updated from V2 wording to V3.
- Status chip row near the page top.
- Routing Overview card with `Axis Routes`, `Button Routes`, and `Hat Routes`.
- Live Route Summary card with six recovered axis routes.
- Full-width Axis Routing table with recovered columns.
- Lower Button Routing and Hat Routing cards with compact action buttons.
- Dark premium console styling, rounded slate cards, cyan borders, pale helper text, and quiet/action button distinction inherited from the Phase 4 shell.

Intentional deviations:

- Product naming is HelmForge / HOTAS Control Panel V3 instead of recovered V2 labels.
- The page displays current runtime truth rather than screenshot `Idle`.
- Because the current HOTAS is disconnected, the page reports `blocked_missing_device`, `HOTAS Not Connected`, `vJoy Detected`, and output writes unverified.
- A compact Runtime Setup / Preflight card is added between the upper summary cards and Axis Routing so runtime truth is visible without changing the Bridge/UI boundary.

Remaining visual gaps:

- Combo-box-like route editors from the screenshot are represented as read-only table cells for this phase, except invert checkboxes.
- Table row sizing and scroll behavior are functional but not yet pixel-tuned to the recovered Qt screenshots.
- Add/remove/reset route actions are safe status-only placeholders until the edit/persistence phase.

## Mapping Defaults Used

Axis routes:

- Roll: Raw axis 1 -> X -> X(axis1)
- Pitch: Raw axis 2 -> Y -> Y(axis2)
- Throttle: Raw axis 3 -> Z -> Z(axis3)
- Yaw: Raw axis 6 -> RZ -> RX(axis4)
- Aux 1: Raw axis 7 -> SL0 -> RY(axis5)
- Aux 2: Raw axis 8 -> RX -> RZ(axis6)

Route counts:

- Axis Routes: 6
- Button Routes: 15
- Hat Routes: 1

Preserved routing note:

`Battlefield-safe runtime routing still remaps RX / RY / RZ / SL0 behind the scenes when needed.`

## Runtime Truth During Implementation

Current machine state recorded during Phase 5:

- Thrustmaster driver/software detected: yes, `T.Flight Hotas drivers`
- HOTAS detected: no, the controller is disconnected
- vJoy detected: yes, `C:\Program Files\vJoy\x64\vJoyInterface.dll`
- Runtime mode: `simulated`
- Runtime truth: `blocked_missing_device`
- Output writes verified: `false`
- Full Live Runtime Ready: false

The Mapping page displays simulated raw/final values from the existing simulation runtime. These are labeled through runtime status text and do not imply real HOTAS polling or vJoy output.

## Functional Actions

Functional in Phase 5:

- Page switching to Mapping through the Phase 4 shell.
- Axis invert checkbox edits mark the workspace unsaved/dirty in shell state.
- Run Preflight Check button reports the already-known preflight state without installing or polling.
- Use Simulation Mode button reports that simulation remains available.
- Open Runtime Setup Guide opens the local runtime setup doc.
- Open Official Thrustmaster Support Page opens the official support page.

Safe placeholders:

- Add Route.
- Remove Selected.
- Reset 1:1.
- Add Hat.
- Remove Selected.

These placeholder actions update status text only. They do not mutate route data yet.

## Bridge/UI Boundary

The Mapping page reads workspace defaults, runtime preflight truth, and deterministic simulation snapshots. It does not own real-time processing. The future Bridge remains responsible for physical input, shared-core signal pipeline execution, virtual output writes, and telemetry.

No PySide6 imports were added to `shared_core`.

## Commands Run

Prechecks:

- `git status --short`
- `git remote -v`
- `python -m pytest`
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- runtime truth probe via Python

TDD:

- `python -m pytest tests\test_phase5_mapping_page.py`
- Initial result: 7 failed, 1 passed, because the Mapping page module and shell registration did not exist yet.
- Focused final result: 8 passed.

Verification:

- `python -m pytest`
- Result: 71 passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- Result: exit code 0.
- offscreen screenshot sanity render to `%TEMP%\helmforge_phase5_mapping_page.png`

Visual note:

- The offscreen Qt backend on this machine renders text glyphs as boxes, so the screenshot was useful for layout/card/scroll sanity only. Screenshot fidelity is based on direct inspection of the recovered PNG evidence plus widget/layout tests.

## Deferred

Recommended next reviewed phase: build the Modes or Base Tuning page internals, or add persistent Mapping edit support if you want the Mapping page to become editable before moving deeper into tuning UI.
