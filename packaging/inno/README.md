# Inno Setup Notes

Phase 18C adds `packaging/inno/helmforge.iss`, an Inno Setup script for the Phase 18B PyInstaller one-folder output. Phase 18D verifies this script as final packaging QA metadata for Phase 19 acceptance readiness.

Installer behavior:

- Installs app files to `%LocalAppData%\Programs\HelmForge` for a per-user install.
- Creates a Start Menu shortcut.
- Offers an optional Desktop shortcut.
- Offers optional launch after install.
- Adds standard uninstall metadata.
- Preserves user data under `%LocalAppData%\HelmForge` by default; user data is preserved when the app binaries are uninstalled.
- Preserves simulation mode first launch when HOTAS/vJoy is missing.

The installer does not install drivers, does not install vJoy, does not install services, does not configure login auto-start, does not add a tray manager, and does not manage Bridge lifecycle.

Build command when Inno Setup 6 is available:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -BuildInstaller
```

If `ISCC.exe` is not on `PATH`, pass the compiler path with `-InnoPath`.

Icon behavior:

- If `assets/app_icon.ico` exists, the script uses it for `SetupIconFile` and shortcuts.
- If `assets/app_icon.ico` is missing, the script still describes the installer metadata; icon conversion remains deferred.

This installer is unsigned and not final release-channel output. Signing and final release-channel metadata remain later packaging work.

Phase 18 is now complete. Phase 19: Final Integration Kraken / Full Acceptance Sweep should compile and inspect the installer when `ISCC.exe` is available.
