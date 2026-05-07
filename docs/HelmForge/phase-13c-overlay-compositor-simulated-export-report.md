# Phase 13C - Overlay Compositor and Simulated Clip Export

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Flight Recorder compositor/export architecture and simulated non-video export bundles only

## Summary

Phase 13C adds a recorder compositor abstraction and deterministic simulated export pipeline. The pipeline can create metadata/trace export bundles from telemetry hindsight samples and Phase 12 overlay trace concepts. These bundles are not recordings and contain no playable video.

## Implemented

New module:

- `v3_app/recorder/compositor.py`

Updated modules:

- `v3_app/recorder/recorder_artifacts.py`
- `v3_app/recorder/recorder_controller.py`
- `v3_app/recorder/clip_library.py`
- `v3_app/pages/flight_recorder_page.py`
- `v3_app/recorder/__init__.py`
- `v3_app/services/help_docs.py`

New test:

- `tests/test_phase13c_recorder_compositor_simulated_export.py`

## Compositor Model

Phase 13C defines:

- `RecorderCompositorCapabilities`
- `RecorderCompositorStatus`
- `RecorderCompositor`
- `MissingRecorderCompositor`
- `SimulatedRecorderCompositor`
- `SimulatedExportResult`

The missing compositor reports unavailable and creates no files.

The simulated compositor reports:

- real video compositing unavailable;
- simulated export available;
- overlay trace rendering available;
- preview metadata available;
- warnings that no real video compositing exists.

## Simulated Export Bundle

The simulated compositor writes a folder such as:

- `simulated_export_<timestamp>/`

Allowed files:

- `manifest.json`
- `overlay_trace.json`
- `summary.md`
- `preview_metadata.json`

It does not create `.mp4`, `.webm`, `.avi`, `.mov`, or any other fake playable video file.

Each simulated export states:

- simulated recorder export;
- not real desktop capture;
- no screen frames captured;
- no video encoding performed;
- overlay trace data generated from telemetry samples;
- no vJoy/output verification;
- no Full Live Runtime Ready claim.

## Overlay Trace Reuse

Phase 13C reuses Phase 12 overlay trace concepts:

- shared recovered axis colors;
- `build_overlay_traces`;
- recorder axis include/exclude settings;
- overlay source `Final output`;
- telemetry sample count;
- included axis list.

## Metadata

`RecorderExportMetadata` stores:

- export/clip id;
- artifact kind;
- export folder path;
- manifest path;
- duration and frame rate;
- overlay/capture/display labels;
- telemetry sample count;
- included axes;
- simulated/non-video truth;
- real-capture truth;
- overlay-trace truth;
- compositor backend;
- capture backend;
- warnings.

The metadata supports dict and JSON round-trips.

## Controller And UI Integration

With missing capture/compositor backends:

- Record Now remains unavailable;
- Save Last Clip remains unavailable;
- no files are written;
- no recording or clip-saved claim is shown.

With explicitly injected simulated capture and simulated compositor backends:

- Record Now or Save Last Clip may create a simulated export bundle;
- the result says `Simulated export created`;
- Recording Library labels it as a simulated/no-video artifact;
- Clip Preview shows metadata-only details;
- Play remains disabled.

Telemetry hindsight can feed simulated overlay trace exports. Desktop video hindsight buffering remains unavailable.

## Runtime Truth

Phase 13C preserves the conservative runtime truth:

- Bridge lifecycle: `Simulated`
- Runtime truth: `blocked_missing_device`
- HOTAS status: HOTAS Not Connected
- vJoy status: vJoy Detected
- vJoy detected, output writes unverified
- `output_verified`: `false`
- Full Live Runtime Ready: `false`

## Boundary

Phase 13C does not add:

- real desktop capture;
- real screen capture APIs;
- real playable video encoding;
- real MP4/WebM/AVI export;
- actual desktop video hindsight buffering;
- recorder global hotkey registration;
- game injection;
- DirectX/OpenGL/Vulkan hooking;
- admin-level capture;
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

- `python -m pytest` - passed, 287 tests.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - passed, 7 tests.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - passed, 6 tests.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - passed, 5 tests.
- `python -m pytest tests\test_phase13a_flight_recorder_ui_foundation.py` - passed, 8 tests.
- `python -m pytest tests\test_phase13b_recorder_backend_hindsight_foundation.py` - passed, 7 tests.
- `python -m pytest tests\test_phase13c_recorder_compositor_simulated_export.py` - passed, 7 tests.
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
- playable clip export;
- desktop video hindsight buffering;
- recorder global hotkey registration;
- clip playback preview;
- broader clip indexing;
- real HOTAS/vJoy runtime work.
