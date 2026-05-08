# Phase 18A Packaging Foundation, Build Script, and User Data Path Plan Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Prompt-book phase: Phase 18A only, Packaging, Installer, Icons, and User Data Locations foundation
Status: Foundation only. Phase 18A does not implement a full installer or claim a verified packaged release.

## Packaging Approach

Phase 18A selects a conservative Windows packaging path:

- First target: PyInstaller one-folder build.
- Later target: Inno Setup installer after the one-folder build is smoke-tested.
- App entry point: `v3_app/main.py`, matching `helmforge = "v3_app.main:main"`.
- Bridge entry point: `bridge_app.main`, matching `helmforge-bridge = "bridge_app.main:main"`.

One-folder output is preferred first because Qt, PySide6, pyqtgraph, plugins, icons, and resource paths are easier to inspect before installer behavior is added.

## Files Created Or Changed

Created:

- `packaging/README.md`
- `packaging/build_release.ps1`
- `packaging/pyinstaller/README.md`
- `packaging/inno/README.md`
- `v3_app/services/app_paths.py`
- `tests/test_phase18a_packaging_foundation.py`

Updated:

- `README.md`
- `v3_app/services/help_docs.py`

## Build Script Behavior

`packaging/build_release.ps1` is a safe Phase 18A build foundation script.

It:

- locates the repository root from the current directory;
- verifies `python` is available;
- verifies expected console script metadata in `pyproject.toml`;
- verifies imports for `PySide6`, `pyqtgraph`, `v3_app.main`, and `bridge_app.main`;
- plans output under `packaging/output`, `packaging/build`, and `packaging/dist`;
- supports `-DryRun`;
- supports a bounded `-Clean` that only targets packaging output paths inside the repo;
- prints the planned `python -m PyInstaller` one-folder command;
- exits without claiming build success when run in dry-run mode;
- never creates an installer.

If run without `-DryRun`, it requires PyInstaller to be importable and fails nonzero if PyInstaller or the build command fails.

## User Data Path Plan

Phase 18A adds `v3_app.services.app_paths` as a planning/helper seam. It does not migrate current user data.

Chosen user data root:

- `%LocalAppData%\HelmForge`

Planned folders:

- `%LocalAppData%\HelmForge\config`
- `%LocalAppData%\HelmForge\profiles`
- `%LocalAppData%\HelmForge\logs`
- `%LocalAppData%\HelmForge\recordings`
- `%LocalAppData%\HelmForge\artifacts`

The helper returns paths without creating directories by default. Phase 18B/18C should decide when first-run creation and migration are appropriate.

## Resource Path Plan

`v3_app.services.app_paths` includes source-tree and PyInstaller-aware resource helpers:

- source-tree root resolution for development;
- `_MEIPASS` support for PyInstaller runtime resources;
- `resolve_resource_path(...)` for packaged/source resource lookup;
- `get_assets_root(...)` for future icon/assets lookup.

The helper avoids absolute developer-machine paths.

## Icon Readiness

Current icon state:

- `assets/app_icon.ico` is not present.
- No `.ico` exists in the repo.
- Detailed PNG candidates exist under `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/00 App Icons and Assets/`.
- A simplified taskbar icon has not been selected as a packaged `.ico`.
- The app does not yet set a Qt application/window icon.

Phase 18B/18C must select or convert a real multi-size `.ico` and embed it in the executable, installer, and shortcuts.

## What Was Tested

Phase 18A closeout verification:

- `python -m pytest` - 380 passed.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed.
- `python -m pytest tests\test_phase16d_full_live_runtime_ready_gate.py` - 4 passed.
- `python -m pytest tests\test_phase17c_final_product_qa_packaging_readiness.py` - 4 passed.
- `python -m pytest tests\test_phase18a_packaging_foundation.py` - 5 passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -DryRun` - passed; printed the planned PyInstaller one-folder command and did not create build or installer output.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed; reported `lifecycle=Simulated truth=blocked_missing_device output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; reported HOTAS not connected, vJoy detected, no installers launched, and Full Live Runtime Ready governed by the Phase 16 proof gate.
- `git diff --check` - passed.

The focused Phase 18A tests cover:

- packaging folder and README presence;
- PyInstaller and Inno handoff notes;
- `build_release.ps1` dry-run and clean-safety wording;
- LocalAppData user data path helper behavior;
- source-tree resource path resolution;
- README/report/help wording that does not claim a completed installer;
- app imports without HOTAS/vJoy;
- no Bridge lifecycle or runtime authority tokens in the Phase 18A seams.

Full verification is recorded during closeout.

## Remaining For 18B/18C

- Install PyInstaller in the build environment if not already available.
- Run and inspect an actual one-folder build.
- Add a real `.ico` asset and embed it.
- Decide whether to keep a generated PyInstaller spec.
- Add Inno Setup script.
- Add Start Menu shortcut.
- Decide optional Desktop shortcut.
- Add uninstall entry.
- Decide Program Files vs LocalAppData Programs install target.
- Implement user data directory creation and any migration policy.
- Smoke-test packaged app launch without HOTAS/vJoy.

## Runtime Truth Preservation Statement

Phase 18A preserves all established runtime boundaries:

- Simulation mode remains available, and simulation mode remains the required packaged first-launch fallback when HOTAS/vJoy is missing.
- Telemetry remains the truth surface.
- Full Live Runtime Ready is controlled by the final Phase 16 readiness gate.
- vJoy detection alone is not output verification.
- Physical input alone is not full readiness.
- Fake/test paths are not real readiness.
- Bridge lifecycle management is not part of Phase 18A.

Phase 18A does not implement a full installer, final release build, real driver/vJoy installer launch, automatic Bridge launch, UI-launched child process, service install, login auto-start, tray manager, StartBridge/StopBridge/RestartBridge behavior, new runtime behavior, new hardware polling, new vJoy/output behavior, output verification changes, recorder capture/encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or unsupported runtime activation.
