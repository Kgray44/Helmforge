# Phase 17C Final Product QA Sweep and Phase 18 Packaging Readiness Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Prompt-book phase: Phase 17C only, final Product Polish, Layout QA, and Motion pass
Status: Phase 17 is now complete. The next prompt-book phase is Phase 18: Packaging, Installer, Icons, and User Data Locations.

## Pages Reviewed

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

The focused QA smoke constructs the shell, navigates every registered page across 1280 x 720, 1440 x 900, and 1920 x 1080 offscreen sizes, and confirms each page remains in a resizable vertical scroll surface. Heavy page instances remain reused across navigation so the Phase 17B anti-jank behavior is preserved.

## Overlays And Dialogs Reviewed

- Helm overlay opens from the shell and still exposes Apply Selected Changes without adding auto-save or runtime mutation.
- Live Overlay Configuration dialog constructs with the Phase 17A minimum size.
- Detached Live Overlay window starts its refresh timer only while shown and stops it when hidden.
- Flight Recorder remains a metadata/simulated-artifact surface; no recorder capture, video encoding, or playable clip behavior is added.
- Help / Docs search remains local and deterministic.

## Final Layout QA Notes

No major redesign was performed. The final QA pass keeps the dark engineering-console style from Phase 17A and the update-discipline work from Phase 17B. The shell keeps scrollable page bodies, the footer does not own runtime behavior, and status chips remain distinct from action buttons. Perf / Diagnostics now exposes a compact "Blocked reason" row beside the readiness proof labels so the same field appears in the visible page and Copy Diagnostics.

Known layout posture for Phase 18 packaging smoke: packaged windows should still be checked manually at 1280 x 720, 1440 x 900, 1920 x 1080, and on the recovered 2048 x 1280 reference display if available.

## Final Runtime Truth Preservation Statement

Phase 17C preserves the final Phase 16 runtime truth gate:

- Telemetry remains the truth surface.
- Command files are requests, not success proof.
- Process presence is a hint only.
- Physical input sampling does not imply output.
- Output intent is not output write proof.
- vJoy detected does not equal output verified.
- Fake/mock output is not real output.
- Full Live Runtime Ready requires the centralized Phase 16 proof gate.
- Simulation mode remains available.
- Bridge lifecycle management is not implemented.

Phase 17C does not implement packaging, installer scripts, icon conversion, user data migration, new hardware polling, vJoy writes, output verification changes, Bridge lifecycle management, recorder capture/encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or unsupported runtime activation.

## Performance And Update Notes

Phase 17B update discipline remains intact. Heavy page instances are reused, hidden Live Monitor and Effective Response Stack update skips remain instrumented, graph widgets update existing plot items in place, and detached Live Overlay refresh timers stop when the overlay is hidden. Phase 17C adds no new timers, background loops, hardware polling, folder scanners, output loops, or capture loops.

## Known Remaining Polish Issues

- Phase 18 should perform a packaged-app visual smoke at common desktop sizes because PyInstaller/installer resource layout can reveal path and DPI differences not visible in source-mode tests.
- The app does not yet set a packaged window/taskbar icon from source. Phase 18 should add icon embedding deliberately.
- Current user data paths are still source/development oriented and need Phase 18 LocalAppData/AppData decisions before packaging.
- The Flight Recorder remains metadata/simulated-artifact only; real capture, encoding, and playable video are outside Phase 17.

## Phase 18 Packaging Readiness Census

Current source entry points:

- App module: `python -m v3_app.main`
- Bridge module: `python -m bridge_app.main`
- Console scripts in `pyproject.toml`: `helmforge = "v3_app.main:main"` and `helmforge-bridge = "bridge_app.main:main"`

Current dependencies from `pyproject.toml`:

- `PySide6`
- `pyqtgraph`
- `pytest`

Current packaging artifact state:

- No `packaging/` directory exists.
- No `installer/` directory exists.
- No PyInstaller `.spec` file exists.
- No `.ico` file exists in the repo.
- No packaging or installer build script exists in `scripts/`; `scripts/runtime_setup_check.ps1` is runtime setup/preflight only.

Icon asset state:

- Detailed PNG icon candidates exist under `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/00 App Icons and Assets/`.
- The app does not currently set a Qt application/window icon from source.
- Phase 18 needs a deliberate multi-size `.ico` conversion/embedding decision and a simplified taskbar icon decision.

Config, telemetry, and artifact path assumptions:

- Workspace config defaults to `hotas_bridge_config_v3.json` in the source working context.
- Bridge telemetry defaults to `%TEMP%/helmforge_bridge_telemetry.json`.
- Bridge command requests default to `%TEMP%/helmforge_bridge_command.json`.
- Flight Recorder simulated artifact destination defaults to `%USERPROFILE%/Videos/hotas_recordings_v3`.
- Help / Docs content is currently built into `v3_app/services/help_docs.py`.
- Packaging-time resource paths and writable user data paths are not separated yet.

Phase 18 should cover:

- PyInstaller or equivalent build approach.
- One-folder release build.
- Inno Setup or equivalent installer.
- Start Menu shortcut.
- Optional Desktop shortcut.
- Uninstall entry.
- App icon embedding.
- Simplified taskbar icon.
- Detailed icon preservation.
- User data path separation.
- Config, profiles, logs, recordings, artifacts, telemetry, and command paths under AppData or LocalAppData.
- Packaged app smoke test.
- Packaged app launch without HOTAS/vJoy.
- Missing vJoy/HOTAS guidance still visible.

## User Data Path Readiness Notes

Phase 17C performs no migration. Phase 18 must decide and test final writable locations for:

- Workspace/config file.
- Profiles or imported profile files if they become separate artifacts.
- Logs and diagnostics artifacts.
- Recorder simulated exports and future recorder artifacts.
- Bridge telemetry and command request files.
- Help / Docs and packaged read-only resources.
- Any future packaged icon or asset resources.

The current source defaults are acceptable for development but should not be silently reused as packaged production data locations without a Phase 18 decision.

## Icon Readiness Notes

The repo contains detailed PNG candidates from the forensic evidence set, but no packaged `.ico`. Phase 18 should create or select:

- A detailed application icon.
- A simplified taskbar icon.
- A multi-size `.ico` for Windows shell integration.
- A Qt application/window icon reference.
- Installer icon references if the installer toolchain requires them.

Phase 17C does not create or convert icons.

## Tests Run

Phase 17C closeout verification:

- `python -m pytest` - 375 passed.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - 7 passed.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - 6 passed.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - 5 passed.
- `python -m pytest tests\test_phase13d_flight_recorder_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase14d_input_boundary_freeze.py` - 4 passed.
- `python -m pytest tests\test_phase15d_output_boundary_freeze.py` - 4 passed.
- `python -m pytest tests\test_phase16d_full_live_runtime_ready_gate.py` - 4 passed.
- `python -m pytest tests\test_phase17a_product_polish_layout_qa.py` - 5 passed.
- `python -m pytest tests\test_phase17b_motion_performance_polish.py` - 6 passed.
- `python -m pytest tests\test_phase17c_final_product_qa_packaging_readiness.py` - 4 passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed; reported `lifecycle=Simulated truth=blocked_missing_device output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; reported HOTAS not connected, vJoy detected, and Full Live Runtime Ready governed by the Phase 16 proof gate.
- `git diff --check` - passed.

The focused Phase 17C test guards page construction, navigation, Helm overlay construction, Live Overlay dialog/window behavior, runtime truth copy, Help / Docs packaging/source truth, README/architecture Phase 18 wording, packaging census truth, and the absence of packaging scripts or new runtime authority.

## Recommendation For Phase 18

Start Phase 18 with a packaging spike that stays simulation-first:

- Build from `python -m v3_app.main` and the `helmforge` script entry point.
- Preserve manual Bridge lifecycle ownership; do not add UI Bridge start/stop/restart controls unless a later phase explicitly scopes them.
- Move writable app data to LocalAppData/AppData through a tested path policy before creating the installer.
- Embed icons only after selecting detailed and simplified assets.
- Smoke the packaged app without HOTAS and without vJoy, confirming simulation mode, Help / Docs guidance, runtime truth, and Full Live Runtime Ready proof behavior remain intact.

Phase 18 must preserve runtime truth behavior and simulation-first launch. Phase 17C does not implement packaging.
