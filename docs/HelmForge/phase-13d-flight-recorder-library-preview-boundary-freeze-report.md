# Phase 13D - Flight Recorder Library, Preview, and Boundary Freeze

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Flight Recorder library/metadata preview polish and final Phase 13 boundary freeze

## Summary

Phase 13D finalizes the prompt-book Phase 13 Flight Recorder work. It polishes the Recording Library artifact index, metadata-only Clip Preview, simulated export wording, Help / Docs copy, and final boundary tests. It does not add real capture, video encoding, playable export, recorder hotkey registration, or runtime authority.

Phase 13 is now complete.

Next prompt-book phase is Phase 14: Real HOTAS Input Integration.

Phase 14 must preserve simulation mode.

Phase 14 must not add vJoy writes/output verification unless a later output phase explicitly scopes that work.

## Phase 13A Summary

Phase 13A added the Flight Recorder page shell:

- Recorder Settings card;
- Axis Overlay card using shared Phase 12 colors;
- Recording Library shell;
- Clip Preview shell;
- recorder settings model;
- recorder state model;
- truthful unavailable status for capture, encoder, compositor, hindsight video buffer, and hotkey.

## Phase 13B Summary

Phase 13B added recorder backend interfaces and telemetry hindsight:

- missing capture backend;
- simulated/test capture backend;
- recorder artifact model;
- telemetry hindsight buffer;
- recorder controller/service;
- simulated non-video manifest behavior.

## Phase 13C Summary

Phase 13C added compositor/export foundations:

- missing compositor;
- simulated compositor/exporter;
- simulated export bundles;
- overlay trace export metadata;
- Flight Recorder simulated export display;
- metadata-only preview for simulated exports.

## Phase 13D Polish And Freeze

Phase 13D finalizes:

- Recording Library scanning of simulated export manifests;
- graceful handling for missing folders and unknown files;
- newest-first sorting for recorder artifacts;
- clearer library columns: Artifact or Clip, Created/Recorded, Duration, Opened;
- metadata-only preview selection for simulated exports;
- status/action copy that avoids real recording claims;
- Help / Docs wording for recorder boundaries;
- final Phase 13 boundary tests.

## Final Flight Recorder Behavior

The Flight Recorder page now shows:

- Recorder Settings;
- Axis Overlay;
- Recording Library;
- Clip Preview;
- runtime truth;
- capture/compositor/hotkey truth;
- telemetry/video hindsight truth.

Recording Library reads simulated export manifests created by the Phase 13C simulated export pipeline. Unknown files are ignored. Missing destination folders are safe and show an empty state.

Clip Preview for simulated exports shows:

- simulated export title;
- metadata-only preview;
- no video preview available;
- no desktop frames were captured;
- no encoding was performed;
- overlay source;
- duration;
- frame rate;
- telemetry sample count;
- included axes;
- artifact path;
- manifest path;
- warnings.

Play and timeline remain disabled for simulated/non-video artifacts.

## Current Runtime Truth

Conservative runtime truth remains:

- Bridge lifecycle: `Simulated`
- Runtime truth: `blocked_missing_device`
- HOTAS: Not Connected unless discovery proves otherwise
- vJoy: Detected if current dry-run sees it, but output writes remain unverified
- `output_verified`: `false`
- Full Live Runtime Ready: `false`

## Recorder Truth

Recorder truth remains:

- default capture backend: missing;
- encoder: unavailable;
- real video capture: unavailable;
- compositor: unavailable by default or simulated when explicitly injected;
- recorder hotkey: Ctrl+Shift+F10 text only;
- hotkey status: Not registered;
- telemetry hindsight: available for simulated metadata/trace export;
- video hindsight: unavailable.

## Simulated Export Truth

Simulated exports are metadata/trace artifacts only:

- simulated exports are not real recordings;
- no screen capture or video encoding is implemented;
- no desktop frames are captured;
- no playable MP4/WebM/AVI/MOV export is created;
- telemetry hindsight is separate from video hindsight;
- Live Overlay colors and traces are reused.

## Final Phase 13 Boundary

Phase 13D does not add:

- real desktop capture;
- real screen capture APIs;
- real playable video encoding;
- real MP4/WebM/AVI/MOV export;
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

- `python -m pytest` - passed, 294 tests.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - passed, 7 tests.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - passed, 6 tests.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - passed, 5 tests.
- `python -m pytest tests\test_phase13a_flight_recorder_ui_foundation.py` - passed, 8 tests.
- `python -m pytest tests\test_phase13b_recorder_backend_hindsight_foundation.py` - passed, 7 tests.
- `python -m pytest tests\test_phase13c_recorder_compositor_simulated_export.py` - passed, 7 tests.
- `python -m pytest tests\test_phase13d_flight_recorder_boundary_freeze.py` - passed, 7 tests.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed with `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed. Thrustmaster software detected, vJoy detected, HOTAS Not Connected, Simulation Mode Active unless physical input and output writes are both verified, Full Live Runtime Ready false, and no installers launched.
- `git diff --check` - passed.

## Recommendation For Phase 14

Phase 14 should begin Real HOTAS Input Integration conservatively. It should preserve simulation mode, keep telemetry as the truth surface, and avoid vJoy writes/output verification unless a later output phase explicitly scopes that work. Phase 14 should prove read-only real input discovery/input sampling before making any output or readiness claims.
