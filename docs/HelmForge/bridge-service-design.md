# Bridge Service Design

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Status: Phase 9C UI telemetry connection over Phase 9B simulation-only file IPC

## Purpose

The Bridge is the background/runtime side of HelmForge. It is intended to own real-time HOTAS input, workspace processing, virtual output, and telemetry. The PySide6 UI owns configuration, visualization, diagnostics, and user interaction.

Phase 9B created the separate process skeleton so future real HOTAS and vJoy work lands outside `v3_app`. Phase 9C adds UI-side telemetry reading without moving Bridge processing into the UI.

## Current Entry Points

Run one simulation tick:

```powershell
python -m bridge_app.main --once
```

Run for a bounded duration:

```powershell
python -m bridge_app.main --run-for-ms 250
```

Print status:

```powershell
python -m bridge_app.main --status
```

Useful options:

- `--telemetry-path <path>` writes telemetry JSON to a chosen file.
- `--command-path <path>` reads a command JSON file.
- `--config-path <path>` loads a V3 workspace config.
- `--simulate` documents/forces simulation intent. Phase 9B is simulation-only even without this flag.

## Current IPC

Phase 9B uses a deliberately simple local file IPC:

- Telemetry: atomic JSON writes to a telemetry path.
- Commands: JSON command request read from a command path.

Default paths are under the local temp directory:

- `helmforge_bridge_telemetry.json`
- `helmforge_bridge_command.json`

This file IPC is a development seam, not the final transport. Phase 9C reads the telemetry file from `v3_app/services/bridge_client.py` and treats files older than 5 seconds as stale. Future phases may replace the file with a named pipe, socket, local API, or service/tray channel.

## Telemetry Shape

Telemetry JSON includes:

- `product_name`
- `technical_subtitle`
- `bridge_name`
- `bridge_process`
- `timestamp`
- `lifecycle_state`
- `runtime_truth`
- `input_status`
- `output_status`
- `output_verified`
- `active_profile`
- `raw_axes`
- `final_axes`
- `buttons`
- `hats`
- `active_modes`
- `rule_summary`
- `output_verification`
- `warnings`
- `errors`
- `config_path`
- `config_status`
- `tick_count`

The payload is shaped from `shared_core/runtime/telemetry.py`, and the Phase 9C UI client validates required fields before Live Monitor consumes the data.

## Commands

The Phase 9B command parser accepts:

- `StartBridge`
- `StopBridge`
- `ReloadConfig`
- `RunPreflight`
- `SwitchToSimulation`
- `ClearError`
- `Status`

Only safe skeleton behavior is implemented. For example, `StopBridge` stops the bounded loop, `ReloadConfig` reloads the workspace/default fallback, and `RunPreflight` refreshes detection truth. No command triggers hardware polling or vJoy writes in Phase 9B.

## Config Loading

The Bridge loads `hotas_bridge_config_v3.json` or a provided `--config-path`.

Missing config:

- non-fatal;
- default workspace is used;
- warning is written to telemetry;
- no config file is created or overwritten.

Corrupt config:

- non-fatal;
- default workspace is used;
- warning/error is written to telemetry;
- corrupt file is not overwritten.

## Lifecycle

Phase 9B exercises:

- `Starting`
- `Simulated`
- `Stopping`

The shared lifecycle model also preserves future states:

- `WaitingForHotas`
- `HotasDetected`
- `WaitingForOutput`
- `LiveUnverified`
- `LiveVerified`
- `Suspended`
- `Error`

`LiveVerified` must not be used until a later phase actually verifies output writes.

## Deferred

- Windows Service installation.
- Auto-start at user login.
- Tray/background manager.
- Device-event wake/suspend behavior.
- Real HOTAS polling.
- Real vJoy writes.
- Output verification.
- command writer UI actions;
- automatic Bridge process launch from UI;
- Final IPC transport.
