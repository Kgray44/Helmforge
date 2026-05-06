# Bridge/UI Architecture

Status: Phase 9B boundary skeleton implemented. Shared contracts exist and `bridge_app` can run as a separate simulation-only Python process, but real HOTAS polling, vJoy writes, output verification, Windows Service install, and login auto-start are not implemented yet.

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

## UI App Responsibilities

The UI App owns the human-facing surface:

- present HelmForge branding and the HOTAS Control Panel V3 technical subtitle;
- edit mappings, modes, base tuning, filtering, combat profile, profiles, workspaces, and conditional rules;
- save and load `hotas_bridge_config_v3.json`;
- request Bridge start/stop/restart/suspend/reload/preflight actions;
- display Bridge telemetry in Live Monitor and Effective Response Stack views;
- display runtime setup, help/docs, performance, and diagnostics;
- host future Helm assistant, Flight Recorder, and Live Overlay UI;
- show truthful runtime state rather than fake live claims.

The UI may run Bridge-like adapters in-process during early development, but real-time processing should remain behind shared-core contracts so it can move to a background component later.

## Communication Boundary

The final IPC mechanism is still intentionally undecided. Phase 9B uses a simple local JSON telemetry file and JSON command file as the first development IPC seam. Candidate later mechanisms include:

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
3. Bridge publishes raw axes, final axes, buttons, hats, active modes, rule counts, output verification state, warnings, and errors.
4. UI reads and renders telemetry in monitor, graph, diagnostics, overlay, recorder, and assistant surfaces.

Phase 2B telemetry contracts are defined in `shared_core/runtime/telemetry.py`. Phase 9B Bridge telemetry is written as JSON shaped from those contracts.

## Runtime Truth Rules

- `Full Live Runtime Ready` is allowed only when physical input and output writes are both detected and verified.
- vJoy detected is not the same thing as output verified.
- HOTAS detected is not the same thing as real polling implemented.
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

Current local precheck for the Phase 9B pass:

- Thrustmaster driver/software detected: yes.
- vJoy detected: yes.
- HOTAS device detected: yes, at precheck time.
- Runtime mode: `simulated`.
- Runtime truth: `detected_unverified`.
- Full Live Runtime Ready: false.
- Live output writes verified: false.

Deferred:

- real Bridge input/output implementation;
- Windows service/tray behavior;
- device-event auto-start/auto-stop;
- real HOTAS polling;
- real vJoy writes;
- socket/named-pipe/streaming IPC;
- UI connection to Bridge telemetry;
- UI pages for Bridge control.
