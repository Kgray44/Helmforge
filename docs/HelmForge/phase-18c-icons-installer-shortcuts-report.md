# Phase 18C Icons, Installer Script, Shortcuts, And Uninstall Metadata Report

Phase 18C adds installer and shortcut metadata for the existing Phase 18B PyInstaller one-folder build. It does not add runtime authority: no driver launch, no vJoy installer launch, no Bridge lifecycle management, no new hardware polling, no output behavior change, and no recorder capture/encoding behavior.

## Packaging Approach

- App name: HelmForge
- Display name: HelmForge - HOTAS Control Panel V3
- Version metadata: 0.1.0-dev from `v3_app.version`
- One-folder build output: `packaging/dist/HelmForge/`
- Packaged executable: `packaging/dist/HelmForge/HelmForge.exe`
- Installer script: `packaging/inno/helmforge.iss`
- Installer output folder: `packaging/installer/`

## Icon Asset Status

`assets/app_icon.ico` is not present in the repository at Phase 18C time. Detailed/simplified icon selection and conversion remain deferred.

Icon conversion remains required before final visual polish of the EXE, installer, and shortcut icon.

## PyInstaller Icon Wiring Status

PyInstaller icon wiring: deferred because assets/app_icon.ico is missing.

`packaging/build_release.ps1` now checks for `assets/app_icon.ico` and passes `--icon` to PyInstaller only when the file exists. When the icon is missing, the build remains allowed and logs that EXE icon embedding is deferred.

## Inno Script Path

The installer script lives at:

```text
packaging/inno/helmforge.iss
```

It targets the Phase 18B one-folder build output and can be compiled by Inno Setup 6 when `ISCC.exe` is available.

## Installer Tasks

The Inno script defines safe installer tasks only:

- optional Desktop shortcut
- optional launch HelmForge after install

It does not install drivers, does not install vJoy, does not install services, does not configure login auto-start, does not add a tray manager, and does not manage Bridge lifecycle.

## Shortcut Behavior

The installer creates a Start Menu shortcut for HelmForge by default. It also offers an optional Desktop shortcut task. Both shortcuts target `{app}\HelmForge.exe` and use the app icon if `assets/app_icon.ico` is available at installer compile time.

## Uninstall Behavior

The installer adds standard uninstall metadata through Inno Setup:

- uninstall display name: HelmForge - HOTAS Control Panel V3
- uninstall display icon: `{app}\HelmForge.exe`
- installed app binaries and shortcuts are removed by the uninstaller

## User Data Preservation Behavior

User data is preserved by default. In lowercase installer copy: user data is preserved under `%LocalAppData%\HelmForge`. The installer does not delete that folder during uninstall. User config, profiles, logs, recordings, and artifacts remain separate from the install directory.

## Installer Build Result

Skipped on this machine because `ISCC.exe` was not found on `PATH`.

Verification commands:

```powershell
Get-Command ISCC.exe -ErrorAction SilentlyContinue
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -DryRun -BuildInstaller
```

The dry-run reported that `-BuildInstaller` would fail without Inno Setup. No installer output is claimed.

## Packaged Smoke Result

Passed after a clean one-folder build. The smoke command was:

```powershell
.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250
```

The command exited successfully without requiring HOTAS hardware, vJoy verification, Bridge lifecycle management, or driver installation.

## Runtime Truth Preservation

Phase 18C packaging metadata does not change runtime truth. The packaged app must still launch without HOTAS/vJoy, preserve simulation mode, keep telemetry as the truth surface, keep vJoy detection separate from output verification, and keep Full Live Runtime Ready controlled by the Phase 16 gate.

## Verification Results

- `python -m pytest` passed: 390 passed.
- `python -m pytest tests\test_phase18a_packaging_foundation.py` passed: 5 passed.
- `python -m pytest tests\test_phase18b_pyinstaller_packaged_smoke.py` passed: 5 passed.
- `python -m pytest tests\test_phase18c_icons_installer_metadata.py` passed: 5 passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -DryRun` passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean` passed and rebuilt `packaging/dist/HelmForge/HelmForge.exe`.
- `.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250` passed.
- `Get-Command ISCC.exe -ErrorAction SilentlyContinue` found no compiler on `PATH`; installer compile was skipped.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` passed.
- `python -m bridge_app.main --once` passed.
- `python -m bridge_app.main --run-for-ms 250` passed.
- `python -m bridge_app.main --status` passed and reported `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` passed. It detected installed vJoy and Thrustmaster software on this machine, HOTAS not connected, and kept Full Live Runtime Ready governed by the Phase 16 proof gate.
- `git diff --check` passed.

## Remaining Phase 18D Work

- Convert/select final `.ico` assets if `assets/app_icon.ico` remains missing.
- Compile the Inno installer on a machine with Inno Setup installed.
- Verify installer launch/uninstall behavior without deleting user data.
- Add final release/signing metadata if scoped.
- Keep simulation-first packaged launch and runtime truth gates intact.
