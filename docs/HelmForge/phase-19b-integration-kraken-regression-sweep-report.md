# Phase 19B Integration Kraken Regression Sweep Report

Phase 19B adds a repeatable Integration Kraken harness and regression sweep artifacts. It is a test/reporting harness phase only. It does not add runtime behavior, hardware polling, vJoy/output behavior changes, output verification changes, Bridge lifecycle management, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray behavior, StartBridge / StopBridge / RestartBridge behavior, driver/vJoy installer launch, recorder capture/encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, packaging behavior beyond smoke verification, or unsupported runtime activation.

## Harness Design

The harness lives at:

```text
scripts/run_phase19b_kraken.py
```

It runs structured smoke checks and writes machine-readable and human-readable artifacts under:

```text
.artifacts/phase19b_kraken/<timestamp>/
```

Artifacts:

- `phase19b_kraken_summary.md`
- `phase19b_kraken_results.json`
- `phase19b_kraken_rows.jsonl`
- `phase19b_kraken_rows.csv`

The harness supports:

- `--list-sections`
- `--dry-run`
- `--output-root <path>`

## Sections Run

The harness sections are:

- `source_app_smoke`
- `packaged_app_smoke`
- `bridge_smoke`
- `runtime_setup_dry_run`
- `page_navigation_smoke`
- `help_docs_search_smoke`
- `perf_diagnostics_copy_smoke`
- `helm_overlay_smoke`
- `live_overlay_smoke`
- `flight_recorder_smoke`
- `packaging_metadata_smoke`
- `installer_metadata_smoke`
- `runtime_truth_boundary_smoke`
- `full_live_runtime_ready_gate_smoke`
- `safety_boundary_smoke`

## Artifacts Written

Latest verified Phase 19B artifact set:

```text
.artifacts/phase19b_kraken/20260508T012841Z/
```

Artifacts written:

- `.artifacts/phase19b_kraken/20260508T012841Z/phase19b_kraken_summary.md`
- `.artifacts/phase19b_kraken/20260508T012841Z/phase19b_kraken_results.json`
- `.artifacts/phase19b_kraken/20260508T012841Z/phase19b_kraken_rows.jsonl`
- `.artifacts/phase19b_kraken/20260508T012841Z/phase19b_kraken_rows.csv`

Dry-run artifacts use the same schema and mark planned checks as skipped.

## Pass / Fail / Skipped Summary

Latest harness result:

- pass: 19
- fail: 0
- skipped: 1

The skipped row is `installer_metadata_smoke / installer_compile`, because `ISCC.exe` is unavailable on this machine. The installer metadata smoke still passed; the compile itself was not faked.

## Source App Smoke Result

Command:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
```

Result is recorded by the harness and by the final verification ladder.

Latest harness result: pass.

## Packaged App Smoke Result

Command:

```powershell
.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250
```

The harness fails this section if the packaged executable is missing. It does not fake packaged smoke success.

Latest harness result: pass. `packaging/dist/HelmForge/HelmForge.exe` existed and the packaged smoke command exited 0.

## Bridge Smoke Result

Commands:

```powershell
python -m bridge_app.main --once
python -m bridge_app.main --run-for-ms 250
python -m bridge_app.main --status
```

Expected conservative status when HOTAS is missing remains `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.

Latest harness result: pass. Bridge status preserved `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.

## Runtime Setup Dry-Run Result

Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
```

Expected truth:

- no installer launched
- no driver installed
- Full Live Runtime Ready remains governed by the Phase 16 proof gate
- missing HOTAS remains acceptable in simulation mode

Latest harness result: pass.

## Page Navigation Smoke Result

The harness constructs the shell offscreen, navigates all registered pages, verifies scroll containers, and confirms each page title is present. Covered pages:

- Mapping
- Modes
- Base Tuning
- Filtering
- Combat Profile
- Profiles
- Conditional Rules
- Effective Response Stack
- Live Monitor
- Flight Recorder
- Help / Docs
- Perf / Diagnostics

Latest harness result: pass.

## Help / Docs Smoke Result

The harness runs local deterministic searches for:

- Runtime Setup / vJoy Setup
- Runtime Indicators
- Helm
- Live Overlay
- Flight Recorder
- Performance / Diagnostics
- packaging source launch

No web, cloud, or LLM search is used.

Latest harness result: pass.

## Perf / Diagnostics Smoke Result

The harness builds Perf / Diagnostics offscreen and verifies Copy Diagnostics contains runtime truth, Bridge lifecycle, telemetry status, physical input truth, virtual output truth, output loop truth, runtime_frame truth, Full Live Runtime Ready, blocked reason, proof summary, and app version metadata when available.

Latest harness result: pass.

## Helm Overlay Smoke Result

The harness opens Helm from the shell and verifies:

- What's wrong?
- What I'd change
- What I found
- Apply / Revert
- deterministic symptom analysis path
- in-memory apply/revert wording
- no auto-save
- no cloud AI/LLM

Latest harness result: pass.

## Live Overlay Smoke Result

The harness constructs the Live Overlay config dialog and detached overlay window offscreen, verifies show/hide timer behavior, and checks that hotkey/click-through remain conservative. It does not add game injection, graphics API hooking, or screen capture.

Latest harness result: pass.

## Flight Recorder Smoke Result

The harness constructs Flight Recorder and verifies:

- Recorder Settings
- Axis Overlay
- Recording Library
- Clip Preview
- Metadata-only preview
- No video captured
- No encoding performed
- Hotkey not registered

It does not add real capture, video encoding, or recorder hotkey registration.

Latest harness result: pass.

## Packaging / Installer Metadata Smoke Result

Packaging checks verify:

- `packaging/build_release.ps1`
- `packaging/README.md`
- one-folder output path
- packaged executable path
- LocalAppData user data path
- icon status
- `assets/app_icon.ico` gap remains documented

Installer checks verify:

- `packaging/inno/helmforge.iss`
- Start Menu shortcut metadata
- optional Desktop shortcut task
- uninstall metadata
- user data preserved by default
- no driver/vJoy installer launch
- no service install
- no login auto-start
- no Bridge auto-launch

If `ISCC.exe` is unavailable, Inno compile is skipped honestly and recorded as such.

Latest harness result: packaging metadata pass, installer metadata pass, installer compile skipped because `ISCC.exe` is unavailable.

## Full Live Runtime Ready Gate Result

The harness calls the central gate with missing input and unverified output proof and expects `full_live_runtime_ready=false` with a blocked reason. The Full Live Runtime Ready proof gate remains the only authority for full runtime readiness.

Latest harness result: pass.

## Safety Boundary Result

Safety checks include:

- no fake readiness
- no Bridge lifecycle management
- no driver/vJoy installer launch
- no game injection
- no graphics API hooking
- no cloud AI/LLM
- no auto-save
- no recorder real capture/encoding
- no unsupported runtime activation

Latest harness result: pass.

## Known Failures / Blockers

Known blockers carried from Phase 19A:

- `assets/app_icon.ico` is missing.
- Inno compile depends on `ISCC.exe`; if absent, compile is skipped.
- Installer install/uninstall execution is not performed.
- Real hardware Full Live Runtime Ready proof is not claimed without live HOTAS/vJoy proof.
- Real recorder capture/video encoding remains deferred.
- Live Overlay global hotkey and verified click-through remain deferred.
- Signed production installer metadata remains future release work.

## Verification Results

- `python -m pytest` passed: 402 passed.
- `python -m pytest tests\test_phase19a_acceptance_inventory.py` passed: 4 passed.
- `python -m pytest tests\test_phase19b_full_integration_kraken.py` passed: 4 passed.
- `python scripts\run_phase19b_kraken.py` passed and wrote `.artifacts/phase19b_kraken/20260508T012841Z/` with 19 pass, 0 fail, and 1 skipped.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -DryRun` passed.
- `.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250` passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` passed.
- `python -m bridge_app.main --once` passed.
- `python -m bridge_app.main --run-for-ms 250` passed.
- `python -m bridge_app.main --status` passed and reported `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` passed. It detected installed vJoy and Thrustmaster software, reported HOTAS not connected, and kept Full Live Runtime Ready governed by the Phase 16 proof gate.
- `git diff --check` passed.

## Recommendation For Phase 19C

Phase 19C consumed the Phase 19B artifacts, found no failed checks, and confirmed the only skipped item is installer compile because `ISCC.exe` is unavailable. Corrections are documentation/reporting only. It should not treat process presence, packaging success, vJoy detection, physical input detection, output intent, or fake/test paths as Full Live Runtime Ready.

## Phase 19C Correction Note

Phase 19C records `RC Ready With Known Non-Blocking Gaps` as the recommended Phase 19D classification if missing icon embedding, skipped Inno compile, installer execution, signed release metadata, and live hardware proof are outside the release-candidate criteria. `assets/app_icon.ico is missing`, installer compile is skipped without `ISCC.exe`, no installer binary is claimed, and real hardware Full Live Runtime Ready proof is not claimed.
