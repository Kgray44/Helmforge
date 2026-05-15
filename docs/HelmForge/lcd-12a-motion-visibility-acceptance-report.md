# LCD-12A Motion Visibility Acceptance Report

## Summary

LCD-12A makes the existing Liquid motion intensity system visible in the running desktop app. It is a corrective patch, not a new design phase: it connects the existing `MotionSettings` policy to live shell controls, visible passive atmosphere, status breathing, page transition overlay, route sweep, quick-switch wheel animation, and a Motion Proof panel.

## Diagnosis

Motion was mostly invisible because the earlier LCD-10/LCD-11/LCD-12 work established policy objects, QSS properties, and metadata without enough paint or timer paths attached to visible widgets. Cinematic existed as a mode, but it was either future-facing, static-only, or identical to Standard for several surfaces.

Specific root causes:

- Cinematic was read as a policy value, but no visible Motion control updated the live shell policy.
- LCD-12 atmosphere used `AtmosphereSpec` and QSS properties only; no passive painted layer or advancing phase existed.
- Status chips exposed pulse properties, but only tiny status lights were registered with the old low-cadence pulse controller.
- Page route motion updated `pageMotion*` properties, but the page host swap still looked visually instant.
- The quick switch wheel exposed animation metadata but opened without an advancing visual phase.
- Route signal hooks were static properties unless another controller advanced them.
- Live Monitor visual ticks preserved cadence discipline, but without hardware the visible values could remain static.

## Motion Systems Fixed

- Added `v3_app/liquid/visible_motion.py` with testable visible-motion primitives:
  - `visible_motion_profile`
  - `LiquidAtmosphereLayer`
  - `LiquidStatusBreathController`
  - `LiquidRouteSweepController`
  - `LiquidPageTransitionOverlay`
  - `MotionProofPanel`
- Added a top command-bar Motion selector: Off, Reduced, Standard, Cinematic.
- Added live shell policy propagation through `LiquidCommandShell.set_motion_intensity`.
- Added a low-cost Cinematic atmosphere layer that paints a faint moving glow and reflection sweep.
- Added actual status breathing properties that advance over time for the top runtime/source/save chips and current-page status surfaces.
- Added a safe page transition overlay that paints a short signal sweep without animating layout geometry.
- Added route/signal sweep controller for existing `RouteFlowRow` and `SignalPipelineStage` widgets.
- Added quick switch wheel open animation phase and segment staging.
- Added Motion Proof panel under Support / Perf Diagnostics, plus shell-visible controller state.
- Added labeled Live Monitor fallback visual motion for no-hardware simulation/fallback display only. It does not append telemetry samples or alter runtime truth.

## Where To See It

- Passive animation: switch Motion to Cinematic and watch the command surface background for faint drift/reflection motion.
- Active animation: switch modes/subpages and watch the transition sweep.
- Status breathing: top runtime/source/save chips breathe in Standard/Cinematic.
- Route/signal sweep: Mapping route rows, Effective Response Stack stages, and support setup route rows sweep in Standard/Cinematic.
- Radial animation: enable/open the Quick Switch wheel; Cinematic unfolds the wheel with visible segment staging.
- Live Monitor: with no HOTAS, the page shows labeled `Simulation/Fallback visual motion only` and animates display-only meter movement without appending samples.
- Motion Proof panel: Support / Perf Diagnostics includes a Motion Proof rail that moves in Standard/Cinematic and freezes in Off/Reduced.

## Motion Mode Behavior

- Off: optional motion controllers are stopped; atmosphere, status breathing, route sweep, quick-wheel animation, proof rail, and transition overlay are disabled.
- Reduced: static/minimal emphasis only; background drift and route sweep remain disabled.
- Standard: restrained visible status breathing, page transition overlay, route sweep, quick-wheel staging, and proof/live preview motion.
- Cinematic: visibly distinct from Standard, with passive atmosphere drift plus the Standard active motion systems at stronger cadence.

## Performance Safeguards

- No `QGraphicsBlurEffect`.
- No `QGraphicsOpacityEffect`.
- No `QPropertyAnimation`.
- No layout width/height animation.
- No dynamic widget reparenting for motion.
- Atmosphere uses one lightweight painted overlay, capped at 20 FPS in Cinematic.
- Status breathing and route sweep update only shell/current-page target widgets.
- Raw diagnostics panels remain excluded from pulse/atmosphere animation.
- Live Monitor fallback motion does not append samples, rebuild models, or call `build_analysis_command_model` per visual tick.

## Runtime Truth Preservation

LCD-12A is UI presentation only. It adds no runtime authority, no hardware polling changes, no vJoy/output behavior changes, no output verification changes, no Full Live Runtime Ready shortcut, no Bridge lifecycle management, no recorder capture/encoding changes, no cloud AI/LLM behavior, and no auto-save.

Fallback motion is explicitly labeled as simulation/fallback visual motion only. It does not claim live hardware, output proof, recording support, or runtime readiness.

## Verification Status

- `python -m pytest tests/test_lcd_12a_motion_visibility_acceptance.py` - passed, 9 tests.
- `python -m pytest tests/test_lcd_12_atmosphere_radial_qa_freeze.py` - passed, 7 tests.
- `python -m pytest tests/test_lcd_11_page_transitions_live_motion.py` - passed, 8 tests.
- `python -m pytest tests/test_lcd_10_microinteractions.py` - passed, 9 tests.
- `python -m pytest tests/test_lcd_9_support_help_diagnostics.py tests/test_phase19d_final_acceptance_report.py` - passed, 12 tests.
- `python -m pytest` - passed, 932 tests.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --status` - passed; reported `truth=blocked_missing_device` and `output_verified=True`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed; no installers launched, HOTAS not connected, vJoy detected.
- `git diff --check` - passed.
- Normal-display motion QA - passed. Off and Reduced stayed still/minimal; Standard showed restrained status motion; Cinematic showed atmosphere drift, status breathing, page transition, quick switch wheel animation, Motion Proof rail motion, and Live Monitor fallback display motion without sample append or full render increase.
- Packaged build - passed with `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean`.
- Packaged smoke - passed with `.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250` while Cinematic motion and quick switch wheel environment flags were enabled.
- Physical/manual continuous HOTAS-axis movement was not performed because no physical HOTAS was connected during this patch.
