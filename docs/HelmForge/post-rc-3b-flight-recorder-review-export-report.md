# Post-RC 3B - Flight Recorder Review, Timeline Summary, and Safe Export Foundation

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Flight Recorder review/export diagnostics only

## Summary

Post-RC 3B adds a review layer on top of the Post-RC 3A capture seam. The Flight Recorder can now summarize an in-memory recorder session, show a deterministic timeline of telemetry channel changes, export a local JSON session summary, export local CSV sample rows, and clear the reviewed session from UI/controller state.

This phase does not add real desktop capture, video recording, video encoding, playable preview, recorder hotkey registration, hardware polling, Bridge launch/control/service/tray/autostart behavior, output write verification, or Full Live Runtime Ready changes.

## Files changed

- `v3_app/recorder/session_review.py`
- `v3_app/recorder/recorder_controller.py`
- `v3_app/pages/flight_recorder_page.py`
- `tests/test_post_rc_3b_flight_recorder_review_export.py`
- `docs/HelmForge/post-rc-3b-flight-recorder-review-export-report.md`

## Session model

The recorder review session records:

- session id;
- source type such as simulated, demo, workspace, Bridge telemetry, or live only when existing runtime truth explicitly proves it;
- truth label;
- start and end timestamps;
- duration;
- sample count;
- event count;
- observed axis, button, and hat channels;
- warnings and errors;
- capture mode;
- capture source and display label;
- runtime truth snapshot with output verification and Full Live Runtime Ready values.

The current implementation builds from existing telemetry samples and optional simulated artifact/export metadata. It does not invent live runtime authority.

## Timeline/review behavior

The timeline summary is a compact deterministic event list. It detects axis value changes between consecutive telemetry samples, records relative time, channel, previous value, new value, and a readable description. This helps answer what changed, when it changed, which channels were active, and whether warnings/errors were present.

The Flight Recorder page adds a Recorder Review card showing the latest session summary, source type, duration, sample count, event count, observed channels, warnings/errors, runtime truth, output verification, and Full Live Runtime Ready state. Empty state remains explicit when no reviewed session exists.

## Export behavior

Exports are local-only and deterministic:

- JSON summary export writes a truth-labeled session payload.
- CSV sample export writes sample rows with source type, runtime truth, and axis columns.
- Existing files are not silently overwritten; suffixes such as `_2` are used when a target exists.
- Export buttons are disabled until a reviewed session exists.
- Clearing review state only clears the in-memory reviewed session; it does not delete arbitrary files or workspace configuration.

## Truthfulness boundaries

- No hardware polling.
- No live HOTAS recording unless a real runtime data source already exists.
- No Bridge lifecycle management.
- No output write verification.
- No Full Live Runtime Ready gate changes.
- No real capture claim for simulated, workspace, demo, or blocked runtime data.
- No game injection or graphics API hooking.
- No cloud AI/LLM behavior.
- No auto-save.

Runtime truth remains telemetry-owned. vJoy detected is not output verification. Physical input alone is not Full Live Runtime Ready. Output intent is not output write proof. Fake/test paths are not real readiness. Simulation mode remains available.

## Tests run

- `python -m pytest tests/test_post_rc_3a_recorder_capture_backend_seam.py -q` - passed, 6 tests.
- `python -m pytest tests/test_post_rc_3b_flight_recorder_review_export.py -q` - passed, 6 tests.
- `python -m pytest -q` - passed, 452 tests.

## Known limitations

- No real video frames are captured.
- No hindsight video buffer exists.
- No video encoder/export pipeline exists.
- Button and hat channel review fields are present but empty until an existing telemetry source supplies those structures.
- Timeline rendering is a table/list, not a video timeline or waveform.
- UI export uses the configured recorder destination folder instead of a file dialog.

## Recommended next phase notes

The next recorder phase should keep the same truth model and add only one narrow proof at a time. A safe Post-RC 3C candidate would be explicit one-frame capture proof behind the 3A backend seam, still disabled by default and still reporting unavailable rather than claiming readiness when the dependency or desktop context is missing.
