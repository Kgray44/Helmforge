# LCD-4F Interactive Startup Freeze Triage and Fix

## Freeze Symptoms

LCD-4 added the real Liquid Preflight Command Page and the short construction/smoke checks passed, but normal interactive Liquid launch could freeze or become effectively unresponsive after the embedded runtime began publishing live telemetry.

## Suspected Root Cause

The first suspicion was an LCD-4 startup/update loop: route hosting, page construction, or Preflight readiness rendering might be doing too much work during the real Qt event loop even though construction-only tests passed.

## Actual Root Cause Found

`LiquidCommandShell.apply_bridge_telemetry()` updated the Preflight page on every embedded bridge telemetry frame, even when the current route was not Preflight. LCD-4's Preflight update rebuilt the full page composition each time: hero, readiness gates, checklist, system details, status rail, and advanced diagnostics.

A deterministic probe reproduced the problem without live hardware: 60 telemetry callbacks while the visible route remained Mapping caused 60 extra hidden Preflight rebuilds and took about 1.1 seconds on the UI thread. The embedded runtime publishes at the existing 16 ms live refresh interval, so this churn can saturate the interactive event loop.

## Files Changed

- `v3_app/liquid/app_shell.py`
- `v3_app/liquid/pages/preflight_command_page.py`
- `tests/test_lcd_4f_interactive_startup_freeze.py`
- `docs/HelmForge/lcd-4f-interactive-freeze-triage-report.md`

## Fix Applied

Liquid now treats Preflight telemetry as a passive latest snapshot:

- Hidden Preflight pages are not rebuilt on every telemetry frame.
- The latest bridge telemetry snapshot is cached without changing runtime authority.
- When the user activates `preflight.command_readiness`, the page synchronizes from the latest passive snapshot.
- The Preflight page keeps a semantic render signature and skips rebuilds when equivalent readiness truth arrives repeatedly.
- Route switching is guarded so selecting the already-current route does not call `setCurrentWidget()` again.
- LCD4F trace markers are available behind `HELMFORGE_LCD4F_TRACE=1`.

## Why Smokes Missed It

The existing smoke tests primarily proved construction and a very short event-loop lifetime. They did not keep the Liquid shell alive long enough with repeated telemetry frames to expose the hidden Preflight rebuild loop.

## Regression Test Added

`tests/test_lcd_4f_interactive_startup_freeze.py` covers:

- Hidden Preflight does not rebuild during telemetry bursts.
- Active Preflight coalesces equivalent telemetry frames.
- The event loop remains responsive with Preflight active.
- Preflight construction continues to use passive sources only.

## Runtime Truth Preservation

LCD-4F does not change runtime authority. It does not alter hardware polling, vJoy writes, output verification logic, Full Live Runtime Ready logic, Bridge lifecycle ownership, Bridge auto-start/stop behavior, telemetry proof rules, workspace apply/save semantics, simulation fallback truth, or recorder/capture behavior.

The Preflight page still reflects the same `AppState`, `RuntimePreflightStatus`, and passive `BridgeTelemetrySnapshot` truth surfaces used by LCD-4. Coalescing skips only semantically identical UI rebuilds.

## Scope Boundaries Preserved

- No Mapping page was rebuilt.
- No Tuning page was rebuilt.
- No Analysis or Live Monitor page was rebuilt.
- No Recorder, Helm, Support, or Diagnostics page was rebuilt.
- No radial menu behavior was added.
- No animations were added.
- No page transitions were added.
- No real blur or distortion was added.
- No hardware polling behavior was changed.
- No vJoy/output behavior was changed.
- No output verification behavior was changed.
- No Bridge lifecycle management was added.
- No recorder capture/encoding was added.
- No cloud AI/LLM behavior was added.
- No auto-save was added.

## Deferred

Higher-frequency live refresh, in-place label patching, richer Preflight actions, Bridge lifecycle UI controls, output verification changes, and later Liquid page rebuilds remain deferred to their own LCD phases.
