# LCD-5 Mapping Command Page

Required coverage: Mapping page architecture; route replaced; mapping presentation model structure; data surfaces used; HOTAS visual map approach; selected control inspector behavior; route flow behavior; metrics behavior; advanced route details behavior; truth consistency with top bar/runtime state; layout/overlap preservation statement; Legacy fallback/reference is preserved; prepares for later mapping/detail/editing phases; explicit deferred items; runtime truth preservation statement.

## mapping page architecture

LCD-5 replaces the `mapping.hotas_map` Liquid placeholder with a real Mapping Command Page in `v3_app/liquid/pages/mapping_command_page.py`. The page is a new Liquid composition, not a wrapper around the Legacy Mapping page. It uses the shared Liquid page shell, hero panel, inspector panel, detail panel, status chips, metric tiles, and route flow components.

The page answers: What is each physical control doing?

## Route replaced

The route replaced is `mapping.hotas_map`. Other Mapping routes, including `mapping.route_details` and `mapping.advanced_route_tables`, remain placeholder/future pages.

## mapping presentation model structure

`v3_app/liquid/models/mapping_command_model.py` adds a pure presentation model with:

- `controls`
- `selected_control`
- `route_flows`
- `mapping_metrics`
- `warnings`
- `advanced_route_details`
- `truth_source_notes`
- `source_label`
- `runtime_truth_label`

Each control carries physical identity, type, group, anchor position, raw channel, logical function, virtual output intent target, current passive value/state, mapped/unmapped status, warning role, and tooltip/detail text.

## data surfaces used

LCD-5 uses the existing workspace/config route surfaces through `WorkspaceConfig`, the existing workspace JSON loader when the normal Liquid app is launched without an injected test state, deterministic default workspace fixtures for tests, and the existing non-visual HOTAS diagram route model in `v3_app/services/hotas_diagram_model.py`. The app state is read only for source/runtime labels. No hardware polling, Bridge lifecycle calls, vJoy writes, or output verification probes are introduced.

## HOTAS visual map approach

The HOTAS visual map is a static Qt Liquid instrument with throttle, stick, and base regions drawn directly in the new Liquid page. It includes markers for Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2, B1-B15, and Hat / POV. Marker selection is inspector-only and route-preview-only.

## selected control inspector behavior

The selected control inspector shows physical control label, control type, physical group, raw channel, logical function, Output Intent target, passive current value/state, mapped/unmapped status, warnings, and the read-only truth note. The default selected control is Roll axis when available.

Selecting a marker updates the highlighted marker, inspector, and route flow. It does not mutate workspace mappings, stage edits, poll hardware, or write runtime state.

## route flow behavior

The route flow uses explicit intent language:

- Physical control
- Logical function
- Output Intent target

It says `Output Intent` and does not claim output proof or vJoy write proof from a mapping route.

## metrics behavior

The Mapping hero includes compact metric tiles for Axis Routes, Button Routes, Hat Routes, Unmapped Controls, Warnings, and Output Intent Targets. Metrics are derived from the mapping presentation model and reflect workspace/config route intent.

## advanced route details behavior

Advanced route details remain visually secondary. They list route key, physical control ID, raw channel, function, Output Intent target, mapped/unmapped status, and notes/warnings. This is not the full Legacy Advanced Route Tables rebuild.

## truth consistency with top bar/runtime state

The Mapping page does not contradict the top command/status bar. It displays the current runtime truth label as a label sourced from `AppState`, and the Liquid shell syncs that state to the visible Mapping page with a bounded/coalesced render signature. Mapping itself remains a read-only mapping-intent surface. The page never treats mapping intent as live output, vJoy write proof, HOTAS connection proof, or output verification proof.

## layout/overlap preservation statement

The layout keeps the visual HOTAS map as the dominant hero instrument, with selected control inspector and route flow adjacent below the hero and advanced route details secondary. The existing floating footer clearance is preserved through the Liquid shell and page scroll area.

## Legacy fallback/reference is preserved

Legacy Mapping modules remain untouched and available as fallback/reference. Liquid remains selectable through the existing Liquid launch path, and LCD-5 does not make Liquid the only UI path.

## prepares for later mapping/detail/editing phases

The presentation model and marker selection seam prepare for later route details, advanced tables, and safe draft-editing phases. LCD-5 intentionally stops at read-only visual selection and route intent explanation.

## explicit deferred items

- no Route Details page was rebuilt
- no Advanced Route Tables page was rebuilt
- no Tuning page was rebuilt
- no Analysis/Live Monitor page was rebuilt
- no Recorder/Helm page was rebuilt
- no Support/Diagnostics page was rebuilt
- no radial menu behavior was added
- no animations were added
- no page transitions were added
- no real blur/distortion was added
- no runtime authority was changed
- no hardware polling was changed
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no recorder capture/encoding was added
- no cloud AI/LLM behavior was added
- no auto-save was added

## runtime truth preservation statement

LCD-5 is presentation-only. It reads existing workspace/config and app-state labels, presents mapping intent, and keeps output proof, runtime authority, hardware polling, vJoy behavior, Bridge lifecycle ownership, recorder behavior, and save/apply semantics unchanged.
