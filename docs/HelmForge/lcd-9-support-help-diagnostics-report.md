# LCD-9 Support / Help / Diagnostics

Date: 2026-05-12

## Scope

LCD-9 replaces the Liquid Support placeholders with new Liquid Command Deck pages for:

- `support.help_docs`
- `support.perf_diagnostics`
- `support.setup_runtime_check`

This pass also adds a small Live Monitor visual smoothness patch. It does not implement LCD-10 microinteractions, LCD-11 page transitions/live-data animation, LCD-12 atmosphere/radial/final QA, Mapping feature work, Recorder backend work, runtime authority changes, hardware polling changes, vJoy behavior changes, output verification changes, Bridge lifecycle ownership, auto-save, cloud/LLM behavior, game injection, graphics API hooks, or packaged-output changes.

## Support Pages Added

`v3_app/liquid/pages/support_command_pages.py` adds a shared `SupportCommandPage` composed from Liquid components:

- `LiquidPage`
- `LiquidPageHeader`
- `LiquidHeroPanel`
- `LiquidInspectorPanel`
- `LiquidDetailPanel`
- `LiquidAdvancedSection`
- `LiquidStatusRail`
- `MetricTile`
- `StatusChip`
- `TruthBadge`
- `ChecklistPanel`
- `ReadinessGate`
- `TelemetryFreshnessRail`
- `GuidanceBlock`
- `RouteFlowRow`

The pages construct offscreen and are hosted by the existing Liquid shell route stack. The old Legacy Help / Docs and Perf / Diagnostics widgets remain fallback/reference only and are not mounted as the primary Liquid composition.

## Help / Docs Structure

`support.help_docs` answers: "How do I understand and use HelmForge?"

The page includes:

- a Help / Docs hero explaining the command-deck model
- a topic rail for Getting Started, Runtime Truth, Mapping, Tuning, Analysis, Recorder, and Troubleshooting
- topic cards for Preflight, Mapping, Tuning, Effective Response Stack, Live Monitor, Flight Recorder limitations, Helm Assistant, Setup / vJoy / Bridge, and Performance diagnostics
- route buttons when the shell provides route navigation
- a parameter reference panel built from existing parameter metadata
- a secondary article index using the existing help article registry

Required runtime truth wording is visible: Output Intent is not output proof, vJoy detected is not output verified, stream connected is not output proof, recorder metadata-only artifacts are not real recordings, simulation mode is safe fallback, and Full Live Runtime Ready requires the full proof chain.

## Perf / Diagnostics Structure

`support.perf_diagnostics` answers: "What is the system actually reporting?"

The page includes:

- a diagnostics hero with runtime truth, telemetry status, output proof, Full Live Runtime Ready, active page, JSON read cadence, graph/update timing, and jank bucket summary
- grouped Runtime Truth, Bridge / Telemetry, Physical Input, Virtual Output / vJoy, Performance, and Workspace / UI sections
- raw runtime-frame detail in an advanced section
- actions for Refresh Diagnostics, Clear Timings, and Copy Diagnostics

Diagnostics are observational and on demand. The page uses timing summaries and jank buckets from the existing diagnostics collector, including the PERF 1A `over_16ms`, `over_33ms`, `over_50ms`, `over_100ms`, and `over_250ms` concepts. It does not introduce a high-frequency diagnostics loop.

## Setup / Runtime Check Structure

`support.setup_runtime_check` answers: "What do I need to install, connect, or check?"

The page includes:

- a setup readiness hero with current blocker and next safe action
- readiness gates for HOTAS input, Bridge telemetry, workspace config, vJoy dependency, vJoy device, output proof, and safety
- a safe setup checklist
- copyable dry-run command guidance:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
```

This page does not launch installers, start/stop Bridge, write vJoy, or verify output. Setup checks are labeled as checks, not runtime activation.

## Data And Services Reused

LCD-9 reuses:

- existing `AppState`
- existing `WorkspaceConfig`
- existing runtime/preflight models
- existing help article service from `v3_app.services.help_docs`
- existing parameter metadata from `v3_app.services.parameter_metadata`
- existing diagnostics snapshot/text builders from `v3_app.services.perf_diagnostics`
- existing PERF 1A diagnostics collector and jank bucket concepts

No competing help metadata or runtime authority model was added.

## Legacy Boundary

The Liquid Support pages do not import or wrap the old Legacy Help / Docs or Perf / Diagnostics pages. Those pages remain available elsewhere as reference/fallback, but the Liquid Support routes now use new command-deck compositions.

## Raw Diagnostics Handling

Raw/internal values are grouped on the Diagnostics page and in advanced Support sections. Help / Docs keeps clean topic cards and parameter reference as the primary interface. Setup keeps readiness gates and checklist items primary, with detailed command guidance secondary.

## Live Monitor Visual Patch

The Liquid Live Monitor now exposes a visual-only render lane:

- `LIQUID_LIVE_MONITOR_VISUAL_TARGET_FPS = 60`
- `LIQUID_LIVE_MONITOR_VISUAL_INTERVAL_MS = 16`
- `liveMonitorVisualTargetFps`
- `liveMonitorVisualIntervalMs`
- `liveMonitorVisualRenderOnly`
- `liveMonitorVisualFrameTickCount`
- `liveMonitorVisualGraphRepaintCount`

The timer calls `advance_live_monitor_visual_frame()`. That method repaints the graph and lightweight axis instruments from cached data. It does not append duplicate samples, rebuild the full page, rebuild the Analysis model, rebuild numeric panels, read JSON, run diagnostics, recompute the pipeline, or mutate layout.

Accepted Live Monitor samples now append when telemetry data changes. Telemetry bursts update cached history without forcing graph paint for every telemetry frame. Visual frames can repaint cached history at the 60 FPS target.

## PERF 1A Lanes Preserved

The patch keeps these lanes throttled or dirty-gated:

- JSON fallback remains a 5 Hz fallback lane.
- Diagnostics remain low cadence / on demand.
- Shell chrome remains dirty-gated.
- Static graph rebuilds remain dirty-only.
- Pipeline/model recompute remains telemetry/data driven, not visual-frame driven.
- Numeric panels update in place and are not rebuilt every visual frame.
- Full page render does not run at 60 Hz.

## Tests Added

Added `tests/test_lcd_9_support_help_diagnostics.py`, covering:

- Help / Docs page offscreen construction
- Perf / Diagnostics page offscreen construction
- Setup / Runtime Check page offscreen construction
- Support route factory wiring
- topic cards and runtime truth wording
- parameter metadata exposure
- grouped diagnostics sections
- PERF 1A timing/jank concepts
- readiness gates and checklist
- safe setup behavior
- no Legacy primary wrapper
- no unsafe runtime actions
- Live Monitor 60 FPS visual target
- visual frames not causing model/full-render/sample-append churn

Updated existing navigation and PERF/Liquid cadence tests to reflect that Support pages are no longer placeholders and the visual timer no longer appends duplicate samples.

## Tests Run

- `python -m pytest` -> 899 passed
- `python -m pytest tests/test_lcd_9_support_help_diagnostics.py` -> 7 passed
- `python -m pytest tests/test_lcd_3_navigation_mode_architecture.py` -> 8 passed
- `python -m pytest tests/test_post_rc_perf_1a1_preset_crash_hotfix.py` -> 5 passed
- `python -m pytest tests/test_lcd_7w_performance_live_monitor_profiles.py` -> 5 passed
- `python -m pytest tests/test_post_rc_perf_1a_liquid_analysis_cadence.py` -> 2 passed
- `python -m pytest tests/test_post_rc_perf_1a_live_monitor_cadence.py` -> 2 passed
- `python -m pytest tests/test_post_rc_perf_1a_shell_telemetry_dirty_gating.py` -> 1 passed
- `python -m pytest tests/test_phase19d_final_acceptance_report.py` -> 5 passed
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 750` -> passed
- `python -m bridge_app.main --status` -> passed, reported `lifecycle=LiveVerified truth=live_verified output_verified=True`
- `python -m bridge_app.main --run-for-ms 250 --telemetry-stream` -> passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` -> passed, launched no installers
- `git diff --check` -> passed
- normal display bounded Liquid launch/sweep -> passed; Support routes opened as Liquid pages and visual frames did not trigger full render

## Runtime Truth Preservation Statement

LCD-9 preserves runtime truth boundaries. It does not weaken Full Live Runtime Ready logic, does not treat stream connection as output proof, does not treat physical input as output proof, does not treat JSON freshness as output proof, does not treat vJoy detection as output proof, preserves simulation fallback and JSON fallback, keeps output intent separate from output write proof, and keeps recorder metadata-only artifacts honest.

## Remaining Risks

- Visual smoothness still depends on actual telemetry frame cadence and desktop paint cost on the target machine.
- Support diagnostics currently show snapshot/on-demand state; future work could add richer low-cadence refresh controls if needed.
- Manual HOTAS movement remains the best confirmation that the graph feels closer to 60 FPS.

## Deferred To Later LCD Phases

- LCD-10: microinteractions.
- LCD-11: page transitions and live-data animation system.
- LCD-12: atmosphere, radial menu, and final visual QA.

No packaged smoke was rerun as part of writing this report.
