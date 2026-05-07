# HelmForge

**HOTAS Control Panel V3**

HelmForge is a safe rebuild of the lost HOTAS Control Panel project. The recovered HOTAS Control Panel V2 forensic notes, raw recovery chats, and PNG screenshot evidence are the governing reconstruction references for this repository.

The current rebuild state includes the Phase 10B Helm intelligence expansion, Phase 10A Helm Assistant Overlay foundation, Phase 9K final stabilization and boundary freeze, Phase 9J Live Monitor diagnostic UX polish, Phase 9I Bridge process presence diagnostics, Phase 9H Bridge-owned real device discovery dry-run, Phase 9G Bridge lifecycle ownership design record, Phase 9F Bridge lifecycle presence and health refinement, Phase 9E Bridge command acknowledgement/status refinement, Phase 9D safe UI-to-Bridge command seam, Phase 9C UI Bridge telemetry connection, Phase 9B Bridge background process skeleton, Phase 9 Live Monitor page, Phase 8 Effective Response Stack page, Phase 7 Conditional Rules page/evaluator, Phase 6B Mapping editor polish, Phase 6 core tuning pages, Phase 5 Mapping page, Phase 4 PySide6 visual shell, Phase 2B Bridge/UI architecture boundary contracts, Phase 2A local runtime setup tooling, and the Phase 3 tuning math and signal pipeline. Phase 9C lets the UI read Bridge telemetry JSON when fresh and fall back to simulation when telemetry is missing, stale, or invalid. Phase 9D lets the UI request safe Bridge status/config/preflight commands through a JSON command file without claiming command completion. Phase 9E echoes consumed Bridge commands through telemetry so the UI can distinguish requested, awaiting telemetry, completed, failed, and ignored-stale states by request ID. Phase 9F exposes compact Bridge health details such as connected/missing/stale/invalid/error, telemetry age, stale threshold, runtime truth, and output verification truth. Phase 9G is design-only and records lifecycle ownership options, wording rules, and safety gates before any launch/service/tray/autostart behavior. Phase 9H publishes read-only HOTAS discovery truth through Bridge telemetry. Phase 9I adds process-presence hints and conservative Live Monitor diagnosis text while keeping telemetry as the truth surface. Phase 9J tightens Live Monitor diagnostic labels, severity categories, manual-launch guidance, command matching display, and discovery-only wording. Phase 9K freezes the Phase 9 boundary with regression tests and documentation consistency checks. Phase 10 is Helm Assistant Overlay according to the prompt book; Phase 10A wires Helm from the top-right ASSISTANT cluster as an overlay/modal assistant, not a sidebar page. Phase 10B expands Helm into a deterministic, local diagnostic assistant with grouped recommendations, confidence scoring, follow-up questions, findings, risks, and richer before/after diffs. The current app still does not implement continuous real HOTAS input polling, live physical input streaming, vJoy output writes, flight recorder, live overlay, Help / Docs internals, cloud AI, LLM tuning, or installer packaging.

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

Phase 9H can run a read-only Bridge-owned discovery dry-run for that hardware. Phases 9I and 9J can show process presence hints and polished diagnostic wording. They do not implement continuous real HOTAS polling, live axis/button streaming, real vJoy output writes, output verification, automatic Bridge launch, process spawning from the UI, Windows Service installation, login auto-start, installer launch, tray manager work, Start/Stop/Restart behavior, or real runtime activation. No live runtime support should be claimed until a later phase implements and verifies it.

The V3 workspace/config filename is `hotas_bridge_config_v3.json`. The recovered V2 notes referenced `hotas_bridge_config_v2.json`; that legacy name is preserved in schema documentation for provenance.

Official Thrustmaster setup guidance is documented in `docs/HelmForge/help/runtime-setup-hotas-driver.md`. Phase 2A local setup guidance is documented in `docs/HelmForge/phase-2a-local-driver-installation-and-runtime-verification.md`. The app links to the official Thrustmaster support page and a verified vJoy setup source; it does not silently download or run driver installers.

## Bridge/UI Split

HelmForge has two main parts:

- Bridge: owns real-time HOTAS input, workspace processing, virtual output, and telemetry.
- UI App: owns configuration, visualization, diagnostics, help/docs, recorder/overlay surfaces, and user interaction.

The Phase 9B Bridge process runs separately from the PySide6 UI and writes simulation-backed telemetry snapshots. Phase 9C adds a UI Bridge telemetry client and wires Live Monitor to use fresh Bridge telemetry, with simulation fallback for missing, stale, or invalid telemetry. Phase 9D adds safe command-file requests for `Status`, `RunPreflight`, `ReloadConfig`, `SwitchToSimulation`, and `ClearError`; unsafe commands such as `VerifyOutput`, `StartBridge`, and `StopBridge` are rejected by the UI. Phase 9E adds Bridge `last_command` telemetry, stale-command protection, and duplicate request protection so command status remains truthful. Phase 9F adds UI-visible Bridge health timing details and explanations without treating stale telemetry as live truth. Phase 9G keeps manual Bridge launch for now and documents a conservative path toward read-only presence hints, later tray/background management, and deferred Windows Service/login auto-start. Phase 9H adds Bridge-owned read-only device discovery telemetry and compact Live Monitor discovery wording. Phase 9I adds process-presence hints as diagnostics only; fresh telemetry remains stronger than any process hint, and the UI still does not own the Bridge lifecycle. Phase 9J polishes the Live State diagnostic hierarchy while preserving telemetry authority and request-id command matching. Phase 9K freezes the Phase 9 safety boundary and adds guard tests for command scope, diagnostic truth, docs consistency, and forbidden runtime authority. Phase 10A adds the Helm overlay foundation: Helm launches from the top-right ASSISTANT cluster, opens as a large overlay/modal, applies selected tuning changes only to the in-memory workspace draft, never auto-saves, and does not auto-edit conditional rules in Helm v1. Phase 10B expands Helm's deterministic engine with symptom definitions, follow-up questions, workspace findings, confidence bands, recommendation groups, expected outcomes, risks, and conflict warnings while preserving in-memory-only apply/revert behavior. Early phases may still use in-process simulation adapters for development views, but the final architecture should allow the Bridge to run without the PySide6 UI open. The Bridge/UI boundary is documented in `docs/HelmForge/bridge-ui-architecture.md`, the process skeleton is documented in `docs/HelmForge/bridge-service-design.md`, the Phase 9G decision record is documented in `docs/HelmForge/phase-9g-bridge-lifecycle-ownership-design.md`, the Phase 9H report is documented in `docs/HelmForge/phase-9h-real-device-discovery-dry-run-report.md`, the Phase 9I report is documented in `docs/HelmForge/phase-9i-bridge-process-presence-diagnostics-report.md`, the Phase 9J report is documented in `docs/HelmForge/phase-9j-live-monitor-diagnostic-ux-polish-report.md`, the Phase 9K report is documented in `docs/HelmForge/phase-9k-phase-9-stabilization-boundary-freeze-report.md`, the Phase 10A report is documented in `docs/HelmForge/phase-10a-helm-assistant-overlay-foundation-report.md`, and the Phase 10B report is documented in `docs/HelmForge/phase-10b-helm-intelligence-expansion-report.md`.

## Phase 10A Helm Assistant Overlay

Phase 10 is Helm Assistant Overlay according to the prompt book. Phase 10A implements the overlay foundation:

- Helm is launched from the top-right `ASSISTANT` cluster.
- Helm behaves as an overlay/modal assistant, not a sidebar page.
- Helm analyzes the current in-memory workspace draft and presents exact before/after diffs.
- The first working symptom path is `Combat mode feels sluggish`.
- Apply Selected Changes updates only the in-memory workspace/draft.
- Revert Last Helm Changes restores the previous in-memory values from the last Helm apply.
- Helm never auto-saves to `hotas_bridge_config_v3.json`.
- Helm v1 does not create, edit, enable, disable, or delete conditional rules.
- Phase 10A does not add real HOTAS polling, vJoy writes, output verification, Bridge lifecycle control, or real runtime activation.

## Phase 10B Helm Intelligence Expansion

Phase 10B keeps Helm deterministic and local while making it behave more like a diagnosis-first tuning engineer:

- Helm now has a structured symptom library for aim/combat, flight, ground/racing, and general control feel issues.
- Supported symptom paths generate exact before/after diffs with reason, expected outcome, risk level, confidence score, reversibility, selected state, and applied state.
- Recommendations are grouped, for example `Fine Aim Control`, `Combat Responsiveness`, `Stability`, `Center Precision`, `High-Speed Tracking`, `Drift Reduction`, and `Overshoot Mitigation`.
- Ambiguous symptoms produce deterministic follow-up questions before Helm stages changes.
- Workspace analysis reports findings such as high deadzone, cross-axis curve mismatch, low combat yaw authority, or restrictive combat slew values.
- Apply Selected Changes still updates only the in-memory workspace draft and marks it unsaved.
- Revert Last Helm Changes still restores the last Helm-applied in-memory batch.
- Helm still never auto-saves, never mutates conditional rules, never calls cloud AI or an LLM, and never claims runtime evidence that telemetry does not prove.
- Phase 10B does not add real HOTAS polling, live physical input streaming, vJoy writes, output verification, automatic Bridge launch, process management, service install, login auto-start, tray manager work, installer launch, or real runtime activation.

## Phase 9 Status Snapshot

Phase 9C through Phase 9K establish the Bridge/UI truth seam without adding live runtime authority:

- telemetry remains the truth surface.
- command files are requests, not success proof.
- Bridge command acknowledgement must use matching request_id.
- process presence is a hint only.
- HOTAS discovery is discovery-only.
- supported_device_detected does not mean polling/live runtime/output verified.
- manual Bridge launch remains the current lifecycle model.
- UI does not start, stop, restart, spawn, install, or manage the Bridge.
- output_verified remains false until a future output verification phase.
- Full Live Runtime Ready remains false until future phases prove input and output.
- live device/runtime work remains deferred.

Current conservative truth:

- Runtime truth: `blocked_missing_device` unless fresh telemetry truth says otherwise.
- Bridge lifecycle: `Simulated`.
- Device discovery: `no_supported_device` unless read-only discovery sees a supported device.
- Process presence: diagnostic hint only.
- `output_verified`: `false`.
- Full Live Runtime Ready: `false`.

Current paths:

- Telemetry: `%TEMP%\helmforge_bridge_telemetry.json`
- Commands: `%TEMP%\helmforge_bridge_command.json`
- Manual Bridge launch: `python -m bridge_app.main --run-for-ms 250`

Safe UI command requests:

- `Status`
- `RunPreflight`
- `ReloadConfig`
- `SwitchToSimulation`
- `ClearError`

Rejected/out-of-scope commands:

- `StartBridge`
- `StopBridge`
- `RestartBridge`
- `SuspendBridge`
- `VerifyOutput`

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
