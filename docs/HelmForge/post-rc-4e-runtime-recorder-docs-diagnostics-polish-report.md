# Post-RC 4E Runtime / Recorder / Docs / Diagnostics Polish Report

## Audit approach

Post-RC 4E re-read the human walkthrough notes and the existing completion matrix, then limited implementation to the runtime/status-heavy pages: Live Monitor, Live Overlay configuration, Flight Recorder, Help / Docs, and Perf / Diagnostics. The pass updated only visual/product clarity, scan structure, draft settings, and truthful labels. It did not add runtime authority.

## Audit matrix updates made

`docs/HelmForge/post-rc-human-walkthrough-completion-matrix.md` now includes 4E-specific evidence and statuses for:

- Live Monitor
- Live Overlay
- Flight Recorder
- Help / Docs
- Perf / Diagnostics
- final walkthrough acceptance summary
- recommended Post-RC 5A manual visible QA checks

Final matrix summary counts:

- Fully Fixed: 45
- Partially Fixed: 28
- Deferred: 5
- Cannot Verify Without Visible QA: 4

## Live Monitor issues fixed/deferred

Fixed:

- Axis dropdown remains populated and readable.
- Bridge request buttons moved into a dedicated `liveMonitorActionBlock`.
- Live Monitor exposes `liveMonitorCompactState` with compact truth/proof/source rows.
- Live Monitor exposes `liveMonitorHistorySecondsLabel` and `liveMonitorGraphCadenceLabel` so graph history and refresh truth are visible.
- Axis Levels exposes `liveMonitorAxisLevelsVertical` and a vertical-layout property for 4E QA/tests.

Partial/deferred:

- The graph UI timer remains at the existing 750 ms diagnostic refresh to avoid changing runtime behavior in a polish phase.
- True 30/60 Hz graph rendering and true rotated axis-level bars are deferred to a later runtime/monitor phase.
- Buttons/Hats and axis-level perceived size still need visible QA.

## Live Overlay issues fixed/deferred

Fixed:

- Configure dialog now exposes `postRc4eStyled=True`.
- Dialog default size is smaller, remains resizable, and uses a scroll area: `liveOverlayConfigScrollArea`.
- Preset controls were added: `liveOverlayPresetDropdown`, `liveOverlayPresetNameInput`, and `liveOverlaySavePresetButton`.
- Five concrete presets plus Custom are available: Regular, Compact, High Contrast, Telemetry Focus, Minimal, and Custom.
- Selecting a preset updates local overlay draft fields only.
- Editing supported fields switches the preset state to Custom.
- Saving a custom preset adds a dialog-local named preset with `Custom 1`, `Custom 2`, etc. fallback naming.

Partial/deferred:

- Persisted overlay default remains `Custom` to preserve existing accepted config/default tests; changing the default to Regular is deferred to an explicit preset-default migration.
- Saved custom presets are dialog-local and not persisted across app launches because 4E must not add auto-save or a persistence feature.

## Flight Recorder issues fixed/deferred

Fixed:

- Added `recorderWorkflowMapCard` to make the flow readable: Settings, Capture Proof, Frame Buffer / Frame Storage, Save Last Clip / Intermediate Artifact, Export / Encoding, Library / Preview.
- `recorderStatusCard` is marked with `scanFriendlyRows=True`.
- Recorder Library sort dropdown now has visible options: Newest First, Oldest First, Artifact Type, Playable First.
- Record Cursor is editable and updates in-memory recorder settings only.
- Axis Overlay Include checkboxes are editable and update in-memory recorder settings only.
- Export / Encoding copy now distinguishes intermediate artifacts, image sequences, encoded clip files, and playable-claim verification.

Partial/deferred:

- Broader recorder settings editing is deferred to avoid adding recorder backend or persistence behavior in 4E.
- New encoder, capture, durable storage, and global hotkey features were not added.

## Help / Docs issues fixed/deferred

Fixed:

- Help article surface remains dark and now exposes `postRc4eReadable=True` for focused QA/tests.
- Existing topic tree, sort dropdown, article surface, parameter reference blocks, and navigation buttons were preserved.
- Recorder encoding/export and durable frame storage truth docs remain available.

Partial/deferred:

- Visible QA should still review topic-tree spacing/selection and final article typography. The 1D architecture was not redone.

## Perf / Diagnostics issues fixed/deferred

Fixed:

- Added `diagnosticsHintProofReadinessLegend` to separate hint, proof, and readiness concepts.
- Bridge / Telemetry card exposes `cardSizing="content"`.
- Performance Timings card exposes `expandedTimingDisplay=True`.
- Existing Full Live Runtime Ready and process-presence truth wording remains intact.

Partial/deferred:

- The Runtime Truth card remains intentionally exhaustive; visible QA should verify the final scan feel.
- New timing metrics were not invented where the collector does not already expose data.

## Files changed

- `v3_app/pages/live_monitor_page.py`
- `v3_app/overlay/config_dialog.py`
- `v3_app/pages/flight_recorder_page.py`
- `v3_app/pages/help_docs_page.py`
- `v3_app/pages/perf_diagnostics_page.py`
- `docs/HelmForge/post-rc-human-walkthrough-completion-matrix.md`
- `docs/HelmForge/post-rc-4e-runtime-recorder-docs-diagnostics-polish-report.md`
- `tests/test_post_rc_4e_runtime_recorder_docs_polish.py`

## Tests run

- `python -m pytest tests/test_post_rc_1d_help_docs_full_overhaul.py -q` - passed, 7 tests.
- `python -m pytest tests/test_phase11a_help_docs_foundation.py -q` - passed, 8 tests.
- `python -m pytest tests/test_post_rc_3a_recorder_capture_backend_seam.py -q` - passed, 6 tests.
- `python -m pytest tests/test_post_rc_3b_flight_recorder_review_export.py -q` - passed, 6 tests.
- `python -m pytest tests/test_post_rc_3c_one_frame_capture_proof.py -q` - passed, 9 tests.
- `python -m pytest tests/test_post_rc_3d_hindsight_frame_buffer.py -q` - passed, 10 tests.
- `python -m pytest tests/test_post_rc_3e_encoding_export_preview.py -q` - passed, 9 tests.
- `python -m pytest tests/test_post_rc_3f_durable_frame_storage.py -q` - passed, 11 tests.
- `python -m pytest tests/test_phase13d_flight_recorder_boundary_freeze.py -q` - passed, 7 tests.
- `python -m pytest tests/test_phase19d_final_acceptance_report.py -q` - passed, 5 tests.
- `python -m pytest tests/test_post_rc_4c_global_helm_walkthrough_polish.py -q` - passed, 8 tests.
- `python -m pytest tests/test_post_rc_4d_control_pages_polish.py -q` - passed, 8 tests.
- `python -m pytest tests/test_post_rc_4e_runtime_recorder_docs_polish.py -q` - passed, 5 tests.
- `python -m pytest tests/test_phase17a_product_polish_layout_qa.py -q` - passed, 5 tests.
- `python -m pytest tests/test_phase17c_final_product_qa_packaging_readiness.py -q` - passed, 4 tests.
- `python -m pytest -q` - passed, 558 tests.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --status` - passed; Bridge reported `lifecycle=Simulated truth=blocked_missing_device output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; dry run only, no installers launched.
- `git diff --check` - passed.

## Visible QA status

Not performed in 4E. This was an offscreen/code/test polish pass. Remaining visual perception items are marked Partial or Cannot Verify Without Visible QA in the matrix.

## Packaged smoke status

Not performed. 4E did not rebuild packaged output, so no packaged smoke is claimed.

## Runtime truth preservation

4E preserved the runtime truth boundary: telemetry remains the truth surface; output intent is not output write proof; vJoy detected is not output verification; one-frame capture proof is not video recording or runtime readiness; frame buffer is not runtime readiness; image sequences and intermediate artifacts are not playable clips; encoded clip is playable only after encoder success and local verification; simulated/test capture is not real desktop capture; packaged smoke is not runtime readiness; and Full Live Runtime Ready gates remain unchanged.

## Recommendation

Proceed with Post-RC 5A Final Visible Desktop QA and RC2 Freeze.
