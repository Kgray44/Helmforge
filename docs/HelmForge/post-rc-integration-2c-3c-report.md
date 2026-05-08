# HelmForge Post-RC 2C + 3C Integration Report

## Scope

This integration branch combines the completed Post-RC 2C Mapping Diagram Editing work with the completed Post-RC 3C Explicit One-Frame Capture Proof work.

No Post-RC 1D, 4B, 3D, 3E, or 5A work was implemented in this pass.

## Branches Merged

- Base branch: `main`
- Base commit: `8c1c8c25c7e0fabed43d2c8d11f104e3e11b03be`
- Integration branch: `postrc-integration-2c-3c`
- Post-RC 2C branch: `postrc-2c-mapping-diagram-editing`
- Post-RC 2C commit: `1fb407f1b8145a53e7f26c443fcea3bebf536369`
- Post-RC 3C branch: `postrc-3c-one-frame-capture-proof`
- Post-RC 3C commit: `e260dc93a83e7547d795ac7b1f3c4b822317beff`
- Rescue backup commit retained separately: `beb1a82ccfbbfdfd66f9f79efd70b69ec5a4392e`

## Merge Order

1. `postrc-2c-mapping-diagram-editing`
2. `postrc-3c-one-frame-capture-proof`

## Conflicts Encountered

No merge conflicts were encountered.

- Post-RC 2C merged by fast-forward from `main`.
- Post-RC 3C merged with Git's `ort` strategy.

## Conflict Resolution Summary

No manual conflict resolution was required.

The integrated result preserves:

- Mapping draft-edit workflow, including Change Mapping, Apply to Draft, Cancel, and Revert Route behavior.
- Mapping route inspector, conflict preview, warning badges/rings, filter chips, keyboard/focus navigation, metadata/help coverage, and no-live-output-claims wording.
- The committed human/spec file at `HOTAS Control Panel Forensic Spec Set/POST REGULAR PHASES - HUMAN WALKTHR.txt`.
- Recorder one-frame proof interfaces and models, including `capture_one_frame`, `FrameCaptureResult`, typed unavailable/offscreen results, guarded Qt candidate behavior, and proof fields separate from recorder support.
- Flight Recorder Capture Proof card and Try One-Frame Capture gating.
- Existing Post-RC 3B review/export behavior without adding video recording, encoding, or playable preview claims.

## Files Changed During Integration

- `HOTAS Control Panel Forensic Spec Set/POST REGULAR PHASES - HUMAN WALKTHR.txt`
- `docs/HelmForge/post-rc-2c-mapping-diagram-editing-report.md`
- `docs/HelmForge/post-rc-3c-one-frame-capture-proof-report.md`
- `docs/HelmForge/post-rc-integration-2c-3c-report.md`
- `tests/test_post_rc_2c_mapping_diagram_editing.py`
- `tests/test_post_rc_3c_one_frame_capture_proof.py`
- `v3_app/pages/flight_recorder_page.py`
- `v3_app/pages/mapping_page.py`
- `v3_app/recorder/capture_backend.py`
- `v3_app/recorder/recorder_controller.py`
- `v3_app/services/help_docs.py`
- `v3_app/services/hotas_diagram_model.py`
- `v3_app/theme/qss.py`
- `v3_app/widgets/hotas_diagram.py`

## Full-Suite Failure Reproduction

The previously reported Mapping order-dependent failure did not reproduce on this integration branch.

Command run:

```powershell
python -m pytest -q
```

Result:

```text
493 passed in 261.85s (0:04:21)
```

Because the full suite passed, no failing Mapping test subset was available to isolate in this pass.

## Root Cause of Mapping Order-Dependent Failures

No root cause was identified or fixed in this integration pass because the full-suite failure did not reproduce.

## Fix Applied

No test-isolation or product-code fix was applied. The only new file added directly by this integration pass is this report.

## Focused Tests Run After 2C Merge

```powershell
python -m pytest tests/test_post_rc_2a_mapping_hotas_diagram.py -q
```

Result: `7 passed`

```powershell
python -m pytest tests/test_post_rc_2b_mapping_diagram_interaction.py -q
```

Result: `8 passed`

```powershell
python -m pytest tests/test_post_rc_2c_mapping_diagram_editing.py -q
```

Result: `14 passed`

```powershell
python -m pytest tests/test_phase19d_final_acceptance_report.py -q
```

Result: `5 passed`

## Focused Tests Run After 3C Merge

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

Result: `493 passed`

```powershell
python -m pytest tests/test_post_rc_2a_mapping_hotas_diagram.py -q
python -m pytest tests/test_post_rc_2b_mapping_diagram_interaction.py -q
python -m pytest tests/test_post_rc_2c_mapping_diagram_editing.py -q
python -m pytest tests/test_post_rc_3a_recorder_capture_backend_seam.py -q
python -m pytest tests/test_post_rc_3b_flight_recorder_review_export.py -q
python -m pytest tests/test_post_rc_3c_one_frame_capture_proof.py -q
python -m pytest tests/test_phase13d_flight_recorder_boundary_freeze.py -q
python -m pytest tests/test_phase19d_final_acceptance_report.py -q
```

Results:

- `7 passed`
- `8 passed`
- `14 passed`
- `6 passed`
- `6 passed`
- `9 passed`
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
- Manual visible QA is still recommended for Mapping and Flight Recorder surfaces before merging onward.
- Packaged smoke was not rerun because no packaged output was rebuilt in this pass.

## Packaged Smoke Status

Packaged smoke was not rerun. No packaged build artifact was rebuilt or tested during this integration pass.

## Runtime Truth Preservation

No runtime authority was added.

This integration did not add Bridge auto-launch, Bridge control/service/tray/autostart behavior, hardware polling, live input capture, physical press-to-bind behavior, vJoy writes, output verification changes, continuous recorder capture, hindsight video buffer, video recording, video encoding, MP4/WebM export, playable video preview, global recorder hotkeys, game injection, graphics API hooking, cloud AI/LLM behavior, or auto-save.

Runtime truth remains conservative:

- Mapping edits are workspace/config draft changes only.
- Output intent is not output write proof.
- vJoy detected is not output verification.
- Physical input alone is not Full Live Runtime Ready.
- Simulation/fallback views remain clearly labeled.
- Save Workspace remains the explicit persistence action.
- Capture proof is not runtime readiness.
- A still frame is not a video recording.
- Simulated/test capture is not real desktop capture.
- Packaged smoke is not runtime readiness.
- Full Live Runtime Ready gates remain unchanged.

## Recommended Next Phase

After this integration branch is reviewed and merged into `main`, the next recommended step is a dedicated Post-RC 4B page-by-page polish pass from the updated `main`, with Post-RC 3D, 3E, and 5A deferred until the 2C/3C baseline is stable.
