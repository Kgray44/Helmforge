# HelmForge Two-Part Architecture Clarification

## Purpose

This note explicitly clarifies that **HelmForge — HOTAS Control Panel V3** is not one single monolithic desktop app.

The software has two main parts:

1. **The Bridge** — the background/runtime control component.
2. **The UI App** — the full desktop configuration, diagnostics, and monitoring application.

This distinction must be preserved in future Codex prompts and implementation phases.

---

# Core Rule

```text
The Bridge owns real-time input/output.
The UI App owns configuration, visualization, diagnostics, and user interaction.
```

The UI should not be required to remain open for the configured HOTAS-to-vJoy processing to work once the Bridge is installed, configured, and running.

In other words: the cockpit dashboard is not the engine. The shiny buttons are lovely, but the Bridge is the thing actually moving electrons around like a tiny caffeinated goblin.

---

# Part 1 — The Bridge

## Role

The **Bridge** is the lightweight runtime/background component responsible for real-time HOTAS processing.

It should eventually run independently from the UI and handle live input/output with low latency.

## Responsibilities

The Bridge should eventually:

- detect the physical HOTAS device;
- specifically support the known target device:
  - **Thrustmaster T-Flight HOTAS One**;
  - also written as **Thrustmaster T.Flight Hotas One**;
- start automatically when the HOTAS is plugged in or becomes available;
- stop, suspend, or enter safe idle when the HOTAS is unplugged;
- read physical HOTAS axes, buttons, and hats;
- apply the active workspace configuration;
- apply axis mappings;
- apply base tuning;
- apply deadzone / anti-deadzone / hysteresis;
- apply curves and output limits;
- apply filtering and slew limiting;
- apply precision/combat modes;
- apply conditional rule injections;
- produce final processed output values;
- write final output to vJoy or the selected virtual output backend;
- expose runtime state and live telemetry to the UI;
- reload updated configuration when the UI saves or requests reload;
- remain low-latency and independent from expensive UI rendering;
- fail safely if HOTAS, vJoy, or drivers are missing.

## Bridge Runtime States

The Bridge should truthfully report states such as:

- `Simulated`
- `Waiting for HOTAS`
- `HOTAS Detected`
- `Thrustmaster Driver Unknown`
- `HOTAS Not Connected`
- `vJoy Missing`
- `vJoy Detected`
- `Output Unverified`
- `Output Verified`
- `Bridge Idle`
- `Bridge Live`
- `Bridge Suspended`
- `Output Error`
- `Input Error`
- `Full Live Runtime Ready`

`Full Live Runtime Ready` must only be used when both input and output are detected and verified.

## Bridge Lifecycle Goal

Final desired behavior:

```text
HOTAS plugged in   -> Bridge starts or wakes automatically.
HOTAS unplugged    -> Bridge stops, suspends, or safe-idles automatically.
UI opened          -> UI connects to Bridge and displays current state.
UI closed          -> Bridge may continue running if configured and safe.
Config saved       -> Bridge reloads or is instructed to reload config.
Runtime error      -> Bridge enters safe idle/error state and reports truthfully.
```

## Important Bridge Constraint

The Bridge must not depend on heavy UI rendering, graph drawing, overlay drawing, or Helm analysis to maintain real-time output.

The Bridge is the real-time path. Keep it boring, fast, testable, and honest.

---

# Part 2 — The UI App

## Role

The **UI App** is the full HelmForge desktop application.

It is the place where the user configures, inspects, diagnoses, records, and manages the HOTAS control system.

## Responsibilities

The UI App should:

- provide the main PySide6 desktop interface;
- show the product branding:
  - **HelmForge — HOTAS Control Panel V3**;
- configure mapping;
- configure modes;
- configure base tuning;
- configure filtering;
- configure combat profile;
- configure profiles and workspaces;
- configure conditional rules;
- display the Effective Response Stack;
- display Live Monitor telemetry;
- display Bridge/runtime status;
- provide Runtime Setup and vJoy/HOTAS setup guidance;
- run preflight checks;
- launch or control the Bridge when appropriate;
- request Bridge start/stop/restart/reload when appropriate;
- save workspace/config files;
- import/export profiles;
- provide Help / Docs;
- provide Perf / Diagnostics;
- host the Helm assistant overlay;
- manage the Live Overlay;
- manage Flight Recorder settings, library, and preview;
- show truthful runtime states instead of fake live claims.

## UI App Constraint

The UI App is allowed to be visually rich, but it must not block real-time Bridge processing.

Graphs, cards, Helm, overlays, diagnostics, and recorder UI must never become required for the low-latency HOTAS-to-vJoy path.

---

# Communication Between Bridge and UI

The final implementation should have a clear communication boundary between Bridge and UI.

Possible mechanisms may include:

- local process communication;
- local socket;
- named pipe;
- localhost API;
- shared state file plus runtime control channel;
- direct in-process mode during early development;
- background service/tray process later.

The exact mechanism is not decided yet.

However, the architectural boundary is required:

```text
UI writes configuration / requests actions.
Bridge reads configuration / processes input / publishes telemetry.
```

## Configuration Flow

Expected configuration flow:

1. User edits settings in the UI.
2. UI updates current workspace/draft.
3. User saves workspace.
4. UI writes `hotas_bridge_config_v3.json` or the chosen V3 config file.
5. UI tells Bridge to reload config, or Bridge detects the update safely.
6. Bridge applies the new configuration to future runtime samples.

## Telemetry Flow

Expected telemetry flow:

1. Bridge samples raw HOTAS input.
2. Bridge applies mapping/tuning/rules/output processing.
3. Bridge publishes raw values, final values, mode states, rule states, output status, and errors.
4. UI displays telemetry in Live Monitor, Effective Response Stack, Perf / Diagnostics, overlays, and recorder views.

---

# Simulation Mode

Simulation mode must remain available even after the real Bridge exists.

Simulation mode is used for:

- UI development;
- tests;
- graph previews;
- running the app without HOTAS connected;
- running the app without vJoy installed;
- validating Helm recommendations;
- validating recorder/overlay UI behavior.

Simulation mode should mimic Bridge snapshots but must be truthfully labeled as simulated.

---

# Codex Instruction Patch

Use this patch at the top of future Codex prompts when the Bridge/UI split matters:

```text
Architecture clarification:
HelmForge — HOTAS Control Panel V3 has two main parts:

1. Bridge:
   A lightweight background/runtime component that detects the Thrustmaster T-Flight HOTAS One, reads physical input, applies the active workspace mappings/tuning/filtering/modes/rules, writes final output to vJoy or the selected virtual output backend, and publishes telemetry. The Bridge should eventually auto-start or wake when the HOTAS is plugged in and stop/suspend/safe-idle when it is unplugged. The Bridge owns real-time input/output and must not depend on expensive UI rendering.

2. UI App:
   The PySide6 desktop application where the user configures mappings, tuning, modes, rules, profiles, Helm, Live Monitor, Effective Response Stack, Flight Recorder, Live Overlay, Help / Docs, and Perf / Diagnostics. The UI reads Bridge telemetry and writes/saves configuration, but it should not be required for real-time processing once the Bridge is configured and running.

Core rule:
The Bridge owns real-time input/output. The UI App owns configuration, visualization, diagnostics, and user interaction.

For current early phases, it is acceptable to keep Bridge behavior as an in-process service or simulation-backed adapter, but the code should preserve this boundary so it can become a background component later.
```

---

# Phase Impact

## Already completed phases

Phases 0, 1, 1A, and 2 have established:

- project foundation;
- runtime truth/status models;
- Thrustmaster setup guidance;
- simulation mode;
- workspace/schema models.

These should now be interpreted with the two-part architecture in mind.

## Near-term phases

Before real hardware/vJoy output work, future phases should avoid collapsing the Bridge into the UI.

Phase 3 math/signal pipeline should live in shared/core logic usable by the Bridge.

Phase 4 UI shell should display Bridge/runtime status, but not own the real-time processing path.

Phase 5 Mapping page should edit configuration that the Bridge can later consume.

Phase 14+ real input/output phases should turn the Bridge boundary into a real runtime service or background component.

---

# Bottom Line

HelmForge has two main parts:

```text
Bridge = real-time HOTAS input, processing, and vJoy output.
UI App = configuration, visualization, diagnostics, and user control.
```

Do not build one giant monolithic UI blob.

Do not make live HOTAS/vJoy processing depend on the settings window staying open.

The cockpit can be beautiful, but the Bridge is the engine room.

