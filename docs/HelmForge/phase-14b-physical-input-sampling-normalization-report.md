# Phase 14B - Physical Input Sampling and Normalization

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Phase: 14B
Scope: Real HOTAS input sampling/normalization foundation only

## Summary

Phase 14B adds a read-only physical input sampling and normalization foundation without adding virtual output authority.

Implemented:

- `shared_core/runtime/input_normalization.py` with deterministic axis normalization for signed, unsigned-centered, already-normalized, and one-sided values.
- `shared_core/runtime/hotas_input.py` sample models:
  - `PhysicalInputSnapshot`
  - `PhysicalAxisSample`
  - `PhysicalButtonSample`
  - `PhysicalHatSample`
  - `PhysicalInputSamplingStatus`
  - `PhysicalInputSampler`
- Fake/test backend support for deterministic read-only sample frames.
- Fake disconnect/error emulation for safe sampling failure paths.
- Logical input hints for the supported Thrustmaster HOTAS One axes, buttons, and hat.
- Perf / Diagnostics sampling truth fields:
  - Last sample
  - Sample source
  - Axis/button/hat counts
  - Sampling warnings
  - Sampling errors
- Help / Docs updates explaining that sampling is read-only and does not imply vJoy output.

## Runtime Boundary

Phase 14B is input-only. It does not add:

- vJoy writes;
- virtual output writes;
- output verification;
- Full Live Runtime Ready;
- end-to-end vJoy runtime loops;
- automatic Bridge launch;
- UI-launched child processes;
- service install;
- login auto-start;
- tray manager work;
- installer launch;
- StartBridge / StopBridge / RestartBridge behavior;
- real process scanning;
- recorder screen capture;
- video encoding;
- game injection;
- graphics API hooking;
- cloud AI or LLM behavior;
- auto-save;
- runtime activation.

Simulation mode remains available when no HOTAS is connected, no physical sampling backend is available, no Bridge is running, or sampling cannot start.

## Sampling Behavior

Phase 14B sampling is on-demand and read-only:

- Missing backend returns unavailable snapshots instead of crashing.
- Fake backend can return deterministic axis/button/hat snapshots for tests and development injection.
- Fake backend can emulate disconnect and read error states.
- Windows PnP discovery remains identity-only and reports sampling unavailable.
- The sampler refuses to sample when no selected device exists or the selected device is missing.

No continuous hardware polling loop was added.

## Normalization

Axis normalization supports:

- signed axis ranges such as `-32768..32767`;
- unsigned centered ranges such as `0..65535`;
- already-normalized `-1.0..+1.0` values;
- one-sided throttle-style values;
- clamping to the safe normalized range;
- invalid/missing value handling with warnings.

## Device/Sample Truth From Verification

Read-only machine check during this phase:

- Physical input backend: `windows_pnp_input_discovery`
- Backend available: `true`
- Physical sampling available from Windows PnP backend: `false`
- Present PnP device names checked: `259`
- Supported HOTAS detected: `Missing`
- Input sampling: `Not active`
- Sample source: `unavailable`
- Runtime setup dry run HOTAS status: `HOTAS Not Connected`
- vJoy status: `vJoy Detected`
- Output verified: `false`
- Full Live Runtime Ready: `false`

This means Phase 14B did not read a physical HOTAS sample from the machine. Deterministic fake samples are test/dev-only. No admin prompts were requested, no controls were moved, and no output path was touched.

## Verification

Passed:

- `python -m pytest` - 308 passed
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - 7 passed
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - 6 passed
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - 5 passed
- `python -m pytest tests\test_phase13d_flight_recorder_boundary_freeze.py` - 7 passed
- `python -m pytest tests\test_phase14a_physical_input_backend_selection.py` - 6 passed
- `python -m pytest tests\test_phase14b_physical_input_sampling_normalization.py` - 8 passed
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed
- `python -m bridge_app.main --once` - passed
- `python -m bridge_app.main --run-for-ms 250` - passed
- `python -m bridge_app.main --status` - passed with `lifecycle=Simulated truth=blocked_missing_device output_verified=False`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; HOTAS Not Connected, vJoy Detected, Full Live Runtime Ready false
- `git diff --check` - passed

## Next Phase

Phase 14C may continue Real HOTAS Input Integration by wiring Bridge-owned telemetry/status reporting for read-only physical input sampling. Phase 15 remains the virtual output/vJoy phase and must explicitly scope any output writes or output verification before they are implemented.
