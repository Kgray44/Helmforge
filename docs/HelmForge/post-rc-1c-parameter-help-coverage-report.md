# Post-RC 1C Parameter Help Coverage Report

## Summary

Post-RC 1C expands the Post-RC 1B parameter metadata and info-icon foundation into broader coverage across the main user-facing tuning and configuration surfaces. The pass keeps the work deliberately in the UI/help/validation layer: metadata now carries clearer support scope, compact tooltip details, default/range/example values, and safer numeric validation helpers without changing any runtime path.

The goal was consistency rather than a page redesign. The UI can now attach the same parameter-help behavior to labels, dropdowns, line edits, spin boxes, and checkboxes, and missing metadata falls back gracefully instead of crashing.

## Files changed

- `v3_app/services/parameter_metadata.py`
- `v3_app/pages/page_helpers.py`
- `v3_app/pages/modes_page.py`
- `v3_app/pages/conditional_rules_page.py`
- `v3_app/pages/mapping_page.py`
- `v3_app/overlay/config_dialog.py`
- `v3_app/pages/flight_recorder_page.py`
- `tests/test_post_rc_1c_parameter_help_coverage.py`
- `docs/HelmForge/post-rc-1c-parameter-help-coverage-report.md`

## Metadata categories added

- Base Tuning: expanded support scope and precision-scale coverage.
- Filtering: numeric range and workspace-only scope coverage remains aligned with the 1B tuning foundation.
- Combat Profile: combat-specific tuning parameters keep workspace-only scope and range examples.
- Modes: precision hold, combat trigger, zoom/aim, extra buttons, and stack mode help.
- Conditional Rules: editor title, button fields, value, stage, comparator, threshold, threshold high, and measurement fields.
- Mapping: raw axis, logical output, output intent axis, invert axis, physical button/hat selectors, output button/POV selectors, and hat direction outputs.
- Live Overlay: placement, display, appearance, behavior, source/history, FPS, and app-owned runtime configuration fields.
- Flight Recorder: simulated recorder settings, destination, length, frame rate, history, capture/display/source fields, cursor, hotkey, trigger mode, and library sort.
- Perf / Diagnostics: runtime preflight dry-run help for diagnostic controls that are true parameters rather than readiness claims.

Every metadata entry now carries a support scope so tooltips can distinguish workspace-only tuning, simulated recorder configuration, app runtime configuration, and diagnostic-only controls.

## UI/helper changes

- `parameter_label()` accepts a metadata id and falls back to a plain label when metadata is missing.
- `field_row()` and `dropdown_field_row()` can apply metadata-backed tooltips, validators, dropdown options, and object properties.
- `apply_parameter_metadata()` centralizes metadata application for line edits, combo boxes, spin boxes, checkboxes, and labels.
- `format_parameter_tooltip()` includes the display name, description, range/options, default value, examples, scope, and warning notes while keeping the tooltip compact.
- `validate_numeric_text()` provides deterministic numeric validation and range clamping results for tests and future UI affordances.
- Representative Modes, Conditional Rules, Mapping, Live Overlay, and Flight Recorder controls now expose metadata-backed help markers or widget properties.

## Validation behavior

The numeric validation foundation rejects non-numeric text for numeric parameters, rejects fractional text for integer parameters, and reports above-range or below-range values with a clamped value. Integrated line-edit rows receive Qt validators where appropriate. Spin boxes use metadata-backed min/max limits when the widget type supports them.

The pass does not silently save invalid values and does not change existing workspace draft behavior.

## Tests run

Planned verification for this pass:

- `python -m pytest tests/test_post_rc_1b_parameter_metadata_info_icons.py -q`
- `python -m pytest tests/test_post_rc_1c_parameter_help_coverage.py -q`
- `python -m pytest -q`

Actual results are recorded in the final implementation summary for the turn.

## Runtime truth/non-goals

No hardware polling was added.
No Bridge lifecycle behavior was added.
No output write verification was added.
No Full Live Runtime Ready gate behavior was changed.
No cloud or network behavior was added.
No recorder capture or encoding backend was added.
No packaged app rebuild was required by this UI metadata pass.

Runtime truth remains conservative: workspace-only help does not imply real HOTAS control, output intent remains distinct from output writes, simulated recorder controls remain simulated/workspace-only, and packaged smoke is not runtime readiness.

## Known limitations

- This is not the full Help / Docs overhaul. The registry is ready to be consumed by richer documentation later.
- Some existing tables expose metadata through widget tooltips and properties rather than visible info icons in every table cell.
- Mapping still uses existing route labels and table headers; Post-RC layout passes can decide whether table header info affordances are worth adding.
- The Flight Recorder backend remains simulated metadata/export behavior only.
- Live Overlay hotkey and click-through fields remain truthful app configuration/status fields, not global OS hooks.

## Recommended next phase notes

Post-RC 1D or the next documentation-focused pass should consume the parameter registry inside Help / Docs, adding structured per-page parameter reference articles and searchable parameter entries. A later page-specific polish pass can add visible info affordances to dense tables where table-cell tooltips are not discoverable enough.
