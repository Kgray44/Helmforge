# Phase 1A Thrustmaster Setup Report

Status: Phase 1A implemented and verified.

Scope:

- Re-check the official Thrustmaster T.Flight Hotas One support page.
- Add official-source-only driver setup guidance.
- Add setup status labels for Thrustmaster driver/device, vJoy, simulation, and full live readiness.
- Add a safe app-side support-page button.
- Add tests for target metadata, fuzzy device detection, setup status labels, official support guidance, and help docs.

Out of scope:

- Driver installation.
- Driver download automation.
- vJoy installation.
- Real HOTAS polling.
- Real vJoy writes.
- Mapping, tuning, recorder, overlay, or Helm assistant work.

## Official Source Check

Official product page checked during implementation:

- https://support.thrustmaster.com/en/product/t-flight-hotas-one-en/

The official page currently shows a driver package resembling `Drivers - Package 2025_TFHT_5 + Firmware` and lists Windows 10 / Windows 11. Future operators should still check the official page because driver packages can change.

## Runtime Behavior

- Setup status remains `Thrustmaster Driver Unknown` unless there is explicit safe evidence to say otherwise.
- Missing HOTAS appears as `HOTAS Not Connected`.
- Detected target HOTAS appears as `T-Flight HOTAS One Detected` plus `Input Ready`.
- Missing vJoy appears as `vJoy Missing`.
- Simulation fallback appears as `Simulation Mode Active`.
- `Full Live Runtime Ready` is only available when the runtime mode is full live and live output writes are verified.

## Files Created

- `shared_core/runtime/setup_guidance.py`
- `docs/HelmForge/help/runtime-setup-hotas-driver.md`
- `docs/HelmForge/phase-1a-thrustmaster-setup-report.md`
- `tests/test_phase1a_thrustmaster_setup.py`

## Files Changed

- `shared_core/models/runtime.py`
- `v3_app/main.py`
- `docs/HelmForge/runtime-preflight-and-vjoy-setup.md`

## Commands Run

- `Get-Content "HOTAS Control Panel Forensic Spec Set/Hotas Control Panel V2  - Phase1A.txt"`
- `git status --short`
- `git log -3 --oneline`
- official Thrustmaster support page web check
- `python -m pytest tests/test_phase1a_thrustmaster_setup.py`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`
- live setup-status check with current machine preflight

## Final Verification Results

- `python -m pytest tests/test_phase1a_thrustmaster_setup.py`: `7 passed`.
- `python -m pytest`: `17 passed`.
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`: exit code `0`.
- Current machine preflight:
  - runtime mode: `simulated`
  - runtime truth: `simulated`
  - input status: `missing`
  - output status: `vjoy_missing`
  - setup labels: `Thrustmaster Driver Unknown | HOTAS Not Connected | vJoy Missing | Simulation Mode Active`

## Issues and Assumptions

- The official Thrustmaster support page was checked during implementation; the package note can change later and should be rechecked before a human installs anything.
- Phase 1A records driver status as unknown unless there is explicit safe evidence to say it is present or missing.
- No driver installer was downloaded or run.
- No Thrustmaster driver, vJoy, or hardware driver installation was attempted.
- No third-party driver source was added.

## Next Recommended Phase

The next phase should remain simulation-first. A practical next step is defining the profile/config/mapping contracts that future runtime polling and vJoy writes will consume.
