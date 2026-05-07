# Phase 13A - Flight Recorder UI, State Model, Settings, and Clip Library Shell

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Flight Recorder UI/state/settings/library/preview shell only

## Summary

Phase 13A starts the prompt-book Phase 13 Flight Recorder work without adding capture or runtime authority. It replaces the Flight Recorder placeholder with a product UI shell, adds recorder settings/state models, adds a read-only clip library shell, adds a clip preview shell, and reuses Phase 12 shared axis colors for the recorder axis overlay settings.

## Implemented

New modules:

- `v3_app/recorder/recorder_settings.py`
- `v3_app/recorder/recorder_state.py`
- `v3_app/recorder/clip_library.py`
- `v3_app/pages/flight_recorder_page.py`

Updated surfaces:

- Flight Recorder navigation now opens the recorder page shell.
- Help / Docs Graphs and Previews article mentions Phase 13A recorder scope.
- README, Bridge/UI architecture, and Bridge service design document Phase 13A boundaries.

## Recorder Settings

Default settings:

- Destination folder ends in `hotas_recordings_v3`
- Length: 20 s
- Frame Rate: 30 fps
- History: 6.00 s
- Overlay Source: Final output
- Capture Source: Current display
- Display: Current display
- Hotkey: Ctrl+Shift+F10
- Record the cursor: true
- Trigger Mode: Press to save previous interval
- Hotkey registered: false
- Capture backend available: false
- Encoder available: false
- Compositor available: false
- Hindsight video buffer available: false

The settings model supports dict round-trip, restore defaults, and safe validation/clamping for length, frame rate, and history.

## Recorder State

Recorder states include:

- idle
- ready
- recording_forward_unavailable
- buffering_unavailable
- saving_unavailable
- capture_backend_missing
- compositor_unavailable
- error

Phase 13A defaults to `capture_backend_missing`.

## Flight Recorder Page

The page includes:

- Recorder Settings
- Axis Overlay
- Recording Library
- Clip Preview

Truthful status chips include:

- UI Ready
- Capture backend missing
- Hotkey not registered
- Final output source
- Buffering unavailable
- Recording unavailable

The page also shows runtime truth, output verification truth, Full Live Runtime Ready truth, capture backend truth, recorder mode, hotkey status, and hindsight video buffering truth.

## Axis Overlay

Axis Overlay uses the shared Phase 12 colors:

- Roll: `#58B8FF`
- Pitch: `#6FDB9F`
- Throttle: `#F0C46A`
- Yaw: `#CF95FF`
- Aux 1: `#FF9B6B`
- Aux 2: `#6ED9D0`

## Library And Preview Shells

The Recording Library shell includes:

- Sort: Newest First
- Refresh button
- Columns: Clip, Recorded, Duration, Opened
- Empty state: No clips recorded yet. Recording backend is not active in this phase.

The Clip Preview shell includes:

- unavailable preview area;
- disabled Play button;
- disabled timeline;
- disabled Reveal File button;
- metadata line with filename, overlay source, resolution, and length.

## Runtime Truth

Observed conservative runtime truth during verification:

- Bridge lifecycle: `Simulated`
- Runtime truth: `blocked_missing_device`
- HOTAS status: HOTAS Not Connected
- vJoy status: vJoy Detected
- vJoy detected, output writes unverified
- `output_verified`: `false`
- Full Live Runtime Ready: `false`

## Boundary

Phase 13A does not add:

- real desktop capture;
- video encoding;
- actual clip export;
- actual hindsight video buffering;
- recorder global hotkey registration;
- screen capture;
- graphics API hooking;
- game injection;
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
- real runtime activation;
- cloud AI or LLM behavior;
- auto-save.

## Verification

Final verification results:

- `python -m pytest` - passed, 273 tests.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - passed, 7 tests.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - passed, 6 tests.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - passed, 5 tests.
- `python -m pytest tests\test_phase13a_flight_recorder_ui_foundation.py` - passed, 8 tests.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed with `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed. Thrustmaster software detected, vJoy detected, HOTAS Not Connected, Simulation Mode Active unless physical input and output writes are both verified, Full Live Runtime Ready false, and no installers launched.
- `git diff --check` - passed.

## Deferred

Deferred to later reviewed phases:

- real capture backend;
- video encoding;
- actual clip export;
- hindsight video buffering;
- recorder global hotkey registration;
- clip playback preview;
- clip indexing beyond the read-only shell;
- real HOTAS/vJoy runtime work.
