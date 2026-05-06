# HelmForge

**HOTAS Control Panel V3**

HelmForge is a safe rebuild of the lost HOTAS Control Panel project. The recovered HOTAS Control Panel V2 forensic notes, raw recovery chats, and PNG screenshot evidence are the governing reconstruction references for this repository.

The current rebuild state includes the Phase 9F Bridge lifecycle presence and health refinement, Phase 9E Bridge command acknowledgement/status refinement, Phase 9D safe UI-to-Bridge command seam, Phase 9C UI Bridge telemetry connection, Phase 9B Bridge background process skeleton, Phase 9 Live Monitor page, Phase 8 Effective Response Stack page, Phase 7 Conditional Rules page/evaluator, Phase 6B Mapping editor polish, Phase 6 core tuning pages, Phase 5 Mapping page, Phase 4 PySide6 visual shell, Phase 2B Bridge/UI architecture boundary contracts, Phase 2A local runtime setup tooling, and the Phase 3 tuning math and signal pipeline. Phase 9C lets the UI read Bridge telemetry JSON when fresh and fall back to simulation when telemetry is missing, stale, or invalid. Phase 9D lets the UI request safe Bridge status/config/preflight commands through a JSON command file without claiming command completion. Phase 9E echoes consumed Bridge commands through telemetry so the UI can distinguish requested, awaiting telemetry, completed, failed, and ignored-stale states by request ID. Phase 9F exposes compact Bridge health details such as connected/missing/stale/invalid/error, telemetry age, stale threshold, runtime truth, and output verification truth. The current app still does not implement real HOTAS input polling, vJoy output writes, flight recorder, live overlay, or installer packaging.

## Recovery Sources

The original app was lost. Reconstruction must be evidence-led:

- `HOTAS Control Panel Forensic Spec Set/` contains the normalized forensic documents, PDFs, raw recovered chats, and prompt book.
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/` contains screenshot evidence organized by feature area.
- `docs/recovery/` records how those sources are preserved and referenced for implementation.
- `docs/HelmForge/` is reserved for implementation notes, decisions, and phase reports.

The forensic documents and screenshots must not be destructively renamed or overwritten. If future phases need derived assets, create copies under an explicit generated or asset folder while keeping the recovered originals intact.

## Runtime Strategy

HelmForge is developed simulation-first so the UI, shared core, and tests can progress before hardware drivers are installed. Real hardware and vJoy runtime support will be implemented in later phases after the data contracts and safety boundaries are reviewed.

Known physical HOTAS target: **Thrustmaster T-Flight HOTAS One**.

Phase 9F does **not** provide real support for that hardware. It does **not** implement real HOTAS polling or real vJoy output writes. No live runtime support should be claimed until a later phase implements and verifies it.

The V3 workspace/config filename is `hotas_bridge_config_v3.json`. The recovered V2 notes referenced `hotas_bridge_config_v2.json`; that legacy name is preserved in schema documentation for provenance.

Official Thrustmaster setup guidance is documented in `docs/HelmForge/help/runtime-setup-hotas-driver.md`. Phase 2A local setup guidance is documented in `docs/HelmForge/phase-2a-local-driver-installation-and-runtime-verification.md`. The app links to the official Thrustmaster support page and a verified vJoy setup source; it does not silently download or run driver installers.

## Bridge/UI Split

HelmForge has two main parts:

- Bridge: owns real-time HOTAS input, workspace processing, virtual output, and telemetry.
- UI App: owns configuration, visualization, diagnostics, help/docs, recorder/overlay surfaces, and user interaction.

The Phase 9B Bridge process runs separately from the PySide6 UI and writes simulation-backed telemetry snapshots. Phase 9C adds a UI Bridge telemetry client and wires Live Monitor to use fresh Bridge telemetry, with simulation fallback for missing, stale, or invalid telemetry. Phase 9D adds safe command-file requests for `Status`, `RunPreflight`, `ReloadConfig`, `SwitchToSimulation`, and `ClearError`; unsafe commands such as `VerifyOutput`, `StartBridge`, and `StopBridge` are rejected by the UI. Phase 9E adds Bridge `last_command` telemetry, stale-command protection, and duplicate request protection so command status remains truthful. Phase 9F adds UI-visible Bridge health timing details and explanations without treating stale telemetry as live truth. Early phases may still use in-process simulation adapters for development views, but the final architecture should allow the Bridge to run without the PySide6 UI open. The Bridge/UI boundary is documented in `docs/HelmForge/bridge-ui-architecture.md`, and the process skeleton is documented in `docs/HelmForge/bridge-service-design.md`.

## Project Layout

```text
shared_core/          Shared models, runtime contracts, math pipeline, rules evaluator, and non-UI core code.
bridge_app/           Simulation-only Bridge background process skeleton and file IPC entry point.
v3_app/               PySide6 application package, app shell, theme, Mapping editor, tuning/rules/stack/live-monitor pages, and remaining placeholder pages.
docs/HelmForge/       Implementation notes, decisions, and phase reports.
docs/recovery/        Recovery-source preservation notes and evidence inventory.
tests/                Phase smoke and contract tests.
```

## Development

Initial dependencies are declared in `pyproject.toml`:

- PySide6
- pyqtgraph
- pytest

Install the declared project dependencies in editable mode:

```powershell
python -m pip install -e .
```

Run tests:

```powershell
python -m pytest
```

Launch the app shell:

```powershell
python -m v3_app.main
```

Run one simulation-only Bridge tick:

```powershell
python -m bridge_app.main --once
```

Run a bounded Bridge loop:

```powershell
python -m bridge_app.main --run-for-ms 250
```

Automated smoke launch:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m v3_app.main --smoke-exit-ms 250
Remove-Item Env:\QT_QPA_PLATFORM
```

Run the Phase 2A runtime setup dry-run checklist:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/runtime_setup_check.ps1 -DryRun
```
