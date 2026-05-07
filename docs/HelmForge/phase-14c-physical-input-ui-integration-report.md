# Phase 14C Physical Input UI Integration Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Phase: 14C only - Real HOTAS Input Integration UI visibility
Status: Implemented and verified

## Scope

Phase 14C integrates read-only physical input sample truth into the main UI surfaces without adding output/runtime authority.

Implemented:

- `v3_app/services/physical_input_ui.py` as the UI-facing input source/status model.
- Mapping page physical input backend/device/sample display.
- Mapping page Live Raw physical sample labeling when fresh samples are available.
- Live Monitor physical input source/status display, read-only axis/button/hat sample use, stale/error fallback wording, and output boundary wording.
- Effective Response Stack diagnostic-only physical sample preview when available.
- Perf / Diagnostics input source and physical input read-only rows.
- Copy Diagnostics physical input source/read-only/sample truth.
- Help / Docs wording for Runtime Setup / vJoy Setup, Runtime Indicators, Mapping, and Effective Response Stack.
- Focused Phase 14C boundary tests.

## Phase 14A-14C Summary

- Phase 14A added physical input backend/device-selection foundations, missing/fake/Windows PnP discovery backends, centralized Thrustmaster HOTAS One matching, and in-memory selection diagnostics.
- Phase 14B added physical input sample/snapshot models, normalization helpers, fake read-only sampling, sampler/controller coordination, and diagnostics display.
- Phase 14C makes those read-only physical samples visible in Mapping, Live Monitor, Effective Response Stack preview, Perf / Diagnostics, Copy Diagnostics, and Help / Docs while preserving simulation fallback.

## UI Behavior

Mapping now shows:

- Physical input backend.
- Selected input device.
- Supported HOTAS.
- Input sampling.
- Last sample.
- Sample source.
- Axis/button/hat counts.
- Output verified false.
- Full Live Runtime Ready false.

When a fresh physical sample is supplied, Mapping labels the Live Raw column as `Live Raw (Physical input sample)` and uses the read-only normalized physical values. When physical input is missing, stale, erroring, or unavailable, Mapping keeps simulation fallback visible.

Live Monitor now shows:

- Input source: Simulation / Physical input / Physical unavailable.
- Sample status: active / stale / unavailable / error.
- Selected device and sample age/source.
- Physical input sample: read-only.
- Output path remains unverified.
- vJoy writes are not active.
- Full Live Runtime Ready false.

Fresh physical samples can update Live Monitor raw axis levels, HOTAS button states, and HOTAS hat state. Final output remains workspace/simulation/telemetry display only and is not written to vJoy.

Effective Response Stack can use a physical normalized sample for a diagnostic-only preview when available. It does not write final output anywhere and keeps output verification false.

Perf / Diagnostics now includes input source, physical input read-only truth, selected device, sample source, sample counts, warnings, and errors. Copy Diagnostics includes the same truth fields.

## Current Runtime Truth

Latest verification output:

- Bridge lifecycle: Simulated.
- Runtime truth: blocked_missing_device.
- HOTAS status: HOTAS Not Connected.
- vJoy status: vJoy Detected.
- output_verified: false.
- Full Live Runtime Ready: false.

The dry-run setup check detected installed vJoy and Thrustmaster runtime software but did not detect the physical HOTAS device through the current read-only check.

## Output / vJoy Boundary

Phase 14C is input-only UI integration.

- No vJoy writes were added.
- No virtual output writes were added.
- No output verification was added.
- Full Live Runtime Ready remains false.
- Physical HOTAS detection or sampling does not mean live output.
- Phase 15 remains the virtual output/vJoy phase.
- Bridge runtime ownership remains protected.

## Verification

Passed:

- `python -m pytest` - 316 passed.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - 7 passed.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - 6 passed.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - 5 passed.
- `python -m pytest tests\test_phase13d_flight_recorder_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase14a_physical_input_backend_selection.py` - 6 passed.
- `python -m pytest tests\test_phase14b_physical_input_sampling_normalization.py` - 8 passed.
- `python -m pytest tests\test_phase14c_physical_input_ui_integration.py` - 8 passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`.
- `python -m bridge_app.main --once`.
- `python -m bridge_app.main --run-for-ms 250`.
- `python -m bridge_app.main --status`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`.
- `git diff --check`.

## Final Boundary

Phase 14C does not add:

- vJoy writes;
- virtual output writes;
- output verification;
- Full Live Runtime Ready;
- end-to-end live output runtime loop;
- automatic Bridge launch;
- UI-launched child process;
- service install;
- login auto-start;
- tray manager;
- installer launch;
- Start/Stop/Restart behavior;
- real process scanner;
- recorder screen capture;
- video encoding;
- game injection;
- graphics API hooking;
- cloud AI or LLM behavior;
- auto-save;
- runtime activation.

## Recommendation

Continue Phase 14 only if the next prompt-book pass remains input-side and preserves simulation mode. Phase 15 should remain the first virtual output/vJoy phase and must not claim output verification until output writes are implemented and verified.
