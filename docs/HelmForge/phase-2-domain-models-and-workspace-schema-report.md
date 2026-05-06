# Phase 2 Domain Models and Workspace Schema Report

Status: Phase 2 implemented and verified.

## Scope

Phase 2 created the UI-independent configuration brain for HelmForge:

- recovered axis definitions,
- mapping defaults,
- mode defaults,
- base tuning schema,
- filtering schema,
- combat profile schema,
- conditional rule schema,
- profile schema,
- workspace state schema,
- JSON save/load persistence.

Phase 2 does not implement UI pages, real HOTAS polling, real vJoy writes, mapping math, tuning math, rule evaluation, recorder, overlay, or Helm assistant behavior.

## Schema Decisions

- Workspace schema version: `3.0.0`.
- V3 config filename: `hotas_bridge_config_v3.json`.
- Recovered V2 config note preserved: `hotas_bridge_config_v2.json`.
- Per-axis configuration maps use canonical axis IDs as keys: `roll`, `pitch`, `throttle`, `yaw`, `aux_1`, `aux_2`.
- Axis records still preserve recovered display names: Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2.
- JSON persistence uses the Python standard library.
- `save_workspace()` refuses to overwrite an existing file unless `overwrite=True`.
- Missing workspace files return a safe default workspace with status `missing_default`.
- Corrupt JSON raises a useful `WorkspaceJsonError` without modifying the source file.

## Default Mapping Summary

Confirmed recovered axis routes:

- Roll: Raw axis 1 -> X -> X(axis1)
- Pitch: Raw axis 2 -> Y -> Y(axis2)
- Throttle: Raw axis 3 -> Z -> Z(axis3)
- Yaw: Raw axis 6 -> RZ -> RX(axis4)
- Aux 1: Raw axis 7 -> SL0 -> RY(axis5)
- Aux 2: Raw axis 8 -> RX -> RZ(axis6)

Additional recovered mapping defaults:

- 15 button routes use 1:1 defaults.
- One hat route is represented: HOTAS Hat 1 -> vJoy POV 1, Up 7, Right 18, Down 19, Left 0, live state Centered.
- Routing note preserved: Battlefield-safe runtime routing may remap RX / RY / RZ / SL0 behind the scenes when needed.

## Mode Defaults

Confirmed recovered defaults:

- Precision Hold Buttons: button 0
- Combat Trigger Buttons: empty
- Combat Zoom/Aim Buttons: button 5
- Combat Extra Buttons: empty
- Precision + Combat Stack Mode: multiply

## Profile Defaults

Confirmed recovered built-in profiles:

- Balanced Flight
- Precision Tracking
- Aggressive Combat
- Smooth Cinematic

Personal/current profile:

- Current Workspace

## Conditional Rule

The recovered example rule is represented but not evaluated:

- Title: `Yaw 0.75 | Roll > 0.35`
- Enabled: false
- Target axis: Yaw
- Parameter: Output Scale
- Operation: Set
- Value: 0.75
- Injection stage: Base Output Limits
- Mode gate: Always
- Reference axis: Roll
- Stage: Final Output
- Measure: absolute
- Comparator: greater than
- Threshold: 0.35

## Confirmed vs Assumed

Confirmed from recovered specs:

- Axis set and ordering.
- Axis mapping routes.
- Mode defaults listed above.
- Profile names.
- Conditional rule visible fields and example values.
- Shared core should own config parsing, profiles, workspace state, and rule/tuning contracts.
- V2 used or displayed `hotas_bridge_config_v2.json`.
- The additional recovered correction note `helm_forge_v_3_naming_and_version_correction_note.md` confirms HelmForge / HOTAS Control Panel V3 naming and `hotas_bridge_config_v3.json` for Phase 2.

Assumed for Phase 2:

- Schema version `3.0.0` is the starting V3 schema because the exact V2 JSON schema is unknown.
- Tuning, filtering, and combat numeric defaults are conservative placeholders where exact shipped values were unknown.
- Per-axis config keys use canonical axis IDs while records retain display names.
- Current workspace source path is `hotas_bridge_config_v3.json`.

## Intentionally Deferred

- Real hardware polling.
- Real vJoy writes.
- Driver installation.
- Tuning math and response calculation.
- Conditional rule evaluation and validation.
- Profile import/export UI.
- UI page polish.
- Effective Response Stack rendering.
- Recorder, overlay, and Helm assistant behavior.

## Commands Run

- `git status --short`
- `git remote -v`
- `git remote add origin https://github.com/Kgray44/Helmforge`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`
- recovered spec searches in documents 03, 04, 05, and 08
- `python -m pytest tests/test_phase2_workspace_schema.py`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`
- workspace save/load round-trip smoke
- runtime preflight/setup-label smoke
- `git status --short`
- `Get-Content "HOTAS Control Panel Forensic Spec Set/helm_forge_v_3_naming_and_version_correction_note.md"`

## Final Verification Results

- `python -m pytest tests/test_phase2_workspace_schema.py`: `10 passed`.
- `python -m pytest`: `27 passed`.
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`: exit code `0`.
- Workspace save/load smoke:
  - schema: `3.0.0`
  - load status: `loaded`
  - source: `hotas_bridge_config_v3.json`
  - axis routes: `6`
  - profiles: Balanced Flight, Precision Tracking, Aggressive Combat, Smooth Cinematic, Current Workspace
- Runtime preflight/setup-label smoke:
  - mode: `simulated`
  - truth: `simulated`
  - input: `missing`
  - output: `vjoy_missing`
  - setup labels: `Thrustmaster Driver Unknown | HOTAS Not Connected | vJoy Missing | Simulation Mode Active`

## Repository Notes

- `origin` was added because no origin remote existed.
- `origin` URL: `https://github.com/Kgray44/Helmforge`
- No other remotes were created.
- No force push or history rewrite was performed.

## Commit and Push

Performed after final verification; commit and push details are reported in the completion response.
