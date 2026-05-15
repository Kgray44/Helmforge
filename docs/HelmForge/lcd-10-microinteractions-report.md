# LCD-10 Microinteractions

## Summary

LCD-10 adds a safe microinteraction layer for the Liquid Command Deck. The system is property- and QSS-driven for buttons, cards, status chips, status lights, save/draft state, and keyboard focus. It does not recompose runtime behavior and does not expand telemetry polling.

Coverage keywords: motion intensity model; button interaction changes; card/focus interaction changes; status chip/light; save/unsaved emphasis; accessibility/focus; performance safety; deferred to LCD-11; deferred to LCD-12; runtime truth preservation; packaged smoke.

## Motion Intensity Model

The motion intensity model lives in `v3_app/liquid/motion.py`.

- OFF: no optional animation, no pulses, no active hover animation hooks; status remains readable through static text and color.
- REDUCED: hover/focus styling remains available, optional pulses and animation are disabled.
- STANDARD: default motion behavior; safe button/card/chip/status-light microinteraction hooks are enabled.
- CINEMATIC: exists as a future mode only. It currently behaves like STANDARD for safe hooks and does not enable large or LCD-12 effects.

Default motion behavior is STANDARD. A future settings UI can attach to the internal environment/config seam without changing page composition.

## Button Interaction Changes

Liquid buttons now expose centralized tone and interaction properties:

- primary: staged draft, validation, and Helm open/apply style actions
- secondary: navigation, copy, and local display toggles
- caution: revert/reset style actions
- disabled: muted, non-interactive, with disabled reasons preserved
- checked/selected: stable rim/highlight through QSS

Hover, press, checked, disabled, focus, caution, and draft-disabled states are implemented through stable style properties. No button geometry is animated.

## Card/Focus Interaction Changes

Interactive or focusable cards now get consistent hooks for hover and keyboard focus. This includes readiness gates, route flow rows, stage cards, support topic cards, recorder action/artifact cards, Helm finding/change cards, and draft parameter rows when safely identifiable.

Non-diagnostic focus rings remain visible with motion OFF. Raw diagnostic panels are marked as raw diagnostic surfaces and do not receive pulse behavior.

## Status Chip/Light Behavior

Status chip/light emphasis follows the existing color meanings:

- green = ready, verified, saved, safe
- amber = attention, waiting, blocked, unsaved, missing proof
- red = hard error, unsafe, failed
- cyan/blue = information, simulation, live-neutral

Small status lights expose pulse hooks in STANDARD/CINEMATIC and stay static in OFF/REDUCED. Pulses are limited to tiny indicators; large panels do not pulse.

## Save/Unsaved Emphasis

Unsaved workspace state marks the save chip and footer strip with draft amber emphasis. The disabled footer Save placeholder can show draft emphasis while remaining disabled and truthful. Saved state returns the chip and footer to the calm green/saved state.

No auto-save was added. Save/apply semantics are unchanged.

## Accessibility/Focus Notes

Keyboard focus hooks were added or strengthened for dock buttons, subpage selectors, action buttons, axis pills, mapping markers, readiness/status cards, support topic cards, and representative selectable cards. Focus styling is static and remains available when motion is OFF.

## Performance Safety

LCD-10 uses QSS pseudo-states and dirty property changes. It does not add a high-frequency app-wide timer, does not add per-card timers, does not animate layout geometry, and does not rebuild graph/model surfaces on visual ticks. The LCD-9 Live Monitor lane remains visual-only and cached-data based.

## Deferred to LCD-11

The following are deferred to LCD-11:

- page transitions
- live data easing expansion
- route trace animation
- broader live motion beyond the existing LCD-9 visual-only lane

## Deferred to LCD-12

The following are deferred to LCD-12:

- radial command wheel
- atmosphere/background drift
- larger cinematic effects
- broader reduced-motion settings UI polish

## Runtime Truth Preservation

LCD-10 added no runtime authority. It does not start or stop Bridge, does not change hardware polling, does not change vJoy/output behavior, does not change output verification, does not change Full Live Runtime Ready logic, does not change recorder capture/encoding, does not add cloud AI/LLM behavior, and does not add auto-save.

Explicit boundary statements:

- no page transitions added
- no radial command wheel added
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

## Packaged Smoke

Packaged smoke was not rerun during initial LCD-10 implementation. If packaging is rebuilt after these UI/theme changes, rerun `packaging/build_release.ps1 -Clean` and `packaging/dist/HelmForge/HelmForge.exe --smoke-exit-ms 250`.
