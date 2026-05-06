# Phase 4 UI Shell and Screenshot Fidelity Report

Status: Phase 4 implemented and verified.

## Scope

Phase 4 builds the HelmForge - HOTAS Control Panel V3 PySide6 application shell:

- left sidebar;
- grouped navigation;
- top header;
- STATUS cluster;
- ASSISTANT / Helm cluster;
- central stacked, scroll-safe workspace;
- footer/status/action bar;
- placeholder pages for recovered major pages;
- reusable theme/QSS tokens;
- runtime truth surfaces.

This phase does not implement detailed page internals, real HOTAS polling, real vJoy writes, output verification, installer launch, recorder capture, overlay rendering, or Helm assistant behavior.

## Screenshots and Folders Inspected

Primary folder:

- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence`

Key screenshots inspected:

- `01 Mapping/v2-mapping_final-top-overview-live-route-summary-axis-routing.png`
- `03 Base Tuning/v2-base-tuning_final-linear-and-adjusted-curves-full-window.png`
- `09 Live Monitor/v2-live-monitor_final-axis-levels-hotas-buttons-output-buttons.png`
- `10 Flight Recorder/v2-flight-recorder_buffering-save-last-clip-settings-axis-overlay.png`
- `13 Help Docs/v2-help-docs_final-topic-tree-conditional-rules-guide.png`

Supporting docs inspected:

- `02-product-vision-and-visual-design-system.md`
- `01-hotas-control-panel-master-recovery-index.md`
- recovered screenshot descriptions in the raw recovered chats and prompt book search results

## Screenshot Basis

The Phase 4 shell uses the later, more polished V2 shell direction:

- The Flight Recorder screenshot guided the grouped sidebar: SETUP, TUNING, ANALYSIS, SUPPORT.
- Mapping/Base/Help screenshots guided the full shell frame: left sidebar, top header, top-right STATUS cluster, ASSISTANT cluster, scrollable workspace, and bottom footer/action bar.
- Base Tuning and Live Monitor guided card radius, dark slate-blue surfaces, cyan borders, pale body text, and compact status/button treatment.
- Help / Docs guided the idea of a central page workspace with clean cards and strong breathing room.

## Matched Visual Elements

Matched as closely as practical in Phase 4:

- dark premium control-console style;
- deep navy app background;
- dark slate-blue panels/cards;
- subtle blue/cyan borders;
- cyan/blue active sidebar highlight;
- grouped sidebar sections;
- active page selection state;
- bottom runtime card in sidebar;
- header title/subtitle hierarchy;
- STATUS cluster with quiet chips;
- ASSISTANT cluster with clickable Helm button;
- central scroll-safe stacked workspace;
- footer with left status message, center context, and right actions;
- action buttons visually distinct from status chips;
- rounded card/button/panel structure via Qt/QSS;
- product-grade placeholder copy without claiming page functionality.

## Intentional V3 Deviations

Intentional changes from recovered V2 evidence:

- Product name is `HelmForge`, not `HOTAS V2`.
- Technical subtitle is `HOTAS Control Panel V3`.
- Source config is `hotas_bridge_config_v3.json`, not the recovered V2 config filename.
- Runtime truth reflects the current machine state instead of screenshot `Idle` or `Live`.
- The shell shows `HOTAS Not Connected` / `Blocked Missing Device` when the HOTAS is unplugged.
- Full Live Runtime Ready is never shown because output writes are not verified.

These deviations are intentional and permanent for the V3 rebuild.

## Temporary Deviations

Temporary Phase 4 placeholders:

- Detailed Mapping, Modes, Base Tuning, Filtering, Combat Profile, Profiles, Conditional Rules, Effective Response Stack, Live Monitor, Flight Recorder, Help / Docs, and Perf / Diagnostics internals are not built yet.
- Graphs, tables, axis controls, recorder controls, Help topic trees, and diagnostics content are represented by placeholder cards only.
- Page transition animation is not implemented yet.
- The Helm button is present but does not open the assistant overlay yet.
- Runtime setup buttons are available in Help / Docs, but the app does not launch installers.

These are temporary and should be addressed in later reviewed phases.

## Current Runtime Truth

Phase 4 precheck and final verification recorded:

- Thrustmaster driver/software detected: yes, `T.Flight Hotas drivers`
- vJoy detected: yes, `C:\Program Files\vJoy\x64\vJoyInterface.dll`
- HOTAS device detected: no, because the controller is disconnected
- Runtime mode: `simulated`
- Runtime truth: `blocked_missing_device`
- Output writes verified: `false`
- Full Live Runtime Ready: false

The UI reads and displays runtime truth but does not own real-time processing.

## Bridge/UI Boundary

The Phase 4 shell imports runtime status from `shared_core`, but no real-time processing was moved into PySide6 UI code. The future Bridge remains responsible for input/output, the shared-core signal pipeline, output writes, and telemetry publication.

## Commands Run

Prechecks:

- `git status --short`
- `git remote -v`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- runtime truth probe via Python

Screenshot/design inspection:

- recovered PNG inventory under `Recovered PNG Evidence`
- direct inspection of final V2 Mapping, Base Tuning, Live Monitor, Flight Recorder, and Help / Docs screenshots
- design-system and recovery-index document reads

TDD and implementation:

- `python -m pytest .\tests\test_phase4_app_shell.py .\tests\test_phase0_foundation.py`
- `python -m pytest .\tests\test_phase4_app_shell.py .\tests\test_phase0_foundation.py .\tests\test_phase1a_thrustmaster_setup.py .\tests\test_phase2a_driver_setup.py`
- offscreen screenshot layout sanity render to `%TEMP%\helmforge_phase4_shell.png`
- `python -m pytest`
- `python -m v3_app.main --smoke-exit-ms 250`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`

## Verification Results

Focused shell tests:

- `python -m pytest .\tests\test_phase4_app_shell.py .\tests\test_phase0_foundation.py`
- Result: `8 passed`

Compatibility shell/setup slice:

- `python -m pytest .\tests\test_phase4_app_shell.py .\tests\test_phase0_foundation.py .\tests\test_phase1a_thrustmaster_setup.py .\tests\test_phase2a_driver_setup.py`
- Result: `23 passed`

Full suite:

- `python -m pytest`
- Result: `63 passed`

Minimal app smoke:

- `python -m v3_app.main --smoke-exit-ms 250`
- Result: exit code `0`

Runtime setup dry-run:

- Thrustmaster driver/software detected.
- vJoy detected.
- HOTAS not connected.
- No installers launched.
- Full Live Runtime Ready remains false.

Final runtime truth probe:

- Driver detected: true, `T.Flight Hotas drivers`
- Mode: `simulated`
- Truth: `blocked_missing_device`
- Input: `missing`
- Output: `vjoy_detected`
- Output backend: `C:\Program Files\vJoy\x64\vJoyInterface.dll`
- Output writes verified: `false`
- Labels: `Thrustmaster Driver Detected | HOTAS Not Connected | vJoy Detected | Simulation Mode Active`

Visual note:

- A local offscreen screenshot was generated at `%TEMP%\helmforge_phase4_shell.png` for layout sanity. The offscreen Qt backend rendered text glyphs as boxes on this machine, so final fidelity assessment is based on direct recovered screenshot inspection plus widget/layout tests rather than that offscreen render as visual proof.
