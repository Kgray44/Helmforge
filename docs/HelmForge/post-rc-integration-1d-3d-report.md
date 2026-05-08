# HelmForge Post-RC 1D + 3D Integration Report

## Scope

This integration branch combines the completed Post-RC 1D Real Help / Docs Full Overhaul work with the completed Post-RC 3D Hindsight Frame Buffer and Capture Pipeline work.

No Post-RC 3E, 4B, or 5A work was implemented in this pass.

## Branches Merged

- Base branch: `main`
- Base commit: `39626df43556e7b4fa926fdc8b5f610350949c07`
- Integration branch: `postrc-integration-1d-3d`
- Post-RC 1D branch: `postrc-1d-help-docs-full-overhaul`
- Post-RC 1D commit: `cdb84ace2ab901aaf6f82bfc44961a1c3b82875f`
- Post-RC 3D branch: `postrc-3d-hindsight-frame-buffer`
- Post-RC 3D commit: `b663fa6890fee620e19c79e4d80d73be78f59cd5`
- Rescue backup commit retained separately: `bcf1480989fe1a0d29873ce023e324aab978f735`

## Merge Order

1. `postrc-1d-help-docs-full-overhaul`
2. `postrc-3d-hindsight-frame-buffer`

## Conflicts Encountered

No merge conflicts were encountered.

- Post-RC 1D merged by fast-forward from `main`.
- Post-RC 3D merged with Git's `ort` strategy.

## Conflict Resolution Summary

No manual conflict resolution was required.

The integrated result preserves:

- Dark in-app Help / Docs article surface.
- Collapsible `helpDocsTopicTree`.
- Hidden compatibility `helpDocsTopicList`.
- Non-article category folder rows.
- Structured `HelpArticleSection` model.
- Sort modes for category, last opened, alphabetical, and importance ordering.
- Parameter metadata reference blocks.
- Internal page navigation buttons.
- Local in-app articles for Mapping edit workflow, one-frame capture proof, recorder review/export, real capture limitations, runtime truth, and related areas.
- Hindsight frame buffer model and Start Buffer / Stop Buffer behavior.
- Capture pipeline usage of the existing 3C `capture_one_frame` seam.
- Telemetry synchronization with frame interval.
- Save Last Clip intermediate JSON artifact behavior.
- Flight Recorder Frame Buffer card.
- `not_encoded` and `not_playable` truth labels.
- Existing Capture Proof and 3B review/export cards as separate concepts.

## Files Changed During Integration

- `docs/HelmForge/post-rc-1d-help-docs-full-overhaul-report.md`
- `docs/HelmForge/post-rc-3d-hindsight-frame-buffer-report.md`
- `docs/HelmForge/post-rc-integration-1d-3d-report.md`
- `tests/test_post_rc_1d_help_docs_full_overhaul.py`
- `tests/test_post_rc_3d_hindsight_frame_buffer.py`
- `v3_app/pages/flight_recorder_page.py`
- `v3_app/pages/help_docs_page.py`
- `v3_app/recorder/capture_backend.py`
- `v3_app/recorder/clip_library.py`
- `v3_app/recorder/hindsight_buffer.py`
- `v3_app/recorder/recorder_controller.py`
- `v3_app/services/help_docs.py`
- `v3_app/theme/qss.py`
- `v3_app/ui/shell.py`

## Full-Suite Failure Reproduction

The previously reported Help / Docs order-dependent failure did not reproduce on this integration branch.

Command run:

```powershell
python -m pytest -q
```

Result:

```text
510 passed in 236.20s (0:03:56)
```

Because the full suite passed, there were no failing Help / Docs tests to isolate in this pass.

## Root Cause of Help / Docs Order-Dependent Failures

No root cause was identified or fixed in this integration pass because the broad-suite Help / Docs failure did not reproduce.

## Fix Applied

No product-code or test-isolation fix was applied. The only new file added directly by this integration pass is this report.

## Focused Tests Run After 1D Merge

```powershell
python -m pytest tests/test_post_rc_1b_parameter_metadata_info_icons.py -q
```

Result: `8 passed`

```powershell
python -m pytest tests/test_post_rc_1c_parameter_help_coverage.py -q
```

Result: `10 passed`

```powershell
python -m pytest tests/test_post_rc_1d_help_docs_full_overhaul.py -q
```

Result: `7 passed`

```powershell
python -m pytest tests/test_phase11a_help_docs_foundation.py -q
```

Result: `8 passed`

```powershell
python -m pytest tests/test_phase19d_final_acceptance_report.py -q
```

Result: `5 passed`

## Focused Tests Run After 3D Merge

```powershell
python -m pytest tests/test_post_rc_3a_recorder_capture_backend_seam.py -q
```

Result: `6 passed`

```powershell
python -m pytest tests/test_post_rc_3b_flight_recorder_review_export.py -q
```

Result: `6 passed`

```powershell
python -m pytest tests/test_post_rc_3c_one_frame_capture_proof.py -q
```

Result: `9 passed`

```powershell
python -m pytest tests/test_post_rc_3d_hindsight_frame_buffer.py -q
```

Result: `10 passed`

```powershell
python -m pytest tests/test_phase13d_flight_recorder_boundary_freeze.py -q
```

Result: `7 passed`

```powershell
python -m pytest tests/test_phase19d_final_acceptance_report.py -q
```

Result: `5 passed`

## Final Validation Commands Run

```powershell
python -m pytest -q
```

Result: `510 passed`

```powershell
python -m pytest tests/test_post_rc_1b_parameter_metadata_info_icons.py -q
python -m pytest tests/test_post_rc_1c_parameter_help_coverage.py -q
python -m pytest tests/test_post_rc_1d_help_docs_full_overhaul.py -q
python -m pytest tests/test_phase11a_help_docs_foundation.py -q
python -m pytest tests/test_post_rc_3a_recorder_capture_backend_seam.py -q
python -m pytest tests/test_post_rc_3b_flight_recorder_review_export.py -q
python -m pytest tests/test_post_rc_3c_one_frame_capture_proof.py -q
python -m pytest tests/test_post_rc_3d_hindsight_frame_buffer.py -q
python -m pytest tests/test_phase13d_flight_recorder_boundary_freeze.py -q
python -m pytest tests/test_phase19d_final_acceptance_report.py -q
```

Results:

- `8 passed`
- `10 passed`
- `7 passed`
- `8 passed`
- `6 passed`
- `6 passed`
- `9 passed`
- `10 passed`
- `7 passed`
- `5 passed`

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
```

Result: exited successfully.

```powershell
python -m bridge_app.main --status
```

Result:

```text
HelmForge Bridge: lifecycle=Simulated truth=blocked_missing_device output_verified=False
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
```

Result:

```text
HOTAS status: HOTAS Not Connected
vJoy status: vJoy Detected
Runtime status: Simulation Mode Active unless physical input and output writes are both verified.
Full Live Runtime Ready: governed by the Phase 16 proof gate; false unless fresh input, pipeline, real output verification, output-loop state, telemetry, and safety proof all pass.
No installers launched.
Dry run only. No installers launched.
```

## Remaining Known Issues

- No automated test failures remain from this pass.
- The previously reported Help / Docs order-dependent broad-suite failure did not reproduce here.
- Manual visible QA is still recommended for Help / Docs and Flight Recorder before merging onward.

## Packaged Smoke Status

Packaged smoke was not rerun. No packaged build artifact was rebuilt or tested during this integration pass.

## Runtime Truth Preservation

No runtime authority was added.

This integration did not add Bridge auto-launch, Bridge control/service/tray/autostart behavior, unrelated hardware polling, vJoy writes, output verification changes, video encoding, MP4/WebM export, playable video preview, global recorder hotkeys, game injection, graphics API hooking, cloud/web docs, LLM behavior, or auto-save.

Runtime truth remains conservative:

- Telemetry remains the truth surface.
- Output intent is not output write proof.
- vJoy detected is not output verification.
- Mapping edits are workspace/config draft only.
- Save Workspace remains explicit persistence.
- One-frame capture proof is not video recording or runtime readiness.
- Frame buffer is not runtime readiness.
- Buffered frames are not encoded video.
- Intermediate artifacts are not playable clips.
- Simulated/test capture is not real desktop capture.
- Packaged smoke is not runtime readiness.
- Full Live Runtime Ready gates remain unchanged.

## Recommended Next Phase

After this integration branch is reviewed and merged into `main`, the next recommended phase is Post-RC 4B page-by-page polish from the updated baseline, with Post-RC 3E and 5A deferred until the 1D/3D baseline is stable.
