# Phase 6 Core Tuning Pages Report

Status: Phase 6 implemented and verified.

## Scope

Phase 6 replaces these placeholders with screenshot-guided configuration pages:

- Modes
- Base Tuning
- Filtering
- Combat Profile
- Profiles

The pages read the Phase 2 workspace schema and use Phase 3 math/data generation for graph previews. They do not implement real HOTAS polling, vJoy output writes, output verification, driver installation, Conditional Rules internals, Effective Response Stack, Live Monitor internals, Helm, recorder, or overlay behavior.

## Screenshots Inspected

Primary recovered evidence:

- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/02 Modes/v2-modes_final-precision-combat-live-state-notes.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/03 Base Tuning/v2-base-tuning_final-linear-and-adjusted-curves-full-window.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/04 Filtering/v2-filtering_final-step-response-preview.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/05 Combat Profile/v2-combat-profile_final-response-preview-guidance.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/06 Profiles/v2-profiles_final-library-profile-detail-setup-summary.png`

Legacy draft screenshots in those folders were inventoried but not used as the primary visual target.

## Screenshot Fidelity Notes

Elements matched:

- Modes: Precision Mode, Combat Mode, Live Mode State, Mode Notes card grid.
- Base Tuning: Mapped Axes card, Parameters card, Response Preview graph, Live Snapshot, Guidance.
- Filtering: same recovered tuning layout with Step Preview graph and filtering parameters.
- Combat Profile: same recovered tuning layout with Combat response preview and Caution guidance.
- Profiles: Profile Library, Profile Detail, Setup Summary, Profile Feel, Profile Actions.
- Dark console surface, rounded cards, pale labels, cyan graph/accent lines, and compact action buttons inherited from Phase 4/5 styling.

Intentional V3 deviations:

- Product/config naming uses HelmForge, HOTAS Control Panel V3, and `hotas_bridge_config_v3.json`.
- Runtime status reflects the current machine: HOTAS disconnected, vJoy detected, output unverified.
- Empty combat trigger/extra lists are also labeled `Not configured` so the recovered defaults are explicit.

Remaining visual gaps:

- Parameter fields are editable-looking text fields and mark the workspace dirty, but they do not yet mutate and persist the frozen workspace model.
- Axis selection is shown visually but not interactive yet.
- Profiles import/export/duplicate/rename/delete actions are status-only placeholders.
- Graphs are functional pyqtgraph previews, but exact pixel tuning and legends can be refined after page review.

## Graph Implementation Notes

Created pure UI-side graph data helpers in `v3_app/pages/graph_data.py`:

- `base_response_preview_data()` uses Phase 3 deadzone, S-curve, and output-limit math.
- `filtering_step_preview_data()` uses Phase 3 `step_filter()` with center/edge alpha and same/reverse slew limits.
- `combat_response_preview_data()` compares the base response against combat curve/scale behavior.

The Base Tuning graph uses `linear_reference_points()` from shared core, and tests prove the linear reference remains true `y=x`.

Created `v3_app/pages/graph_widgets.py` for pyqtgraph-backed dark previews. This remains in `v3_app`; no PySide6 or pyqtgraph dependency was added to `shared_core`.

## pyqtgraph Dependency Status

Precheck found `pyqtgraph` missing from the active Python environment even though it was declared in `pyproject.toml`.

Install command run:

```powershell
python -m pip install -e .
```

Result:

- Installed editable `helmforge`.
- Installed `pyqtgraph 0.14.0`.
- PySide6 and pytest were already installed.

## Runtime Truth During Implementation

Current machine state recorded during Phase 6:

- Thrustmaster driver/software detected: yes, `T.Flight Hotas drivers`
- HOTAS detected: no, the controller is disconnected
- vJoy detected: yes, `C:\Program Files\vJoy\x64\vJoyInterface.dll`
- Runtime mode: `simulated`
- Runtime truth: `blocked_missing_device`
- Output writes verified: `false`
- Full Live Runtime Ready: false

## Functional Edits and Placeholder Actions

Functional:

- Shell navigation now uses real pages for Modes, Base Tuning, Filtering, Combat Profile, and Profiles.
- Modes, Base Tuning, Filtering, and Combat Profile parameter text edits mark the workspace Unsaved in shell state.
- Base Tuning, Filtering, and Combat Profile previews render pyqtgraph data from the current workspace defaults.

Placeholders/status-only:

- Axis selection is display-only.
- Profile actions: Save Current As New, Import JSON, Duplicate, Export JSON, Use This Profile, Rename, Delete.
- Edits are in-memory UI draft markers only; save/revert persistence remains shell-level and deferred.

## Commands Run

Prechecks:

- `git status --short`
- `git remote -v`
- `python -m pytest`
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- pyqtgraph import probe
- runtime truth probe via Python

Dependency setup:

- `python -m pip install -e .`

Screenshot/design inspection:

- Direct inspection of the final recovered Modes, Base Tuning, Filtering, Combat Profile, and Profiles screenshots listed above.

TDD:

- `python -m pytest tests\test_phase6_core_tuning_pages.py`
- Initial result: 8 failed, 1 passed because the five page modules and shell routes did not exist yet.
- Focused final result: 9 passed.

Verification:

- `python -m pytest`
- Result: 80 passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- Result: exit code 0.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- Result: completed, no installers launched.
- offscreen screenshot sanity renders:
  - `%TEMP%\helmforge_phase6_core_pages.png`
  - `%TEMP%\helmforge_phase6_base_tuning.png`

Visual note:

- The offscreen Qt backend on this machine still renders text glyphs as boxes, but graph/card/layout structure rendered. Screenshot fidelity assessment is based on direct recovered PNG inspection plus widget/data tests.

## Deferred

Recommended next reviewed phase: Conditional Rules page internals, because the workspace schema and rule placeholder already exist and it naturally precedes Effective Response Stack.
