# Post-RC 3C - One-Frame Capture Proof Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Explicit one-frame Flight Recorder capture proof only

## Summary

Post-RC 3C extends the Post-RC 3A capture backend seam with an explicit one-frame proof call and a small Flight Recorder proof surface. The proof is manual, typed, and local. It does not start recording, does not run a capture loop, does not create a video buffer, does not encode video, does not add a playable preview, and does not register a global recorder hotkey.

## Backend interface changes

The recorder capture backend now exposes `capture_one_frame(...)` returning `FrameCaptureResult`. The result records success, backend name/kind, display/source identity, timestamp, frame dimensions when available, pixel format when known, optional diagnostic artifact path, warnings, errors, a truth label, and explicit `real_capture` / `simulated_capture` flags.

The capability model also has one-frame proof fields separate from recording support. This keeps a still-frame proof distinct from the existing broader `frame_capture_available` and `real_capture_supported` recorder pipeline fields.

## One-frame proof behavior

The missing backend returns a typed unavailable result. The default simulated backend remains metadata-only and does not claim a real desktop proof. Test/fake backends can return deterministic proof metadata for focused tests, and those results remain labeled as simulated.

The Qt candidate remains guarded. It can only attempt one explicit still-frame proof when Qt is available, a real GUI display context exists, and the selected display/source is available. The call is one frame only.

## Unavailable/offscreen behavior

Unavailable dependency, missing display/source, missing Qt app context, and offscreen/test contexts return a typed unavailable result instead of crashing. Offscreen proof attempts do not write files and do not claim desktop capture.

## Diagnostic artifact behavior

When a real Qt still frame is captured, the backend writes a local JSON metadata proof artifact under the configured recorder destination folder. The artifact uses a deterministic `one_frame_capture_proof_*.json` name with suffixing to avoid silent overwrite. It is labeled as still-frame proof metadata, not a recording, not encoded output, and not previewable video.

No MP4, WebM, or other video extension is produced in this phase.

## UI proof behavior

The Flight Recorder page now includes a Capture Proof card showing backend status, dependency status, display/source, one-frame proof availability, last proof result, frame dimensions, pixel format, artifact path, warnings/errors, truth label, and real/simulated capture flags.

The `Try One-Frame Capture` button is enabled only when the controller reports proof availability. The card explicitly says: still-frame proof, not video recording, not encoded, not previewable video, and no global hotkey registered.

## Preserved 3B review/export behavior

The 3B review/export path remains separate. Session review summaries, timeline summaries, JSON summary export, CSV sample export, and clear-reviewed-session behavior are preserved. One-frame proof results do not replace recorder review truth and do not mark a session as live verified.

## What remains for 3D frame buffering

Post-RC 3D still needs any real frame buffer, repeated capture loop, timestamped ring buffer, frame/telemetry synchronization, memory budget, dropped-frame tracking, and intermediate Save Last Clip artifact behavior. None of that is implemented in 3C.

## Files changed

- `v3_app/recorder/capture_backend.py`
- `v3_app/recorder/recorder_controller.py`
- `v3_app/pages/flight_recorder_page.py`
- `v3_app/services/help_docs.py`
- `tests/test_post_rc_3c_one_frame_capture_proof.py`
- `docs/HelmForge/post-rc-3c-one-frame-capture-proof-report.md`

## Tests run

- `python -m pytest tests/test_post_rc_3a_recorder_capture_backend_seam.py -q` - passed, 6 tests.
- `python -m pytest tests/test_post_rc_3b_flight_recorder_review_export.py -q` - passed, 6 tests.
- `python -m pytest tests/test_post_rc_3c_one_frame_capture_proof.py -q` - passed, 9 tests.
- `python -m pytest tests/test_phase13d_flight_recorder_boundary_freeze.py -q` - passed, 7 tests.
- `python -m pytest tests/test_phase19d_final_acceptance_report.py -q` - passed, 5 tests.
- `python -m pytest tests/test_phase13b_recorder_backend_hindsight_foundation.py -q` - passed, 7 tests.
- `python -m pytest tests/test_post_rc_2a_mapping_hotas_diagram.py -q` - passed, 7 tests after the full-suite mapping failures reproduced there only in broad order.
- `python -m pytest tests/test_post_rc_2c_mapping_diagram_editing.py -q` - passed, 14 tests after the full-suite mapping failures reproduced there only in broad order.
- `python -m pytest tests/test_post_rc_2a_mapping_hotas_diagram.py tests/test_post_rc_2c_mapping_diagram_editing.py -q` - passed, 21 tests.
- `python -m pytest -q` - failed with 487 passed and 6 failed. The failures were all in Post-RC 2A/2C Mapping tests and passed when those Mapping files were rerun in isolation/together; no recorder test failed.

## Smoke/runtime setup validation

- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --status` - passed; reported `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; dry run only, HOTAS not connected, vJoy detected, Full Live Runtime Ready still governed by the Phase 16 proof gate.
- `git diff --check` - passed.

## Runtime truth preservation

Telemetry remains the truth surface. Capture proof is not runtime readiness. A still frame is not a video recording. Simulated/test capture is not real desktop capture. Output intent is not output write proof. vJoy detected is not output verification. Packaged smoke is not runtime readiness. Full Live Runtime Ready gates were not weakened.

No continuous capture, hindsight video buffer, video recording, video encoding, MP4/WebM export, playable preview, global recorder hotkeys, hardware polling, vJoy behavior changes, output verification changes, Bridge lifecycle behavior, game injection, graphics API hooking, admin-level capture, cloud AI/LLM behavior, or auto-save was added.
