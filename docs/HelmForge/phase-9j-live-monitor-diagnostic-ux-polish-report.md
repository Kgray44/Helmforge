# Phase 9J Live Monitor Diagnostic UX Polish Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Date: 2026-05-06
Scope: Live Monitor diagnostic UX wording/layout hardening only

## Summary

Phase 9J polishes the Live Monitor diagnostic UX around Bridge telemetry, process hints, device discovery, command acknowledgement, runtime truth, and manual-launch guidance.

This is a UX/wording/layout hardening phase only. Telemetry remains the truth surface. Process presence remains a hint. Phase 9H device discovery remains discovery-only.

Phase 9 boundary contract carried forward into Phase 9K:

- telemetry remains the truth surface.
- command files are requests, not success proof.
- Bridge command acknowledgement must use matching request_id.
- process presence is a hint only.
- HOTAS discovery is discovery-only.
- supported_device_detected does not mean polling/live runtime/output verified.
- manual Bridge launch remains the current lifecycle model.
- UI does not start, stop, restart, spawn, install, or manage the Bridge.
- output_verified remains false until a future output verification phase.
- Full Live Runtime Ready remains false until future phases prove input and output.
- live device/runtime work remains deferred.

## Diagnostic Hierarchy

The Live State card now has a stable compact hierarchy:

- Telemetry
- Lifecycle
- Runtime
- Output verified
- HOTAS discovery
- Process hint
- Last command
- Diagnosis
- Manual launch, only when telemetry is missing or stale

The existing dense health text remains as a compatibility summary for earlier diagnostics, while the new rows make the edge states easier to scan.

## Severity Mapping

Phase 9J adds diagnostic-only severity categories for row metadata:

- `ok`
- `info`
- `warning`
- `error`
- `muted`

Severity is display metadata only. It does not change runtime truth, process presence truth, device discovery truth, or output verification truth.

Examples:

- fresh telemetry: `ok`
- missing telemetry: `warning`
- stale telemetry: `warning`
- invalid telemetry: `error`
- simulated lifecycle: `info`
- blocked missing device: `warning`
- output verified false: `muted`
- supported device detected: `info`
- process unavailable: `muted`

## Discovery-Only Wording

Supported-device discovery remains conservative:

- Supported HOTAS detected; polling not active.
- Discovery only; output verification false.

No UI text claims:

- HOTAS active;
- input live;
- polling active;
- ready;
- connected and ready;
- runtime active.

When no supported HOTAS is detected, the UI says:

- No supported HOTAS detected.
- Runtime blocked: missing device.

## Command Status Cleanup

The Live State diagnostic rows now distinguish:

- no command requested;
- command requested, awaiting Bridge telemetry;
- completed or acknowledged only when telemetry `last_command.request_id` matches the latest UI request;
- failed, rejected, or ignored only when the request ID matches;
- unrelated telemetry does not complete the current UI request.

This preserves the Phase 9E request-id matching rule.

## Manual Launch Guidance

When telemetry is missing or stale, the Live State card can show:

```powershell
python -m bridge_app.main --run-for-ms 250
```

This is guidance text only. The UI does not execute it and does not add launch controls.

## Files Changed

- `v3_app/services/bridge_presence.py`
- `v3_app/pages/live_monitor_page.py`
- `tests/test_phase9j_live_monitor_diagnostic_ux.py`
- `docs/HelmForge/bridge-service-design.md`
- `docs/HelmForge/bridge-ui-architecture.md`
- `docs/HelmForge/phase-9j-live-monitor-diagnostic-ux-polish-report.md`
- `README.md`

## Tests Added

New focused tests:

- `tests/test_phase9j_live_monitor_diagnostic_ux.py`

Coverage includes:

- stable row labels/order;
- missing telemetry manual launch guidance;
- stale telemetry fallback wording;
- invalid telemetry no readiness claims;
- fresh telemetry suppressing manual launch guidance;
- supported-device discovery-only wording;
- no-supported-device blocked/missing wording;
- process hint not becoming runtime truth;
- command completion only for matching request ID;
- unrelated command telemetry ignored for current UI request;
- no lifecycle/process-control buttons;
- no hardware/vJoy/process-spawn dependencies introduced.

## Verification

Commands run during Phase 9J implementation:

- `git status --short`
- `git remote -v`
- `python -m pytest`
- `python -m pytest tests\test_phase9j_live_monitor_diagnostic_ux.py`
- `python -m pytest tests\test_phase9c_ui_bridge_telemetry_connection.py tests\test_phase9d_ui_bridge_command_seam.py tests\test_phase9e_bridge_command_acknowledgement.py tests\test_phase9f_bridge_lifecycle_health.py tests\test_phase9g_lifecycle_design_docs.py tests\test_phase9h_real_device_discovery_dry_run.py tests\test_phase9i_bridge_process_presence_diagnostics.py tests\test_phase9j_live_monitor_diagnostic_ux.py`
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- `python -m bridge_app.main --once`
- `python -m bridge_app.main --run-for-ms 250`
- `python -m bridge_app.main --status`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`

Results:

- Full suite: `186 passed`.
- Phase 9C-9I regression slice: `50 passed`.
- Phase 9J focused tests: `6 passed`.
- UI smoke launch exited cleanly.
- Bridge `--once`, `--run-for-ms 250`, and `--status` exited cleanly.
- Bridge status reported `lifecycle=Simulated truth=blocked_missing_device output_verified=False`.
- Runtime setup dry run detected Thrustmaster runtime software and vJoy, reported HOTAS Not Connected, and confirmed Full Live Runtime Ready false for this phase.

## Runtime Truth

Current runtime truth during verification:

- Runtime truth: `blocked_missing_device`
- Bridge lifecycle: `Simulated`
- HOTAS discovery: `no_supported_device`
- vJoy/output status: `vjoy_detected`
- `output_verified`: `false`
- Full Live Runtime Ready: `false`

Phase 9J did not alter runtime authority. The Live Monitor diagnostic polish only changes how existing telemetry, fallback, discovery, process-hint, and command-acknowledgement states are displayed.

## Deferred

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
- StartBridge/StopBridge/RestartBridge behavior;
- real runtime activation;
- real process scanner.
