# Phase 9 Live Monitor Page Report

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Date: 2026-05-06

## Scope

Phase 9 replaced the Live Monitor placeholder with a screenshot-guided diagnostic page. The page visualizes simulation/runtime snapshots for raw axes, processed final axes, buttons, hats, axis levels, and recent trace graphs.

This phase did not add real HOTAS polling, real vJoy writes, driver installation, installer launching, output verification, Bridge service behavior, Flight Recorder internals, or Live Overlay internals.

## Screenshots Inspected

- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/09 Live Monitor/v2-live-monitor_final-raw-input-trace-graph.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/09 Live Monitor/v2-live-monitor_final-raw-vs-final-overlay-graph-view.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/09 Live Monitor/v2-live-monitor_final-axis-levels-hotas-buttons-output-buttons.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/09 Live Monitor/v2-live-monitor_live-overlay-card-active-raw-input-trace.png`
- `HOTAS Control Panel Forensic Spec Set/07-flight-recorder-live-monitor-and-live-overlay.md`

## Screenshot Fidelity Notes

Matched:

- Recovered page title `Live Monitor`.
- Recovered page copy about raw HOTAS input, final vJoy output, buttons, hats, and axis levels.
- Monitor Controls card with axis selector and `Show raw and output together`.
- Raw Input Trace graph title/copy/note.
- Raw vs Final Overlay graph title/copy/caption.
- Live State and Buttons / Hats cards.
- Axis Levels card with raw and final values for all six recovered axes.
- HOTAS Buttons B1-B15.
- Mapped Output Buttons Out1-Out20.
- Dark premium control-console visual language inherited from the Phase 4 shell.

Intentional deviations:

- Runtime pills do not say `Live`; they show the current runtime truth such as `Detected Unverified` or `Blocked Missing Device`.
- Axis levels use compact paired horizontal bars rather than the exact recovered vertical gauge treatment. This keeps the Phase 9 implementation simple and testable while preserving the raw/final comparison meaning.
- Button pills are display/status labels, not real hardware state claims.
- The recovered Live Overlay card remains deferred because Phase 9 is scoped to Live Monitor internals.

Remaining visual gaps:

- The exact recovered vertical axis gauge rendering can be refined later.
- The Live Overlay card/dialog belongs to a later overlay phase.
- Graph legend/axis polish can be improved after the Bridge telemetry cadence is real.

## Implementation Decisions

- `v3_app/pages/live_monitor_page.py` owns only PySide6 visualization.
- `v3_app/pages/live_monitor_data.py` provides bounded history, clamping, runtime snapshot conversion, and a Bridge telemetry snapshot adapter.
- Live Monitor data currently comes from `SimulatedRuntime`, which already uses the shared-core Phase 3 pipeline for final axis values.
- The page is telemetry-shaped through the Phase 2B `BridgeTelemetrySnapshot` contract so a future Bridge feed can replace the simulation source without moving real-time processing into UI code.
- The UI refresh timer updates graphs, labels, bars, and chips in place. It does not rebuild the page/cards on every tick.
- Hidden pages skip timer refresh through `should_skip_timer_refresh()`.

## Graph Behavior

- Raw Input Trace shows recent raw values for the selected axis.
- Raw vs Final Overlay shows final values and, when enabled, raw values overlaid.
- Both graphs use bounded sample history with newest samples on the right edge.
- The graph widgets are reused; only the plotted series are refreshed.

## Runtime Truth

Runtime truth observed before Phase 9 implementation:

- Thrustmaster driver/software: detected
- HOTAS: detected during the precheck
- vJoy: detected
- Runtime truth: `detected_unverified`
- Output writes verified: `false`

The Phase 9 page displays current runtime truth and explicitly reports that output writes are not verified. It does not claim Full Live Runtime Ready.

## Deferred

- Real Bridge telemetry subscription.
- Real HOTAS polling.
- Real vJoy writes.
- Output verification.
- Flight Recorder pages and capture buffers.
- Live Overlay configuration and desktop overlay behavior.
- Exact recovered vertical axis-gauge rendering.

## Verification

Commands run during the phase:

```powershell
git status --short
git remote -v
python -m pytest
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
```

Focused Phase 9 tests passed:

```text
10 passed
```

Full regression suite passed after implementation:

```text
121 passed
```
