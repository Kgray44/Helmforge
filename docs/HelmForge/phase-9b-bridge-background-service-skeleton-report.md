# Phase 9B Bridge Background Service Skeleton Report

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Date: 2026-05-06

## Scope

Phase 9B created a separate `bridge_app` package that can run independently from the PySide6 UI. The Bridge runs simulation-only ticks, loads the V3 workspace safely, writes Bridge-shaped telemetry JSON, accepts basic command JSON, and exits cleanly in once/bounded modes.

This phase did not implement real HOTAS polling, real vJoy writes, output verification, Windows Service installation, login auto-start, driver installation, installer launching, or UI-to-Bridge wiring.

## Files Created

- `bridge_app/__init__.py`
- `bridge_app/main.py`
- `bridge_app/service.py`
- `bridge_app/state.py`
- `bridge_app/ipc.py`
- `bridge_app/config_loader.py`
- `tests/test_phase9b_bridge_process_skeleton.py`
- `docs/HelmForge/bridge-service-design.md`
- `docs/HelmForge/phase-9b-bridge-background-service-skeleton-report.md`

## Files Changed

- `README.md`
- `pyproject.toml`
- `shared_core/runtime/bridge_contracts.py`
- `docs/HelmForge/bridge-ui-architecture.md`

## Runtime Truth at Precheck

- Thrustmaster driver/software: detected
- HOTAS: detected
- vJoy: detected
- Runtime mode: `simulated`
- Runtime truth: `detected_unverified`
- Output writes verified: `false`
- Full Live Runtime Ready: false

## Bridge Commands

Examples:

```powershell
python -m bridge_app.main --once
python -m bridge_app.main --run-for-ms 250
python -m bridge_app.main --status
python -m bridge_app.main --once --telemetry-path .\tmp\bridge-telemetry.json --command-path .\tmp\bridge-command.json --config-path .\hotas_bridge_config_v3.json --simulate
```

Supported command JSON values:

- `StartBridge`
- `StopBridge`
- `ReloadConfig`
- `RunPreflight`
- `SwitchToSimulation`
- `ClearError`
- `Status`

## Telemetry Path and Format

Default telemetry path:

```text
%TEMP%\helmforge_bridge_telemetry.json
```

Telemetry JSON includes:

- product/Bridge identity;
- lifecycle state;
- runtime truth;
- input/output status;
- `output_verified`;
- active profile;
- raw axes;
- final axes;
- buttons;
- hats;
- mode state;
- rule summary;
- warnings/errors;
- config path/status;
- tick count.

## Sample Telemetry Summary

Expected Phase 9B telemetry:

```text
product_name: HelmForge
technical_subtitle: HOTAS Control Panel V3
bridge_name: HelmForge Bridge
lifecycle_state: Simulated
runtime_truth: detected_unverified
output_status: vjoy_detected
output_verified: false
raw_axes: Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2
final_axes: Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2
```

## Lifecycle States Exercised

- `Starting`
- `Simulated`
- `Stopping`

The shared lifecycle model still contains future real-runtime states, but Phase 9B does not use `LiveVerified`.

## Config Behavior

- Missing config is non-fatal and falls back to a default workspace with a warning.
- Corrupt config is non-fatal and falls back to a default workspace with warning/error telemetry.
- The Bridge does not overwrite missing or corrupt config files.

## Deferred

- UI connection to Bridge telemetry, planned for Phase 9C.
- Real HOTAS input adapter/polling.
- Real vJoy output writes.
- Output verification.
- Windows Service/tray lifecycle.
- Auto-start at login.
- Device plug/unplug wake/safe-idle behavior.
- Final IPC transport.

## Verification

Commands run:

```powershell
git status --short
git remote -v
python -m pytest
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
python -m pytest tests\test_phase9b_bridge_process_skeleton.py
python -m bridge_app.main --once --telemetry-path <temp>\bridge-once.json
python -m bridge_app.main --run-for-ms 250 --telemetry-path <temp>\bridge-run.json
python -m bridge_app.main --status --telemetry-path <temp>\bridge-status.json
```

Focused Phase 9B tests:

```text
9 passed
```

Full regression suite before implementation:

```text
121 passed
```

Full regression suite after implementation:

```text
130 passed
```
