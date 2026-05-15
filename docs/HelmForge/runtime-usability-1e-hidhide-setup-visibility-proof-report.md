# Runtime Usability 1E-B HidHide Install / Configure / Verification Report

## 1. Executive result

Runtime Usability 1E-B installed HidHide through the explicit confirmed winget path and stopped safely at manual GUI configuration because the installed HidHide CLI is present but not safely usable from this non-elevated process.

Current result on 2026-05-14:

- HidHide is installed.
- HidHide version: `1.5.230`.
- Install command used: `winget install -e --id Nefarius.HidHide`.
- Package identity was verified first through `winget search HidHide`, which returned exact package ID `Nefarius.HidHide`.
- winget reported the installer would request administrator approval; installation completed successfully.
- Reboot required: no.
- HidHide Configuration Client detected.
- HidHide CLI detected, but CLI help/config access returned `Access is denied`; no CLI configuration syntax was guessed.
- HidHide configuration is manual-required through HidHide Configuration Client.
- No device hiding was applied by this probe.
- vJoy was not hidden.
- Target game was not allow-listed by default.
- Bridge/setup still detect the physical HOTAS and vJoy after installation, before HidHide hiding is enabled.
- Physical smoke after HidHide hiding was not run because manual GUI configuration is still required.
- vJoy write-call proof after hiding was not run. Current pre-HidHide real-vJoy write-call probes remain passing.
- vJoy readback remains not implemented and not claimed.

This is the safe-blocked path: installation succeeded, but configuration/after-hide verification requires user GUI action before proceeding.

## 2. Installation

- Installed during this phase: yes.
- Exact install command: `winget install -e --id Nefarius.HidHide`.
- Search command: `winget search HidHide`.
- Verified package ID: `Nefarius.HidHide`.
- Publisher/source observed by winget: Nefarius / winget.
- UAC/admin: winget output said the installer would request administrator approval. The install completed; no bypass was attempted.
- Reboot required: no.
- Reboot completed/pending: not required.
- Random download mirrors: not used.

## 3. HidHide paths

- Client: `C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideClient.exe`
- CLI: `C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe`
- Install location: `C:\Program Files\Nefarius Software Solutions\HidHide\x64`

CLI probe:

- `HidHideCLI.exe --help` returned `Access is denied`.
- `HidHideCLI.exe /?` returned `The command is not recognized.`
- Because the CLI contract was not available safely, configuration was not applied programmatically.

## 4. Physical HOTAS proof

Target:

- Thrustmaster T-Flight HOTAS One
- `VID_044F&PID_B68D`

Detected entries:

- `HID\VID_044F&PID_B68D\8&39EC0CDD&0&0000`
- `USB\VID_044F&PID_B68D\7&18CB956B&0&3`

Planned hidden entries are limited to those VID/PID matches only. No keyboard, mouse, touchpad, unrelated controller, Bluetooth device, or vJoy entry is selected for hiding.

## 5. vJoy status

Detected vJoy entries:

- `vJoy Driver` / `{D6E55CA0-1A2E-4234-AAF3-3852170B492F}\VJOYRAWPDO\1&2D595CA7&0&VJOYINSTANCE00`
- `vJoy Device` / `ROOT\HIDCLASS\0000`
- `C:\Program Files\vJoy\x64\vJoyInterface.dll`

Explicit vJoy hiding status: vJoy was not hidden.

## 6. Allow-list

Generated allow-list:

- `C:\Users\kkids\AppData\Local\Programs\Python\Python312\python.exe`
- `C:\Users\kkids\AppData\Local\Programs\Python\Python312\pythonw.exe`

Packaged Bridge executable: not detected/provided.

Packaged HelmForge executable: not detected/provided.

Target game allow-listed by default: no.

## 7. Configuration state

Configuration command run:

- `python scripts/hidhide_setup_probe.py --configure --confirm`

Result:

- `manual_required_cli_contract_unverified`
- No HidHide hidden-device state was changed by the probe.
- Manual GUI steps were generated at `artifacts/runtime-hidhide-setup/20260514T014909Z/manual-hidhide-setup-steps.md`.
- Game-readiness checklist was generated at `artifacts/runtime-hidhide-setup/20260514T014838Z/game-readiness-after-hidhide.md`.

Manual configuration required:

1. Open HidHide Configuration Client.
2. Applications tab: add the Python/Bridge/HelmForge reader executable paths.
3. Devices tab: select only the physical HOTAS entries matching `VID_044F&PID_B68D`.
4. Do not select vJoy.
5. Enable device hiding.
6. Reconnect the HOTAS if needed.
7. Rerun `python scripts/hidhide_setup_probe.py --verify --real-hotas-check --real-vjoy-writes --confirm`.

## 8. Verification

Post-install, pre-hide checks:

- `python -m bridge_app.main --status`: passed; `lifecycle=LiveVerified truth=live_verified output_verified=True`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`: passed; detected HOTAS and vJoy.
- `python scripts/hidhide_setup_probe.py --verify --confirm`: passed; physical HOTAS detection proof `detected`, configuration proof `dry_run`.
- `python scripts/hidhide_setup_probe.py --install --configure --verify --real-hotas-check --real-vjoy-writes --confirm`: passed safely; did not reinstall, reported manual-required configuration, detected HOTAS through setup check, skipped real after-hide probes.

After-hide checks not yet complete:

- Bridge after HidHide hiding: not claimed.
- Minimal physical smoke after HidHide hiding: not run.
- vJoy write-call after HidHide hiding: not run.
- Game-facing hidden-device proof: not claimed.

Existing write-call probes after HidHide install but before HidHide hiding:

- `python scripts/runtime_truth_value_probe.py --real-vjoy-writes`: passed; artifact `artifacts/runtime-truth-value-usability/20260514T015149Z`.
- `python scripts/runtime_tuning_matrix_probe.py --real-vjoy-writes`: passed; artifact `artifacts/runtime-tuning-matrix/20260514T015148Z`.

## 9. Artifacts

- Install artifact: `artifacts/runtime-hidhide-setup/20260514T014352Z/summary.json`
- Configure artifact: `artifacts/runtime-hidhide-setup/20260514T014909Z/summary.json`
- Full safe-blocked artifact: `artifacts/runtime-hidhide-setup/20260514T014838Z/summary.json`
- Manual setup steps: `artifacts/runtime-hidhide-setup/20260514T014909Z/manual-hidhide-setup-steps.md`
- Game readiness checklist: `artifacts/runtime-hidhide-setup/20260514T014838Z/game-readiness-after-hidhide.md`

## 10. Known gaps

- Manual HidHide GUI configuration is still required.
- Automated game-level visibility proof is not implemented.
- Physical smoke after HidHide hiding has not run.
- vJoy write-call proof after HidHide hiding has not run.
- vJoy readback remains not implemented.

## 11. Files changed

- `scripts/hidhide_setup_probe.py`
- `tests/test_runtime_usability_1e_hidhide_setup_probe.py`
- `docs/HelmForge/runtime-usability-1e-hidhide-setup-visibility-proof-report.md`

## 12. Tests run

- `python -m pytest tests/test_runtime_usability_1e_hidhide_setup_probe.py -q` - 26 passed.
- `python -m pytest tests/test_runtime_usability_1d_physical_hotas_smoke_probe.py -q` - 11 passed.
- `python -m pytest tests/test_runtime_usability_1c_close_known_gaps.py -q` - 14 passed.
- `python -m pytest tests/test_runtime_usability_1b_full_tuning_matrix.py -q` - 19 passed.
- `python -m pytest tests/test_runtime_usability_1a_control_chain_correctness.py -q` - 6 passed.
- `python -m pytest tests/test_phase16b_runtime_frame_telemetry_ui.py -q` - 6 passed.
- `python -m pytest tests/test_phase3_tuning_math_pipeline.py -q` - 17 passed.
- `python -m py_compile scripts/hidhide_setup_probe.py scripts/runtime_physical_hotas_smoke_probe.py scripts/runtime_truth_value_probe.py scripts/runtime_tuning_matrix_probe.py v3_app/services/bridge_client.py shared_core/runtime/runtime_orchestrator.py shared_core/math/filtering.py shared_core/math/curves.py shared_core/math/deadzone.py shared_core/math/stack.py shared_core/math/pipeline.py shared_core/runtime/vjoy_output.py` - passed.
- `python scripts/runtime_truth_value_probe.py --real-vjoy-writes` - passed.
- `python scripts/runtime_tuning_matrix_probe.py --real-vjoy-writes` - passed.
- `git diff --check` - passed.

Full `python -m pytest` was not run.

## 13. Runtime truth preservation

Accepted vJoy write calls are not treated as vJoy readback proof. Bridge/setup detection proves HelmForge-side visibility only; it does not prove game-level filtering unless a non-whitelisted game or ordinary controller observer is actually checked. Full Live Runtime Ready semantics were not changed or loosened.

## 14. Rollback instructions

If HidHide is configured and needs to be undone:

1. Open HidHide Configuration Client.
2. Disable device hiding, or uncheck the HOTAS hidden device entries.
3. Keep vJoy installed.
4. Do not uninstall vJoy.
5. Reconnect HOTAS.
6. Rerun `python -m bridge_app.main --status`.
7. Rerun `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`.
8. If needed, uninstall HidHide from Windows Apps & Features, then reboot.
