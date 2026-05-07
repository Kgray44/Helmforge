# Bridge Service Design

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Status: Phase 16D Full Live Runtime Ready gate and final runtime boundary freeze plus Phase 16C verified runtime-path proof semantics, Phase 16B runtime_frame telemetry/UI integration, Phase 16A runtime orchestrator simulation path, Phase 15D output integration boundary freeze, and Phase 9K runtime boundary freeze; no automatic output enablement, process control, capture backend implementation, encoding, or lifecycle implementation added

## Purpose

The Bridge is the background/runtime side of HelmForge. It is intended to own real-time HOTAS input, workspace processing, virtual output, and telemetry. The PySide6 UI owns configuration, visualization, diagnostics, and user interaction.

Phase 9B created the separate process skeleton so future real HOTAS and vJoy work lands outside `v3_app`. Phase 9C added UI-side telemetry reading without moving Bridge processing into the UI. Phase 9D added a safe UI command writer for status/config/preflight requests only. Phase 9E added per-command acknowledgement/status telemetry while keeping telemetry as the truth source. Phase 9F refined telemetry health and timing details for UI-visible lifecycle presence. Phase 9G records lifecycle ownership options, wording rules, and safety gates; it adds no lifecycle implementation. Phase 9H adds a Bridge-owned, read-only HOTAS discovery dry-run and publishes discovery truth through telemetry. Phase 9I adds UI-side process presence hints and diagnostic wording while keeping telemetry as the truth surface. Phase 9J polishes the Live Monitor diagnostic UX and edge-state wording without changing Bridge authority. Phase 9K freezes the Phase 9 boundary with regression tests and documentation consistency checks. Phase 10E finalizes the Helm overlay without adding any Bridge runtime authority. Phase 11B adds an observational Perf / Diagnostics page without adding any Bridge runtime authority. Phase 11C completes Phase 11 with Help / Docs + Perf / Diagnostics cross-links, terminology consistency, and final boundary tests; it does not add runtime authority. Phase 12A adds Live Overlay config/core models, a Live Monitor card, and a configuration dialog shell. Phase 12B adds an app-owned detached Live Overlay renderer. Phase 12C freezes the Live Overlay boundary without adding Bridge runtime authority. Phase 13A adds the Flight Recorder UI/state/settings/library/preview shell without capture, encoding, hotkey registration, or Bridge runtime authority. Phase 13B adds recorder backend interfaces, telemetry hindsight buffering, simulated non-video artifacts, and controller wiring without adding real capture, encoding, video hindsight, hotkeys, or Bridge runtime authority. Phase 13C adds a compositor abstraction and simulated export bundles with trace/metadata files without adding real capture, encoding, playable export, video hindsight, hotkeys, or Bridge runtime authority. Phase 13D finalizes library indexing, metadata-only preview, Help / Docs wording, reports, and boundary tests without adding real capture, encoding, video hindsight, hotkeys, or Bridge runtime authority. Phase 14A adds shared-core physical input backend/device-selection interfaces, missing/fake/read-only Windows PnP discovery backends, centralized supported HOTAS matching, and diagnostics display without adding sampling loops, output writes, output verification, or Bridge lifecycle authority. Phase 14B adds read-only input sample models, deterministic axis normalization, fake on-demand sampling, sampler/controller coordination, and diagnostics display without adding vJoy output, output verification, or Bridge lifecycle authority. Phase 14C integrates those read-only samples into Mapping, Live Monitor, Effective Response Stack preview, Perf / Diagnostics, and Help / Docs without moving polling ownership or output authority into the UI. Phase 15A adds virtual output contracts and fake/missing backends. Phase 15B adds optional guarded real vJoy detection/write-path verification. Phase 15C adds a controlled write-loop service that is disabled by default, requires explicit enablement and verified backend proof, rate-limits writes, attempts neutral restore on stop, and safety-stops on failure. Phase 15D freezes Phase 15 terminology, diagnostics, docs, and boundary tests while preparing Phase 16 readiness. Phase 16A adds a shared-core runtime orchestrator that can build deterministic simulation frames, produce final output intent, and optionally hand off to an explicitly enabled fake output loop in tests. Phase 16B publishes compact runtime_frame summaries from that orchestrator through Bridge telemetry and lets UI surfaces display them safely. Phase 16C adds verified-path proof fields and conservative candidate semantics for fresh physical input, pipeline success, guarded output verification, and output-loop state. Phase 16D centralizes the final Full Live Runtime Ready gate and readiness proof object. It does not add automatic Bridge launch, Bridge lifecycle management, uncontrolled real output, or unsupported runtime activation.

## Current Entry Points

## Phase 15C Output Loop Boundary

The Phase 15C output loop lives behind shared-core backend contracts. It can write only when a backend is available, the output device path is verified, the loop is explicitly enabled, the intent is bounded, and the write-rate limiter allows the tick. Missing backends, missing devices, unverified output, failed writes, and restore failures are typed states instead of startup failures.

Stopping the loop after writes attempts neutral restore with axes at zero, buttons released, and hats centered. Restore failures are surfaced in diagnostics and are not hidden. Fake output loops are deterministic test/dev behavior and never prove real vJoy. Real vJoy output loops require prior guarded real verification. Phase 15C keeps Full Live Runtime Ready false because Phase 16 remains the end-to-end live runtime integration phase if readiness is deferred.

## Phase 15D Boundary Freeze

Phase 15 is now complete. Output intent is not output write proof, vJoy detection is not output verification, fake/mock output is not real vJoy output, and real output verification requires guarded write success plus neutral restore. The output loop remains disabled by default, explicitly enabled, rate-limited, and safety-gated.

Next prompt-book phase: Phase 16: Runtime End-to-End Live Mode. Phase 16 may build on Phase 14 physical input sampling, Phase 15 output intents, guarded output verification, controlled output loop state, diagnostics, and simulation fallback. Phase 16 must preserve simulation mode and must not claim Full Live Runtime Ready until both input and output are verified under the end-to-end runtime conditions.

## Phase 16A Runtime Orchestrator Boundary

Phase 16A begins Runtime End-to-End Live Mode with a contract-first orchestrator:

- `shared_core/runtime/runtime_orchestrator.py` builds compact runtime frames from simulation or guarded physical samples.
- The deterministic simulation path runs through mapping, tuning, filtering, modes, conditional rules, and final output intent generation.
- The orchestrator can accept a fresh physical input snapshot but falls back to simulation for missing, stale, or error samples.
- Output intent is not output write proof.
- A fake output-loop handoff is available only when a fake backend is injected, verified, explicitly enabled, and the orchestrator is configured to tick it.
- Real output remains governed by Phase 15 verification and output-loop gates.
- Full Live Runtime Ready remains false in this slice.

Phase 16A does not add Bridge lifecycle management, automatic output enablement, uncontrolled real vJoy output, service install, login auto-start, tray manager work, recorder capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or unsupported runtime activation.

## Phase 16B Runtime Frame Telemetry Boundary

Phase 16B adds Bridge telemetry integration for the Phase 16A runtime frame:

- `runtime_frame` is a compact summary, not a full internal pipeline dump.
- It includes schema version, frame sequence, generated time, input source/status, input sample age/stale truth, pipeline status, compact modes/rules summary, final output axes, output intent readiness, output backend, output verification status, output loop state, last output write status, output_verified, Full Live Runtime Ready, runtime truth, blocked reason, warnings, and errors.
- Missing `runtime_frame` remains backward-compatible for older telemetry.
- Malformed `runtime_frame` is parsed as unavailable/invalid in the UI client instead of crashing the UI.
- Mapping, Live Monitor, Perf / Diagnostics, Copy Diagnostics, and Help / Docs can show runtime frame truth.

Output intent is not output write proof. Runtime frame generation alone never writes vJoy, starts an output loop, or proves Full Live Runtime Ready.

Phase 16B does not add Bridge lifecycle management, automatic output enablement, unsupported real vJoy writes, service install, login auto-start, tray manager work, recorder capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or unsupported runtime activation.

## Phase 16C Verified Runtime Path Boundary

Phase 16C connects verified input/output runtime path semantics without opening lifecycle authority:

- physical input, pipeline success, output verification, and output-loop state are tracked as separate proofs;
- `runtime_frame` includes input proof, pipeline proof, output proof, output-loop enabled/running/safety-stop state, runtime candidate, blocked reason, and proof summary;
- fake/test output paths remain test-only and cannot set real output verified;
- a fully proven real-path injection can report `verified_runtime_candidate`;
- Full Live Runtime Ready remains false because Phase 16D owns the final readiness gate.

Output intent is still not output write proof. Runtime frame generation does not start a loop, write vJoy, launch the Bridge, or manage lifecycle.

## Phase 16D Full Live Runtime Ready Gate

Phase 16D completes Runtime End-to-End Live Mode by centralizing readiness evaluation in `shared_core/runtime/runtime_orchestrator.py`.

- Full Live Runtime Ready requires fresh physical input, successful pipeline processing, guarded real output verification, explicit output loop enable/running according to policy, fresh runtime_frame/Bridge telemetry, and no safety stop or blocking errors.
- The readiness proof reports ready state, blocked reason, input proof, pipeline proof, output proof, telemetry proof, safety proof, fake/real path, proof summary, warnings, errors, and evaluation time.
- Fake physical input, fake output verification, and fake output loops can prove test mechanics only. They never set real output verified or Full Live Runtime Ready.
- Stale telemetry, stale input, missing input, pipeline errors, unverified output, disabled output loop, safety stops, write failures, and neutral restore failures keep readiness blocked.
- Phase 16 is now complete. The next prompt-book phase is Phase 17: Product Polish, Layout QA, and Motion.

Phase 16D does not add Bridge lifecycle management, automatic output enablement, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or unsupported runtime activation.

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
- `runtime_frame`
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

## Phase 13B Recorder Backend Boundary

Phase 13B adds Flight Recorder backend interfaces and safe foundation models only. The default capture backend remains missing/unavailable. A deterministic simulated backend can be injected by tests or dev code to write JSON manifest artifacts that are explicitly simulated, non-video, and not real recordings.

Phase 13B adds telemetry hindsight buffering only. It does not add desktop video hindsight buffering. Save Last Clip cannot save real video until future capture and buffer backends exist.

Phase 13B does not add real desktop capture, real screen capture APIs, video encoding, real clip export, actual desktop video hindsight buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, live physical input streaming, vJoy writes, output verification, automatic Bridge launch, UI-launched child process, service install, login auto-start, tray manager, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanner, cloud AI or LLM behavior, auto-save, or real runtime activation.

## Phase 13C Simulated Compositor Boundary

Phase 13C adds Flight Recorder compositor/export architecture only. The default compositor remains unavailable. A deterministic simulated compositor can be injected by tests or dev code to write simulated export bundles containing `manifest.json`, `overlay_trace.json`, `summary.md`, and `preview_metadata.json`.

Simulated export bundles are metadata/trace artifacts, not recordings. They do not contain playable video and must not be presented as desktop capture.

Phase 13C reuses Phase 12 overlay trace concepts and shared axis colors. Telemetry hindsight can feed simulated overlay trace exports, but desktop video hindsight buffering remains unavailable/deferred.

Phase 13C does not add real desktop capture, real screen capture APIs, video encoding, playable clip export, actual desktop video hindsight buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, live physical input streaming, vJoy writes, output verification, automatic Bridge launch, UI-launched child process, service install, login auto-start, tray manager, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanner, cloud AI or LLM behavior, auto-save, or real runtime activation.

## Phase 13D Flight Recorder Boundary Freeze

Phase 13D completes Phase 13. It polishes simulated export indexing and metadata-only preview, keeps Play/timeline disabled for simulated/non-video artifacts, and documents the final recorder boundary.

Phase 13D confirms that telemetry hindsight can support simulated overlay metadata, while video hindsight buffering is not implemented yet. Save Last Clip cannot save real video until capture buffering exists.

The next prompt-book phase is Phase 14 Real HOTAS Input Integration. Phase 14 must preserve simulation mode and must not add vJoy writes/output verification unless a later output phase explicitly scopes that work.

Phase 13D does not add real desktop capture, real screen capture APIs, video encoding, playable clip export, actual desktop video hindsight buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, live physical input streaming, vJoy writes, output verification, automatic Bridge launch, UI-launched child process, service install, login auto-start, tray manager, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanner, cloud AI or LLM behavior, auto-save, or real runtime activation.

## Phase 14A Physical Input Backend Boundary

Phase 14A implements a physical input backend and device-selection foundation only. The shared-core seam can enumerate read-only device identities through a missing backend, deterministic fake backend, or Windows PnP discovery backend. It centralizes support matching for the Thrustmaster T-Flight / T.Flight HOTAS One, including VID/PID `044f:b68d`.

The selection model is in-memory for Phase 14A. It can report backend unavailable, no device selected, selected device available, selected device missing, and unsupported selected device. Perf / Diagnostics can display those states, but the UI does not own runtime polling loops.

Supported HOTAS detected means only that a matching input device identity is visible to discovery. Input sampling remains not active in Phase 14A. Output verified remains false. Full Live Runtime Ready remains false. Phase 15 remains the virtual output/vJoy phase.

Phase 14A does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, end-to-end live runtime loops, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 14B Physical Input Sampling Boundary

Phase 14B implements physical input sampling and normalization foundations only. Sample snapshots include device/backend/time/source metadata, axis/button/hat samples, normalized values, sampling status, warnings, and errors.

The fake backend can return deterministic read-only samples and emulate disconnect/error states. Missing and Windows PnP discovery backends report sampling unavailable. This keeps simulation mode available and avoids fragile physical sampling dependencies.

Physical input sampling is read-only and on-demand in Phase 14B. It does not write vJoy, verify output, start the Bridge, or create an end-to-end runtime loop. Output verified remains false. Full Live Runtime Ready remains false. Phase 15 remains the virtual output/vJoy phase.

Phase 14B does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, end-to-end vJoy runtime loops, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 14C Physical Input UI Boundary

Phase 14C implements UI integration for read-only physical input samples. Mapping, Live Monitor, Effective Response Stack preview, Perf / Diagnostics, Copy Diagnostics, and Help / Docs can show input source, selected device, sample status, sample source, sample counts, stale/error fallback, and physical input read-only truth.

Physical samples are still input-only evidence. They do not make the UI the owner of a long-running Bridge polling loop, do not write vJoy, do not verify output, and do not make Full Live Runtime Ready true. Simulation mode remains available when samples are missing, stale, erroring, or unavailable.

Phase 14C does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, end-to-end live output runtime loops, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 14D Physical Input Boundary Freeze

Phase 14 is now complete.

Phase 14D finalizes the physical input side before virtual output work begins. The Bridge/service boundary keeps physical input models and sampling seams read-only: device discovery and sample snapshots can inform UI diagnostics, Mapping, Live Monitor, and diagnostic previews, but they do not write virtual output or verify output.

Simulation fallback remains available for no backend, no selected device, selected device missing, stale physical samples, sample errors, backend disconnects, and missing/stale/invalid Bridge telemetry. Output verified remains false. Full Live Runtime Ready remains false.

## Phase 15A Virtual Output Backend Contract

Phase 15A starts the virtual output side with contracts only:

Phase 15: vJoy / Virtual Output Integration remains the active prompt-book phase. Phase 15A is the contract-only opening slice.

Full Live Runtime Ready must remain false until both input and output are verified.

- virtual output backend capabilities/status;
- virtual output device info;
- output intent, axis/button/hat output models, and recovered route intent;
- write-result and verification-result models;
- a safe default missing backend;
- a deterministic fake backend for tests/dev injection.

The missing backend does not enumerate devices, write output, or verify output. The fake backend can record an output intent in memory and report `fake_verified`, but that result is explicitly fake/mock and Not real vJoy. Real output verified remains false.

The Bridge remains the future runtime owner for real output writes. Phase 15A does not create a live output loop, does not add real vJoy writes, and does not infer output verification from vJoy detection. output_verified remains false in normal runtime. Full Live Runtime Ready remains false.

## Phase 15B Real vJoy Detection And Guarded Verification

Phase 15B adds guarded real vJoy detection and write-path verification only. The real backend is optional and guarded, and app startup does not require the vJoy dependency.

The backend can report:

- vJoy dependency available/missing/unknown;
- vJoy backend/driver detected or missing;
- output device detected/missing/busy/unknown;
- selected output device;
- output write status;
- verification status/source;
- fake output verified;
- real output verified;
- last verification timestamp;
- verification warnings/errors.

Guarded verification is explicit. It does not run on app startup or passive page rendering. It uses a bounded verification intent, not arbitrary user profile output, and attempts neutral restore after a real verification write.

Real output verified can become true only after guarded write success and neutral restore success. vJoy detected does not equal output verified. Fake/mock verification is not real vJoy verification. Full Live Runtime Ready remains false.

Phase 15B does not add a continuous output loop, end-to-end live output runtime loop, automatic output enablement, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

Next prompt-book slice: Phase 15C may add runtime output-loop integration only after the guarded verification layer is stable and simulation fallback is preserved.

Phase 14D does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, end-to-end live output runtime loops, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

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
