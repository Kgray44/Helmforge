# Phase 10D - Helm Context Integration

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Scope: Helm context integration only

## Summary

Phase 10D adds a deterministic, read-only context extraction layer for Helm. Helm can now reason over workspace values, mode settings, conditional rules, optional Effective Response Stack snapshots, and Phase 9 runtime diagnostics without gaining runtime authority.

The new context model lives in `v3_app/helm/context.py`.

## Context Model

Phase 10D adds:

- `HelmEvidenceSource`
- `HelmContext`
- `HelmAxisContext`
- `HelmModeContext`
- `HelmRuleContext`
- `HelmStackContext`
- `HelmRuntimeContext`

The context captures:

- selected axis when available;
- tuning, filtering, and combat profile values for each axis;
- precision/combat mode controls and stack mode;
- conditional rule counts, disabled rules, target axes, and selected-axis relevance;
- optional response stack snapshot summary;
- runtime truth;
- lifecycle label;
- output verification truth;
- Full Live Runtime Ready truth;
- device discovery status;
- telemetry/process hint labels when provided.

Context extraction is deterministic. It does not poll hardware, write vJoy, start the Bridge, stop the Bridge, restart the Bridge, or verify output.

## Evidence Labels

Helm evidence labels include:

- Workspace values
- Mode settings
- Conditional rules
- Response stack snapshot
- Bridge telemetry
- Runtime diagnostics
- Discovery-only status
- Simulated data
- Unavailable

Helm displays evidence boundaries in the overlay. Findings and context-aware recommendations can now state where the evidence came from.

Examples:

- `Evidence: workspace values.`
- `Evidence: mode settings and combat profile.`
- `Evidence: response stack snapshot.`
- `Bridge telemetry says runtime truth is blocked_missing_device.`
- `I'm using workspace/simulation context only; live hardware analysis is not active.`

## Mode Context

Helm now inspects:

- precision hold buttons;
- combat trigger buttons;
- combat zoom/aim buttons;
- combat extra buttons;
- precision/combat stack mode.

When stack mode is `multiply`, Helm adds caution that precision and combat scaling can compound.

## Rule Context

Helm summarizes rules as read-only context:

- total rule count;
- enabled/disabled count;
- target axes;
- selected-axis relevant rules;
- disabled rule summaries.

Helm does not create, edit, delete, enable, or disable rules.

Example:

- `Disabled Yaw rule targets Output Scale at Base Output Limits. I'm not changing rules in Helm v1.`

## Stack Context

If a `WorkspaceSignalPipelineResult` or compatible stack snapshot is supplied, Helm summarizes:

- selected axis;
- raw input;
- final output;
- largest stage delta;
- active stages;
- rule injection stages;
- stage count.

If no stack snapshot is available, Helm records stack context as unavailable and does not pretend stage evidence exists.

Phase 10D does not rebuild the Effective Response Stack page and does not introduce UI layout churn.

## Runtime Diagnostics

Runtime context remains conservative:

- Runtime truth: `blocked_missing_device` unless diagnostics prove otherwise;
- lifecycle: `Simulated` fallback;
- `output_verified`: `false`;
- Full Live Runtime Ready: `false`;
- discovery: `no_supported_device` unless read-only discovery sees a supported device.

If no physical HOTAS is available, Helm says live validation is not available. If a supported HOTAS is detected in future discovery-only telemetry, Helm must still say polling is not active and output verification is false.

## Overlay Changes

The Helm overlay now includes a compact context summary in `What I found`:

- Axis context;
- Evidence labels;
- Runtime truth;
- Output verified;
- Discovery-only status;
- Live analysis state.

Helm remains:

- launched from the top-right ASSISTANT cluster;
- overlay/modal behavior;
- not a sidebar page;
- scroll-safe;
- first-person and polished.

## Preserved Apply/Revert Behavior

Phase 10D preserves Phase 10C behavior:

- recommendations are staged before apply;
- group selection works;
- individual diff selection works;
- Apply Selected Changes applies selected diffs only;
- Apply Selected Changes updates only the in-memory workspace draft;
- Save Workspace remains explicit;
- Revert Last Helm Changes restores exact previous values;
- no auto-save occurs.

## Safety Boundaries

Phase 10D does not add:

- Help / Docs;
- Perf / Diagnostics page work;
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
- cloud AI or LLM integration;
- conditional-rule auto-editing;
- auto-save.

## Verification

Phase 10D focused verification:

- `python -m pytest tests\test_phase10d_helm_context_integration.py` - 6 passed
- `python -m pytest tests\test_phase10c_helm_guided_review_apply_revert.py` - 8 passed
- `python -m pytest tests\test_phase10b_helm_intelligence_expansion.py` - 7 passed
- `python -m pytest tests\test_phase10a_helm_overlay_foundation.py` - 6 passed
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed

Final verification is recorded after the full verification pass:

- `python -m pytest` - 220 passed
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - 7 passed
- `python -m pytest tests\test_phase10a_helm_overlay_foundation.py` - 6 passed
- `python -m pytest tests\test_phase10b_helm_intelligence_expansion.py` - 7 passed
- `python -m pytest tests\test_phase10c_helm_guided_review_apply_revert.py` - 8 passed
- `python -m pytest tests\test_phase10d_helm_context_integration.py` - 6 passed
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed
- `python -m bridge_app.main --once` - passed
- `python -m bridge_app.main --run-for-ms 250` - passed
- `python -m bridge_app.main --status` - passed, `lifecycle=Simulated truth=blocked_missing_device output_verified=False`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; HOTAS Not Connected, vJoy Detected, Full Live Runtime Ready false
- `git diff --check` - passed

## Deferred

Deferred work remains:

- Help / Docs;
- Perf / Diagnostics;
- Live Overlay;
- Flight Recorder;
- live runtime analysis;
- live telemetry tuning;
- automatic profile optimization;
- cloud AI or LLM integration;
- voice interaction;
- conditional rule auto-editing;
- auto-save;
- real hardware observation;
- runtime process management.
