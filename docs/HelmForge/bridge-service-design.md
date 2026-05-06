# Bridge Service Design

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Status: Phase 9I process presence diagnostics added; no polling, output, process control, or lifecycle implementation added

## Purpose

The Bridge is the background/runtime side of HelmForge. It is intended to own real-time HOTAS input, workspace processing, virtual output, and telemetry. The PySide6 UI owns configuration, visualization, diagnostics, and user interaction.

Phase 9B created the separate process skeleton so future real HOTAS and vJoy work lands outside `v3_app`. Phase 9C added UI-side telemetry reading without moving Bridge processing into the UI. Phase 9D added a safe UI command writer for status/config/preflight requests only. Phase 9E added per-command acknowledgement/status telemetry while keeping telemetry as the truth source. Phase 9F refined telemetry health and timing details for UI-visible lifecycle presence. Phase 9G records lifecycle ownership options, wording rules, and safety gates; it adds no lifecycle implementation. Phase 9H adds a Bridge-owned, read-only HOTAS discovery dry-run and publishes discovery truth through telemetry. Phase 9I adds UI-side process presence hints and diagnostic wording while keeping telemetry as the truth surface.

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

This file IPC is a development seam, not the final transport. Phase 9C reads the telemetry file from `v3_app/services/bridge_client.py` and treats files older than 5 seconds as stale. Phase 9D writes safe command requests from `v3_app/services/bridge_commands.py`. Phase 9E has the Bridge echo the most recently consumed command request in telemetry. Phase 9F exposes telemetry read time, generated time, age, stale threshold, status, and reason to the UI. Future phases may replace the file with a named pipe, socket, local API, or service/tray channel.

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
- `device_discovery`

The payload is shaped from `shared_core/runtime/telemetry.py`, and the Phase 9C/9E UI client validates required fields before Live Monitor consumes the data.

The UI-side health read result distinguishes:

- `Connected`: telemetry is fresh and usable.
- `Missing`: telemetry file was not found.
- `Stale`: telemetry exists but is older than the stale threshold and must not be treated as live truth.
- `Invalid`: telemetry could not be parsed or failed schema validation.
- `Error`: telemetry file could not be read.

The read result exposes the telemetry path, read time, generated time when available, telemetry age, stale threshold, and a human-readable reason. Stale, missing, invalid, and error states use simulation fallback.

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

`device_discovery` reports the Phase 9H read-only discovery dry-run. It includes:

- `status`
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

Allowed discovery states are `not_checked`, `no_supported_device`, `supported_device_detected`, `discovery_error`, and `backend_unavailable`. A supported-device match means only that a supported HOTAS identity was visible to the Bridge discovery backend. It does not mean input polling is active, output writes are verified, or Full Live Runtime Ready is true.

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

No command triggers continuous HOTAS polling, vJoy writes, output verification, driver installation, installer launch, Windows Service installation, automatic Bridge launch, child process launch, tray manager work, or login auto-start in Phase 9I.

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

## Phase 9H Device Discovery Dry-Run

Phase 9H adds `shared_core/runtime/hotas_discovery.py` as the typed discovery model and backend boundary. The Bridge owns this boundary; the UI never scans hardware directly.

Current discovery pieces:

- `HotasDeviceInfo`: a read-only identity record for a discovered device.
- `HotasDiscoveryResult`: a typed discovery status payload for telemetry.
- `DeviceDiscoveryBackend`: the backend protocol.
- `FakeDeviceDiscoveryBackend`: deterministic tests.
- `WindowsPnpDeviceDiscoveryBackend`: guarded Windows PnP enumeration using the existing read-only preflight path.

The initial supported-device matcher is centralized. It recognizes the recovered target by conservative name matching and the known Thrustmaster T-Flight HOTAS One USB pair `VID_044F` / `PID_B68D` when those IDs are visible.

Discovery is run during Bridge ticks and preflight/status command handling. It may update input discovery truth, but it does not start a polling loop, stream live axes/buttons, write vJoy, or verify output. With no supported HOTAS found and vJoy present, runtime truth remains `blocked_missing_device`. If a supported HOTAS is only detected by dry-run discovery, output verification still remains false.

## Phase 9I Process Presence Diagnostics

Phase 9I adds `v3_app/services/bridge_presence.py` as a UI-side diagnostic seam. Process presence is only a hint. Fresh Bridge telemetry remains stronger than process presence, and runtime truth still comes from telemetry/preflight models.

Presence states:

- `unavailable`
- `unknown`
- `not_found`
- `maybe_running`
- `seen_but_telemetry_missing`
- `seen_but_telemetry_stale`
- `fresh_telemetry_confirmed`
- `telemetry_invalid`
- `telemetry_error`

The Phase 9I provider defaults to an unavailable read-only provider and includes a fake provider for tests. It does not start, stop, restart, signal, kill, spawn, or manage any process. The first UI use is compact Live Monitor diagnostic wording that can say, for example, that telemetry is missing and manual Bridge launch may be required.

Manual Bridge launch remains the current lifecycle model:

```powershell
python -m bridge_app.main --run-for-ms 250
```

The UI may show that command as help text, but it does not execute it in Phase 9I.

## Phase 9G Lifecycle Ownership Decision

Phase 9G is documented in `docs/HelmForge/phase-9g-bridge-lifecycle-ownership-design.md`.

Decision summary:

- keep manual Bridge launch during current development;
- do not let the UI start, stop, or restart the Bridge yet;
- do not add process spawning from the UI;
- later consider read-only process presence hints;
- later prefer a tray/background manager over premature service behavior;
- defer Windows Service unless there is a strong reason;
- defer login auto-start until Bridge behavior is stable, user-controlled, and opt-in;
- never imply runtime readiness without fresh telemetry and output verification.

This is design-only. No lifecycle implementation, tray manager, service install, login startup task, automatic Bridge launch, or real runtime activation is added by Phase 9G.

## Deferred

- Windows Service installation.
- Auto-start at user login.
- Tray/background manager.
- Device-event wake/suspend behavior.
- Continuous real HOTAS polling.
- Live physical axis/button streaming.
- Real vJoy writes.
- Output verification.
- automatic Bridge process launch from UI.
- process spawning from UI.
- process start/stop/restart controls.
- Final IPC transport.
