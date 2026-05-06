# Phase 2B Bridge/UI Architecture Boundary Report

Status: Phase 2B implemented and verified.

## Scope

Phase 2B explicitly hardens the architecture boundary for HelmForge - HOTAS Control Panel V3 before further runtime work:

- Bridge owns real-time input/output.
- UI App owns configuration, visualization, diagnostics, and user interaction.
- Shared contracts live under `shared_core`.
- PySide6 UI code does not own Bridge contracts or real-time processing.

This phase does not implement real HOTAS polling, real vJoy writes, UI pages, installer launch, Windows service/tray behavior, or device-event auto-start.

## Governing Reference

Used recovered evidence note:

`HOTAS Control Panel Forensic Spec Set/helm_forge_two_part_architecture_clarification.md`

That file is preserved as recovered evidence and was not renamed.

## Files Created

- `shared_core/runtime/bridge_lifecycle.py`
- `shared_core/runtime/bridge_contracts.py`
- `shared_core/runtime/telemetry.py`
- `tests/test_phase2b_bridge_ui_boundary.py`
- `docs/HelmForge/bridge-ui-architecture.md`
- `docs/HelmForge/phase-2b-bridge-ui-architecture-boundary-report.md`

## Files Changed

- `README.md`

## Shared Contracts Added

Lifecycle:

- `BridgeLifecycleState`
- `BridgeLifecycleStatus`
- `BridgeLifecycleTransition`

Commands/config:

- `BridgeCommandType`
- `BridgeCommandRequest`
- `BridgeConfigurationReloadRequest`
- `BridgeHealthSummary`

Telemetry:

- `BridgeTelemetrySnapshot`
- `AxisTelemetrySnapshot`
- `ButtonHatTelemetrySnapshot`
- `ModeStateTelemetrySnapshot`
- `RuleStateSummary`
- `OutputVerificationState`

## Lifecycle State Semantics

Phase 2B supports:

- `NotInstalled`
- `Stopped`
- `Starting`
- `WaitingForHotas`
- `HotasDetected`
- `WaitingForOutput`
- `Simulated`
- `LiveUnverified`
- `LiveVerified`
- `Suspended`
- `Stopping`
- `Error`

## Command Semantics

Phase 2B models future UI-to-Bridge requests:

- `StartBridge`
- `StopBridge`
- `RestartBridge`
- `SuspendBridge`
- `ReloadConfig`
- `RunPreflight`
- `SwitchToSimulation`
- `VerifyOutput`
- `ClearError`

No real command execution is implemented in Phase 2B.

## Runtime Truth Recorded Before Implementation

Required precheck result:

- Thrustmaster driver/software detected: yes, `T.Flight Hotas drivers`
- vJoy detected: yes, `C:\Program Files\vJoy\x64\vJoyInterface.dll`
- HOTAS device detected: no, because the HOTAS was disconnected during this phase
- Runtime mode: `simulated`
- Runtime truth: `blocked_missing_device`
- Input status: `missing`
- Output status: `vjoy_detected`
- Live output writes verified: `false`
- Full Live Runtime Ready: false

This is truthful and expected for the disconnected HOTAS state. It does not indicate that the Phase 2A driver/vJoy installation failed.

## Dependency Boundary Verification

Tests verify:

- shared_core modules do not import `v3_app`;
- shared_core modules do not import `PySide6`;
- runtime/preflight/status modules remain importable without PySide6;
- Bridge contracts serialize to dictionaries for future IPC;
- telemetry can represent simulated state;
- telemetry can represent detected-but-unverified state;
- output verification defaults to false.

## Commands Run

Prechecks:

- `git status --short`
- `git remote -v`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- runtime truth probe via Python

TDD/verification:

- `python -m pytest .\tests\test_phase2b_bridge_ui_boundary.py`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- final runtime truth probe via Python

## Verification Results

Focused Phase 2B test:

- `python -m pytest .\tests\test_phase2b_bridge_ui_boundary.py`
- Result: `7 passed`

Pre-implementation full test run:

- `python -m pytest`
- Result: `48 passed`

Final full test run:

- Recorded in final response after completion verification.

Minimal app smoke:

- `python -m v3_app.main --smoke-exit-ms 250`
- Result: exit code `0`

Runtime setup dry-run:

- Driver/vJoy software detected.
- HOTAS device currently not connected.
- vJoy detected.
- No installers launched.

## Deferred Real Bridge Work

Still deferred:

- background Bridge process;
- Windows service/tray mode;
- HOTAS plug/unplug event watcher;
- real HOTAS polling;
- real vJoy writes;
- output write verification;
- IPC transport;
- telemetry streaming;
- Bridge control UI pages;
- recorder/overlay/Helm runtime integration.

## Next Recommended Phase

Next recommended phase: review Phase 2B, then continue with the math/signal pipeline only if you want to proceed into the Phase 3 boundary. Future Bridge runtime work should consume the shared-core contracts created here rather than moving real-time processing into PySide6 UI code.
