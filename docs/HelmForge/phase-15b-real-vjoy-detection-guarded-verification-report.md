# Phase 15B Real vJoy Detection And Guarded Verification Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Phase: 15B only - guarded real vJoy detection/write verification
Status: Implemented and verified

## Scope

Phase 15B adds guarded real vJoy detection and write-path verification on top of the Phase 15A virtual output contract. It remains conservative: no continuous output loop, no automatic output enablement, and no Full Live Runtime Ready claim.

Implemented:

- `RealVJoyOutputBackend`.
- Optional provider seam for real vJoy dependency/device/write behavior.
- Safe default real-provider detection that does not require app startup dependencies.
- New verification statuses:
  - `dependency_missing`;
  - `device_busy`;
  - `acquisition_failed`;
  - `neutral_restore_failed`.
- Bounded safe verification intent.
- Guarded verification flow:
  - dependency/backend check;
  - device selection;
  - acquisition;
  - bounded verification write;
  - neutral restore;
  - release.
- Diagnostics fields:
  - vJoy dependency;
  - vJoy device;
  - selected output device;
  - output write status;
  - verification status/source;
  - fake output verified;
  - real output verified;
  - last verification timestamp;
  - verification warnings/errors.
- Help / Docs and architecture documentation updates.

## Real vJoy Detection Behavior

The real backend is optional and guarded. Importing the app does not require a vJoy dependency. Missing dependencies or missing drivers become typed unavailable states instead of startup crashes.

The default provider can detect a vJoy backend/library path conservatively. If safe device enumeration is unavailable, it reports no device instead of inventing axis/button support. Tests can inject a provider that exposes deterministic devices and write behavior.

## Guarded Verification Behavior

Guarded verification is explicit. It does not run on startup or page render.

The safe verification intent:

- uses a low-magnitude axis value;
- does not press buttons;
- keeps hats centered;
- is labeled as bounded verification only;
- is not arbitrary user profile output.

When a provider supports real writes, verification requires:

- successful acquisition;
- successful bounded write;
- successful neutral restore.

If neutral restore fails, real output remains unverified.

## Output Truth

Rules preserved:

- vJoy detected does not equal output verified.
- Dependency available does not equal output verified.
- Device detected does not equal output verified.
- Fake verified does not equal real verified.
- Real output verified can become true only after guarded write and neutral restore succeed.
- Full Live Runtime Ready remains false in Phase 15B.

## Current Runtime Truth

Current expected conservative truth:

- Bridge lifecycle: Simulated.
- Runtime truth: blocked_missing_device unless telemetry proves otherwise.
- Physical input sampling remains read-only when available.
- vJoy may be detected.
- Output verification is not attempted unless explicitly invoked.
- Full Live Runtime Ready: false.

## Boundary

Phase 15B does not add:

- continuous vJoy output loop;
- end-to-end live output runtime loop;
- automatic output enablement;
- Full Live Runtime Ready;
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

## Verification Results

Passed:

- `python -m pytest` - 332 passed.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - 7 passed.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - 6 passed.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - 5 passed.
- `python -m pytest tests\test_phase13d_flight_recorder_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase14d_input_boundary_freeze.py` - 4 passed.
- `python -m pytest tests\test_phase15a_virtual_output_backend_contract.py` - 5 passed.
- `python -m pytest tests\test_phase15b_real_vjoy_detection_guarded_verification.py` - 7 passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`.
- `python -m bridge_app.main --once`.
- `python -m bridge_app.main --run-for-ms 250`.
- `python -m bridge_app.main --status` - `lifecycle=Simulated truth=blocked_missing_device output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - HOTAS Not Connected, vJoy Detected, Full Live Runtime Ready false.
- `git diff --check`.

## Recommendation

Phase 15C may add runtime output-loop integration only after this guarded verification layer remains stable. Phase 15C must preserve simulation mode, keep Bridge ownership clear, and avoid Full Live Runtime Ready until both input and real output are verified by separate tests.
