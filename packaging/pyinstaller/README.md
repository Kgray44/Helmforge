# PyInstaller Notes

Phase 18A selected PyInstaller as the first packaging path because a one-folder build is inspectable before an installer is introduced. Phase 18B turns that into the first real one-folder build command and packaged smoke path. Phase 18C keeps the one-folder path intact and adds icon-aware metadata for installer work. Phase 18D freezes this one-folder path for Phase 19 acceptance readiness.

Current entry point:

- `v3_app/main.py`
- Console script equivalent: `helmforge = "v3_app.main:main"`

Bridge entry point for future packaging decisions:

- `bridge_app.main`
- Console script equivalent: `helmforge-bridge = "bridge_app.main:main"`

Current command-line build behavior:

- Output folder: `packaging/dist/HelmForge/`
- Packaged executable: `packaging/dist/HelmForge/HelmForge.exe`
- Packaged smoke command: `packaging/dist/HelmForge/HelmForge.exe --smoke-exit-ms 250`
- The build script uses `--onedir`, not one-file.
- The build script excludes pytest/tests, pyqtgraph examples, PySide6 QtTest, and does not add recovery/forensic document data.

Current considerations:

- PySide6 must be importable in the build environment.
- pyqtgraph must be importable in the build environment.
- The first build should be one-folder, not one-file, so Qt plugin and resource behavior can be inspected.
- `assets/app_icon.ico` does not exist yet, so icon embedding is deferred. When that file exists, `packaging/build_release.ps1` passes `--icon` to PyInstaller.
- User data migration is deferred; source-mode paths remain unchanged in Phase 18A.
- Packaged smoke must preserve simulation mode and the Phase 16 Full Live Runtime Ready gate when HOTAS/vJoy is missing.

Run the dry-run script from the repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -DryRun
```

Do not claim packaged build success until the non-dry-run PyInstaller command completes and the generated app is smoke-tested without HOTAS/vJoy. Phase 18B does not create an installer; Phase 18C keeps installer compilation separate from the one-folder build and does not add Bridge lifecycle management.

Forensic documents are not bundled by the current command. Installer compilation is handled by `packaging/inno/helmforge.iss` only when Inno Setup is installed and `packaging/build_release.ps1 -BuildInstaller` succeeds.

Phase 18 is now complete. Phase 19: Final Integration Kraken / Full Acceptance Sweep should verify this packaged smoke path together with the rest of the product.
