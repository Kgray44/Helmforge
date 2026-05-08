# Post-RC 2C Mapping Diagram Editing / Advanced Interaction Report

## Summary

Post-RC 2C promotes the Mapping HOTAS diagram from inspection-only selection into a safe workspace draft editor. The diagram still does not gain runtime authority: edits are config intent only, output intent is not output write proof, and Save Workspace remains the explicit persistence action.

## edit workflow implemented

1. Click or focus a routed HOTAS diagram marker.
2. Review the selected route in Route Inspector.
3. Press Change Mapping.
4. Edit the selected workspace draft route in the inline route editor.
5. Review the workspace/config conflict preview.
6. Choose Apply to Draft, Cancel, or Revert Route.

The inspector now distinguishes Inspecting workspace route from Editing workspace draft. The editor repeats the truth wording: Output intent only - not live output proof, and Save Workspace required to persist changes.

## supported editable route types

- Axis routes: physical/raw axis display, raw axis channel, logical output, output intent axis, and invert.
- Button routes: physical button display and output virtual button intent.
- Hat routes: physical hat display, output POV intent, and existing directional button intent fields.

All editor dropdowns reuse existing Mapping metadata ids and option sets where available.

## deferred route types

Unsupported route shapes remain read-only/deferred. The phase does not invent new output types, new hat schemas, physical bind capture, or runtime output behaviors.

## conflict preview behavior

The route editor previews conservative workspace/config conflicts before apply. It reuses the existing warning model for duplicate exclusive output intent targets, missing output targets, unsupported route shape, invalid route shape, unmapped important controls, and targets already used by another control.

Warnings are intentionally labeled as workspace/config warnings or conflict previews. They do not claim live runtime failure, hardware failure, vJoy write failure, or Full Live Runtime Ready state.

## Visual warning behavior

Affected diagram markers receive a warning badge-style text prefix and warning ring property. Table rows receive warning metadata/tooltips where practical. The Route Inspector and route editor conflict preview summarize selected-route warnings without implying hardware failure.

## filter chip behavior

The HOTAS diagram area now includes compact route filter chips:

- All
- Axes
- Buttons
- Hats
- Mapped
- Unmapped
- Warnings
- Selected Profile

Filters only change visual focus on diagram markers and table rows. They do not mutate mappings or persistence state.

## keyboard/accessibility

Diagram markers are focusable. Focus updates the Route Inspector, Enter/Space reselects the focused marker, and arrow keys move focus between markers. A visible focus ring is styled through the app theme.

## Files changed

- `v3_app/pages/mapping_page.py`
- `v3_app/services/hotas_diagram_model.py`
- `v3_app/widgets/hotas_diagram.py`
- `v3_app/theme/qss.py`
- `tests/test_post_rc_2c_mapping_diagram_editing.py`
- `docs/HelmForge/post-rc-2c-mapping-diagram-editing-report.md`

## Tests run

Focused 2C red/green validation:

- `python -m pytest tests/test_post_rc_2c_mapping_diagram_editing.py -q`

Final validation commands are recorded in the final response for the implementation pass.

## runtime truth preservation

- No runtime authority was added.
- No hardware polling was added; no hardware polling behavior exists in this phase.
- No live input capture or physical press-to-bind behavior was added.
- No vJoy writes were added; no vJoy writes occur from Mapping edits.
- No output verification logic was changed.
- Full Live Runtime Ready gates were not changed.
- Bridge auto-launch/control/service/tray/autostart behavior was not added.
- Recorder capture/encoding, game injection, graphics API hooking, cloud AI/LLM behavior, and auto-save were not added.
- Mapping edits are workspace/config draft changes only.
- Output intent is not output write proof.
- vJoy detected is not output verification.
- Physical input alone is not Full Live Runtime Ready.
- Simulation/fallback views remain clearly labeled.
- Save Workspace remains the explicit persistence action.
