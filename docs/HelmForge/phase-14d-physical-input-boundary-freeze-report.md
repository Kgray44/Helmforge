# Phase 14D Physical Input Boundary Freeze Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Phase: 14D only - Real HOTAS Input Integration boundary freeze
Status: Implemented and verified

## Phase 14A Summary

Phase 14A added the physical input backend and device-selection foundation:

- `PhysicalInputBackend` capability/status contracts.
- Missing and fake backends.
- Read-only Windows PnP discovery backend where available.
- `PhysicalInputDeviceInfo`.
- Centralized Thrustmaster T-Flight / T.Flight HOTAS One matching, including VID/PID `044f:b68d`.
- In-memory selected-device diagnostics.
- Perf / Diagnostics and Help / Docs selection truth.

Phase 14A did not add sampling loops, vJoy writes, output verification, Full Live Runtime Ready, or Bridge lifecycle authority.

## Phase 14B Summary

Phase 14B added read-only physical input sampling and normalization foundations:

- `PhysicalInputSnapshot`.
- Axis/button/hat sample models.
- Deterministic normalization helpers.
- Fake on-demand sample snapshots.
- Sampling status/error models.
- `PhysicalInputSampler`.
- Diagnostics and Help / Docs wording for read-only sampling.

Phase 14B did not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, or an end-to-end live output loop.

## Phase 14C Summary

Phase 14C integrated read-only physical sample truth into UI surfaces:

- Mapping physical input display and Live Raw physical sample labels.
- Live Monitor physical axis/button/hat sample display.
- Perf / Diagnostics input source/sample fields.
- Copy Diagnostics sample truth.
- Effective Response Stack diagnostic-only physical sample preview when available.
- Help / Docs updates explaining read-only sample visibility and Phase 15 output boundary.

Phase 14C preserved simulation fallback and did not add output authority.

## Phase 14D Polish / Freeze Summary

Phase 14D finalizes the Phase 14 boundary:

- Physical input terminology is standardized around Physical input backend, Selected input device, Supported HOTAS, Physical input sample, Read-only input sampling, Sample source, Sample age, Sample stale, Sampling unavailable, and Simulation fallback.
- The input source model now labels backend unavailable, no selected device, selected device missing, unsupported device, sampling unavailable, stale sample, and sample error states clearly.
- Perf / Diagnostics and Copy Diagnostics include simulation fallback state.
- Help / Docs, README, bridge UI architecture, and bridge service design state that Phase 14 is complete and Phase 15 is the vJoy / Virtual Output Integration phase.

## Final Phase 14 Input Behavior

Phase 14 can:

- Detect/select physical input devices through guarded backends.
- Recognize the supported Thrustmaster HOTAS One identity.
- Represent read-only physical input snapshots.
- Normalize axis values.
- Represent button and hat samples.
- Display fresh physical input samples in Mapping and Live Monitor.
- Feed physical normalized input into Effective Response Stack as a diagnostic-only preview.
- Surface physical input truth in Perf / Diagnostics and Copy Diagnostics.

Phase 14 cannot and does not:

- Write vJoy.
- Write virtual output.
- Verify output writes.
- Claim Full Live Runtime Ready.
- Own an end-to-end live output runtime loop.

## Simulation Fallback Behavior

Simulation fallback remains available when:

- no physical backend exists;
- no physical device is selected;
- selected device is missing;
- physical sample is stale;
- physical sample has errors;
- backend disconnects;
- Bridge telemetry is missing, stale, invalid, or erroring.

Stale physical samples are not treated as current. Error and unavailable states do not crash the UI and preserve simulation/fallback display.

## Current Runtime Truth

Current expected conservative truth:

- Bridge lifecycle: Simulated.
- Runtime truth: blocked_missing_device.
- HOTAS discovery: no_supported_device unless a supported device is found by the active read-only backend.
- vJoy/output state: vJoy may be detected, but output writes remain unverified.
- output_verified: false.
- Full Live Runtime Ready: false.

## Output / vJoy Truth

Phase 14 is input-only. vJoy detected does not mean output verified. Physical HOTAS detection or sampling does not imply live output. Phase 15 remains the virtual output/vJoy phase.

## Phase 15 Readiness

Phase 15 may build on:

- the physical input sample model;
- selected device state;
- normalized axis/button/hat snapshots;
- Mapping and Live Monitor physical sample display paths;
- Effective Response Stack diagnostic preview;
- simulation fallback behavior.

Phase 15 may add virtual output/vJoy integration only with separate tests. output verification must require real or mock write success. Full Live Runtime Ready must remain false until both input and output are verified. simulation mode must remain available.

Guardrails Phase 15 must preserve:

- telemetry remains the truth surface;
- command files are requests, not success proof;
- command acknowledgement requires matching request_id;
- process presence is a hint only;
- physical input sampling alone is not runtime readiness;
- output verification must not be inferred from vJoy detection.

## Verification Results

Passed:

- `python -m pytest` - 320 passed.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - 7 passed.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - 6 passed.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - 5 passed.
- `python -m pytest tests\test_phase13d_flight_recorder_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase14a_physical_input_backend_selection.py` - 6 passed.
- `python -m pytest tests\test_phase14b_physical_input_sampling_normalization.py` - 8 passed.
- `python -m pytest tests\test_phase14c_physical_input_ui_integration.py` - 8 passed.
- `python -m pytest tests\test_phase14d_input_boundary_freeze.py` - 4 passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`.
- `python -m bridge_app.main --once`.
- `python -m bridge_app.main --run-for-ms 250`.
- `python -m bridge_app.main --status`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`.
- `git diff --check`.

## Final Phase 14 Boundary

Phase 14D does not add:

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

Move next to Phase 15: vJoy / Virtual Output Integration only after preserving the Phase 14 input-only boundary in tests. Phase 15 should introduce virtual output behind explicit missing/fake/real backend seams, keep simulation mode available, and require real or mock write success before any output verification claim.
