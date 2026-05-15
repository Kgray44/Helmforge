# Post-RC PERF 1A.1 Preset Crash Hotfix and Live Monitor Cadence Balance

Date: 2026-05-12

## Scope

This hotfix stays on top of Post-RC PERF 1A. It fixes the preset-selection crash and retunes the Liquid Live Monitor visual cadence without reopening Mapping, Recorder, Help / Docs, runtime authority, hardware polling, vJoy, output verification, Bridge lifecycle, cloud, game injection, or graphics-hook work.

## Crash Cause

The reproducible crash was in the Liquid Profiles Library preset tree. Selecting a built-in preset, first reproduced with `Balanced Default`, called `TuningProfilesLibraryPage.select_profile_preset()`, which synchronously called `_render()` from inside the `QTreeWidget.itemSelectionChanged` handler.

That render replaced the inspector panel and deleted the `liquidTuningProfilesPresetTree` while Qt was still unwinding the tree selection event. In normal display mode this manifested as a brief freeze followed by a crash. In the diagnostic click sweep the failing evidence was:

`RuntimeError: libshiboken: Internal C++ object (PySide6.QtWidgets.QTreeWidget) already deleted.`

The Analysis route selector, Live Monitor route button, Effective Response Stack route button, overlay raw/final toggle, pause button, and clear-history button were clicked during the same sweep and did not reproduce the crash.

## Fix

- `TuningProfilesLibraryPage.select_profile_preset()` now updates the selected preset state immediately but queues the render with `QTimer.singleShot(0, ...)`.
- The old tree remains valid until the original selection signal returns.
- The queued render refreshes the hero, preview, actions, and selected preset properties on the next Qt event turn.
- Added `profilesLibraryRenderQueued`, `deferredPresetRenderCount`, `selectedPresetId`, and `selectedPresetName` properties for regression coverage.
- Liquid telemetry bursts no longer paint the graph once per telemetry update; changing telemetry updates the model/numeric state, while the display timer owns repeated graph paints.

## Cadence Adjustment

PERF 1A reduced the Liquid Live Monitor display timer to 100 ms. That protected responsiveness, but it made joystick motion look too sparse.

Updated cadence:

| Surface | PERF 1A | PERF 1A.1 |
| --- | ---: | ---: |
| Liquid Live Monitor display timer | 100 ms / 10 Hz | 33 ms / about 30 Hz |
| Shared Live Monitor graph lane | 18 Hz | 30 Hz |
| JSON fallback reads | 5 Hz | unchanged |
| Shell chrome | dirty-gated / 10 Hz max | unchanged |
| Diagnostics | low cadence | unchanged |
| Static graph rebuilds | dirty-only | unchanged |

The timer still appends and paints through the local visual path only; it does not reintroduce the old 60 Hz full-refresh architecture.

## Telemetry Display Mismatch

The screenshot pattern was plausible: Liquid Live Monitor graph/numeric updates could occur while status rail and hero telemetry badges still showed the previous missing-telemetry render. The hotfix adds a compact Live Monitor status signature so a full status render happens when telemetry availability/source/proof category changes, while ordinary axis-value motion continues through the lightweight numeric/graph path.

No axis data is invented. Missing/stale telemetry remains labeled as missing/stale when that is the latest snapshot truth.

## Instrumentation

Liquid Live Monitor now exposes:

- `liveMonitorDisplayTimerTickCount`
- `liveMonitorAcceptedSampleCount`
- `liveMonitorDuplicateSampleSkipCount`
- `liveMonitorGraphUpdateCount`
- `liveMonitorFullRenderCount`
- `liveMonitorDisplayIntervalMs`
- `liveMonitorGraphCadenceHz`

The Liquid shell also exposes route/sync guard counters for crash-focused tests.

## Files Changed

- `v3_app/liquid/pages/tuning_command_pages.py`
- `v3_app/liquid/pages/analysis_command_pages.py`
- `v3_app/liquid/app_shell.py`
- `v3_app/services/live_ui_scheduler.py`
- `tests/test_post_rc_perf_1a1_preset_crash_hotfix.py`
- `tests/test_post_rc_perf_1a_live_ui_scheduler.py`
- `docs/HelmForge/post-rc-perf-1a1-preset-crash-hotfix-report.md`

## Tests Added

`tests/test_post_rc_perf_1a1_preset_crash_hotfix.py` covers:

- Profiles Library preset selection does not delete the tree during its own selection signal.
- Liquid Live Monitor uses a 33-50 ms visual timer range and stays below 60 Hz.
- Live Monitor status cards refresh when fresh telemetry arrives after a missing state.
- Telemetry bursts with changing values do not repaint the Liquid graph every frame; timer-driven samples still advance the graph.
- Live Monitor overlay/pause/clear and route switching do not recurse or leave the hidden visual timer active.

## Verification Run

- `python -m pytest` -> 892 passed.
- `python -m pytest tests/test_post_rc_perf_1a1_preset_crash_hotfix.py` -> 5 passed.
- `python -m pytest tests/test_post_rc_perf_1a_live_monitor_cadence.py` -> 2 passed.
- `python -m pytest tests/test_post_rc_perf_1a_liquid_analysis_cadence.py` -> 2 passed.
- `python -m pytest tests/test_post_rc_perf_1a_shell_telemetry_dirty_gating.py` -> 1 passed.
- `python -m pytest tests/test_post_rc_perf_1a_overlay_cadence.py` -> 3 passed.
- `python -m pytest tests/test_phase19d_final_acceptance_report.py` -> 5 passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 750` -> passed.
- `python -m bridge_app.main --status` -> `lifecycle=LiveVerified truth=live_verified output_verified=True`.
- `python -m bridge_app.main --run-for-ms 250 --telemetry-stream` -> passed.
- `git diff --check` -> passed.

## Manual Display Sweep

Normal display mode was exercised from source. The reproduced crash control, `Balanced Default` in `liquidTuningProfilesPresetTree`, was selected and left active for 60 seconds with no freeze/crash. The related Analysis route controls, Live Monitor overlay/pause/clear actions, remaining profile presets, and overlay preset dropdown entries also completed without crashing.

The same sweep drove synthetic changing telemetry through Liquid Live Monitor for 3 seconds. Final counters reported a 33 ms interval with timer-owned graph updates (`ticks=115`, `samples=115`, `graphs=116` in that run).

## Runtime Truth Preservation

This hotfix does not change Full Live Runtime Ready logic or output verification semantics. Stream connection, physical input, JSON freshness, and graph motion remain passive telemetry/display facts only. Output proof still comes only from the existing runtime truth chain. Simulation fallback and JSON fallback remain available.

## Remaining Risks

- The graph is smoother at about 30 Hz, but true joystick smoothness still depends on actual telemetry frame cadence from embedded/stream transport.
- Profiles Library still rebuilds its preview after preset selection; it is now safely deferred, but a future PERF pass could update the preview in place.
- A hardware-backed visual confirmation should still be performed on the target HOTAS setup because this environment can validate synthetic telemetry but cannot physically move the joystick.
