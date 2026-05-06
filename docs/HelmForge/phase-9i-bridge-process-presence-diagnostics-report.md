# Phase 9I Bridge Process Presence and Diagnostic Visibility Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Date: 2026-05-06
Scope: read-only process presence hints and conservative lifecycle diagnostics

## Summary

Phase 9I adds UI-side Bridge process presence hints and diagnostic composition. This helps the Live Monitor explain telemetry state, stale/missing files, command acknowledgement state, device discovery, and manual Bridge launch expectations without controlling the Bridge process.

Process presence is a hint, not runtime truth. Fresh Bridge telemetry remains the strongest UI truth surface. The UI still does not start, stop, restart, spawn, install, or manage the Bridge.

## Implementation

New module:

- `v3_app/services/bridge_presence.py`

Added:

- `BridgeProcessPresenceState`
- `BridgeProcessPresenceHint`
- `BridgeProcessPresenceProvider`
- `FakeBridgeProcessPresenceProvider`
- `UnavailableBridgeProcessPresenceProvider`
- `BridgeLifecycleDiagnostics`
- `compose_bridge_lifecycle_diagnostics`
- `build_bridge_diagnostic_copy_text`

Initial process presence states:

- `unavailable`
- `unknown`
- `not_found`
- `maybe_running`
- `seen_but_telemetry_missing`
- `seen_but_telemetry_stale`
- `fresh_telemetry_confirmed`
- `telemetry_invalid`
- `telemetry_error`

The default provider is intentionally unavailable/read-only. A fake provider covers deterministic tests. Phase 9I does not add a Windows process scanner because the phase goal is diagnostic visibility without process lifecycle ownership or fragile inspection dependencies.

## Diagnostic Composition

Diagnostics combine:

- telemetry status: Connected, Missing, Stale, Invalid, Error;
- telemetry age;
- Bridge lifecycle from telemetry;
- runtime truth from telemetry or fallback;
- output verification truth;
- latest command acknowledgement status;
- Phase 9H device discovery status;
- process presence hint.

Example conservative sentences:

- `Bridge telemetry fresh.`
- `Bridge telemetry missing; manual Bridge launch may be required.`
- `Bridge process may be running, but telemetry is missing.`
- `Bridge process may be running, but telemetry is stale.`
- `Bridge telemetry invalid; simulation fallback active.`
- `Supported HOTAS detected; polling not active.`
- `Device discovery only; output verification false.`
- `No supported HOTAS detected.`

Manual launch help text may be displayed:

```powershell
python -m bridge_app.main --run-for-ms 250
```

The UI displays this as guidance only. It does not execute it.

## Live Monitor UI

The Live State card now includes compact diagnostics:

- Bridge telemetry status;
- Bridge lifecycle;
- process hint;
- runtime truth;
- output verified false/true text;
- device discovery status;
- short diagnosis sentence;
- manual launch helper line when telemetry is missing or stale.

No new lifecycle buttons were added. The UI still has only the safe Phase 9D command requests:

- Refresh Bridge Status
- Run Bridge Preflight
- Reload Bridge Config
- Switch to Simulation
- Clear Bridge Error

No Start Bridge, Stop Bridge, Restart Bridge, Install Service, Enable Auto Start, or Verify Output controls were added.

## Safety Boundaries

Phase 9I does not add:

- real HOTAS polling;
- live physical input streaming;
- vJoy writes;
- output verification;
- automatic Bridge launch;
- UI-launched child process;
- Windows Service installation;
- login auto-start;
- tray/background manager implementation;
- installer launch;
- real runtime activation;
- StartBridge/StopBridge/RestartBridge behavior.

Phase 9H discovery remains discovery-only. `supported_device_detected` never implies polling, output verification, or Full Live Runtime Ready.

## Current Runtime Truth

Phase 9I verification recorded:

- Runtime truth: `blocked_missing_device`.
- Output verified: `false`.
- Full Live Runtime Ready: `false`.
- Device discovery: `no_supported_device`.
- Process presence hint: `Unavailable` by default in the UI diagnostic provider.

## Tests Added

New focused tests:

- `tests/test_phase9i_bridge_process_presence_diagnostics.py`

Coverage includes:

- missing telemetry plus unavailable provider;
- missing telemetry plus maybe-running process hint;
- stale telemetry plus process hint;
- invalid telemetry diagnostics;
- fresh telemetry overriding process uncertainty;
- supported-device discovery remaining discovery-only;
- diagnostic copy text;
- Live Monitor compact diagnostic fields;
- absence of Start/Stop/Restart/Service/Auto Start/Verify Output controls;
- unsafe lifecycle commands remain rejected;
- boundary checks for no process spawn, no vJoy write APIs, and no UI imports from Bridge/shared-core.

## Verification

Commands run during Phase 9I:

- `git status --short`
- `git remote -v`
- `python -m pytest tests\test_phase9i_bridge_process_presence_diagnostics.py`
- `python -m pytest tests\test_phase9c_ui_bridge_telemetry_connection.py tests\test_phase9d_ui_bridge_command_seam.py tests\test_phase9e_bridge_command_acknowledgement.py tests\test_phase9f_bridge_lifecycle_health.py tests\test_phase9g_lifecycle_design_docs.py tests\test_phase9h_real_device_discovery_dry_run.py tests\test_phase9i_bridge_process_presence_diagnostics.py`
- `python -m pytest`
- `python -m pytest tests\test_phase9c_ui_bridge_telemetry_connection.py tests\test_phase9d_ui_bridge_command_seam.py tests\test_phase9e_bridge_command_acknowledgement.py tests\test_phase9f_bridge_lifecycle_health.py tests\test_phase9g_lifecycle_design_docs.py tests\test_phase9h_real_device_discovery_dry_run.py`
- `python -m pytest tests\test_phase9i_bridge_process_presence_diagnostics.py`
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- `python -m bridge_app.main --once`
- `python -m bridge_app.main --run-for-ms 250`
- `python -m bridge_app.main --status`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- `git diff --check`

Results:

- Full suite: 180 passed.
- Phase 9C-9H focused slice: 43 passed.
- Phase 9I focused tests: 7 passed.
- UI smoke launch: exit 0.
- Bridge `--once`: exit 0.
- Bridge `--run-for-ms 250`: exit 0.
- Bridge `--status`: `lifecycle=Simulated truth=blocked_missing_device output_verified=False`.
- Runtime setup dry-run: Thrustmaster software detected, vJoy detected, HOTAS not connected.
- Telemetry sample: `runtime_truth=blocked_missing_device`, `device_discovery.status=no_supported_device`, `output_verified=False`, `lifecycle_state=Simulated`.
- `git diff --check`: exit 0.

## Deferred

- real process presence scanner, if later justified;
- tray/background manager;
- automatic Bridge launch;
- UI-owned process lifecycle controls;
- Windows Service;
- login auto-start;
- real HOTAS polling;
- live physical input streaming;
- vJoy writes;
- output verification;
- runtime activation.
