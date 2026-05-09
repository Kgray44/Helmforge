# Post-RC 3E - Encoding, Export, and Preview Integration Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Safe Flight Recorder encoding/export/preview integration

## Summary

Post-RC 3E adds a conservative local encoding/export layer on top of the Post-RC 3D frame-buffer metadata pipeline. The default app remains encoder-unavailable unless an encoder backend is explicitly present, and a playable clip claim is allowed only after encoding succeeds and the output file passes basic local verification.

This phase does not add runtime authority, Bridge lifecycle behavior, unrelated hardware polling, vJoy writes, global recorder hotkeys, game injection, graphics API hooking, admin-level capture, cloud upload/share, cloud AI/LLM behavior, auto-save, or Full Live Runtime Ready changes.

## Encoder Backend Model

The new `v3_app.recorder.encoding_backend` module defines:

- `EncoderCapability`
- `EncoderResult`
- `EncodableFrameSource`
- `EncoderExportJob`
- `EncoderBackend`
- `MissingEncoderBackend`
- `SimulatedTestEncoderBackend`

`EncoderCapability` reports backend name/kind, dependency availability, version, supported formats, video/audio/overlay capabilities, external binary requirements, binary path, warnings, and errors.

`EncoderResult` reports success, output path, output existence, output size, frame/duration metadata, playable-claim permission, verification summary, warnings, errors, and truth label.

## Encoder Backend Selected

The production default is `MissingEncoderBackend`, which reports encoding unavailable and does not crash app startup. The deterministic `SimulatedTestEncoderBackend` exists for tests and explicitly labels itself as a test encoder.

No encoder binary is bundled in this phase. No external encoder dependency is required for app startup.

## Dependency Behavior

If no encoder backend is injected, Export Clip remains unavailable. Missing dependencies produce typed unavailable results instead of fake MP4/WebM outputs.

The test encoder requires no external binary. It writes deterministic local bytes only in tests and still runs through output verification before allowing a playable claim.

## Source Frame Truth

Post-RC 3D frame-buffer entries are metadata/reference entries by default. Post-RC 3E checks each frame reference for an accessible image file before considering the source encodable.

If a frame has no `artifact_path`, references a missing file, or points to a metadata artifact instead of an image frame, export is blocked with `frame pixels not available`.

Intermediate JSON artifacts remain metadata only. They are not playable clips and are not treated as video.

## Export Job Model

The controller exposes:

- `export_clip_availability(...)`
- `export_clip(...)`

Export jobs include export id, source artifact path/type, requested format, output path, overlay/telemetry options, encoder backend, status, progress, warnings, errors, and truth label.

No background daemon, global hotkey, automatic export, Bridge lifecycle control, or auto-save was added.

## Overlay Compositor Behavior

`build_overlay_composition_plan(...)` aligns telemetry samples to the frame-buffer interval when overlay burn-in is requested and frame references exist.

If frame pixels are unavailable, overlay composition reports unavailable or not applicable. It does not invent telemetry and does not claim output write proof.

## Output Verification

After encoding, verification checks:

- output file exists;
- output size is greater than zero;
- extension matches requested format;
- requested format is supported;
- encoder capability allows video encoding;
- no backend errors are present.

Only then is `playable_claim_allowed` set to true. Failed or incomplete verification returns a conservative not-playable result.

## Flight Recorder UI Changes

The Flight Recorder page now includes an `Export / encoding` card showing:

- encoder backend;
- encoder kind;
- dependency status;
- supported formats;
- selected source;
- export readiness;
- export status;
- output path;
- output size;
- playable claim allowed;
- preview status;
- truth label;
- verification summary;
- warnings/errors.

Buttons added:

- `Export Clip`
- `Reveal Export File`
- `Preview Clip`

Export is disabled unless the source and encoder are available. Reveal is disabled unless an encoded output file exists. Preview remains disabled because no reliable in-app playback mechanism exists in this phase.

## Clip Library Integration

`ClipLibrary` now scans `encoded_clip_*/manifest.json` entries. Encoded clips are listed only when the manifest exists, the output file exists, and `playable_claim_allowed` is true.

Intermediate JSON artifacts are still listed as metadata/non-video artifacts and are not promoted to playable clips.

## Help / Docs Update

Help / Docs now includes a focused `Recorder encoding/export preview` article that explains:

- what encoding is;
- when Export Clip is available;
- why intermediate artifacts are not playable;
- why encoder dependency may be unavailable;
- what `playable claim allowed` means;
- no game injection;
- no graphics hooks;
- no global recorder hotkeys.

This was a narrow update to the existing Post-RC 1D Help / Docs structure, not a second full docs overhaul.

## Known Limitations

- No production encoder binary is bundled.
- Default app state remains encoder unavailable.
- Real playable export requires durable frame image files; metadata-only frame references are not enough.
- No in-app playback preview mechanism was added.
- No package smoke was run because packaged output was not rebuilt.

## What Remains For Polish / Packaging

- Decide whether and how to package an approved external encoder backend.
- Add a reliable local playback preview only after the product has a safe preview mechanism.
- Improve visual polish as part of Post-RC 4B, not this phase.

## Tests Run

During development:

- `python -m pytest tests/test_post_rc_3e_encoding_export_preview.py -q` - red first because the encoder module and report did not exist; green after implementation and report creation.
- `python -m pytest tests/test_post_rc_3a_recorder_capture_backend_seam.py -q` - passed, 6 tests after compatibility wording fixes.
- `python -m pytest tests/test_post_rc_3b_flight_recorder_review_export.py -q` - passed, 6 tests.
- `python -m pytest tests/test_post_rc_3c_one_frame_capture_proof.py -q` - passed, 9 tests.
- `python -m pytest tests/test_post_rc_3d_hindsight_frame_buffer.py -q` - passed, 10 tests.
- `python -m pytest tests/test_post_rc_3e_encoding_export_preview.py -q` - passed, 9 tests after the report assertion was added.
- `python -m pytest tests/test_phase13d_flight_recorder_boundary_freeze.py -q` - passed, 7 tests after compatibility wording fixes.
- `python -m pytest tests/test_phase19d_final_acceptance_report.py -q` - passed, 5 tests.

Final validation:

- `python -m pytest -q` - passed, 519 tests.
- `python -m pytest tests/test_post_rc_3a_recorder_capture_backend_seam.py -q` - passed, 6 tests.
- `python -m pytest tests/test_post_rc_3b_flight_recorder_review_export.py -q` - passed, 6 tests.
- `python -m pytest tests/test_post_rc_3c_one_frame_capture_proof.py -q` - passed, 9 tests.
- `python -m pytest tests/test_post_rc_3d_hindsight_frame_buffer.py -q` - passed, 10 tests.
- `python -m pytest tests/test_post_rc_3e_encoding_export_preview.py -q` - passed, 9 tests.
- `python -m pytest tests/test_phase13d_flight_recorder_boundary_freeze.py -q` - passed, 7 tests.
- `python -m pytest tests/test_phase19d_final_acceptance_report.py -q` - passed, 5 tests.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --status` - passed; reported `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; dry run only, HOTAS not connected, vJoy detected, and Full Live Runtime Ready remains governed by the Phase 16 proof gate.
- `git diff --check` - passed.

## Runtime Truth Preservation

Telemetry remains the truth surface. Capture buffer is not runtime readiness. One-frame capture proof is not video recording. Buffered frames are not encoded video until an encoder succeeds. Intermediate artifacts are not playable clips. Simulated/test capture is not real desktop capture. Output intent is not output write proof. vJoy detected is not output verification. Packaged smoke is not runtime readiness. Full Live Runtime Ready gates remain unchanged.
