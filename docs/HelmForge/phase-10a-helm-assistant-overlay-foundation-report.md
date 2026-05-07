# Phase 10A Helm Assistant Overlay Foundation Report

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Date: 2026-05-06  
Scope: Helm Assistant Overlay foundation only

## Summary

Phase 10 is Helm Assistant Overlay according to the recovered prompt book. Phase 10A creates the overlay foundation and one deterministic local recommendation path without adding runtime authority.

Helm now launches from the top-right `ASSISTANT` cluster as a large modal overlay. It is not a sidebar page and does not change app navigation. The overlay uses the recovered Helm structure: title, subtitle, active status, context-linked assistant text, `In-memory only` safety pill, symptom input, chips, diffs, findings, and apply/revert controls.

## Evidence Inspected

- `HOTAS Control Panel Forensic Spec Set/06-helm-assistant-specification.md`
- `HOTAS Control Panel Forensic Spec Set/hotas_control_panel_v_2_codex_prompt_book.md`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/12 Helm/v2-helm_overlay_idle-in-memory-only.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/12 Helm/legacy-helm_overlay_v2-draft-analysis-results-diff-list.png`

The final V2 overlay screenshot guided the large modal/right-side treatment, dimmed parent behavior, header/status structure, card hierarchy, symptom chips, and in-memory-only safety wording.

## UI Behavior

- Helm button is wired in the top-right `ASSISTANT` cluster.
- Helm opens as a large modal overlay sized around 70 percent of the shell width when practical.
- The parent shell is visually de-emphasized while Helm is open.
- The overlay is scroll-safe.
- Close returns to the current app page without sidebar navigation.
- Helm is not registered as a sidebar page.

## Helm Sections

Visible sections:

- `What's wrong?`
- `What I'd change`
- `What I found`
- `Apply / Revert`

Header elements:

- `Helm`
- `Diagnosis-first tuning guidance for the current workspace.`
- green status indicator
- `Helm is active`
- `Context-linked assistant`
- `In-memory only`
- close button

## Engine Scaffolding

Added `v3_app/helm/` modules:

- `diff_model.py`
- `helm_engine.py`
- `helm_overlay.py`
- `recommendation_library.py`
- `symptom_library.py`

The pure engine path supports symptom matching, context extraction, recommendation results, exact before/after diffs, selected/applied state, applying selected diffs to a workspace object, and reverting the last Helm-applied batch.

## Working Symptom Path

Implemented symptom:

- `Combat mode feels sluggish`

It produces recovered example-style diffs using current workspace values as the `before` values:

- Yaw Combat Center Alpha -> `0.68`
- Pitch Combat Center Alpha -> `0.68`
- Yaw Combat Reverse Slew -> `0.09`
- Yaw Combat Same Slew -> `0.09`
- Yaw Combat Scale -> `0.79`

Each diff includes axis, section, parameter, before value, after value, reason, selected state, and applied state.

## Workspace Safety

Helm changes:

- apply only to the current in-memory workspace/draft;
- mark the shell workspace as unsaved through the existing dirty-state seam;
- never auto-save;
- never write `hotas_bridge_config_v3.json`;
- support `Revert Last Helm Changes`;
- do not create, edit, enable, disable, or delete conditional rules in Helm v1.

## Runtime Boundary

Phase 10A preserves the Phase 9K boundary:

- no real HOTAS polling;
- no live physical input streaming;
- no vJoy writes;
- no output verification;
- no automatic Bridge launch;
- no UI-launched child process;
- no Bridge service installation;
- no login auto-start;
- no tray/background manager implementation;
- no installer launch;
- no StartBridge/StopBridge/RestartBridge behavior;
- no real process scanner;
- no real runtime activation.

Runtime truth remains whatever Phase 9 telemetry/preflight reports. Output verification remains false unless a future output verification phase proves otherwise.

## Files Changed

- `README.md`
- `docs/HelmForge/bridge-ui-architecture.md`
- `docs/HelmForge/phase-10a-helm-assistant-overlay-foundation-report.md`
- `tests/test_phase10a_helm_overlay_foundation.py`
- `v3_app/helm/__init__.py`
- `v3_app/helm/diff_model.py`
- `v3_app/helm/helm_engine.py`
- `v3_app/helm/helm_overlay.py`
- `v3_app/helm/recommendation_library.py`
- `v3_app/helm/symptom_library.py`
- `v3_app/theme/qss.py`
- `v3_app/ui/header.py`
- `v3_app/ui/shell.py`

## Deferred

- deeper Helm symptom library;
- adaptive recommendation sizing;
- rule relevance analysis beyond a conservative context note;
- follow-up questions;
- Helm icon asset integration;
- Help / Docs implementation;
- Live Overlay implementation;
- Flight Recorder implementation;
- real HOTAS/vJoy runtime work.

## Verification

Commands run during Phase 10A:

- `python -m pytest`
- `python -m pytest tests\test_phase9k_boundary_freeze.py`
- `python -m pytest tests\test_phase10a_helm_overlay_foundation.py`
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- `python -m bridge_app.main --once`
- `python -m bridge_app.main --run-for-ms 250`
- `python -m bridge_app.main --status`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- `git diff --check`

Results:

- Full suite: `199 passed`.
- Phase 9K boundary suite: `7 passed`.
- Phase 10A focused suite: `6 passed`.
- UI smoke launch exited cleanly.
- Bridge `--once`, `--run-for-ms 250`, and `--status` exited cleanly.
- Bridge status reported `lifecycle=Simulated truth=blocked_missing_device output_verified=False`.
- Runtime setup dry run detected Thrustmaster runtime software and vJoy, reported HOTAS Not Connected, and confirmed Full Live Runtime Ready false for this phase.
- `git diff --check` passed.

Screenshot note:

- A Qt offscreen overlay screenshot was generated at `%TEMP%\helmforge_phase10a_helm_overlay_styled.png` for local inspection. The offscreen renderer used in this environment displayed text glyphs poorly, so the screenshot was not used as the primary fidelity proof.
