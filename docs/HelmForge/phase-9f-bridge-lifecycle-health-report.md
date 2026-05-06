# Phase 9F - Bridge Lifecycle Presence and Health

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Scope: UI-visible Bridge health, lifecycle presence, and telemetry freshness refinement only

## Summary

Phase 9F improves the UI-visible health model for the existing Bridge telemetry seam. The UI can now distinguish fresh, missing, stale, invalid, and error telemetry with explicit timing details, while stale or unavailable telemetry remains a simulation fallback state.

This phase does not add real HOTAS polling, vJoy writes, output verification, automatic Bridge launch, Windows Service installation, login auto-start, installer launch, tray/background manager work, or real runtime activation.

## Bridge Health States

The UI telemetry client reports:

- `Connected`: telemetry is fresh and usable.
- `Missing`: telemetry file was not found.
- `Stale`: telemetry exists but is older than the stale threshold.
- `Invalid`: telemetry could not be parsed or failed schema validation.
- `Error`: telemetry could not be read.

Only `Connected` is treated as fresh Bridge telemetry. `Missing`, `Stale`, `Invalid`, and `Error` use simulation fallback and must not be presented as live Bridge truth.

## Timing Details

`v3_app/services/bridge_client.py` now exposes:

- telemetry path;
- last read timestamp;
- telemetry generated timestamp when available;
- telemetry age in seconds;
- stale threshold seconds;
- status;
- human-readable reason.

The client supports an injectable clock for deterministic tests.

## Live Monitor UI

The Live Monitor Live State card now includes compact Bridge health text:

- Bridge health state;
- telemetry age;
- runtime truth;
- output verification truth;
- last command status;
- short missing/stale/invalid/error explanation when applicable.

The top Monitor Controls row remains compact. Command controls stay in the Live State card.

## Command Acknowledgement Preservation

Phase 9E request matching remains intact:

- The UI only treats telemetry `last_command` as relevant when `request_id` matches the latest UI-written command.
- Unrelated `last_command` telemetry does not complete the current UI request.
- Stale telemetry does not complete the current UI request.

## Current Runtime Truth

Phase 9F precheck state:

- Thrustmaster driver/software detected: yes.
- HOTAS device detected: no.
- vJoy detected: yes.
- Runtime truth: `blocked_missing_device`.
- Full Live Runtime Ready: false.
- Output writes verified: false.

## Tests Added

Added `tests/test_phase9f_bridge_lifecycle_health.py` covering:

- fresh telemetry health display;
- missing telemetry health display;
- stale telemetry health display;
- invalid telemetry health display;
- telemetry age calculation;
- compact Live Monitor Bridge health details;
- stale telemetry fallback behavior;
- Phase 9E request ID command matching preservation;
- output verification truth remains false;
- Bridge/shared-core dependency boundaries remain UI-free.

## Verification Commands

Required final verification:

```powershell
python -m pytest
python -m pytest tests\test_phase9c_ui_bridge_telemetry_connection.py tests\test_phase9d_ui_bridge_command_seam.py tests\test_phase9e_bridge_command_acknowledgement.py
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
python -m bridge_app.main --once
python -m bridge_app.main --run-for-ms 250
python -m bridge_app.main --status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
git diff --check
```

Results:

- `python -m pytest`: 162 passed.
- `python -m pytest tests\test_phase9c_ui_bridge_telemetry_connection.py tests\test_phase9d_ui_bridge_command_seam.py tests\test_phase9e_bridge_command_acknowledgement.py`: 26 passed.
- UI smoke launch with `QT_QPA_PLATFORM=offscreen`: passed.
- `python -m bridge_app.main --once`: passed.
- `python -m bridge_app.main --run-for-ms 250`: passed.
- `python -m bridge_app.main --status`: `lifecycle=Simulated`, `truth=blocked_missing_device`, `output_verified=False`.
- Runtime setup dry-run: HOTAS Not Connected, vJoy Detected, no installers launched.
- `git diff --check`: passed.

## Deferred

- Real HOTAS polling.
- Real vJoy writes.
- Output verification.
- Automatic Bridge launching.
- Windows Service installation.
- Login auto-start.
- Installer launching.
- Tray/background manager.
- Real runtime activation.
- Final IPC transport.
