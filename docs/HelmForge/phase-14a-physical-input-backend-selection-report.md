# Phase 14A - Physical HOTAS Input Backend and Device Selection

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Phase: 14A
Scope: Real HOTAS Input Integration foundation only

## Summary

Phase 14A adds a read-only physical input backend and device-selection foundation without adding runtime or output authority.

Implemented:

- `shared_core/runtime/hotas_input.py` now defines physical input backend capabilities/status, physical device info, selection results, diagnostics summaries, and guarded future sampling placeholders.
- Missing, fake, and read-only Windows PnP physical input backends are available.
- Supported HOTAS matching is centralized for Thrustmaster T-Flight / T.Flight HOTAS One by VID/PID `044f:b68d` and conservative name matching.
- Device selection is in-memory for Phase 14A and reports backend unavailable, no device selected, selected device available, selected device missing, and unsupported selected device.
- Perf / Diagnostics now shows a Physical Input card with backend, supported HOTAS, selected device, sampling, and selection-status truth.
- Help / Docs now explains that physical input selection does not write output, does not make vJoy active, and does not make Full Live Runtime Ready true.

## Runtime Boundary

Simulation mode remains available with:

- no HOTAS connected;
- no Bridge running;
- no vJoy output verification;
- no physical input backend dependency installed.

Phase 14A does not add:

- vJoy writes;
- virtual output writes;
- output verification;
- Full Live Runtime Ready;
- end-to-end live runtime loops;
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

## Device Truth

The Phase 14A backend can use read-only Windows PnP identity discovery. During verification on this machine:

- Physical input backend: `windows_pnp_input_discovery: Available`
- Checked present PnP device names: `259`
- Supported HOTAS detected by Phase 14A PnP matching: `Missing`
- Runtime setup dry run HOTAS status: `HOTAS Not Connected`
- vJoy status: `vJoy Detected`
- Input sampling: `Not active`
- Output verified: `false`
- Full Live Runtime Ready: `false`

This means the OS-visible read-only discovery path did not see the supported Thrustmaster HOTAS One at verification time. No admin prompts were requested, no controls were moved, and no polling loop was started.

## UI And Docs

Perf / Diagnostics now includes Physical Input rows:

- Physical input backend
- Supported HOTAS
- Selected input device
- Input sampling
- Input selection status

Help / Docs updates:

- Runtime Setup / vJoy Setup explains Phase 14A physical input detection/selection.
- Runtime Indicators defines Physical input backend, Supported HOTAS, Selected input device, and Input sampling as device-selection truth only.
- Performance / Diagnostics states that physical input diagnostics are observational.
- The docs state that supported HOTAS detected does not mean vJoy output is active and that Phase 15 is where virtual output/vJoy work begins.

## Verification

Passed:

- `python -m pytest` - 300 passed
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - 7 passed
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - 6 passed
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - 5 passed
- `python -m pytest tests\test_phase13d_flight_recorder_boundary_freeze.py` - 7 passed
- `python -m pytest tests\test_phase14a_physical_input_backend_selection.py` - 6 passed
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed
- `python -m bridge_app.main --once` - passed
- `python -m bridge_app.main --run-for-ms 250` - passed
- `python -m bridge_app.main --status` - passed with `lifecycle=Simulated truth=blocked_missing_device output_verified=False`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; HOTAS Not Connected, vJoy Detected, Full Live Runtime Ready false
- `git diff --check` - passed

## Next Phase

Phase 14B should continue Real HOTAS Input Integration carefully, likely by adding a guarded read-only sampling seam under Bridge/shared-core ownership. Simulation mode must remain available. Phase 15 remains the virtual output/vJoy phase and should be the first phase to scope vJoy writes/output verification explicitly.
