# Phase 12A - Live Overlay Core, Config Model, and Live Monitor Card

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Live Overlay core/config foundation only

## Summary

Phase 12A implements the Live Overlay foundation layer. It adds shared overlay configuration, shared axis colors, a telemetry history buffer, a trace-building core, a Live Monitor Live Overlay card, and a Live Overlay Configuration dialog shell.

At Phase 12A completion, detached overlay rendering was deferred to Phase 12B. Phase 12B now supersedes that deferral by adding the app-owned detached overlay window and renderer while preserving the same runtime boundary.

## Implemented Core

New overlay modules:

- `v3_app/overlay/axis_colors.py`
- `v3_app/overlay/overlay_config.py`
- `v3_app/overlay/telemetry_buffer.py`
- `v3_app/overlay/trace_builder.py`
- `v3_app/overlay/config_dialog.py`

The core is simulation/runtime-snapshot friendly and does not require real HOTAS hardware.

## Axis Colors

Recovered defaults are centralized:

- Roll: `#58B8FF`
- Pitch: `#6FDB9F`
- Throttle: `#F0C46A`
- Yaw: `#CF95FF`
- Aux 1: `#FF9B6B`
- Aux 2: `#6ED9D0`

These colors are shared for future Flight Recorder reuse. Flight Recorder is not implemented in Phase 12A.

## Overlay Configuration

The default config is serializable and round-trippable. Defaults include:

- preset: Custom
- visible: false
- source: Final output
- history: 7.50 seconds
- position: Bottom strip
- margin: 18 px
- attach mode: Attach to display
- width: Standard
- height: 0.60
- opacity: 0.66
- background: 0.82
- line thickness: 2.80
- legend and live values enabled
- always on top true
- click-through false
- FPS cap 60
- toggle hotkey Ctrl+Shift+F9
- hotkey registered false
- click-through support unknown

Validation clamps opacity, background, line thickness, FPS cap, height, margin, and history into safe ranges.

## Telemetry Buffer And Trace Builder

`OverlayTelemetryBuffer` stores bounded timestamped samples with six axis values and a source label.

`build_overlay_traces` converts samples into plain trace data:

- included axes only;
- recovered axis colors;
- normalized/clamped axis values;
- relative timestamps;
- no Qt painter object;
- no detached renderer in Phase 12A.

## Live Monitor Card

Live Monitor includes a Live Overlay card with:

- Preset: Custom
- Status: Inactive
- Attached display: Current display
- Toggle: Ctrl+Shift+F9
- Summary: Custom | Bottom strip | 66% opacity | Final output
- Runtime truth
- Output verified false
- Full Live Runtime Ready false
- Hotkey status Not registered
- Click-through not verified

The Show Overlay button was disabled at Phase 12A completion because detached overlay rendering was not implemented yet. Phase 12B enables Show/Hide through the real detached overlay window. Configure opens the configuration dialog shell.

## Configuration Dialog

The dialog title is:

`Live Overlay Configuration - HOTAS Control Panel V3`

It includes:

- Placement
- Appearance
- Behavior
- Data
- Axes

Restore Defaults restores the dialog draft. OK applies the draft to the in-memory Live Monitor overlay config. Cancel discards dialog edits.

No auto-save is added.

## Runtime Boundary

Overlay telemetry can use simulation/runtime snapshots, but Phase 12A does not create live hardware runtime.

Phase 12A does not add:

- Flight Recorder;
- real HOTAS polling;
- live physical input streaming;
- vJoy writes;
- output verification;
- automatic Bridge launch;
- UI-launched child process;
- service install;
- login auto-start;
- tray manager;
- installer launch;
- StartBridge/StopBridge/RestartBridge behavior;
- real process scanner;
- global hotkey registration;
- click-through support;
- game injection;
- graphics API hooking;
- cloud AI or LLM behavior;
- auto-save;
- real runtime activation.

## Current Runtime Truth

Current conservative runtime truth remains:

- Bridge lifecycle: `Simulated`
- Runtime truth: `blocked_missing_device`
- HOTAS discovery: `no_supported_device` unless read-only discovery sees a supported device
- vJoy detected, output writes unverified
- `output_verified`: `false`
- Full Live Runtime Ready: `false`

## Verification

Final verification results:

- `python -m pytest` - passed, 254 tests.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - passed, 7 tests.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11a_help_docs_foundation.py` - passed, 8 tests.
- `python -m pytest tests\test_phase11b_perf_diagnostics_page.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - passed, 6 tests.
- `python -m pytest tests\test_phase12a_live_overlay_foundation.py` - passed, 6 tests.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed with `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed. Thrustmaster software detected, vJoy detected, HOTAS Not Connected, Simulation Mode Active unless physical input and output writes are both verified, Full Live Runtime Ready false, and no installers launched.
- `git diff --check` - passed.

## Deferred

Deferred to later reviewed phases after Phase 12A:

- detached overlay rendering, now implemented by Phase 12B;
- live overlay window positioning, now minimally implemented by Phase 12B bottom-strip placement;
- real hotkey registration;
- click-through implementation;
- Flight Recorder reuse;
- any real HOTAS/vJoy runtime work.
