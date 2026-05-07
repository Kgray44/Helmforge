# Phase 12B - Detached Live Overlay Window and Renderer

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Detached Live Overlay window and renderer only

## Summary

Phase 12B implements the detached Live Overlay window and renderer on top of the Phase 12A overlay core. The overlay is app-owned, Qt-rendered, and driven by telemetry samples already available to the UI.

Phase 12B does not add runtime authority. It does not poll real HOTAS hardware, stream physical input, write vJoy, verify output, launch or manage the Bridge, inject into games, hook graphics APIs, capture the screen, implement Flight Recorder, register a global hotkey, or enable click-through behavior.

Phase 12C later finalizes the Live Overlay boundary by tightening copy, close-state status updates, Help / Docs wording, and final guard tests. Phase 12B remains the detached-renderer implementation phase.

## Implemented

New modules:

- `v3_app/overlay/overlay_renderer.py`
- `v3_app/overlay/live_overlay_window.py`

Updated surfaces:

- Live Monitor Live Overlay card
- Live Overlay Configuration dialog integration
- README and Bridge/UI architecture documentation
- Help / Docs Graphs and Previews article
- Phase 12A report stale deferral wording

## Detached Overlay Window

`LiveOverlayWindow` is a separate top-level Qt widget. It is frameless, uses translucent-window support, and applies `WindowStaysOnTopHint` when the overlay config requests always-on-top.

Default placement is the bottom strip on the current display when Qt exposes screen geometry. If screen geometry is unavailable, the window falls back to a safe default size.

The overlay window:

- can be shown and hidden without blocking the main UI;
- stops its refresh timer when hidden or closed;
- does not require a physical HOTAS;
- does not require vJoy;
- does not require the Bridge to be running.

## Renderer

`OverlayRenderer` consumes Phase 12A trace data from `build_overlay_traces`.

It renders:

- axis trace lines;
- recovered axis colors;
- optional legend;
- optional live values;
- a subtle dark background;
- idle/runtime truth text when no samples are available.

The idle state says the overlay is waiting for telemetry samples and repeats conservative truth:

- Runtime truth: `blocked_missing_device`
- Output verified: `false`
- Full Live Runtime Ready: `false`

The renderer does not expose raw debug object dumps.

## Live Monitor Integration

The Live Overlay card now has truthful Show/Hide behavior:

- Show Overlay creates/shows the detached overlay window.
- Hide Overlay hides the detached overlay window.
- Status is `Active` only when the detached overlay window is actually visible.
- Status returns to `Inactive` when hidden.
- Summary remains `Custom | Bottom strip | 66% opacity | Final output` with default config.

Configuration dialog OK updates the active overlay config and visible overlay window. Cancel discards edits. Restore Defaults resets the dialog draft until OK is pressed.

Phase 12C adds the final close-notification polish so closing the detached overlay window directly also updates the Live Monitor card to `Inactive`.

## Hotkey, Click-Through, And Always-On-Top Truth

- Hotkey text remains `Ctrl+Shift+F9`.
- Hotkey status remains `Not registered`.
- Click-through status remains `Not enabled - not verified`.
- Always-on-top is applied through Qt window flags when configured.

No global hotkey registration or click-through platform behavior was added.

## Runtime Boundary

Phase 12B preserves the Phase 9K runtime boundary:

- Telemetry remains the truth surface.
- Command files are requests, not success proof.
- Process presence is a hint only.
- HOTAS discovery is discovery-only.
- vJoy detected does not mean output verified.
- `output_verified` remains `false`.
- Full Live Runtime Ready remains `false`.

The overlay can render simulation/final-output telemetry already available to the UI, but it does not create live hardware runtime.

## Current Runtime Truth

Observed conservative runtime truth during verification:

- Bridge lifecycle: `Simulated`
- Runtime truth: `blocked_missing_device`
- HOTAS status: HOTAS Not Connected
- vJoy status: vJoy Detected
- vJoy detected, output writes unverified
- `output_verified`: `false`
- Full Live Runtime Ready: `false`

## Verification

Final verification results:

- `python -m pytest` - passed, 260 tests.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - passed, 7 tests.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11a_help_docs_foundation.py` - passed, 8 tests.
- `python -m pytest tests\test_phase11b_perf_diagnostics_page.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - passed, 6 tests.
- `python -m pytest tests\test_phase12a_live_overlay_foundation.py` - passed, 6 tests.
- `python -m pytest tests\test_phase12b_live_overlay_window_renderer.py` - passed, 6 tests.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed with `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed. Thrustmaster software detected, vJoy detected, HOTAS Not Connected, Simulation Mode Active unless physical input and output writes are both verified, Full Live Runtime Ready false, and no installers launched.
- `git diff --check` - passed.

## Deferred

Deferred to later reviewed phases:

- Flight Recorder;
- global hotkey registration;
- click-through implementation;
- game/window attachment beyond current display placement;
- real HOTAS polling;
- live physical input streaming;
- vJoy writes;
- output verification;
- automatic Bridge launch or lifecycle management;
- game injection or graphics API hooking;
- screen capture;
- runtime activation.
