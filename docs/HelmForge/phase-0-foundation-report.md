# Phase 0 Foundation Report

Status: Phase 0 foundation implemented and verified.

Scope:

- Create HelmForge project foundation.
- Preserve and reference recovered forensic specs and PNG evidence.
- Add minimal PySide6 entry point with Phase 0 wording.
- Add smoke tests.

Out of scope:

- Real HOTAS hardware support.
- vJoy runtime support.
- Driver installation.
- Tuning, profiles, mapping, overlays, Helm assistant logic, or packaging.

## Files Created

- `.gitignore`
- `README.md`
- `pyproject.toml`
- `shared_core/__init__.py`
- `v3_app/__init__.py`
- `v3_app/main.py`
- `docs/HelmForge/README.md`
- `docs/HelmForge/decisions.md`
- `docs/HelmForge/phase-0-foundation-report.md`
- `docs/recovery/README.md`
- `docs/recovery/forensic-inventory.md`
- `tests/test_phase0_foundation.py`

## Folder Structure Created

- `shared_core/`
- `v3_app/`
- `docs/HelmForge/`
- `docs/recovery/`
- `tests/`

## Commands Run

- `git status --short`
  - Result: this folder is not currently a git repository.
- `Get-ChildItem -Force`
  - Result: confirmed the forensic spec set folder was present before foundation files were added.
- `rg --files`
  - Result: blocked by Windows with `Access is denied`; PowerShell enumeration was used instead.
- `Get-ChildItem -Path "HOTAS Control Panel Forensic Spec Set" -Recurse -File`
  - Result: inventoried recovered documents, raw chats, and PNG evidence.
- `python -m pytest tests/test_phase0_foundation.py`
  - Result before implementation: expected red failure because `v3_app` and `docs/recovery/README.md` did not exist.
- `python -m pytest`
  - Result after implementation: `2 passed`.
- PySide6 import check
  - Result: PySide6 is available.
- Dependency import check for PySide6, pyqtgraph, and pytest
  - Result: PySide6 and pytest are available in the active Python; pyqtgraph is documented in `pyproject.toml` but is not installed in the active Python.
- `python -m v3_app.main --smoke-exit-ms 250` with `QT_QPA_PLATFORM=offscreen`
  - Result: app launch smoke exited with code 0.
- Qt window-title assertion with `QT_QPA_PLATFORM=offscreen`
  - Result: actual window title was `HelmForge — HOTAS Control Panel V3`.

## Recovery Preservation

The recovered forensic documents and screenshots were not renamed or moved. Phase 0 preserves them in place and records explicit references under `docs/recovery/`.

- Governing spec root: `HOTAS Control Panel Forensic Spec Set/`
- Raw recovered chats: `HOTAS Control Panel Forensic Spec Set/raw-recovered-v2-chats/`
- Screenshot evidence root: `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/`
- Recovered PNG count observed in Phase 0: 34.

## Next Recommended Phase

Phase 1 should remain simulation-first and define the shared core data contracts before hardware work: app state model, profile/config schema draft, axis/button/hat DTOs, and a simulated runtime adapter. Real HOTAS polling, vJoy output, and driver installation should stay out of scope until those contracts are reviewed.
