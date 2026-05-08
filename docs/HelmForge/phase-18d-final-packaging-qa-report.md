# Phase 18D Final Packaging QA And Phase 19 Acceptance Readiness Report

Phase 18D finalizes Packaging, Installer, Icons, and User Data Locations with a QA and boundary-freeze pass. It verifies the one-folder build path, installer metadata, icon truth, resource/user-data path behavior, runtime-truth preservation, and Phase 19 handoff. Phase 18D does not add runtime authority.

## Phase 18A Summary

Phase 18A created the packaging foundation:

- `packaging/README.md`
- `packaging/build_release.ps1`
- `packaging/pyinstaller/README.md`
- `packaging/inno/README.md`
- LocalAppData user data path helper
- source-tree and PyInstaller resource path helper

It selected a PyInstaller one-folder build first and Inno Setup installer work later.

## Phase 18B Summary

Phase 18B made the one-folder build real. The stable build output is:

```text
packaging/dist/HelmForge/
```

The packaged executable path is:

```text
packaging/dist/HelmForge/HelmForge.exe
```

The packaged smoke command is:

```powershell
.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250
```

## Phase 18C Summary

Phase 18C added installer and shortcut metadata:

- Inno script: `packaging/inno/helmforge.iss`
- Start Menu shortcut
- optional Desktop shortcut
- optional launch after install
- uninstall metadata
- optional `-BuildInstaller`, `-SkipInstaller`, and `-InnoPath` build script flags

The installer script does not install drivers, does not install vJoy, does not install services, does not configure login auto-start, does not add tray behavior, and does not manage Bridge lifecycle.

## Phase 18D QA Summary

Phase 18D reviewed packaging files, documentation, installer metadata, icon/resource truth, user-data separation, and runtime boundaries. Phase 18 is now complete. The next prompt-book phase is Phase 19: Final Integration Kraken / Full Acceptance Sweep.

## Build Script Status

`packaging/build_release.ps1` supports:

- `-DryRun`
- `-Clean`
- `-BuildInstaller`
- `-SkipInstaller`
- `-InnoPath`

The script locates the repo root, checks Python imports, reads version metadata from `v3_app.version`, runs PyInstaller in one-folder mode, keeps build outputs under `packaging/output`, `packaging/build`, and `packaging/dist`, and refuses to clean paths outside the repo.

## One-Folder Build Status

The one-folder build target remains:

```text
packaging/dist/HelmForge/
```

The executable remains:

```text
packaging/dist/HelmForge/HelmForge.exe
```

The PyInstaller command excludes tests, pytest, pyqtgraph examples, PySide6 QtTest, and does not add forensic documents or user data.

## Packaged Smoke Result

Packaged smoke is expected to use:

```powershell
.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250
```

The smoke path must launch without HOTAS hardware, without real vJoy output verification, without Bridge auto-launch, without driver installation, and without administrator privileges.

## Installer Script Status

Installer script:

```text
packaging/inno/helmforge.iss
```

Installer metadata:

- app name: HelmForge
- display name: HelmForge - HOTAS Control Panel V3
- version: 0.1.0-dev
- install path: `%LocalAppData%\Programs\HelmForge`
- Start Menu shortcut: yes
- optional Desktop shortcut: yes
- uninstall metadata: yes

The script preserves user data by not deleting `%LocalAppData%\HelmForge`.

## Installer Compile Result

Inno Setup compiler lookup is performed through `ISCC.exe` or `-InnoPath`.

If `ISCC.exe` is unavailable, installer compile is skipped honestly. The later compile command is:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -BuildInstaller
```

## Icon Status

`assets/app_icon.ico is missing`.

PyInstaller and Inno Setup both reference the app icon only when it exists:

- PyInstaller adds `--icon` when `assets/app_icon.ico` exists.
- Inno Setup uses `SetupIconFile={#AppIcon}` behind `#if FileExists(AppIcon)`.
- Start Menu and optional Desktop shortcuts use the icon when available.

Because the `.ico` is missing, icon conversion remains deferred.

## User Data Separation Status

Install/binary path:

```text
%LocalAppData%\Programs\HelmForge
```

User data root:

```text
%LocalAppData%\HelmForge
```

User subfolders:

- `%LocalAppData%\HelmForge\config`
- `%LocalAppData%\HelmForge\profiles`
- `%LocalAppData%\HelmForge\logs`
- `%LocalAppData%\HelmForge\recordings`
- `%LocalAppData%\HelmForge\artifacts`

User data is preserved by default on uninstall. In lowercase installer copy: user data is preserved under `%LocalAppData%\HelmForge`. Phase 18D does not migrate existing source-mode files.

Temporary Bridge telemetry and command files remain under the system temp path, as documented by runtime diagnostics.

## Resource Path Status

`v3_app.services.app_paths` resolves:

- source tree root for normal source execution
- PyInstaller `_MEIPASS` or an injected frozen root for packaged execution
- `assets` through the resource root
- user data under LocalAppData/AppData, without creating directories during path lookup

Missing optional assets, including the app icon, do not crash startup.

## Runtime Truth Preservation

Packaging does not change runtime semantics:

- simulation mode remains available
- telemetry remains the truth surface
- vJoy detection does not equal output verification
- physical input alone is not full readiness
- fake/test paths are not real readiness
- Full Live Runtime Ready remains controlled by the Phase 16 proof gate
- no Bridge lifecycle management is added
- no driver/vJoy installer launch is added
- no new hardware polling is added
- no vJoy/output behavior changes are added
- no recorder capture/encoding behavior is added
- no game injection or graphics API hooking is added
- no cloud AI/LLM behavior is added
- auto-save remains out of scope

## Repository Packaging Exclusions

The PyInstaller command does not add:

- `.git`
- `.venv` / `venv`
- `__pycache__`
- `.pytest_cache`
- tests or pytest
- unrelated forensic documents
- temporary recorder artifacts
- local user data
- secrets or API keys

Generated packaging output folders are ignored by `.gitignore`.

## Known Remaining Packaging Issues

- `assets/app_icon.ico` is still missing, so final EXE/installer/shortcut icon embedding is deferred.
- Installer compile requires Inno Setup 6 and `ISCC.exe`; if absent, only script/dry-run verification is possible.
- Installer install/uninstall execution is not performed in Phase 18D.
- Signing and final release-channel metadata remain future release work.
- User data migration from source-mode paths is not implemented.

## Phase 19 Readiness Checklist

Phase 19 should validate:

- App shell
- all pages
- Runtime setup
- Simulation mode
- Mapping
- Modes
- Base Tuning
- Filtering
- Combat Profile
- Profiles
- Conditional Rules
- Effective Response Stack
- Live Monitor
- Helm
- Live Overlay
- Flight Recorder
- Help / Docs
- Perf / Diagnostics
- Runtime truth
- Full Live Runtime Ready gate
- Layout/performance
- Packaging
- Installer if available

## Recommendation For Phase 19

Phase 19 should be a full prompt-book acceptance sweep. It should verify source launch, packaged launch, all major UI surfaces, runtime truth, boundary wording, and installer metadata if Inno Setup is available. It should not weaken the Phase 16 readiness gate or treat packaging success as runtime readiness.

## Verification Results

- `python -m pytest` passed: 394 passed.
- `python -m pytest tests\test_phase18a_packaging_foundation.py` passed: 5 passed.
- `python -m pytest tests\test_phase18b_pyinstaller_packaged_smoke.py` passed: 5 passed.
- `python -m pytest tests\test_phase18c_icons_installer_metadata.py` passed: 5 passed.
- `python -m pytest tests\test_phase18d_final_packaging_qa.py` passed: 4 passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -DryRun` passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean` passed and rebuilt `packaging/dist/HelmForge/HelmForge.exe`.
- `.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250` passed.
- `Get-Command ISCC.exe -ErrorAction SilentlyContinue` found no compiler on `PATH`; installer compile was skipped.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -DryRun -BuildInstaller` passed and reported that a real installer compile would fail without `ISCC.exe`.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` passed.
- `python -m bridge_app.main --once` passed.
- `python -m bridge_app.main --run-for-ms 250` passed.
- `python -m bridge_app.main --status` passed and reported `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` passed. It detected installed vJoy and Thrustmaster software on this machine, HOTAS not connected, and kept Full Live Runtime Ready governed by the Phase 16 proof gate.
