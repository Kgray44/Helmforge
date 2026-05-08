# HelmForge Packaging Foundation

Phase 18A added packaging foundation for HelmForge / HOTAS Control Panel V3. Phase 18B adds the first real PyInstaller one-folder build path and packaged app smoke command without claiming a completed installer or runtime activation. Phase 18C adds icon-aware build behavior and an Inno Setup installer script with shortcuts and uninstall metadata. Phase 18D completes final packaging QA and Phase 19 acceptance readiness without adding runtime authority.

## Strategy

- Build path: PyInstaller one-folder build.
- Installer path: Inno Setup later, after the one-folder build is smoke-tested.
- App name: HelmForge.
- Entry point: `v3_app/main.py`, matching the source console script `helmforge = "v3_app.main:main"`.
- Bridge entry point: `bridge_app.main`, matching `helmforge-bridge = "bridge_app.main:main"`. Phase 18A does not add Bridge lifecycle management.

## Phase 18D Status

Phase 18D freezes the Phase 18 packaging state:

- `packaging/build_release.ps1`, a conservative PowerShell build script with `-DryRun`, safe `-Clean` support, and a real PyInstaller one-folder build path.
- Optional installer compile support through `-BuildInstaller`, `-SkipInstaller`, and `-InnoPath`.
- `packaging/pyinstaller/README.md`, PyInstaller notes for the one-folder build.
- `packaging/inno/helmforge.iss`, an Inno Setup installer script.
- `packaging/inno/README.md`, installer notes.
- A user data path plan for LocalAppData.
- Resource path helper planning for source-tree and PyInstaller execution.

Phase 18D does not add runtime authority. It does not install drivers, does not install vJoy, does not install services, does not add login auto-start, does not add tray behavior, does not start or stop the Bridge, and does not alter runtime truth.

Phase 18 is now complete. The next prompt-book phase is Phase 19: Final Integration Kraken / Full Acceptance Sweep.

## Phase 19C Correction Status

The reviewed Phase 19B Kraken artifact is `.artifacts/phase19b_kraken/20260508T012841Z/`: 19 pass, 0 fail, and 1 skipped installer compile. The skipped compile is because `ISCC.exe` is unavailable on this machine. Installer metadata passed, packaged smoke passed, and no installer binary is claimed.

`assets/app_icon.ico is missing`, so icon embedding remains a known packaging blocker for final release polish. Packaging smoke is not runtime readiness; Full Live Runtime Ready remains governed by the Phase 16 proof gate.

## One-Folder Build Goal

The first release artifact is a one-folder build under `packaging/dist/HelmForge/`. A one-folder build is easier to inspect, smoke-test, and debug before an installer is introduced.

Expected build command from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -DryRun
```

When PyInstaller is installed, omit `-DryRun` to attempt the one-folder build:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1
```

The script does not claim build success unless the PyInstaller command exits successfully. It never claims an installer exists.

Expected executable after a successful build:

```text
packaging/dist/HelmForge/HelmForge.exe
```

Expected packaged smoke command:

```powershell
.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250
```

Phase 18B does not create an installer. Phase 18C adds the Inno Setup script and optional compile path, but an installer exists only after `-BuildInstaller` succeeds on a machine with Inno Setup available.

## Installer Build

The installer script is:

```text
packaging/inno/helmforge.iss
```

If Inno Setup 6 is installed and `ISCC.exe` is on `PATH`, compile after the one-folder build with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -BuildInstaller
```

If `ISCC.exe` is not on `PATH`, pass it explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -BuildInstaller -InnoPath "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

Expected installer output folder:

```text
packaging/installer/
```

The installer creates a Start Menu shortcut, offers an optional Desktop shortcut, offers optional launch after install, and adds standard uninstall metadata. It does not install drivers, does not install vJoy, and does not manage Bridge lifecycle.

## Prerequisites

- Python available on `PATH`.
- Editable project dependencies installed with `python -m pip install -e .`.
- PyInstaller available only when attempting an actual build.
- PySide6 and pyqtgraph importable in the build environment.

## User Data Separation Goal

Phase 18 should keep installed binaries separate from user data.

Planned binary install location:

- `%LocalAppData%\Programs\HelmForge` for per-user install, or `%ProgramFiles%\HelmForge` for an elevated machine-wide install.

Planned user data root:

- `%LocalAppData%\HelmForge`

Planned user data folders:

- `%LocalAppData%\HelmForge\config`
- `%LocalAppData%\HelmForge\profiles`
- `%LocalAppData%\HelmForge\logs`
- `%LocalAppData%\HelmForge\recordings`
- `%LocalAppData%\HelmForge\artifacts`

Phase 18C does not migrate current source-mode config or recording paths. User data is preserved by default on uninstall; in installer terms, user data is preserved under `%LocalAppData%\HelmForge`.

## Icon Goal

Phase 18 should embed a real `.ico` in the executable, installer, and shortcuts. Current detailed PNG candidates live in the preserved recovery evidence. `assets/app_icon.ico` is missing; plain status: assets/app_icon.ico is missing, so icon conversion remains deferred to later acceptance/release work.

Forensic documents are not bundled by the PyInstaller command.

## Smoke-test Goal

A packaged app must launch without HOTAS and without vJoy. It must preserve simulation mode, missing-device guidance, telemetry truth, and the Phase 16 Full Live Runtime Ready gate.

Suggested source-mode smoke before packaging:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
python -m bridge_app.main --status
```

## Known Remaining Packaging Issues

- A checked-in PyInstaller spec, if command-line invocation becomes too limited.
- Icon conversion and embedding when `assets/app_icon.ico` is available.
- AppData/LocalAppData migration or first-run directory creation.
- Installer compile verification on machines where Inno Setup is not installed.

## Phase 19 Handoff

Phase 19 should validate the whole product against the prompt book, including app shell, all pages, runtime truth, Full Live Runtime Ready gate behavior, one-folder packaging, and the installer script if Inno Setup is available.

Phase 19D should make the final acceptance / release-candidate freeze decision. Current recommendation is RC Ready With Known Non-Blocking Gaps if missing icon embedding, skipped Inno compile, installer execution, and live hardware proof are outside the RC criteria.
