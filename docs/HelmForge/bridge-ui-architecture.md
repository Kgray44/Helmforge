# Bridge/UI Architecture

Status: Phase 9I adds UI-side Bridge process presence hints and diagnostic visibility. Shared contracts exist, `bridge_app` can run as a separate simulation-only Python process, the PySide6 Live Monitor can consume fresh Bridge telemetry JSON with safe simulation fallback, and the UI can request safe Bridge commands through a JSON command file. The Bridge echoes the most recently consumed command request in telemetry, and the UI shows compact Bridge health/timing details, device discovery truth, and process-presence hints. Continuous real HOTAS polling, live physical input streaming, vJoy writes, output verification, automatic Bridge launch, process spawning from the UI, Windows Service install, tray manager work, and login auto-start are not implemented yet.

## Core Rule

The Bridge owns real-time input/output. The UI App owns configuration, visualization, diagnostics, and user interaction.

HelmForge is two-part software:

- Bridge: lightweight runtime/background control component.
- UI App: PySide6 desktop configuration, diagnostics, monitoring, and user interaction surface.

The UI App should not be required to stay open for configured HOTAS-to-vJoy processing once the Bridge is installed, configured, and running.

## Bridge Responsibilities

The future Bridge owns the low-latency runtime path:

- detect the Thrustmaster T-Flight HOTAS One / Thrustmaster T.Flight Hotas One;
- read physical HOTAS axes, buttons, and hats;
- load the active `hotas_bridge_config_v3.json` workspace;
- apply mappings, tuning, filtering, modes, and conditional rules;
- produce final output values;
- write final output to vJoy or the selected virtual output backend;
- publish telemetry snapshots;
- reload configuration when the UI saves and requests reload;
- truthfully report missing drivers, missing HOTAS, missing output backend, unverified output, and runtime errors;
- eventually auto-start or wake when the HOTAS is plugged in;
- eventually suspend, stop, or safe-idle when the HOTAS is unplugged.

The Bridge must not depend on PySide6, graph rendering, overlay rendering, Helm analysis, or expensive UI refresh work to maintain real-time output.

Phase 9H adds a Bridge-owned read-only discovery boundary for the supported HOTAS. This boundary can identify whether a supported device is visible to the operating system, but it is not the live polling path and it does not activate vJoy output.

## UI App Responsibilities

The UI App owns the human-facing surface:

- present HelmForge branding and the HOTAS Control Panel V3 technical subtitle;
- edit mappings, modes, base tuning, filtering, combat profile, profiles, workspaces, and conditional rules;
- save and load `hotas_bridge_config_v3.json`;
- request future Bridge lifecycle actions only after later safety gates are implemented;
- request current safe Bridge status/config/preflight commands through the Phase 9D command seam;
- display Bridge telemetry in Live Monitor and Effective Response Stack views;
- display runtime setup, help/docs, performance, and diagnostics;
- host future Helm assistant, Flight Recorder, and Live Overlay UI;
- show truthful runtime state rather than fake live claims.

The UI may run Bridge-like adapters in-process during early development, but real-time processing should remain behind shared-core contracts so it can move to a background component later.

## Communication Boundary

The final IPC mechanism is still intentionally undecided. Phase 9B uses a simple local JSON telemetry file and JSON command file as the first development IPC seam. Phase 9C reads the telemetry JSON from the UI and falls back when it is missing, stale, or invalid. Phase 9D writes safe UI command requests to the command file. Candidate later mechanisms include:

- local process IPC;
- named pipe;
- localhost API;
- shared state file plus a command channel;
- direct in-process adapter during early phases;
- background service or tray process in later phases.

Required boundary:

```text
UI writes configuration and sends commands.
Bridge reads configuration, processes input/output, and publishes telemetry.
```

## Configuration Flow

1. User edits a workspace in the UI.
2. UI updates its current workspace draft.
3. User saves the workspace.
4. UI writes `hotas_bridge_config_v3.json`.
5. UI sends `ReloadConfig`, or the Bridge detects the safe configuration update later.
6. Bridge applies the new configuration to future runtime samples.

The Bridge should never rely on the settings window staying open to keep processing once the real background runtime exists.

## Telemetry Flow

1. Bridge samples raw HOTAS input.
2. Bridge applies the active workspace transformation pipeline.
3. Bridge publishes raw axes, final axes, buttons, hats, active modes, rule counts, output verification state, device discovery status, warnings, and errors.
4. UI reads and renders telemetry in monitor, graph, diagnostics, overlay, recorder, and assistant surfaces.

Phase 2B telemetry contracts are defined in `shared_core/runtime/telemetry.py`. Phase 9B Bridge telemetry is written as JSON shaped from those contracts. Phase 9C validates the JSON in `v3_app/services/bridge_client.py`; telemetry older than 5 seconds is treated as stale and not live.

Phase 9F exposes explicit UI health fields from the Bridge telemetry client:

- telemetry path;
- last read time;
- telemetry generated time;
- age in seconds;
- stale threshold;
- status and reason.

The Live Monitor shows these compactly in the Live State card. Missing, stale, invalid, and error telemetry all remain simulation fallback states; stale telemetry is not treated as live Bridge truth.

Phase 9H adds `device_discovery` to telemetry. The UI may display:

- HOTAS discovery not checked;
- no supported device found;
- supported HOTAS detected, polling not active;
- discovery error;
- discovery backend unavailable.

The UI must not scan hardware directly and must not translate discovery into live runtime readiness. A supported-device discovery result only means the Bridge dry-run can see a matching device identity.

## Process Presence Diagnostics

Phase 9I adds UI-side process presence hints. Presence hints are diagnostic only:

- telemetry remains the truth surface;
- fresh telemetry is stronger than a process hint;
- process presence never becomes runtime truth;
- process presence never proves output verification;
- process presence never permits Full Live Runtime Ready wording.

Initial presence states:

- unavailable;
- unknown;
- not found;
- maybe running;
- seen but telemetry missing;
- seen but telemetry stale;
- fresh telemetry confirmed;
- telemetry invalid;
- telemetry error.

The Live Monitor can now show compact text such as:

- `Bridge telemetry: Connected`;
- `Process hint: Fresh telemetry confirmed`;
- `Bridge telemetry missing; manual Bridge launch may be required`;
- `Bridge process may be running, but telemetry is stale`;
- `Manual Bridge launch expected: python -m bridge_app.main --run-for-ms 250`.

The UI does not execute the manual-launch command and does not add Start, Stop, Restart, Service, Auto Start, or Verify Output controls.

## Command Flow

Phase 9D added `v3_app/services/bridge_commands.py`, which writes safe command requests to `%TEMP%\helmforge_bridge_command.json` using atomic JSON writes. Phase 9E adds request IDs, schema versioning, Bridge `last_command` telemetry, stale-command protection, and in-memory duplicate request protection.

Allowed UI commands in Phase 9D:

- `Status`
- `RunPreflight`
- `ReloadConfig`
- `SwitchToSimulation`
- `ClearError`

Disallowed UI commands in Phase 9D:

- `StartBridge`
- `StopBridge`
- `RestartBridge`
- `SuspendBridge`
- `VerifyOutput`

Writing a command file is a request, not a success response. UI labels must use wording such as "command requested" and "awaiting Bridge telemetry" until a later fresh telemetry snapshot provides the actual state.

Phase 9E acknowledgement rules:

- UI command writes include `schema_version`, `request_id`, `command`, `created_at`, and `source`.
- Bridge telemetry includes `last_command` when it consumes, completes, fails, or ignores a command.
- The UI shows acknowledged/completed/failed/ignored only when telemetry `last_command.request_id` matches the latest UI-written request ID.
- Stale command files older than 30 seconds are ignored and reported as `ignored_stale`.
- Re-reading the same request ID on later ticks does not re-execute the command.

## Runtime Truth Rules

- `Full Live Runtime Ready` is allowed only when physical input and output writes are both detected and verified.
- vJoy detected is not the same thing as output verified.
- HOTAS detected is not the same thing as real polling implemented.
- Supported-device discovery is not the same thing as a live HOTAS input stream.
- Process presence is not the same thing as Bridge runtime truth.
- Manual launch help text is not a UI-owned launch mechanism.
- Simulation mode remains valid for development, tests, graph previews, and no-hardware states.
- Missing devices or drivers must be visible and non-fatal when simulation can continue.
- The Bridge should fail safe and publish typed errors instead of pretending live output works.

## Lifecycle Goal

Future lifecycle target:

```text
HOTAS plugged in -> Bridge starts or wakes.
HOTAS unplugged -> Bridge suspends, stops, or safe-idles.
UI opened -> UI connects to Bridge and displays current truth.
UI closed -> Bridge may continue if configured and safe.
Config saved -> Bridge reloads config or receives a reload command.
Runtime error -> Bridge enters error/safe-idle and reports the reason.
```

Phase 2B lifecycle contracts are defined in `shared_core/runtime/bridge_lifecycle.py`. Phase 9B exercises `Starting`, `Simulated`, and `Stopping` in tests, with `WaitingForHotas`, `WaitingForOutput`, and `LiveUnverified` preserved for the future real runtime.

## Phase 9G Lifecycle Ownership Decision

Phase 9G records the lifecycle ownership decision in `docs/HelmForge/phase-9g-bridge-lifecycle-ownership-design.md`.

Conservative staged path:

1. Keep manual Bridge launch for now.
2. Add read-only process presence hints later if needed.
3. Prefer a tray/background Bridge manager later for user-session ownership.
4. Defer UI-launched child process until crash/log/stale-state behavior is safe.
5. Defer Windows Service until there is a strong reason.
6. Defer login auto-start until Bridge behavior is stable, user-controlled, and opt-in.
7. Never imply runtime readiness without fresh telemetry and output verification.

Phase 9G is design-only. No lifecycle implementation, process spawning, automatic Bridge launch, tray manager, Windows Service, login auto-start, or real runtime activation was added.

## Current Early-Phase Status

Implemented:

- shared runtime status/preflight models;
- simulation-first runtime snapshots;
- Thrustmaster/vJoy setup detection;
- workspace/config schema;
- Phase 3 shared-core math pipeline from earlier work;
- Phase 2B Bridge lifecycle, command, health, and telemetry contracts.
- Phase 9B separate `bridge_app` package;
- `python -m bridge_app.main --once`;
- `python -m bridge_app.main --run-for-ms <milliseconds>`;
- `python -m bridge_app.main --status`;
- local telemetry JSON output;
- local command JSON parsing for initial Bridge commands.
- Phase 9C UI telemetry client;
- Live Monitor consumption of fresh Bridge telemetry;
- simulation fallback for missing, stale, corrupt, or invalid Bridge telemetry.
- Phase 9D UI command writer for safe commands;
- compact Live Monitor command request controls;
- UI rejection of unsafe commands such as `VerifyOutput` and `StartBridge`.
- Phase 9E Bridge `last_command` telemetry;
- UI command status matching by request ID;
- stale-command and duplicate-request protection.
- Phase 9F telemetry health/timing details;
- compact Live Monitor Bridge health display;
- explicit missing/stale/invalid/error explanation text.
- Phase 9G lifecycle ownership decision record;
- lifecycle wording and safety gates before launch/service/tray work.
- Phase 9H Bridge-owned read-only HOTAS discovery dry-run;
- Live Monitor discovery status wording that preserves output-unverified truth.
- Phase 9I UI-side process presence diagnostics;
- compact Live Monitor diagnosis text that preserves manual Bridge launch ownership.

Current local precheck for the Phase 9I pass:

- Thrustmaster driver/software detected: yes.
- vJoy detected: yes.
- HOTAS device detected: no, at precheck time.
- Runtime mode: `simulated`.
- Runtime truth: `blocked_missing_device`.
- Full Live Runtime Ready: false.
- Live output writes verified: false.

Deferred:

- real Bridge input/output implementation;
- Windows service/tray behavior;
- device-event auto-start/auto-stop;
- real HOTAS polling;
- continuous physical input streaming;
- real vJoy writes;
- socket/named-pipe/streaming IPC;
- UI pages for Bridge control;
- UI-launched Bridge process management.
