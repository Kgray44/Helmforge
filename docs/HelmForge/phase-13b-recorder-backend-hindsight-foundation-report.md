# Phase 13B - Recorder Backend Interfaces and Hindsight Buffer Foundation

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Flight Recorder backend interfaces, simulated artifacts, and telemetry hindsight only

## Summary

Phase 13B adds the first backend-facing Flight Recorder seams while preserving the Phase 13 safety boundary. The default recorder still has no real capture backend, no video encoder, no video hindsight buffer, and no registered recorder hotkey. A deterministic simulated backend can be injected by tests or development code to write a clearly labeled JSON manifest artifact, but that artifact is not a playable desktop recording.

## Implemented

New modules:

- `v3_app/recorder/capture_backend.py`
- `v3_app/recorder/recorder_artifacts.py`
- `v3_app/recorder/hindsight_buffer.py`
- `v3_app/recorder/recorder_controller.py`

Updated modules:

- `v3_app/pages/flight_recorder_page.py`
- `v3_app/recorder/clip_library.py`
- `v3_app/recorder/__init__.py`
- `v3_app/services/help_docs.py`

New test:

- `tests/test_phase13b_recorder_backend_hindsight_foundation.py`

## Capture Backend Interface

The capture backend seam reports capabilities instead of implying readiness:

- desktop capture available;
- frame capture available;
- cursor capture available;
- video encoding available;
- simulated artifact available;
- backend name;
- backend kind.

`MissingCaptureBackend` is the default. It reports capture unavailable, encoding unavailable, and writes no files.

`SimulatedCaptureBackend` is deterministic and explicit. It can create JSON manifest artifacts only when injected. It does not capture the desktop, capture frames, encode video, or register hotkeys.

## Simulated Artifact Truth

Simulated artifacts are JSON manifests named like:

- `simulated_recorder_artifact_<timestamp>.json`

Each manifest states:

- simulated recorder artifact;
- not real desktop capture;
- no video frames captured;
- no encoding performed.

Artifact metadata includes:

- `is_simulated: true`
- `has_video: false`
- backend name;
- overlay source;
- capture source;
- duration;
- frame rate;
- warnings and notes.

The Recording Library can list simulated manifests as metadata-only artifacts. Clip Preview shows metadata-only status and keeps Play disabled.

## Telemetry Hindsight

Phase 13B adds telemetry hindsight only:

- timestamped axis telemetry samples;
- configurable history window;
- previous-interval retrieval;
- deterministic timestamp injection for tests.

Desktop video hindsight buffering remains unavailable and deferred. `Save Last Clip` cannot save real video until a future capture and buffer backend exists.

## Controller Behavior

`FlightRecorderController` coordinates:

- recorder settings;
- capture backend status;
- telemetry hindsight;
- simulated artifact creation;
- UI status messages.

Default missing-backend behavior:

- `Record Now` reports recording unavailable;
- `Save Last Clip` reports video hindsight unavailable;
- no files are written.

Injected simulated-backend behavior:

- `Record Now` or `Save Last Clip` may write a simulated JSON manifest;
- the UI says `Simulated artifact saved`;
- the artifact remains metadata-only and non-video.

## Runtime Truth

Phase 13B preserves the conservative runtime truth:

- Bridge lifecycle: `Simulated`
- Runtime truth: `blocked_missing_device`
- HOTAS discovery: no supported physical runtime input unless read-only discovery says otherwise
- vJoy may be detected, but output writes are unverified
- `output_verified`: `false`
- Full Live Runtime Ready: `false`

## Boundary

Phase 13B does not add:

- real desktop capture;
- real screen capture APIs;
- real video encoding;
- real clip export as playable video;
- actual desktop video hindsight buffering;
- recorder global hotkey registration;
- screen capture;
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

- `python -m pytest` - passed, 280 tests.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - passed, 7 tests.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - passed, 6 tests.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - passed, 5 tests.
- `python -m pytest tests\test_phase13a_flight_recorder_ui_foundation.py` - passed, 8 tests.
- `python -m pytest tests\test_phase13b_recorder_backend_hindsight_foundation.py` - passed, 7 tests.
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
- actual playable clip export;
- desktop video hindsight buffering;
- recorder global hotkey registration;
- clip playback preview;
- broader clip indexing;
- real HOTAS/vJoy runtime work.
