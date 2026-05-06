# Phase 9C UI Bridge Telemetry Connection Report

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Date: 2026-05-06

## Scope

Phase 9C connected the PySide6 UI to the Phase 9B Bridge telemetry JSON seam. Live Monitor can now read fresh telemetry emitted by `bridge_app`, display its source/lifecycle/runtime truth, and fall back to simulation when telemetry is missing, stale, corrupt, invalid, or unreadable.

This phase did not implement real HOTAS polling, real vJoy writes, output verification, driver installation, installer launching, Windows Service installation, login auto-start, or automatic Bridge launching from the UI.

## Files Created

- `v3_app/services/bridge_client.py`
- `tests/test_phase9c_ui_bridge_telemetry_connection.py`
- `docs/HelmForge/phase-9c-ui-bridge-telemetry-connection-report.md`

## Files Changed

- `README.md`
- `docs/HelmForge/bridge-service-design.md`
- `docs/HelmForge/bridge-ui-architecture.md`
- `v3_app/pages/live_monitor_data.py`
- `v3_app/pages/live_monitor_page.py`

## Telemetry Path

Default UI telemetry path:

```text
%TEMP%\helmforge_bridge_telemetry.json
```

This matches the Phase 9B Bridge default telemetry path.

Custom telemetry paths are injectable in tests through `BridgeTelemetryClient(telemetry_path=...)` and `LiveMonitorPage(..., telemetry_path=...)`.

## UI Bridge Client

`v3_app/services/bridge_client.py` reads Bridge telemetry JSON and reports one of:

- `Connected`
- `Missing`
- `Stale`
- `Invalid`
- `Error`

It validates required fields:

- timestamp
- lifecycle state
- runtime truth
- input/output status
- output verification flag
- active profile
- raw/final axes
- buttons
- hats
- active modes
- rule summary

Missing, corrupt, partial, invalid, stale, or unreadable telemetry never crashes the UI.

## Stale Threshold

Bridge telemetry is stale when its `timestamp` is older than 5 seconds.

Stale telemetry is not treated as live. Live Monitor falls back to simulation and shows `Bridge Stale`.

## Live Monitor Behavior

Fresh Bridge telemetry:

- source chip: `Bridge Telemetry`
- raw/final axes come from Bridge telemetry
- buttons and hats come from Bridge telemetry
- lifecycle and runtime truth are displayed in Live State
- output verification remains whatever telemetry reports, currently `false`

Missing/stale/invalid telemetry:

- source label: `Simulation Fallback`
- source chip: `Bridge Missing`, `Bridge Stale`, `Bridge Invalid`, or `Bridge Error`
- raw/final values come from the existing simulation runtime
- output writes remain unverified

## Screenshot Fidelity Notes

Screenshots inspected:

- `Recovered PNG Evidence/09 Live Monitor/v2-live-monitor_final-raw-input-trace-graph.png`
- `Recovered PNG Evidence/09 Live Monitor/v2-live-monitor_final-raw-vs-final-overlay-graph-view.png`
- `Recovered PNG Evidence/09 Live Monitor/v2-live-monitor_final-axis-levels-hotas-buttons-output-buttons.png`

Visual change:

- Added one compact telemetry source chip to the existing Monitor Controls row.
- Added Bridge lifecycle/source wording to the existing Live State card.

Reason:

- The UI now needs to distinguish Bridge telemetry from simulation fallback without disrupting the recovered Live Monitor card hierarchy.

The change is intentional for Phase 9C and should remain compact unless a later diagnostics page takes over deeper Bridge status detail.

## Current Runtime Truth at Precheck

- Thrustmaster driver/software: detected
- HOTAS: not connected
- vJoy: detected
- Runtime mode: `simulated`
- Runtime truth: `blocked_missing_device`
- Output writes verified: `false`
- Full Live Runtime Ready: false

Bridge command telemetry during precheck also reported:

- lifecycle: `Simulated`
- runtime truth: `blocked_missing_device`
- output verified: `false`

## Deferred

- UI command writer buttons/actions.
- Automatic Bridge launch from UI.
- Windows Service/tray/startup behavior.
- Real HOTAS input polling.
- Real vJoy output writes.
- Output verification.
- Final IPC transport.
- Effective Response Stack consumption of Bridge telemetry.

## Verification

Commands run:

```powershell
git status --short
git remote -v
python -m pytest
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
python -m bridge_app.main --once --telemetry-path <temp>\helmforge_phase9c_precheck_once.json
python -m bridge_app.main --run-for-ms 250 --telemetry-path <temp>\helmforge_phase9c_precheck_run.json
python -m bridge_app.main --status --telemetry-path <temp>\helmforge_phase9c_precheck_status.json
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
python -m pytest tests\test_phase9c_ui_bridge_telemetry_connection.py
python -m pytest tests\test_phase9_live_monitor_page.py tests\test_phase9b_bridge_process_skeleton.py tests\test_phase9c_ui_bridge_telemetry_connection.py
python -m bridge_app.main --once
python -m bridge_app.main --run-for-ms 250
python -m bridge_app.main --status
python -m bridge_app.main --once; <read BridgeTelemetryClient default path>
```

Focused Phase 9C tests:

```text
9 passed
```

Phase 9/9B/9C slice:

```text
28 passed
```

Full regression suite after implementation:

```text
139 passed
```

Manual Bridge telemetry read after `python -m bridge_app.main --once`:

```text
path=%TEMP%\helmforge_bridge_telemetry.json
status=Connected
source=Bridge Telemetry
fallback=False
lifecycle=Simulated
truth=blocked_missing_device
output_verified=False
```
