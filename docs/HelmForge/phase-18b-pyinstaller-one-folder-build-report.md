# Phase 18B PyInstaller One-Folder Build and Packaged App Smoke Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Prompt-book phase: Phase 18B only, Packaging, Installer, Icons, and User Data Locations
Status: PyInstaller one-folder build path implemented. No final installer release.

## Packaging Approach

Phase 18B uses PyInstaller one-folder output as the first real Windows packaging target. The installer remains deferred until the one-folder output is stable and smoke-tested.

- Build tool: PyInstaller.
- Build type: one-folder, not one-file.
- App entry point: `v3_app/main.py`.
- App name: `HelmForge`.
- Bridge package handling: `bridge_app.main` is included as a hidden import for packaged-module availability, but the packaged UI does not launch or manage the Bridge.
- Test/package exclusions: pytest, project tests, pyqtgraph examples, and PySide6 QtTest are excluded. Forensic documents are not bundled.

## Build Command

Dry run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -DryRun
```

Build:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean
```

The build script prints the exact `python -m PyInstaller` command before executing it.

## Output Path

The expected one-folder output path is:

```text
packaging/dist/HelmForge/
```

## Packaged Executable Path

The expected packaged executable path is:

```text
packaging/dist/HelmForge/HelmForge.exe
```

## Packaged Smoke Result

Phase 18B local verification passed.

Build command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean
```

Build result:

- PyInstaller completed successfully.
- `packaging/dist/HelmForge/HelmForge.exe` was created.
- No installer was created.
- PyInstaller emitted an optional pyqtgraph OpenGL collection warning because PyOpenGL is not installed. HelmForge does not currently rely on pyqtgraph OpenGL surfaces, and the warning did not block the one-folder GUI smoke.
- A packaged-output scan found no bundled recovery/forensic documents, `.git` files, project tests, pytest package files, or local runtime artifacts.

Packaged smoke commands:

```powershell
.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250
$env:QT_QPA_PLATFORM='offscreen'; .\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250
```

Both packaged smoke launches exited cleanly. The packaged smoke launched without HOTAS hardware, without vJoy output verification, without admin rights, without installing drivers, and without starting the Bridge automatically.

## Missing HOTAS/vJoy Behavior

The packaged app must preserve simulation mode and the Phase 16 Full Live Runtime Ready gate. Missing HOTAS, missing or unverified vJoy, stale telemetry, and missing Bridge telemetry must remain conservative runtime truth states. vJoy detection alone is not output verification, and physical input alone is not full readiness.

The local runtime setup dry-run during Phase 18B reported HOTAS not connected and vJoy detected. Full Live Runtime Ready remained governed by the Phase 16 proof gate.

## Resource Path Notes

`v3_app.services.app_paths` supports source-tree and PyInstaller-style resource roots. Help / Docs content remains built into Python modules, so no external Help / Docs data folder is bundled in Phase 18B. Optional assets remain gracefully missing until icon work lands.

## Icon Status

No `.ico` is present yet. `assets/app_icon.ico` is still missing. Phase 18B does not create icon art or block the build on icon availability. Final icon selection, conversion, and embedding remain Phase 18C work.

## Known Packaging Gaps

- No final installer release.
- No Inno Setup installer script.
- No Start Menu shortcut.
- No Desktop shortcut.
- No uninstall entry.
- No embedded `.ico`.
- No user data migration or first-run directory creation.
- No packaged Bridge service/tray/autostart behavior.

## Verification

Phase 18B closeout verification:

- `python -m pytest` - 385 passed.
- `python -m pytest tests\test_phase18a_packaging_foundation.py` - 5 passed.
- `python -m pytest tests\test_phase18b_pyinstaller_packaged_smoke.py` - 5 passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -DryRun` - passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean` - passed and created `packaging/dist/HelmForge/HelmForge.exe`.
- `.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250` - passed.
- `$env:QT_QPA_PLATFORM='offscreen'; .\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250` - passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed; reported `lifecycle=Simulated truth=blocked_missing_device output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; reported HOTAS not connected, vJoy detected, no installers launched, and Full Live Runtime Ready governed by the Phase 16 proof gate.
- `git diff --check` - passed.

## What Remains For Phase 18C

Phase 18C should decide and implement the installer slice after the one-folder output is accepted:

- select or convert the final multi-size `.ico`;
- wire icon embedding into the PyInstaller build and installer;
- add Inno Setup script;
- add Start Menu shortcut;
- decide optional Desktop shortcut;
- add uninstall entry;
- decide Program Files versus LocalAppData Programs install target;
- smoke-test the installed app without HOTAS/vJoy.

## Runtime Truth Preservation

Phase 18B does not add a final installer release, driver/vJoy installer launch, automatic Bridge launch, UI-launched child process, service install, login auto-start, tray manager, StartBridge/StopBridge/RestartBridge behavior, new runtime behavior, new hardware polling, new vJoy/output behavior, output verification changes, recorder capture/encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or unsupported runtime activation.
