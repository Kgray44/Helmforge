# Phase 1 Runtime Preflight Report

Status: Phase 1 runtime preflight foundation implemented and verified.

Scope:

- Verify Phase 0 cleanup before starting.
- Initialize local git repository because the folder was not yet a repository.
- Add typed runtime status models.
- Add safe input and vJoy/output detection placeholders.
- Add deterministic and animated simulation runtime.
- Add runtime bridge interface that selects simulation fallback when live runtime is missing or unverified.
- Surface preflight status in the minimal PySide6 app.
- Add tests for missing runtime pieces, simulation snapshots, fuzzy device detection, and no fake full-live claims.
- Document runtime preflight and the Thrustmaster/vJoy separation.

Out of scope:

- Real HOTAS polling.
- Real vJoy writes.
- Driver installation.
- Mapping, tuning math, UI pages, overlay, recorder, or Helm assistant logic.

## Phase 0 Cleanup Verification

- `shared_core/__init__.py` exists and is correctly named.
- `v3_app/__init__.py` exists and is correctly named.
- No `init.py` rename was needed.
- `python -m pytest` passed before Phase 1 changes.
- `python -m v3_app.main --smoke-exit-ms 250` passed in offscreen smoke mode before Phase 1 changes.
- PySide6 imports.
- pytest imports.
- pyqtgraph is declared in `pyproject.toml`.
- pyqtgraph is not installed in the active Python at the time of Phase 1.
- Editable install command to install declared dependencies, including pyqtgraph: `python -m pip install -e .`

## Runtime Truth Behavior

- Missing HOTAS and missing vJoy select `RuntimeMode.SIMULATED` with `RuntimeTruth.SIMULATED`.
- Detected HOTAS with missing vJoy selects `RuntimeMode.SIMULATED` with `RuntimeTruth.BLOCKED_MISSING_DRIVER`.
- Missing HOTAS with detected/unverified vJoy selects `RuntimeMode.SIMULATED` with `RuntimeTruth.BLOCKED_MISSING_DEVICE`.
- Detected HOTAS and detected but unverified output selects `RuntimeMode.SIMULATED` with `RuntimeTruth.DETECTED_UNVERIFIED`.
- `RuntimeMode.FULL_LIVE` is only produced when physical input is detected and output writes are verified.

## Missing Runtime Reporting

- Missing vJoy appears as `OutputStatus.VJOY_MISSING` and is non-fatal.
- Missing HOTAS appears as `InputStatus.MISSING` and is non-fatal.
- Simulation mode is selected by default whenever live input/output is missing or unverified.

## Files Created

- `shared_core/models/__init__.py`
- `shared_core/models/runtime.py`
- `shared_core/runtime/__init__.py`
- `shared_core/runtime/device_discovery.py`
- `shared_core/runtime/vjoy_output.py`
- `shared_core/runtime/hotas_input.py`
- `shared_core/runtime/simulated_runtime.py`
- `shared_core/runtime/runtime_bridge.py`
- `tests/test_phase1_runtime_preflight.py`
- `docs/HelmForge/runtime-preflight-and-vjoy-setup.md`
- `docs/HelmForge/phase-1-runtime-preflight-report.md`

## Files Changed

- `v3_app/main.py`

## Commands Run

- `Get-ChildItem -Force shared_core, v3_app`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`
- PySide6/pytest import and pyqtgraph declaration check
- `git rev-parse --is-inside-work-tree`
- `git init`
- `git status --short`
- `python -m pytest tests/test_phase1_runtime_preflight.py`
- `python -m pytest`
- Runtime preflight status check without injected test data
- Dependency import check for PySide6, pytest, and pyqtgraph
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`

## Final Verification Results

- `python -m pytest`: `10 passed`.
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`: exit code `0`.
- Live preflight check on this machine:
  - mode: `simulated`
  - truth: `simulated`
  - input: `missing`
  - output: `vjoy_missing`
  - detected devices: none
  - detected output backend: none
  - live output writes verified: `False`
- Dependency check:
  - PySide6 imports.
  - pytest imports.
  - pyqtgraph remains missing from the active Python, but is declared in `pyproject.toml`.
  - Editable install command for declared dependencies: `python -m pip install -e .`

## Issues and Assumptions

- The local folder was initialized as a git repository during Phase 1 because it was not already one.
- No remote named `origin` was created.
- Device enumeration is conservative and non-blocking. It uses safe name discovery hooks and treats no match as missing.
- vJoy detection is conservative and never marks output writes verified in Phase 1.
- No driver installation or driver download was attempted.

## Next Recommended Phase

Phase 2 should remain simulation-first and build the first shared configuration/profile schema plus mapping data contracts. Real vJoy writes and real HOTAS polling should remain blocked until the runtime contracts are reviewed.
