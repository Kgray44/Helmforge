# Bridge Service Design

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Status: Phase 9E Bridge command acknowledgement/status refinement over Phase 9B simulation-only file IPC

## Purpose

The Bridge is the background/runtime side of HelmForge. It is intended to own real-time HOTAS input, workspace processing, virtual output, and telemetry. The PySide6 UI owns configuration, visualization, diagnostics, and user interaction.

Phase 9B created the separate process skeleton so future real HOTAS and vJoy work lands outside `v3_app`. Phase 9C added UI-side telemetry reading without moving Bridge processing into the UI. Phase 9D added a safe UI command writer for status/config/preflight requests only. Phase 9E adds per-command acknowledgement/status telemetry while keeping telemetry as the truth source.

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

This file IPC is a development seam, not the final transport. Phase 9C reads the telemetry file from `v3_app/services/bridge_client.py` and treats files older than 5 seconds as stale. Phase 9D writes safe command requests from `v3_app/services/bridge_commands.py`. Phase 9E has the Bridge echo the most recently consumed command request in telemetry. Future phases may replace the file with a named pipe, socket, local API, or service/tray channel.

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
- `last_command`

The payload is shaped from `shared_core/runtime/telemetry.py`, and the Phase 9C/9E UI client validates required fields before Live Monitor consumes the data.

`last_command` is `null` until the Bridge consumes or ignores a command. When present it includes:

- `schema_version`
- `request_id`
- `command`
- `status`
- `received_at`
- `completed_at`
- `updated_at`
- `message`
- `error`

## Commands

The Phase 9B command parser accepts the shared command model. Phase 9D intentionally allows only this safe subset from the UI:

- `ReloadConfig`
- `RunPreflight`
- `SwitchToSimulation`
- `ClearError`
- `Status`

The UI rejects these commands in Phase 9D:

- `StartBridge`
- `StopBridge`
- `RestartBridge`
- `SuspendBridge`
- `VerifyOutput`

Writing the command file means only "command requested." A later fresh telemetry snapshot is the truth source for whether the Bridge noticed or reflected the request. The UI must not say a command completed just because the JSON file was written.

Phase 9E command request payloads include:

- `schema_version`
- `request_id`
- `command`
- `created_at`
- `source`

The Bridge ignores command requests older than 30 seconds and reports them as `ignored_stale` in `last_command`. The Bridge also remembers the last consumed `request_id` in memory and does not execute the same request on every tick while the command file remains present.

No command triggers hardware polling, vJoy writes, output verification, driver installation, installer launch, Windows Service installation, or login auto-start in Phase 9E.

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
- automatic Bridge process launch from UI.
- Final IPC transport.
