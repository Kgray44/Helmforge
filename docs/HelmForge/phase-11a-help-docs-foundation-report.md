# Phase 11A - Help / Docs Foundation and Runtime Setup Guide

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Help / Docs foundation only

## Summary

Phase 11A implements Help / Docs foundation only. The page is built as integrated local product documentation with category browsing, deterministic search, and a scrollable guide pane.

Perf / Diagnostics page work is deferred to Phase 11B.

## Page Behavior

The Help / Docs page includes:

- title: Help / Docs;
- subtitle: Search the built-in guide, browse by category, and keep the details you use most close at hand.;
- search field with placeholder: Search features, pages, or tuning terms;
- sort dropdown default: By Category;
- topic/category list;
- guide pane with title, category, summary, article body, and related topics.

Search is local and deterministic. It matches title, category, keywords, and body text. It does not call web services, cloud AI, or an LLM.

## Local Docs Model

Phase 11A adds `v3_app/services/help_docs.py` with:

- `HelpArticle`;
- `HelpSearchResult`;
- category ordering;
- `all_articles`;
- `articles_by_category`;
- `get_article`;
- `search_articles`.

## Categories and Topics

Implemented categories and topics:

- Advanced Pages: Conditional Rules, Effective Response Stack, Helm
- Analysis: Graphs and Previews, Runtime Indicators
- Core Pages: Base Tuning, Combat Profile, Filtering, Modes, Profiles, Mapping
- Diagnostics: Performance / Diagnostics
- Getting Started: Quick Start, Runtime Setup / vJoy Setup
- Reference: Tuning Glossary
- Workflow: Saving and Importing

## Runtime Setup / vJoy Setup

The Runtime Setup / vJoy Setup article is local built-in documentation. It explains:

- simulation mode works without physical HOTAS hardware;
- simulation mode works without output verification;
- Bridge telemetry is the runtime truth surface;
- manual Bridge launch remains the current lifecycle model;
- the UI does not start, stop, restart, spawn, install, or manage the Bridge;
- physical HOTAS discovery is discovery-only;
- vJoy detected does not equal output verified;
- `output_verified` remains false until a future output verification phase proves writes;
- Full Live Runtime Ready remains false until future phases prove both input and output;
- missing HOTAS may produce `blocked_missing_device`;
- stale, missing, or invalid telemetry falls back safely;
- Run Preflight and Bridge commands are safe requests, not proof of runtime success;
- command acknowledgement requires matching `request_id`;
- manual Bridge launch command: `python -m bridge_app.main --run-for-ms 250`.

The article does not imply live HOTAS polling, live input streaming, vJoy writes, output verification, Full Live Runtime Ready availability, or UI-owned Bridge launch.

## Helm Article

The Helm article reflects Phase 10:

- Helm launches from the top-right ASSISTANT cluster;
- Helm is overlay/modal behavior, not a sidebar page;
- Helm is deterministic and local;
- Helm does not use cloud AI or LLM behavior;
- Helm can use workspace, mode, rule, stack, and runtime diagnostic context when available;
- Helm labels evidence sources;
- recommendations are staged before apply;
- Apply Selected Changes modifies only the in-memory workspace draft;
- Save Workspace remains the only persistence action;
- Revert Last Helm Changes restores the last applied Helm batch;
- Helm does not mutate conditional rules in v1;
- Helm does not perform live hardware analysis.

## Runtime Boundary

Help / Docs does not add runtime authority. It does not perform hardware polling, vJoy writes, output verification, Bridge lifecycle control, process spawning, automatic Bridge launch, service install, login auto-start, tray manager work, installer launch, cloud AI or LLM behavior, auto-save, or runtime activation.

## Current Runtime Truth

Current conservative runtime truth remains:

- Bridge lifecycle: `Simulated`
- Runtime truth: `blocked_missing_device`
- HOTAS discovery: `no_supported_device` unless read-only discovery sees a supported device
- vJoy/output state: vJoy may be detected, but output writes are not verified
- `output_verified`: `false`
- Full Live Runtime Ready: `false`

## Verification

Final verification for Phase 11A:

- `python -m pytest` - 235 passed
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed
- `python -m pytest tests\test_phase10a_helm_overlay_foundation.py` - 6 passed
- `python -m pytest tests\test_phase10b_helm_intelligence_expansion.py` - 7 passed
- `python -m pytest tests\test_phase10c_helm_guided_review_apply_revert.py` - 8 passed
- `python -m pytest tests\test_phase10d_helm_context_integration.py` - 6 passed
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - 7 passed
- `python -m pytest tests\test_phase11a_help_docs_foundation.py` - 8 passed
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed
- `python -m bridge_app.main --once` - passed
- `python -m bridge_app.main --run-for-ms 250` - passed
- `python -m bridge_app.main --status` - passed; `lifecycle=Simulated truth=blocked_missing_device output_verified=False`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; Thrustmaster software detected, vJoy detected, HOTAS Not Connected, Full Live Runtime Ready false, no installers launched
- `git diff --check` - passed

## Deferred

Deferred to later phases:

- Phase 11B Perf / Diagnostics page work;
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
- cloud AI or LLM behavior;
- auto-save;
- real runtime activation.
