# HelmForge Post-RC 2B Mapping Diagram Interaction Report

## Summary

Post-RC 2B makes the Mapping page HOTAS diagram operable instead of decorative. Diagram markers, route tables, selected-route state, route inspector details, and workspace/config warnings now share the same read-only selection model.

## Files changed

- `v3_app/services/hotas_diagram_model.py`
- `v3_app/widgets/hotas_diagram.py`
- `v3_app/pages/mapping_page.py`
- `v3_app/theme/qss.py`
- `tests/test_post_rc_2b_mapping_diagram_interaction.py`
- `docs/HelmForge/post-rc-2b-mapping-diagram-interaction-report.md`

## Selection model

Each routed diagram control now carries a route type, related table object name, and table row when the workspace route is editable in the current Mapping UI. The shared selection model maps controls such as `axis_pitch`, `button_b5`, and `hat_pov` to their axis, button, or hat table row.

Selecting a Mapping table row updates the diagram marker. Clicking a diagram marker updates the related table row. Selection is stateful and visually highlighted on the diagram.

## Inspector behavior

The Route Inspector panel shows:

- selected physical input;
- mapped virtual output intent;
- route type;
- active profile context;
- source of truth;
- whether the route is editable in the Mapping table;
- conflict/warning status;
- no-live-output-verification notice.

The inspector describes workspace/config routes with simulation/fallback display values unless existing telemetry proves otherwise. It does not claim live hardware control.

## Conflict/warning logic

Warnings are conservative and workspace/config only. The detector covers:

- duplicate exclusive output intent targets;
- missing output targets;
- unmapped important controls;
- invalid route shapes;
- unsupported diagram route names.

Warnings do not infer device failures or live runtime problems.

## Truthfulness constraints

No hardware polling was added. No live input capture was added. No Bridge lifecycle, service, tray, autostart, launch, stop, or restart behavior was added. No output write verification was added. Full Live Runtime Ready gates were not changed.

The Mapping diagram remains a workspace/config and simulated/fallback diagnostic view. Output intent does not prove live output. vJoy detection is not output verification. Physical input alone is not Full Live Runtime Ready.

## Tests run

Planned verification:

- `python -m pytest tests/test_post_rc_2a_mapping_hotas_diagram.py -q`
- `python -m pytest tests/test_post_rc_2b_mapping_diagram_interaction.py -q`
- `python -m pytest -q`

Final command results are reported in the completion summary.

## Known limitations

The diagram supports selection and inspection only. It does not implement drag-to-remap, click-to-edit route forms, live route capture, or graphical conflict overlays. Warnings are intentionally conservative and do not attempt to diagnose real device state.

## Recommended next phase notes

A later phase can add a richer diagram edit workflow, keyboard navigation for diagram markers, and optional route-filter chips. Any future live behavior should remain gated by existing runtime proof surfaces and must not treat workspace intent as output write proof.
