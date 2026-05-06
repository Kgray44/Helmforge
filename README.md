# HelmForge

**HOTAS Control Panel V3**

HelmForge is a safe rebuild of the lost HOTAS Control Panel project. The recovered HOTAS Control Panel V2 forensic notes, raw recovery chats, and PNG screenshot evidence are the governing reconstruction references for this repository.

The current rebuild state is Phase 1 runtime preflight foundation. Phase 0 created the package structure, dependency metadata, documentation anchors, and a minimal PySide6 window titled `HelmForge — HOTAS Control Panel V3`. Phase 1 adds typed runtime status, safe missing-device detection, simulation snapshots, and a runtime bridge contract. It does not implement real HOTAS input polling, vJoy output writes, profiles, tuning math, overlays, or installer packaging.

## Recovery Sources

The original app was lost. Reconstruction must be evidence-led:

- `HOTAS Control Panel Forensic Spec Set/` contains the normalized forensic documents, PDFs, raw recovered chats, and prompt book.
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/` contains screenshot evidence organized by feature area.
- `docs/recovery/` records how those sources are preserved and referenced for implementation.
- `docs/HelmForge/` is reserved for implementation notes, decisions, and phase reports.

The forensic documents and screenshots must not be destructively renamed or overwritten. If future phases need derived assets, create copies under an explicit generated or asset folder while keeping the recovered originals intact.

## Runtime Strategy

HelmForge will be developed simulation-first so the UI, shared core, and tests can progress before hardware drivers are installed. Real hardware and vJoy runtime support will be implemented in later phases after the data contracts and safety boundaries are reviewed.

Known physical HOTAS target: **Thrustmaster T-Flight HOTAS One**.

Phase 1 does **not** provide real support for that hardware. It does **not** install or use Thrustmaster drivers, vJoy, or any hardware driver. No live runtime support should be claimed until a later phase implements and verifies it.

## Project Layout

```text
shared_core/          Shared models and non-UI core code for future phases.
v3_app/               PySide6 application package and Phase 0 entry point.
docs/HelmForge/       Implementation notes, decisions, and phase reports.
docs/recovery/        Recovery-source preservation notes and evidence inventory.
tests/                Phase smoke tests.
```

## Development

Initial dependencies are declared in `pyproject.toml`:

- PySide6
- pyqtgraph
- pytest

Run tests:

```powershell
python -m pytest
```

Launch the Phase 0 window:

```powershell
python -m v3_app.main
```

Automated smoke launch:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m v3_app.main --smoke-exit-ms 250
Remove-Item Env:\QT_QPA_PLATFORM
```
