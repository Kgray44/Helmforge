# Phase 10B - Helm Intelligence Expansion and Guided Diagnostic System

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Package boundary: `v3_app` UI, `bridge_app` Bridge, `shared_core` common domain code

## Summary

Phase 10B expands Helm from the Phase 10A single-path assistant into a deterministic, local, diagnosis-first tuning assistant.

Helm now supports:

- structured symptom definitions across aim/combat, flight, ground/racing, and general control-feel issues;
- deterministic follow-up questions when symptom confidence is low or the symptom is ambiguous;
- workspace findings for deadzone, axis mismatch, combat scaling, and slew-limit patterns;
- grouped recommendation cards with confidence, affected parameter count, expected outcome, risk, and "Why?" details;
- richer exact before/after diffs;
- in-memory-only apply and revert behavior.

No cloud AI, LLM integration, live telemetry inference, automatic tuning, auto-save, rule mutation, Bridge lifecycle control, real HOTAS polling, or vJoy output authority was added.

## Symptom Architecture

The symptom table lives in `v3_app/helm/symptom_library.py`.

Supported deterministic examples include:

- `Combat mode feels sluggish`
- `Combat aim overshoots`
- `Aim feels twitchy`
- `Hard to track smoothly`
- `Small movements feel ignored`
- `Reversals feel sticky`
- `Roll feels too sensitive`
- `Pitch response feels inconsistent`
- `Rudder feels delayed`
- `Helicopter hover feels unstable`
- `Steering oscillates`
- `Controls feel inconsistent`

The matcher is deterministic. It checks exact labels first, then conservative keyword phrases, then falls back to a follow-up-required general symptom.

## Confidence Model

Confidence is deterministic and conservative:

- `High`: score >= 0.80
- `Medium`: score >= 0.60
- `Low`: score > 0.0

Scores are intentionally human-scale values such as `0.84` or `0.72`. Helm does not use false precision.

Confidence comes from:

- symptom specificity;
- whether follow-up answers narrowed the symptom;
- the recommendation table attached to the symptom;
- the average confidence of grouped diffs.

## Follow-Up Questions

Ambiguous symptoms such as `Controls feel inconsistent` produce deterministic follow-up questions before any diffs are staged.

Current questions:

- Does the issue happen mostly near center?
- Does the issue occur in all modes or only combat?
- Is the issue more noticeable during tracking or snapping?

Answers refine the deterministic path and raise confidence modestly. They do not call external AI and do not inspect hardware.

## Recommendation Grouping

Recommendation diffs now carry group metadata. The overlay renders collapsible-style group cards with selection, confidence, affected count, and a compact "Why?" disclosure.

Current group labels include:

- Fine Aim Control
- Combat Responsiveness
- Stability
- Center Precision
- High-Speed Tracking
- Drift Reduction
- Overshoot Mitigation

Groups support selection at the group level. Individual diff selection remains available.

## Diff Model

Each diff now includes:

- axis;
- section;
- parameter;
- before value;
- after value;
- delta amount;
- reason;
- confidence score;
- expected outcome;
- risk level;
- reversibility;
- selected state;
- applied state;
- recommendation group.

Diff application remains limited to workspace draft sections that already exist:

- Combat Profile;
- Base Tuning;
- Filtering.

Conditional Rules are not mutated by Helm.

## Workspace Analysis

Helm inspects current workspace values for conservative findings such as:

- unusually high yaw deadzone;
- roll curve more aggressive than yaw;
- combat yaw scale lower than pitch;
- low yaw combat same/reverse slew values.

Findings appear in `What I found`. Warnings are surfaced when the workspace already contains extreme values so users can apply changes in small batches.

## UI Changes

The Phase 10A overlay architecture is preserved:

- Helm launches from the top-right `ASSISTANT` cluster.
- Helm remains a modal/overlay, not a sidebar page.
- The existing cards remain: `What's wrong?`, `What I'd change`, `What I found`, and `Apply / Revert`.
- Recommendation groups now render inside `What I'd change`.
- Diffs show expected outcome, risk, confidence, and in-memory reversibility.
- The overlay remains scroll-safe.

## Safety Boundaries

Phase 10B preserves the Phase 9K runtime freeze:

- no real HOTAS polling;
- no live physical input streaming;
- no vJoy writes;
- no output verification;
- no automatic Bridge launch;
- no UI-launched child process;
- no Bridge service installation;
- no login auto-start;
- no tray/background manager work;
- no installer launch;
- no StartBridge/StopBridge/RestartBridge behavior;
- no real process scanner;
- no real runtime activation;
- no cloud AI or LLM integration;
- no rule auto-editing;
- no auto-save.

Apply Selected Changes updates only the current in-memory workspace draft. Save Workspace remains the explicit shell-level persistence action.

## Current Runtime Truth

Implementation and verification remained conservative:

- Runtime truth: `blocked_missing_device`
- Bridge lifecycle: `Simulated`
- Device discovery truth: `no_supported_device` unless read-only discovery sees a supported device
- `output_verified`: `false`
- Full Live Runtime Ready: `false`

## Verification

Commands run during Phase 10B:

- `python -m pytest tests\test_phase10b_helm_intelligence_expansion.py` - 7 passed
- `python -m pytest tests\test_phase10a_helm_overlay_foundation.py` - 6 passed
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed

Final full verification was run after documentation updates:

- `python -m pytest` - first 4-minute run timed out without a failure summary; rerun with a longer timeout passed, 206 passed
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed
- `python -m pytest tests\test_phase10a_helm_overlay_foundation.py` - 6 passed
- `python -m pytest tests\test_phase10b_helm_intelligence_expansion.py` - 7 passed
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed
- `python -m bridge_app.main --once` - passed
- `python -m bridge_app.main --run-for-ms 250` - passed
- `python -m bridge_app.main --status` - passed, `lifecycle=Simulated truth=blocked_missing_device output_verified=False`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; HOTAS Not Connected, vJoy Detected, Full Live Runtime Ready false
- `git diff --check` - passed

## Deferred

Deferred work remains:

- live runtime analysis;
- live telemetry tuning;
- automatic profile optimization;
- cloud AI or LLM integration;
- voice interaction;
- conditional rule auto-editing;
- auto-save;
- real hardware observation;
- Flight Recorder integration;
- runtime process management.

## Recommended Next Phase

Continue with the next prompt-book Phase 10 slice only after review. The next Helm phase can deepen guided workflows or add richer review UX, but it should still remain local, deterministic, reversible, and bounded unless a later hardware/runtime phase explicitly changes authority.
