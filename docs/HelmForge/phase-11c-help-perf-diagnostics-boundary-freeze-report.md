# Phase 11C - Help / Docs + Perf / Diagnostics Polish and Boundary Freeze

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Phase 11 polish, terminology consistency, cross-links, and boundary freeze only

## Summary

Phase 11 is now complete.

Phase 11C finalizes the Phase 11 Help / Docs and Perf / Diagnostics surfaces together. It tightens cross-links, standardizes runtime terminology, updates stale Phase 11B report wording, and adds final boundary tests before Phase 12.

Phase 11C does not add runtime authority.

## Phase 11A Summary

Phase 11A implemented the Help / Docs foundation:

- local deterministic search;
- category/topic browsing;
- scrollable guide pane;
- Runtime Setup / vJoy Setup article;
- Helm article;
- Runtime Indicators article;
- Tuning Glossary article;
- local article model in `v3_app/services/help_docs.py`;
- integrated page in `v3_app/pages/help_docs_page.py`.

## Phase 11B Summary

Phase 11B implemented the Perf / Diagnostics page:

- runtime truth diagnostics;
- Bridge telemetry status and telemetry age;
- process hint display;
- HOTAS discovery and output/vJoy truth;
- lightweight timing and hidden-page skip counters;
- Copy Diagnostics text builder;
- safe Run Runtime Preflight control.

Diagnostics are observational. Timing metrics are app/UI diagnostics, not live hardware proof.

## Phase 11C Polish / Freeze Summary

Phase 11C adds:

- Help / Docs related-topic cross-links between Runtime Setup / vJoy Setup, Runtime Indicators, Performance / Diagnostics, Helm, Saving and Importing, Effective Response Stack, Graphs and Previews, and Conditional Rules;
- Performance / Diagnostics article wording that matches the implemented Phase 11B page;
- Perf / Diagnostics page copy that states telemetry remains the truth surface, process presence is a hint only, HOTAS discovery is discovery-only, vJoy detected does not mean output verified, Output verified is false, and Full Live Runtime Ready is false;
- final Phase 11 boundary tests in `tests/test_phase11c_help_perf_boundary_freeze.py`;
- Phase 11 documentation consistency updates.

## Current Runtime Truth

Current conservative runtime truth remains:

- Bridge lifecycle: `Simulated`
- Runtime truth: `blocked_missing_device`
- HOTAS discovery: `no_supported_device` unless read-only discovery sees a supported device
- vJoy/output state: vJoy may be detected, but output writes are not verified
- `output_verified`: `false`
- Full Live Runtime Ready: `false`
- Telemetry remains the truth surface
- Process presence is a hint only

## Final Phase 11 Boundary

Help / Docs and Perf / Diagnostics are observational UI/product surfaces.

They do not:

- implement Live Overlay;
- implement Flight Recorder;
- poll real HOTAS hardware;
- stream live physical input;
- write vJoy;
- verify output;
- automatically launch the Bridge;
- spawn the Bridge from the UI;
- install a service;
- enable login auto-start;
- implement a tray manager;
- launch installers;
- add StartBridge/StopBridge/RestartBridge behavior;
- add a real process scanner;
- use cloud AI or LLM behavior;
- auto-save workspace changes;
- activate real runtime behavior.

## Verification

Final verification results:

- `python -m pytest` - passed, 248 tests.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - passed, 7 tests.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11a_help_docs_foundation.py` - passed, 8 tests.
- `python -m pytest tests\test_phase11b_perf_diagnostics_page.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - passed, 6 tests.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed with `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed. Thrustmaster software detected, vJoy detected, HOTAS Not Connected, Simulation Mode Active unless physical input and output writes are both verified, Full Live Runtime Ready false, no installers launched.
- `git diff --check` - passed.

## Recommendation For Phase 12

The next prompt-book phase is Phase 12 Live Overlay Foundation.

Phase 12 must preserve the Phase 9K runtime boundary and Phase 10E Helm boundary. It should begin as an overlay foundation and display surface only unless a later reviewed phase explicitly authorizes live hardware/runtime work.
