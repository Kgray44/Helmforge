# Bridge Service Design

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Status: Phase 13A Flight Recorder UI shell and Phase 9K runtime boundary freeze; no polling, output, process control, capture backend, or lifecycle implementation added

## Purpose

The Bridge is the background/runtime side of HelmForge. It is intended to own real-time HOTAS input, workspace processing, virtual output, and telemetry. The PySide6 UI owns configuration, visualization, diagnostics, and user interaction.

Phase 9B created the separate process skeleton so future real HOTAS and vJoy work lands outside `v3_app`. Phase 9C added UI-side telemetry reading without moving Bridge processing into the UI. Phase 9D added a safe UI command writer for status/config/preflight requests only. Phase 9E added per-command acknowledgement/status telemetry while keeping telemetry as the truth source. Phase 9F refined telemetry health and timing details for UI-visible lifecycle presence. Phase 9G records lifecycle ownership options, wording rules, and safety gates; it adds no lifecycle implementation. Phase 9H adds a Bridge-owned, read-only HOTAS discovery dry-run and publishes discovery truth through telemetry. Phase 9I adds UI-side process presence hints and diagnostic wording while keeping telemetry as the truth surface. Phase 9J polishes the Live Monitor diagnostic UX and edge-state wording without changing Bridge authority. Phase 9K freezes the Phase 9 boundary with regression tests and documentation consistency checks. Phase 10E finalizes the Helm overlay without adding any Bridge runtime authority. Phase 11B adds an observational Perf / Diagnostics page without adding any Bridge runtime authority. Phase 11C completes Phase 11 with Help / Docs + Perf / Diagnostics cross-links, terminology consistency, and final boundary tests; it does not add runtime authority. Phase 12A adds Live Overlay config/core models, a Live Monitor card, and a configuration dialog shell. Phase 12B adds an app-owned detached Live Overlay renderer. Phase 12C freezes the Live Overlay boundary without adding Bridge runtime authority. Phase 13A adds the Flight Recorder UI/state/settings/library/preview shell without capture, encoding, hotkey registration, or Bridge runtime authority.

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

## Phase 9J Live Monitor Diagnostic UX

Phase 9J keeps the Phase 9I truth model and adds a compact display hierarchy for the Live Monitor Live State card:

- `Telemetry`
- `Lifecycle`
- `Runtime`
- `Output verified`
- `HOTAS discovery`
- `Process hint`
- `Last command`
- `Diagnosis`
- `Manual launch`, only when telemetry is missing or stale

The formatting layer uses diagnostic-only severity categories: `ok`, `info`, `warning`, `error`, and `muted`. These categories are visual hints only. They do not change runtime truth, process presence truth, device discovery truth, or output verification truth.

Phase 9J also tightens command-status display:

- no UI command requested;
- command requested and awaiting Bridge telemetry;
- completed/acknowledged only for matching `request_id`;
- failed/rejected/ignored only for matching `request_id`;
- unrelated telemetry does not complete the current UI request.

Discovery remains discovery-only. If a supported HOTAS is discovered, UI wording remains conservative: supported HOTAS detected, polling not active, discovery only, output verification false.

## Phase 9K Boundary Freeze

Phase 9K is the final Phase 9 stabilization and boundary freeze:

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

Current development paths:

- Telemetry: `%TEMP%\helmforge_bridge_telemetry.json`
- Commands: `%TEMP%\helmforge_bridge_command.json`
- Manual Bridge launch: `python -m bridge_app.main --run-for-ms 250`

Safe UI command requests remain limited to `Status`, `RunPreflight`, `ReloadConfig`, `SwitchToSimulation`, and `ClearError`. `StartBridge`, `StopBridge`, `RestartBridge`, `SuspendBridge`, and `VerifyOutput` remain rejected/out of scope.

## Phase 10E Helm Boundary

Phase 10E finalizes Helm for Phase 10 while preserving this Bridge service boundary:

- Helm remains overlay/modal from the ASSISTANT cluster.
- Helm remains deterministic/local and recommendation-only.
- Helm can read workspace, mode, read-only rule, optional stack, and runtime diagnostic context.
- Helm may display Bridge telemetry truth, blocked runtime truth, output verification false, and discovery-only status as evidence labels.
- Apply Selected Changes modifies only the in-memory workspace draft.
- Save Workspace remains the only persistence action.
- Helm does not start, stop, restart, spawn, install, or manage the Bridge.
- Helm does not mutate conditional rules, does not use cloud AI or LLM behavior, and does not perform live hardware analysis.
- Phase 10E does not add Help / Docs implementation, Perf / Diagnostics page work, Live Overlay, Flight Recorder, hardware polling, live physical input streaming, vJoy writes, output verification, automatic Bridge launch, UI-launched child process, service install, login auto-start, tray manager work, installer launch, auto-save, or real runtime activation.

The next prompt-book phase is Phase 11: Help / Docs and Perf / Diagnostics. Phase 11 still must not treat documentation or diagnostics UI as proof of live runtime readiness.

## Phase 11B Perf / Diagnostics Boundary

Phase 11B implements Perf / Diagnostics page only. The page is observational:

- telemetry remains the truth surface;
- process presence remains a hint;
- Run Runtime Preflight remains safe and does not prove output verification;
- timing metrics are UI/app diagnostics, not live hardware proof;
- copy diagnostics text is a local summary, not a runtime command.

Phase 11B does not add hardware polling, live physical input streaming, vJoy writes, output verification, Bridge lifecycle control, process spawning, installer launch, service install, login auto-start, tray manager work, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 11C Help / Docs + Perf / Diagnostics Boundary Freeze

Phase 11 is now complete.

Phase 11C aligns Help / Docs and Perf / Diagnostics wording:

- telemetry remains the truth surface;
- process presence remains a hint;
- HOTAS discovery is discovery-only;
- vJoy detected does not mean output verified;
- Output verified remains false until a future output verification phase proves writes;
- Full Live Runtime Ready remains false until future phases prove both input and output;
- Run Runtime Preflight is a safe check/request, not runtime activation;
- Copy Diagnostics creates local diagnostic text.

Phase 11C does not add runtime authority. It does not add Live Overlay, Flight Recorder, real HOTAS polling, live physical input streaming, vJoy writes, output verification, automatic Bridge launch, UI-launched child process, service install, login auto-start, tray manager, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanner, cloud AI or LLM behavior, auto-save, or real runtime activation.

The next prompt-book phase is Phase 12 Live Overlay Foundation. Phase 12 must preserve the Phase 9K runtime boundary and Phase 10E Helm boundary.

## Phase 12 Live Overlay Boundary

Phase 12A implements Live Overlay core/config foundation only:

- shared axis colors;
- serializable overlay configuration defaults and validation;
- overlay telemetry history buffer;
- trace-building data structures;
- Live Monitor Live Overlay card;
- Live Overlay Configuration dialog shell.

Phase 12B adds an app-owned detached overlay window and Qt renderer. Show Overlay and Hide Overlay only control that UI-owned window. Status is Active only while the window is visible. The overlay can render simulation/runtime snapshots already available to the UI, but it does not create live hardware runtime.

Phase 12C finalizes the Live Overlay boundary. Hotkey registration is not claimed and remains `Not registered`. Click-through support is not claimed and remains `Not enabled - not verified`. Always-on-top is config-backed through Qt window flags only. Direct overlay-window close events update the Live Monitor status to Inactive.

Phase 12 does not add Flight Recorder, clip capture, video encoding, clip library, clip preview, hindsight buffer, recorder hotkey Ctrl+Shift+F10, real HOTAS polling, live physical input streaming, vJoy writes, output verification, automatic Bridge launch, UI-launched child process, service install, login auto-start, tray manager, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanner, game injection, graphics API hooking, screen capture, cloud AI or LLM behavior, auto-save, or real runtime activation.

## Phase 13A Flight Recorder Boundary

Phase 13A implements Flight Recorder UI/state/settings/library/preview shell only. It reuses shared Live Overlay colors for axis overlay settings.

Phase 13A does not add real desktop capture, video encoding, clip export, actual hindsight video buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, live physical input streaming, vJoy writes, output verification, automatic Bridge launch, UI-launched child process, service install, login auto-start, tray manager, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanner, cloud AI or LLM behavior, auto-save, or real runtime activation.

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
- Live Monitor launch buttons.
- Final IPC transport.
