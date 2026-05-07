# Phase 15A Virtual Output Backend Contract Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Phase: 15A only - vJoy / Virtual Output Integration contract foundation
Status: Implemented and verified

## Scope

Phase 15A starts the virtual output phase conservatively. It adds shared-core contracts and truth surfaces for output intent, output backend state, and safe fake/mock verification without performing real vJoy writes.

Implemented:

- `VirtualOutputBackend` capability/status contract.
- `VirtualOutputDeviceInfo`.
- `VirtualOutputIntent`, `VirtualAxisOutput`, `VirtualButtonOutput`, and `VirtualHatOutput`.
- `VirtualOutputWriteResult`.
- `VirtualOutputVerificationResult` with statuses for `not_attempted`, `backend_missing`, `device_missing`, `write_failed`, `fake_verified`, `real_verified`, `unsupported`, and `error`.
- Missing virtual output backend.
- Deterministic fake virtual output backend for tests/dev injection.
- Recovered virtual output route intent:
  - Roll -> X.
  - Pitch -> Y.
  - Throttle -> Z.
  - Yaw -> RX.
  - Aux 1 -> RY.
  - Aux 2 -> RZ.
- Perf / Diagnostics virtual output fields and Copy Diagnostics text.
- Mapping and Live Monitor virtual output truth labels.
- Help / Docs wording for output intent, fake verification, and vJoy detection truth.

## Output Intent Truth

An output intent is the app/shared-core representation of what would be sent to a virtual output backend later. It is not write proof.

Phase 15A can model intended axes, buttons, hats, source, warnings, output-enabled state, and write-requested state. Creating an intent does not touch a real device and does not change output verification.

## Missing Backend Truth

The missing backend is the safe default. It:

- imports without a real vJoy dependency;
- reports backend missing;
- enumerates no output devices;
- returns write unavailable;
- returns output verification unverified;
- never sets `output_verified` true;
- never sets real output verified true.

## Fake Backend Truth

The fake backend is deterministic and in-memory. It:

- can record the last `VirtualOutputIntent`;
- can return a fake write result;
- can return `fake_verified`;
- labels verification as fake/mock and Not real vJoy;
- never sets real output verified true;
- does not prove a real vJoy write.

Fake/mock verification is useful for tests and future development seams only. It is not normal runtime proof.

## UI / Diagnostics Behavior

Perf / Diagnostics now includes:

- Virtual output backend.
- Output device status.
- Output write status.
- Output verification status.
- Output verification source.
- Fake output verified.
- Real output verified.
- output_verified.
- Full Live Runtime Ready.

Mapping and Live Monitor show the same output contract truth compactly while preserving Phase 14 read-only physical input labels.

Copy Diagnostics includes the virtual output backend and real/fake verification truth.

## Current Runtime Truth

Conservative runtime truth remains:

- Bridge lifecycle: Simulated.
- Runtime truth: blocked_missing_device unless telemetry proves a different typed state.
- Physical input sampling may be read-only when available.
- vJoy may be detected, but detection is not verification.
- output_verified: false in normal runtime.
- Real output verified: false.
- Full Live Runtime Ready: false.

## Boundary

Phase 15A does not add:

- real vJoy writes;
- real virtual joystick writes;
- real output verification;
- end-to-end live output loop;
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

## Documentation Notes

README, bridge UI architecture, bridge service design, Runtime Setup / vJoy Setup, Runtime Indicators, and Performance / Diagnostics now state:

- Phase 15A adds virtual output backend contracts only.
- Real vJoy writes are not implemented yet.
- Output intent is not output write proof.
- Fake/mock output verification is not real output verification.
- vJoy detected does not equal output verified.
- output_verified remains false in normal runtime.
- Full Live Runtime Ready remains false.
- Simulation mode remains available.
- Phase 15B may add guarded real vJoy detection/write verification.

## Verification Results

Passed:

- `python -m pytest` - 325 passed.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - 7 passed.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - 6 passed.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - 5 passed.
- `python -m pytest tests\test_phase13d_flight_recorder_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase14d_input_boundary_freeze.py` - 4 passed.
- `python -m pytest tests\test_phase15a_virtual_output_backend_contract.py` - 5 passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`.
- `python -m bridge_app.main --once`.
- `python -m bridge_app.main --run-for-ms 250`.
- `python -m bridge_app.main --status` - `lifecycle=Simulated truth=blocked_missing_device output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - HOTAS Not Connected, vJoy Detected, Full Live Runtime Ready false.
- `git diff --check`.

## Recommendation

Move next to Phase 15B only after Phase 15A verification is green. Phase 15B should add any guarded real vJoy detection/write verification behind explicit missing/fake/real backend seams, preserve simulation mode, and keep Full Live Runtime Ready false until both input and real output are verified.
