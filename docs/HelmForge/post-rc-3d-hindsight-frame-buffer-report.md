# Post-RC 3D - Hindsight Frame Buffer and Capture Pipeline Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Explicit-start recorder frame-buffer metadata pipeline only

## Summary

Post-RC 3D adds the next recorder infrastructure step after the 3C one-frame proof: a safe hindsight frame buffer that stores typed frame references/metadata and can save an intermediate local JSON artifact. It does not encode video, export MP4/WebM, add playable preview, register global recorder hotkeys, or change runtime readiness.

## Buffer model

The new frame buffer tracks max duration, target FPS, max frame count, stored frame count, dropped frame count, oldest/newest timestamps, buffer duration, display/source identity, frame dimensions, pixel format, health, warnings, and errors. It enforces monotonic timestamps and drops older/non-monotonic frame entries.

This phase stores frame references and metadata only. It does not retain heavy pixel data or image sequences as the durable recorder output.

## Capture pipeline behavior

The controller exposes explicit frame-buffer availability, start, stop, and single-sample capture operations. Frame capture uses the existing 3C `capture_one_frame(...)` backend seam and writes successful results into the ring buffer as metadata references.

The pipeline does not start at app launch. It does not run through a global hotkey. It does not create a background encoder. Repeated backend failures increment dropped-frame tracking and stop the buffer after repeated failures.

## Start/stop behavior

Start is allowed only when the backend dependency is available, a display/source exists, and the backend reports one-frame/frame-buffer support. Start clears the previous buffer and marks the buffer active. Stop marks it inactive without deleting captured metadata. Controller shutdown stops the buffer.

## Telemetry sync

Save Last Clip aligns existing telemetry samples to the frame-buffer interval. Samples outside the oldest/newest frame timestamps are excluded. Runtime truth, output verification, and Full Live Runtime Ready are copied from the provided runtime status when available; missing runtime status is labeled unavailable rather than invented.

## Intermediate artifact format

Save Last Clip can now write `intermediate_frame_buffer_*.json` when the frame buffer contains usable frame metadata. The artifact includes frame-buffer status, frame references, aligned telemetry samples, runtime truth, optional timeline summary, and warnings.

The artifact is explicitly labeled `not_encoded`, `not_playable`, and not a video recording. It has no MP4/WebM extension and no playable preview claim.

## UI changes

The Flight Recorder page now has a Frame Buffer card showing buffer state, health, availability, display/source, duration, stored frames, dropped frames, frame budget, frame interval, dimensions, pixel format, aligned telemetry count, last intermediate save state, warnings, and errors.

Buttons added:

- `Start Buffer`
- `Stop Buffer`

`Save Last Clip` is enabled only when frame-buffer metadata exists. The existing Capture Proof card and `Try One-Frame Capture` remain separate.

## Preserved 3B/3C behavior

Post-RC 3B review summaries, timeline summaries, JSON summary export, CSV sample export, and clear-reviewed-session behavior are preserved. Post-RC 3C one-frame proof and the Capture Proof card remain separate from frame buffering.

## Limitations

- No video encoding.
- No MP4/WebM export.
- No playable video preview.
- No persistent image sequence.
- No global recorder hotkey.
- No automatic capture on app launch.
- No Bridge lifecycle behavior.
- No hardware polling outside the recorder capture backend seam.

## What remains for 3E encoding

Post-RC 3E still needs an encoder backend, dependency/packaging behavior, output format selection, overlay compositing into frames, encoded artifact truth labels, and any preview/reveal workflow that can truthfully prove a playable clip.

## Tests run

- `python -m pytest tests/test_post_rc_3a_recorder_capture_backend_seam.py -q` - passed, 6 tests.
- `python -m pytest tests/test_post_rc_3b_flight_recorder_review_export.py -q` - passed, 6 tests.
- `python -m pytest tests/test_post_rc_3c_one_frame_capture_proof.py -q` - passed, 9 tests.
- `python -m pytest tests/test_post_rc_3d_hindsight_frame_buffer.py -q` - passed, 10 tests.
- `python -m pytest tests/test_phase13d_flight_recorder_boundary_freeze.py -q` - passed, 7 tests.
- `python -m pytest tests/test_phase19d_final_acceptance_report.py -q` - passed, 5 tests.
- `python -m pytest tests/test_post_rc_1d_help_docs_full_overhaul.py -q` - passed, 7 tests when rerun to classify broad-suite Help / Docs failures.
- `python -m pytest tests/test_phase11a_help_docs_foundation.py -q` - passed, 8 tests when rerun to classify broad-suite Help / Docs failures.
- `python -m pytest -q` - failed with 504 passed and 6 failed. The failures were all Help / Docs 11A/1D assertions and passed when those Help / Docs files were rerun directly; no recorder test failed.

## Smoke/runtime setup validation

- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --status` - passed; reported `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; dry run only, HOTAS not connected, vJoy detected, and Full Live Runtime Ready remains governed by the Phase 16 proof gate.
- `git diff --check` - passed.

## Runtime truth preservation

Telemetry remains the truth surface. Capture buffer is not runtime readiness. Buffered frames are not encoded video. Intermediate artifacts are not playable clips. Simulated/test capture is not real desktop capture. Output intent is not output write proof. vJoy detected is not output verification. Packaged smoke is not runtime readiness. Full Live Runtime Ready gates were not weakened.

No video encoding, MP4/WebM export, playable preview, global recorder hotkeys, game injection, graphics API hooking, admin-level capture, cloud upload/share, Bridge auto-launch/control/service/tray/autostart behavior, unrelated hardware polling, vJoy behavior changes, or output verification changes were added.
