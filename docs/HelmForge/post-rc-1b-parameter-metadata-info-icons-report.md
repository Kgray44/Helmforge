# Post-RC 1B Parameter Metadata and Info Icons Report

## metadata model overview

Post-RC 1B adds a reusable parameter-help foundation in `v3_app.services.parameter_metadata`. The model is UI-consumable but pure Python: parameter definitions include stable IDs, display names, page/category placement, value type, min/max or dropdown options, default values, examples, warning text, and related help topic references.

The shared tooltip formatter emits compact Qt-friendly help with:

- What it does
- Range or Options
- Examples
- Notes

## parameters covered

Initial metadata now covers the core requested groups:

- Base Tuning: Curve Mode, Curve Strength, Deadzone, Anti-Deadzone, Hysteresis, Output Scale, Max Output.
- Filtering: Center Alpha, Edge Alpha, Same Slew Limit, Reverse Slew Limit.
- Combat Profile: Combat Curve, Combat Scale, Combat Center Alpha, Combat Edge Alpha, Combat Same Slew, Combat Reverse Slew.
- Representative Modes, Conditional Rules, Live Overlay, and Flight Recorder settings.

Dropdown metadata is intentionally limited to currently supported options when the runtime or UI only supports one option. Future options are not presented as active behavior.

## pages integrated

The first page integration is intentionally representative rather than exhaustive:

- Base Tuning parameter labels now show info icons.
- Filtering parameter labels now show info icons.
- Combat Profile parameter labels now show info icons.
- Base Tuning Curve Mode is now a dropdown backed by metadata options.

The remaining pages already have metadata entries where practical, but their visible row-by-row rollout is deferred to avoid broad page redesign in this pass.

## info icon behavior

`v3_app.widgets.info_icon.ParameterInfoIcon` renders a compact circular `i` marker next to integrated parameter labels. Hovering or focusing exposes the shared tooltip text. The icon uses the existing dark engineering theme and keeps labels readable without creating a large layout footprint.

## validation behavior

Representative numeric fields on Base Tuning, Filtering, and Combat Profile now receive metadata-backed Qt validators. The validators reject letters and mark out-of-range values as not acceptable before the value can be treated as valid input. This preserves existing draft/workspace behavior and does not silently save invalid values.

## remaining pages still needing rollout

Post-RC 1C/4A should continue the visible rollout:

- Modes controls should move stack mode and enum-like settings to dropdowns.
- Conditional Rules should attach metadata icons to editor rows and apply numeric validators to value and threshold fields.
- Live Overlay and Flight Recorder dialogs/pages should use metadata labels beside spin boxes, checkboxes, and dropdowns.
- Mapping route fields should receive metadata help during the later HOTAS diagram/mapping passes.
- Help / Docs should consume the registry during the full structured docs overhaul.

## runtime truth preservation

This pass does not change runtime proof gates, Bridge telemetry, physical input sampling, output verification, output loop behavior, Flight Recorder capture state, Live Overlay runtime behavior, Helm apply/revert behavior, or packaged runtime truth. Parameter help and validation are UI foundation only, with no runtime behavior or unsupported runtime activation added.

## Recommendation for Post-RC 1C

Use the new registry as the source of truth for a deeper Help / Docs overhaul. The next pass should create structured articles that can reference parameter metadata, add page navigation links, and keep all runtime authority claims conservative.
