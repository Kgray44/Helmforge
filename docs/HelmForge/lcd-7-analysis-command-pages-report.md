# LCD-7 Analysis Command Pages

## routes implemented

LCD-7 replaces these Liquid placeholder routes with real Liquid pages:

- `analysis.effective_response_stack`
- `analysis.live_monitor`

The recorder, support, help, and diagnostics routes remain deferred placeholders.

## Analysis page architecture

The implementation adds `v3_app/liquid/pages/analysis_command_pages.py` and a pure presentation model in `v3_app/liquid/models/analysis_command_model.py`.

Both Analysis pages are composed from Liquid components and static instrument widgets. They do not wrap Legacy `EffectiveResponseStackPage` or `LiveMonitorPage`.

## Effective Response Stack page behavior

`analysis.effective_response_stack` centers on a selected-axis signal pipeline:

- Raw Input
- Base Tuning
- Filtering
- Modes / Combat Profile
- Conditional Rules
- Final Output Intent

The page uses passive raw telemetry when present and the existing workspace signal pipeline for preview-derived stage values. Final Output Intent is labeled as intent, not proof.

## Live Monitor page behavior

`analysis.live_monitor` centers on passive instrument visibility:

- axis raw/final paired bars for Roll, Pitch, Throttle, Yaw, Aux 1, and Aux 2
- B1-B15 button illumination grid
- Hat / POV indicator
- telemetry freshness rail
- runtime truth and output proof chips

Unavailable button, hat, axis, stale, and missing samples stay explicitly labeled.

## analysis/live monitor presentation model structure

The model exposes:

- selected axis and selectable axis list
- runtime truth label
- telemetry label, source label, freshness label, and sample truth label
- output proof label as a separate field from final output intent
- pipeline stage records
- axis monitor records
- button monitor records
- hat/POV state
- compact metrics
- warnings
- secondary advanced details
- a stable signature used to coalesce identical render frames

## data surfaces used

LCD-7 reads only:

- `AppState`
- `WorkspaceConfig`
- `BridgeTelemetrySnapshot`
- existing `WorkspaceSignalPipeline` preview math
- existing runtime enums and telemetry dataclasses

It does not instantiate Legacy live monitor clients, physical input backends, runtime bridges, command clients, or output loops.

## passive telemetry behavior

Analysis pages update from the existing shell `apply_bridge_telemetry()` path only when the visible route is an Analysis route. Hidden Analysis pages are not synced on telemetry bursts. Identical snapshots are coalesced by model signature so the page does not rebuild repeatedly for semantically identical frames.

## stale/missing/simulation truth behavior

Telemetry is labeled as:

- `Telemetry fresh` when a passive fresh Bridge snapshot is present.
- `Telemetry stale` when the runtime frame marks stale input, telemetry proof is stale, or the frame age exceeds the freshness limit.
- `Telemetry missing` when no passive frame is available.
- `Simulation mode` when the runtime truth is simulated.

Retained stale values remain visible but are marked stale. Missing stage values are shown as unavailable and are not invented.

## pipeline stage behavior

Pipeline stages use existing workspace response math only as a preview from passive raw input. If raw input is unavailable, all stages report unavailable. The final stage is `Final Output Intent`, and output proof is shown separately.

## axis/button/hat instrument behavior

The Live Monitor page renders normalized axis bars, button chips, and hat direction chips from passive telemetry values. If a button or hat state is missing, it is labeled unavailable. No hardware polling is started.

## advanced raw details behavior

Advanced details are visually secondary and compact. They include route key, selected axis, telemetry source/freshness, runtime truth label, output proof state, runtime frame proof fields, Bridge lifecycle state if reported, active profile, active modes, rule summary, and raw/final/control counts.

## output intent differs from output proof

Final axis values are displayed as Final Output Intent. Output proof is a separate truth field sourced from existing runtime/telemetry proof. A final value or mapping/tuning preview never proves a vJoy write.

## hidden-route rebuild protection

The shell syncs Analysis pages only when `current_route_key` starts with `analysis.`. The Analysis page also skips render when the model signature is unchanged. No timer, animation, or background refresh loop is introduced.

## Legacy fallback/reference is preserved

Legacy modules remain present and unchanged. Liquid launch remains opt-in through the existing Liquid shell path, while default launch behavior remains whatever the current app configuration selects.

## limitations/deferred live motion features

Continuous live easing, animated traces, richer signal graphs, recorder surfaces, Helm surfaces, support diagnostics, radial navigation, and route transitions remain deferred to later LCD phases.

## runtime truth preservation statement

LCD-7 is a passive/read-only visualization of existing state. It does not change runtime authority, hardware polling, vJoy output behavior, output verification behavior, Bridge lifecycle ownership, recorder capture/encoding, cloud AI/LLM behavior, workspace save/apply semantics, Helm apply/revert semantics, or auto-save behavior.

## explicit deferred items

- no Recorder/Helm page was rebuilt
- no Support/Diagnostics page was rebuilt
- no radial menu behavior was added
- no animations were added
- no page transitions were added
- no live data easing was added
- no real blur/distortion was added
- no runtime authority was changed
- no hardware polling was changed
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no recorder capture/encoding was added
- no cloud AI/LLM behavior was added
- no auto-save was added
- analysis pages are passive/read-only visualizations of existing state
