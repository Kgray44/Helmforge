# Post-RC 3F Durable Frame Storage Report

## Frame Storage Model

Post-RC 3F adds `v3_app/recorder/frame_storage.py` with `StoredFrameArtifact`, `FrameSequenceArtifact`, `FrameStorageSettings`, and `FrameStorageManager`. The manager writes bounded local image-frame sequences only when explicitly enabled by the recorder controller or tests.

## Frame Sequence Folder / Manifest Behavior

Frame sequences are stored under `<destination>/frame_sequences/<sequence_id>/` with a `manifest.json` file and a `frames/` folder. Manifests label the artifact as an image sequence with `not_encoded: true`, `not_playable: true`, and `encoder_source_ready` only when all referenced frame files exist.

## Qt Image Save Behavior

The Qt candidate capture path can save a grabbed `QImage` into a provided frame-storage sequence. Offscreen/test contexts remain unavailable and do not create image frames. Image-save failures return metadata-only or unavailable truth with errors instead of claiming encodable frames.

## Metadata-Only Fallback

Existing metadata-only frame-buffer behavior remains intact. Metadata-only frame references are not encodable, intermediate JSON artifacts are not playable clips, and one-frame capture proof remains separate from video recording.

## Disk Budget / Cache Cleanup

Frame storage enforces a maximum cache size and maximum frames per sequence. Failed temporary sequences can be cleaned up by explicit backend cleanup. User exports and encoded clips are not silently deleted.

## Export Availability Integration With 3E

3E export source analysis now recognizes durable `image_path` frame references. Metadata-only buffers report frame pixels unavailable. File-backed sequences with all image files present can be encoder sources, but export still requires the 3E encoder backend and output verification.

## Clip Library Behavior

The Clip Library scans `frame_sequences/*/manifest.json` and lists image sequences separately from encoded clips. Image sequences are shown as not encoded and not playable, with encoder-source readiness based on frame file existence.

## UI Changes

The Flight Recorder Frame Buffer card now reports frame storage mode, stored image frame count, frame sequence path, manifest path, current image-byte usage, encoder-source readiness, and the image sequence truth label. The 3E Export / Encoding card remains the authority for encoded clip export.

## Help / Docs Update

Help / Docs includes the focused `Recorder durable frame storage` article covering image sequence artifacts, metadata-only versus file-backed storage, budget limits, encoder-source readiness, and hard boundaries around hotkeys, game injection, graphics hooks, cloud behavior, and runtime authority.

## Known Limitations

Durable frame storage is a source foundation, not a playback feature. It does not encode video by itself, does not preview clips, does not register global hotkeys, and does not add durable long-running capture management beyond explicit frame-buffer operation.

## Tests Run

Planned validation:

- `python -m pytest tests/test_post_rc_3a_recorder_capture_backend_seam.py -q`
- `python -m pytest tests/test_post_rc_3b_flight_recorder_review_export.py -q`
- `python -m pytest tests/test_post_rc_3c_one_frame_capture_proof.py -q`
- `python -m pytest tests/test_post_rc_3d_hindsight_frame_buffer.py -q`
- `python -m pytest tests/test_post_rc_3e_encoding_export_preview.py -q`
- `python -m pytest tests/test_post_rc_3f_durable_frame_storage.py -q`
- `python -m pytest tests/test_phase13d_flight_recorder_boundary_freeze.py -q`
- `python -m pytest tests/test_phase19d_final_acceptance_report.py -q`
- `python -m pytest -q`

## Runtime Truth Preservation

No runtime authority was added. Capture buffer state is not runtime readiness. One-frame capture proof is not video recording. File-backed frame sequences are not encoded video or playable clips. Buffered frames become encoded video only after 3E encoder success and local output verification. Simulated/test capture remains clearly labeled as not real desktop capture, and Full Live Runtime Ready gates remain unchanged.
