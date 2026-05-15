# LCD-11 Page Transitions and Live Data Motion

## Summary

LCD-11 adds page transition approach hooks and presentation-only live data easing to the Liquid Command Deck. The work extends the LCD-10 motion intensity model instead of creating a second settings system. Motion decorates stable widgets and cached display values only; it does not change runtime source truth, sampling, Bridge lifecycle, hardware polling, output behavior, or workspace save/apply semantics.

Scope keywords: page transition approach; motion intensity behavior; live data easing primitives; stale telemetry behavior; route trace status; recorder timeline status; Helm motion status; performance safeguards; deferred to LCD-12; packaged smoke status; physical HOTAS validation status; runtime truth preservation.

## Motion intensity behavior

- OFF: immediate page switches, no live easing, no route trace, no panel settle, no optional pulses.
- REDUCED: short minimal page cue and light display smoothing only; no panel stagger, route trace, recorder sweep, or cinematic effects.
- STANDARD: page fade/slide-style route-host cue, panel settle properties, live value easing, marker easing, telemetry stale freeze/dim hooks, and simple visual route trace hooks.
- CINEMATIC: currently the same safe LCD-11 feature set as STANDARD, with cinematic effects still disabled.

## Page transition approach

The Liquid shell now uses a route-host page motion layer with deterministic route state updates. Route selection switches the `QStackedWidget` immediately, then applies short-lived `pageMotion*` properties for a cockpit-style settle cue. The implementation avoids root opacity effects, blur effects, dynamic reparenting, complex layout geometry animation, animated width/height, and blocking sleeps.

## Live data easing primitives

LCD-11 adds `EasedValue`, `EasedVectorValue`, and `LiveMotionController` primitives in the Liquid motion module. These helpers track source, target, and display values separately. Source values remain the truth. Display values may interpolate toward already-known targets, snap when motion is OFF, and freeze when telemetry is stale.

## Instruments and pages

Axis meters and raw/final paired bars now expose display and target percentage hooks. Live Monitor axis bars advance during the existing visual-only frame lane without appending samples or rebuilding models. Live time-series graphs expose in-place marker display values and stale freeze state. Button and hat instruments expose truthful active/direction state with visual motion hooks only.

Analysis / Effective Response Stack and Mapping route rows now expose route trace status hooks for STANDARD/CINEMATIC. Tuning preview instruments inherit the axis meter display hooks where values already update safely. Support diagnostics/raw panels remain static and non-flashy.

## Stale telemetry behavior

Stale telemetry stops live-style display motion. The affected Live Monitor surfaces expose `staleMotionFrozen` and readable stale state while keeping cached values visible. Easing does not hide stale warnings, delay stale detection, create artificial samples, or make fallback/simulated data look verified.

## Route trace status

Route trace is implemented as a simple visual-only signal path hook on Mapping route rows and Response Stack stages. It is disabled in OFF and REDUCED, enabled in STANDARD/CINEMATIC, and does not change remapping, output intent, output proof, or vJoy behavior.

## Recorder timeline status

Recorder timeline sweep remains deferred. Recorder pages explicitly expose `recorderTimelineSweepEnabled=False` and `recorderTimelineStatus=deferred_metadata_only`. No real capture, recording, playback, export, or encoding behavior was added.

## Helm motion status

Helm receives local draft-only motion flags for proposed change surfaces. Helm motion does not add cloud AI/LLM behavior, background analysis, unsafe auto-apply, or hidden runtime mutation.

## Performance safeguards

LCD-11 preserves the LCD-9/LCD-10 performance discipline: the Live Monitor visual lane remains visual-only, duplicate telemetry samples are not appended, graph/model rebuilds are not triggered per visual tick, diagnostics remain low cadence/on demand, shell chrome stays dirty-gated, and `build_analysis_command_model` is not called by the motion primitives. No new app-wide high-frequency timer was introduced.

## Deferred to LCD-12

The radial command wheel, background/atmosphere drift, cursor-following glare, broad cinematic effects, real blur/distortion, and parallax-style surface motion remain deferred to LCD-12.

## Packaged smoke status

Packaged smoke status: not rerun for LCD-11. The packaged output may be stale relative to these UI/theme changes until `packaging/build_release.ps1 -Clean` and the packaged executable smoke are run.

## Physical HOTAS validation status

Physical HOTAS validation status: physical/manual continuous HOTAS-axis movement was not performed.

## Runtime truth preservation

No runtime authority added. No hardware polling changes. No vJoy/output behavior changes. No output verification changes. No Bridge lifecycle management. No recorder capture/encoding changes. No cloud AI/LLM behavior. No auto-save.

Explicitly:

- no radial command wheel added
- no background/atmosphere drift added
- no real blur/distortion added
- no layout geometry animation added
- no runtime authority added
- no hardware polling changes
- no vJoy/output behavior changes
- no output verification changes
- no Bridge lifecycle management
- no recorder capture/encoding changes
- no cloud AI/LLM behavior
- no auto-save
