# Post-RC PERF 1A Master Refresh-Rate Architecture Report

Post-RC PERF 1A fixes the app-wide live refresh architecture that was letting many independent 16 ms or 60 Hz paths recompute, repaint, parse JSON, and rebuild graph data at the same time. This pass is performance architecture only. It does not add Mapping features, Recorder backend behavior, Help / Docs overhaul work, Liquid visual redesign, hardware polling behavior, vJoy behavior, output verification changes, Bridge lifecycle ownership, auto-save, cloud/LLM behavior, game injection, or graphics API hooks.

## Root Cause Summary

The slow/skipping Live Monitor and nearly unusable Effective Response Stack were caused by a shared pattern: one timer heartbeat was being treated as permission to do every kind of work. Telemetry ingest, JSON fallback reads, history append, axis labels, button chips, diagnostic text, graph point rebuilds, overlay trace building, pipeline compute, static graph plotting, and shell chrome updates were all too tightly coupled.

PERF 1A separates those into named cadence lanes in `v3_app/services/live_ui_scheduler.py`, then applies dirty-update helpers from `v3_app/services/ui_dirty.py` so unchanged labels, chips, bars, graph series, and shell chrome do not repaint just because a timer fired.

## Refresh Sources Found

The audit found active cadence sources in:

- `LiveMonitorPage`: 16 ms page timer, JSON read path, graph refresh, overlay sync, diagnostic rows.
- `EffectiveResponseStackPage`: 16 ms timer, per-refresh pipeline construction, static graph rebuild, stage-card repolish.
- `BaseTuningPage`, `FilteringPage`, `CombatProfilePage`: 16 ms timers calling `LiveAxisSampleSource.raw_axes()`.
- `LiveAxisSampleSource`: unthrottled JSON fallback read before this pass.
- `HelmForgeShell` and Liquid shell: chrome updates on every telemetry event.
- `LiveOverlayWindow` and `OverlayRenderer`: overlay timer plus setter-triggered updates.
- `OverlayTelemetryBuffer` and `build_overlay_traces()`: repeated list/tuple rebuilds.
- Liquid Analysis pages: 100 ms visual timer plus telemetry-driven model rebuilds, with age text in the structural model signature.
- `BridgeService`: runtime frame build plus a second pipeline process for rule summary.
- `EmbeddedBridgeRuntime`: every worker tick could submit diagnostic JSON.
- `DiagnosticsCollector` and `UiStallMonitor`: broad/unbounded timing storage and only catastrophic stall thresholds.

## Old vs New Cadence

| Source | Old cadence / behavior | New PERF 1A behavior |
| --- | --- | --- |
| Live Monitor heartbeat | 16 ms full refresh | Lightweight timer drives lane gates |
| Embedded telemetry | Accepted on production cadence | Still first priority; downstream rendering dirty-gated |
| Stream telemetry | Opt-in only | External Bridge stream defaults on, local-only, still not output proof |
| JSON telemetry read | Caller could read near 60 Hz | Callers throttle fallback to 5 Hz and reuse last good result between reads |
| Axis values | Updated every Live Monitor tick | 30 Hz max |
| Buttons / hats | Updated every Live Monitor tick | 30 Hz max |
| Live Monitor graphs | Updated every tick | 18 Hz max and only when graph data changed |
| Diagnostics text | Updated with full refresh | 4 Hz lane |
| Overlay trace build | Rebuilt through setters/timer | 24 Hz max, cached, new sample driven |
| Overlay paint | 60 FPS default plus setter updates | 30 FPS default; setters mark dirty, timer paints when dirty |
| Effective Stack compute | Every 16 ms, new pipeline each time | Persistent pipeline, compute lane max 18 Hz unless user/raw input forces |
| Effective Stack static graph | Rebuilt every render | Dirty-triggered on axis/workspace/settings changes |
| Effective Stack marker | Coupled to static series | 30 Hz marker lane, no static replot required |
| Tuning live sample | 16 ms raw read | 30 Hz max |
| Tuning snapshot text | Every sample | 12 Hz max or forced user action |
| Shell chrome | Every telemetry event | Dirty signature or 10 Hz shell lane |
| Liquid Analysis structural render | Could include freshness age | Data signature excludes age text; freshness updates are separate |
| Diagnostics timings | Unbounded lists | Bounded timing series plus jank buckets |

## Transport Priority

PERF 1A implements and preserves this order:

1. Embedded telemetry.
2. Local Bridge telemetry stream.
3. JSON fallback.
4. Simulation fallback.

Fresh embedded telemetry bypasses JSON. Fresh stream telemetry bypasses high-rate JSON reads. JSON remains available as diagnostic/fallback transport and simulation fallback remains available when live telemetry is missing, stale, invalid, or errored.

## JSON Fallback Policy

`BridgeTelemetryClient.read()` remains simple. The throttle is applied at callers:

- `LiveMonitorPage._read_bridge_telemetry()` gates JSON fallback through `telemetry_json` at 5 Hz.
- `LiveAxisSampleSource.raw_axes()` gates JSON fallback at 5 Hz and reuses the last good result between allowed reads.
- Cached JSON results are aged/staleness-labeled rather than hidden.
- Embedded runtime keeps in-memory telemetry as primary and reduces threaded diagnostic JSON publishing to a default 5 Hz cadence.

External Bridge JSON publish remains compatible. It is now fallback/diagnostic from the app perspective because the stream is preferred when available.

## Stream Default Policy

`bridge_app.main` now defaults `--telemetry-stream` to true, with `--no-telemetry-stream` preserved for debugging. The stream continues to use the local-only default host `127.0.0.1`. If the port is unavailable, the stream server status reports failure and the app continues through embedded, JSON, or simulation fallback. Stream connected is not output verification and is not part of Full Live Runtime Ready.

Embedded Bridge runtime explicitly disables the socket stream by default because in-memory embedded telemetry is the preferred first-priority path inside the app.

## Live Monitor Changes

Live Monitor now has separate counters and lanes for telemetry poll, embedded read, stream read, JSON read, accepted frame, repeated-frame skip, history append, values, buttons/hats, graphs, diagnostics, and overlay sync.

Repeated bridge frames no longer append duplicate history samples and no longer force graph updates. Graph data is cached in `BoundedTelemetryHistory` and invalidated only when new samples append. Axis labels and bars dirty-update at the values lane. Button and hat chips dirty-update at their lane. Diagnostics update separately from graph/value painting.

## Effective Response Stack Changes

The legacy Effective Response Stack page now keeps a persistent `WorkspaceSignalPipeline` and a persistent `RuntimeBridge`. It no longer constructs a pipeline every timer tick or processes from `initial_state()` every heartbeat. Pipeline compute, full render, static graph rebuild, marker update, stage-card update, and selected-stage update are separated and counted.

Static graph series rebuild only when the selected axis/workspace/settings signature changes. Marker updates can run without static-series rebuilds. Stage cards keep signatures, dirty-update labels/bars/chips, and avoid repolish when tone/text did not change. Frozen mode and Copy Snapshot behavior are preserved.

## Tuning Page Changes

Base Tuning, Filtering, and Combat Profile now use the shared live scheduler. Their timers remain lightweight, but source reads are limited to the `tuning_live_marker` lane at 30 Hz. Snapshot text is lower frequency. Static graph series rebuild on selected-axis or setting changes, not timer ticks. Axis buttons only repolish when active state changes.

## Overlay Changes

The default overlay FPS cap is now 30, while the existing allowed range still accepts high caps such as 144 when explicitly configured. Overlay setters now mark the renderer dirty instead of requesting duplicate immediate paints. The overlay timer skips repaint when no data/runtime truth changed. `OverlayTelemetryBuffer` uses a bounded deque and cached sample tuple. `OverlayTraceBuilderCache` avoids rebuilding trace sets for repeated identical samples/config.

## Liquid Analysis Changes

`AnalysisCommandModel.signature` no longer includes continuously changing freshness age text. `AnalysisCommandPage` keeps a cached workspace pipeline, tracks data signatures separately from freshness display, and skips full model/render rebuilds when only timestamp/age changes. The Liquid Live Monitor no longer appends duplicate history from telemetry updates for the same data. Numeric values update in place instead of rebuilding the numeric panel on each sample.

## Shell Dirty-Gating Changes

Classic `HelmForgeShell` and the Liquid shell now keep the latest telemetry but update header/sidebar/footer or top/footer chrome only when the runtime/chrome signature changes or the `shell_chrome` cadence lane is due. Runtime truth changes update immediately. Active pages still receive runtime status or telemetry sync through their existing page-specific methods.

## Graph Optimization Changes

`GraphPreview` now caches pens, reuses `PlotDataItem`s, avoids `setData()` when the series is unchanged, supports marker-only updates, and exposes counters for series updates, marker updates, item creation, and stale removals. `BoundedTelemetryHistory` caches raw/final point tuples until a sample append invalidates them.

## Diagnostics Changes

`DiagnosticsCollector` now stores timing lanes in bounded series and exposes jank buckets:

- `over_16ms`
- `over_33ms`
- `over_50ms`
- `over_100ms`
- `over_250ms`

It keeps compatibility names such as `heartbeat`, `graph`, and `page_switch`, and adds lane names for telemetry, JSON, stream, embedded, values, graph, diagnostics, overlay, effective stack, stage-card, and shell-chrome timing. `UiStallMonitor` still tracks catastrophic 250 ms stalls but also records smaller frame-gap jank buckets.

## Bridge Duplicate Pipeline Review

`BridgeService._telemetry_from_runtime()` now reuses `RuntimeFrame.pipeline.rule_status_counts` for the rule summary instead of running the workspace pipeline a second time. Runtime orchestrator reconstruction is signature-gated through `_ensure_runtime_orchestrator()`. Rebuilds are counted and labeled; unchanged simulated ticks keep the existing orchestrator. Output loop behavior and runtime truth gates are preserved.

## Tests Added

- `tests/test_post_rc_perf_1a_live_ui_scheduler.py`
- `tests/test_post_rc_perf_1a_live_monitor_cadence.py`
- `tests/test_post_rc_perf_1a_effective_stack_cadence.py`
- `tests/test_post_rc_perf_1a_graph_preview_efficiency.py`
- `tests/test_post_rc_perf_1a_tuning_page_cadence.py`
- `tests/test_post_rc_perf_1a_overlay_cadence.py`
- `tests/test_post_rc_perf_1a_shell_telemetry_dirty_gating.py`
- `tests/test_post_rc_perf_1a_liquid_analysis_cadence.py`
- `tests/test_post_rc_perf_1a_bridge_tick_efficiency.py`

The focused suite verifies cadence gates, JSON throttling, embedded/stream source priority, repeated-frame history dedupe, graph cadence, persistent Effective Stack pipeline use, stage-card dirty updates, GraphPreview pen/item caching, tuning source-read throttles, overlay dirty paints, shell chrome dirty-gating, Liquid freshness/data separation, bounded diagnostics, and Bridge single pipeline processing per tick.

## Runtime Truth Preservation

PERF 1A does not weaken Full Live Runtime Ready. Stream connected is not output verification. Physical input is not output proof. JSON freshness is not output proof. vJoy detected is not output proof. Output intent remains separate from output writes. Simulation fallback and JSON fallback are preserved. No hardware/vJoy authority, output verification shortcut, Bridge lifecycle ownership, recorder runtime, game injection, or graphics hook was added.

## Known Remaining Risks

- Some deep page widgets may still have local repaint costs not visible in offscreen tests.
- External Bridge JSON writes remain compatible and can still be frequent in standalone runs, though the app now treats JSON as fallback/diagnostic transport.
- The Liquid Analysis pipeline model is reduced and cached, but further PERF 1B work could make stage-detail widgets even more granular.
- A real desktop performance trace should still be captured on the problem machine after merge to confirm subjective smoothness under actual hardware telemetry.

## Recommended PERF 1B Follow-Up

PERF 1B should run a live desktop profiling pass with embedded telemetry, external stream telemetry, and JSON fallback-only scenarios. It should focus on any remaining high-cost paint paths inside individual Qt widgets, especially dense Liquid detail panels and any native style recalculation that is not captured by current counters.
