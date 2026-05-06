# Phase 9H Real Device Discovery Dry-Run Report

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Date: 2026-05-06  
Scope: Bridge-owned, read-only HOTAS device discovery dry-run

## Summary

Phase 9H adds a read-only device discovery layer owned by the Bridge. The Bridge can now publish whether a supported HOTAS identity is visible to the operating system through telemetry `device_discovery`.

This phase does not add continuous HOTAS polling, live axis/button streaming from the physical device, vJoy writes, output verification, automatic Bridge launching, Windows Service installation, login auto-start, installer launching, tray/background manager implementation, or real runtime activation.

## Discovery Model

The new discovery model lives in `shared_core/runtime/hotas_discovery.py`.

It adds:

- `DeviceDiscoveryState`
- `HotasDeviceInfo`
- `HotasDiscoveryResult`
- `DeviceDiscoveryBackend`
- `FakeDeviceDiscoveryBackend`
- `WindowsPnpDeviceDiscoveryBackend`
- `discover_supported_hotas`

Discovery status values:

- `not_checked`
- `no_supported_device`
- `supported_device_detected`
- `discovery_error`
- `backend_unavailable`

Discovery payload fields:

- `available`
- `matched`
- `device_name`
- `manufacturer`
- `vendor_id`
- `product_id`
- `serial_number`
- `backend`
- `checked_at`
- `error`
- `warnings`

## Supported Device Matching

The first supported target remains the recovered/known physical target:

- Thrustmaster T-Flight HOTAS One
- Thrustmaster T.Flight Hotas One

The matcher is centralized and conservative. It recognizes the device by known name variants and by the known Thrustmaster USB identity when available:

- vendor ID: `044f`
- product ID: `b68d`

Exact device IDs can be expanded later without spreading matching logic across the codebase.

## Bridge Ownership

The Bridge owns discovery. The PySide6 UI does not scan hardware directly.

Bridge behavior in Phase 9H:

- runs discovery during Bridge ticks;
- runs discovery when preflight/status command handling refreshes runtime status;
- includes `device_discovery` in telemetry JSON;
- updates input preflight truth from supported-device discovery;
- keeps all output verification false.

The Windows backend uses the existing read-only PnP preflight path. If the backend is unavailable or errors, the Bridge reports `backend_unavailable` or `discovery_error` without crashing or activating runtime behavior.

## Telemetry

Bridge telemetry now includes:

```json
{
  "device_discovery": {
    "status": "no_supported_device",
    "available": false,
    "matched": false,
    "device_name": null,
    "manufacturer": null,
    "vendor_id": null,
    "product_id": null,
    "serial_number": null,
    "backend": "windows_pnp",
    "checked_at": "2026-05-06T00:00:00+00:00",
    "error": null,
    "warnings": []
  }
}
```

If a supported HOTAS is detected, telemetry may report `supported_device_detected`, but that means discovery only. It does not mean live polling is implemented, output is verified, or Full Live Runtime Ready is true.

## UI Display

Live Monitor now consumes `device_discovery` from Bridge telemetry and displays compact discovery truth in the Live State card.

Conservative wording examples:

- `HOTAS discovery: not checked`
- `HOTAS discovery: no supported device found`
- `HOTAS discovery: supported device detected`
- `Supported HOTAS detected; polling not active.`
- `Device discovery only; output verification false.`
- `HOTAS discovery: discovery error`
- `HOTAS discovery: backend unavailable`

The UI still treats missing, stale, invalid, or error telemetry as simulation fallback. Stale telemetry is not treated as live Bridge truth.

## Current Runtime Truth

Phase 9H verification on this machine recorded:

- Thrustmaster driver/software: detected.
- vJoy: detected.
- HOTAS: not connected.
- Runtime truth: `blocked_missing_device`.
- Bridge lifecycle status: `Simulated`.
- Device discovery status: `no_supported_device`.
- Output writes verified: `false`.
- Full Live Runtime Ready: `false`.

## Tests Added

New focused tests live in `tests/test_phase9h_real_device_discovery_dry_run.py`.

Coverage includes:

- fake backend returns no device;
- fake backend returns supported HOTAS;
- fake backend returns unsupported device;
- backend unavailable/error status is truthful;
- telemetry includes `device_discovery`;
- runtime truth remains `blocked_missing_device` when no supported device exists;
- output remains unverified even when a supported device is detected;
- Live Monitor displays discovery status without live/output claims;
- Bridge/shared-core boundary stays free of `v3_app`, `PySide6`, and vJoy write APIs.

## Verification

Commands run during the Phase 9H implementation:

- `git status --short`
- `git remote -v`
- `python -m pytest tests\test_phase9h_real_device_discovery_dry_run.py`
- `python -m pytest tests\test_phase9c_ui_bridge_telemetry_connection.py tests\test_phase9d_ui_bridge_command_seam.py tests\test_phase9e_bridge_command_acknowledgement.py tests\test_phase9f_bridge_lifecycle_health.py tests\test_phase9g_lifecycle_design_docs.py tests\test_phase9h_real_device_discovery_dry_run.py`
- `python -m pytest`
- `python -m pytest tests\test_phase9c_ui_bridge_telemetry_connection.py tests\test_phase9d_ui_bridge_command_seam.py tests\test_phase9e_bridge_command_acknowledgement.py tests\test_phase9f_bridge_lifecycle_health.py tests\test_phase9g_lifecycle_design_docs.py`
- `python -m pytest tests\test_phase9h_real_device_discovery_dry_run.py`
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- `python -m bridge_app.main --once`
- `python -m bridge_app.main --run-for-ms 250`
- `python -m bridge_app.main --status`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- `git diff --check`

Results:

- Full suite: 173 passed.
- Phase 9C-9G focused slice: 35 passed.
- Phase 9H focused tests: 8 passed.
- UI smoke launch: exit 0.
- Bridge `--once`: exit 0.
- Bridge `--run-for-ms 250`: exit 0.
- Bridge `--status`: `lifecycle=Simulated truth=blocked_missing_device output_verified=False`.
- Runtime setup dry-run: Thrustmaster software detected, vJoy detected, HOTAS not connected.
- `git diff --check`: exit 0.

## Deferred

- continuous real HOTAS polling;
- live physical axis/button streaming;
- vJoy writes;
- output verification;
- Full Live Runtime Ready;
- Bridge process auto-launch;
- Windows Service installation;
- login auto-start;
- tray/background manager implementation;
- installer launch;
- real runtime activation;
- richer HID backend support if future optional dependencies are justified.
