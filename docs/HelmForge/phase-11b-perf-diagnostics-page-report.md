# Phase 11B - Perf / Diagnostics Page and Timing Visibility

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Perf / Diagnostics page only

## Summary

Phase 11B implements Perf / Diagnostics page only. The page is an observational product diagnostics surface for runtime truth, Bridge telemetry state, UI/workspace state, timing summaries, hidden-page skip visibility, safe preflight refresh, and local diagnostic copy text.

Diagnostics are observational and do not add runtime authority.
In product wording, diagnostics are observational and do not add runtime authority.

## Implemented Page

The Perf / Diagnostics page includes these sections:

- Runtime Truth
- Bridge / Telemetry
- Workspace / UI State
- Performance Timings
- Hidden Page Skips
- Commands / Preflight
- Diagnostic Actions

The page displays stable rows for active page, runtime mode/truth, Bridge lifecycle, telemetry status and age, process hint, HOTAS discovery, input device status, output/vJoy status, `output_verified`, Full Live Runtime Ready, selected axis, workspace/source file, last command status/request ID, preflight status, hidden-page skips, page switch timing, heartbeat/update timing, graph/update timing, startup timing, and diagnostics collection state.

## Diagnostics Service

Phase 11B adds `v3_app/services/perf_diagnostics.py`.

It provides:

- `DiagnosticsCollector`
- `PerfMetricSummary`
- `DiagnosticsSnapshot`
- timing sample recording and summaries
- hidden-page skip counters
- summary formatting
- pure diagnostics text building

The service is deterministic and testable without PySide6.

## Runtime and Preflight Truth

Run Runtime Preflight remains safe and does not prove output verification. It refreshes local runtime setup truth and does not install drivers, launch installers, start the Bridge, poll live HOTAS input, write vJoy, verify output, or activate runtime.

Runtime wording remains conservative:

- Runtime truth: `blocked_missing_device`
- Bridge lifecycle: `Simulated`
- HOTAS discovery: `no_supported_device` unless read-only discovery sees a supported device
- vJoy detected; output writes unverified
- Output verified: `false`
- Full Live Runtime Ready: `false`
- Process presence is a hint only
- Telemetry remains the truth surface

## Timing and Hidden-Skip Visibility

Timing metrics are UI/app diagnostics, not live hardware proof.

Implemented:

- page switch/build visibility through shell switch timing and optional collector samples;
- heartbeat/update timing summary when samples are recorded;
- graph draw/update timing summary when samples are recorded;
- startup timing summary when samples are recorded;
- hidden-page skip counters when instrumentation records them;
- truthful unavailable/not implemented text when no counter exists.

## Copy Diagnostics

Copy Diagnostics builds local text containing:

- app/version label;
- active page;
- runtime truth;
- Bridge lifecycle;
- telemetry status/age;
- HOTAS discovery;
- output/vJoy status;
- `output_verified`;
- Full Live Runtime Ready;
- process hint;
- command status/request ID;
- selected axis;
- workspace/source file;
- timing summaries;
- hidden-page skip counts;
- manual Bridge launch guidance.

Clipboard integration is not required for Phase 11B.

## Safety Boundary

Phase 11B does not add:

- Live Overlay;
- Flight Recorder;
- real HOTAS polling;
- live physical input streaming;
- vJoy writes;
- output verification;
- automatic Bridge launch;
- UI-launched child process;
- service install;
- login auto-start;
- tray manager;
- installer launch;
- StartBridge/StopBridge/RestartBridge behavior;
- real process scanner;
- real runtime activation;
- cloud AI or LLM behavior;
- conditional-rule auto-editing;
- auto-save.

## Verification

Final verification results:

- `python -m pytest` - passed, 242 tests.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - passed, 7 tests.
- `python -m pytest tests\test_phase10a_helm_overlay_foundation.py` - passed, 6 tests.
- `python -m pytest tests\test_phase10b_helm_intelligence_expansion.py` - passed, 7 tests.
- `python -m pytest tests\test_phase10c_helm_guided_review_apply_revert.py` - passed, 8 tests.
- `python -m pytest tests\test_phase10d_helm_context_integration.py` - passed, 6 tests.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11a_help_docs_foundation.py` - passed, 8 tests.
- `python -m pytest tests\test_phase11b_perf_diagnostics_page.py` - passed, 7 tests.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed with `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed. Runtime truth during implementation: Thrustmaster software detected, vJoy detected, HOTAS not connected, Simulation Mode Active unless physical input and output writes are both verified, Full Live Runtime Ready false, and no installers launched.
- `git diff --check` - pending final diff hygiene pass after this report update.
