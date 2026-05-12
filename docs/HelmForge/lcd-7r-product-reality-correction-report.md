# LCD-7R Product Reality Correction

LCD-7R was needed because several real Liquid pages had become too passive: useful as visual dashboards, but not yet credible command surfaces for tuning/control software. This corrective pass keeps runtime authority unchanged while adding safe page actions, clearer editing routes, stronger graph instruments, and a real live-monitor concept.

## Mapping editing fixes

Mapping / HOTAS Map now keeps marker clicks as selection actions: selecting a marker updates the selected control inspector and route flow without navigating or scrolling as the only behavior. The page now exposes Edit selected route, Open Route Details, Open Advanced Route Tables, Copy selected route, Copy mapping summary, and a disabled Reset selected route action with an explicit reason.

Mapping / Route Details and Mapping / Advanced Route Tables remain the real editing surfaces. Supported edits stage workspace/draft mapping changes through the existing mapping edit model. Invalid edits are rejected. Output Intent remains route intent, not output proof.

## Mapping route stability fixes

Mapping route switching remains cached through the existing route host. The route host avoids same-route churn, pages stay mounted, and repeated switching across `mapping.hotas_map`, `mapping.route_details`, and `mapping.advanced_route_tables` is bounded and stable.

An interactive follow-up found that `mapping.advanced_route_tables` could still freeze in the normal visible Liquid launch when embedded telemetry was active. The root cause was not route construction; the page switched quickly offscreen and remained responsive when the embedded runtime was suppressed. The issue was telemetry-triggered page rebuilding: Advanced Route Tables rebuilt the full grouped editor on every runtime telemetry frame even though the mapping route table had not changed. LCD-7R now gives Mapping edit pages a semantic render signature so telemetry-only updates refresh shell truth without re-rendering unchanged Mapping edit surfaces. The visible Advanced Route Tables launch stayed responsive for 8 seconds after the fix with `render_count=1`.

## visual map selection behavior fix

HOTAS marker clicks select controls only. The selected control then drives the inspector, route flow, and edit/navigation buttons. Editing still happens only in the dedicated Mapping edit routes.

## Preflight action buttons added

Preflight now includes safe command actions: Open Setup / Runtime Check, Open Help / Docs, Open Mapping / HOTAS Map, Copy preflight status, and Copy setup checklist. The Simulation Mode control is disabled because LCD-7R does not add a safe runtime mode toggle.

## square glyph replacement

Shared `StatusLight` markers now identify as a non-interactive status dot instead of a checkbox-looking square. Checkbox-like UI remains reserved for real toggle controls.

## Base Tuning graph behavior

Base Tuning now has a prominent response graph from x=-1..1 and y=-1..1 with a Reference line and Current tuning line. The graph is preview-only and updates when the selected axis or staged parameter values change.

## Filtering step-response graph behavior

Filtering now has a prominent step-response graph showing Input step and Filtered response. The response uses a deterministic preview model based on existing filtering parameters and is labeled as preview, not runtime proof.

## Combat Profile graph behavior

Combat Profile now shows Reference, Base tuning, and Combat profile lines on the same x=-1..1 / y=-1..1 graph. The graph distinguishes combat profile intent from live/runtime application.

## axis selection dependency update fix

Axis selection now updates the selected-axis property, graph model, live/current snapshot, guidance text, and advanced details for Base Tuning, Filtering, Combat Profile, and Conditional Rules.

## Conditional Rules system completion status

Conditional Rules is now structured as a usable rule system surface: rule status hero, enabled/disabled/warning metrics, condition -> action rows, selected rule inspector, validation/conflict panel, and disabled edit/add/enable controls explaining that rule mutation is deferred until a safe workspace rule edit seam exists.

## Effective Response Stack chain redesign

Effective Response Stack now presents a visible chain: Raw Input -> Base Tuning -> Filtering -> Modes / Combat Profile -> Conditional Rules -> Final Output Intent. Connectors make the modifier order obvious. Copy stage, copy stack, and route navigation actions open the relevant Tuning pages or Live Monitor.

## Live Monitor time-series redesign

Live Monitor now uses a bounded right-to-left local time-series history for Roll, Pitch, Throttle, Yaw, Aux 1, and Aux 2. The raw/final overlay is a UI-only toggle. Pause/resume pauses only the local visual monitor, Clear local graph history clears only the page buffer, and copy actions expose current sample and telemetry summary. The page does not poll hardware or write output.

## route/page freeze protections

The corrections preserve the LCD-4F hidden-route lesson: hidden pages are not rebuilt on telemetry bursts, unchanged Mapping edit pages ignore telemetry-only render requests, and the Live Monitor graph updates its bounded history in place when visible instead of reconstructing the whole page on every frame.

## data surfaces used

LCD-7R uses existing Liquid models, AppState, WorkspaceConfig, passive BridgeTelemetrySnapshot data, mapping edit model, tuning parameter metadata, and workspace response preview math. It does not introduce runtime authority.

## Command Actions Added

This section lists enabled actions, disabled/deferred actions, why disabled actions are not available, which actions mutate workspace draft, which actions are navigation-only, which actions are copy/export-only, and confirmation that no unsupported runtime authority was added.

Preflight enabled actions: Open Setup / Runtime Check, Open Help / Docs, Open Mapping / HOTAS Map, Copy preflight status, Copy setup checklist. Disabled/deferred actions: Simulation Mode control, disabled because no safe Liquid simulation toggle exists in this phase. Mutations: none. Navigation-only actions: setup/help/mapping. Copy/export-only actions: status and checklist copy.

Mapping / HOTAS Map enabled actions: Edit selected route, Open Route Details, Open Advanced Route Tables, Copy selected route, Copy mapping summary. Disabled/deferred actions: Reset selected route, disabled because route-level defaults are not represented as a safe workspace operation. Mutations: none on HOTAS Map. Navigation-only actions: edit/details/tables. Copy/export-only actions: selected route and summary.

Mapping / Route Details enabled actions: Stage route change, Validate route, Copy route details, Copy route table summary, Open Advanced Route Tables, Back to HOTAS Map. Disabled/deferred actions: Add route when shown, disabled because route creation is not represented in the current workspace schema. Mutations: supported stage actions mutate workspace draft only.

Mapping / Advanced Route Tables enabled actions: inline Stage route changes, Select route, Validate all routes, Copy route table summary, Revert staged route edits when shell draft ownership exists. Disabled/deferred actions: Add route, disabled because safe creation is deferred. Mutations: supported stage actions mutate workspace draft only.

Base Tuning enabled actions: Stage tuning change, Copy tuning parameters, Copy curve preview values, Open Filtering, Open Combat Profile, Revert staged tuning edits when shell draft ownership exists. Disabled/deferred actions: Reset selected axis, disabled because route-level default restore is not added in LCD-7R. Mutations: supported stage actions mutate workspace draft only.

Filtering enabled actions: Stage filtering change, Copy filtering parameters, Open Base Tuning, Open Combat Profile, Revert staged tuning edits when shell draft ownership exists. Disabled/deferred actions: Reset selected axis filtering, disabled for the same draft-default reason. Mutations: supported stage actions mutate workspace draft only.

Combat Profile enabled actions: Stage combat profile change, Copy combat profile parameters, Open Base Tuning, Open Filtering, Revert staged tuning edits when shell draft ownership exists. Disabled/deferred actions: Reset selected axis combat settings, disabled for the same draft-default reason. Mutations: supported stage actions mutate workspace draft only.

Conditional Rules enabled actions: Validate rules and Copy rule summary. Disabled/deferred actions: Add rule, Edit selected rule, Enable / disable rule; disabled because safe rule mutation is not exposed by the current Liquid workspace rule edit seam. Mutations: none.

Effective Response Stack enabled actions: Copy selected stage, Copy full response stack summary, Open Base Tuning, Open Filtering, Open Combat Profile, Open Conditional Rules, Open Live Monitor. Disabled/deferred actions: none on the shell route. Mutations: none. Navigation-only actions open Tuning/Analysis routes. Copy/export-only actions copy stage/stack text.

Live Monitor enabled actions: Toggle raw/final overlay, Pause/resume visual monitor, Clear local graph history, Copy current sample, Copy telemetry summary, Open Effective Response Stack. Disabled/deferred actions: no hardware polling/output toggles are offered. Mutations: UI-local graph buffer only; no workspace/runtime mutation.

## limitations/deferred features

LCD-7R does not add route creation, rule mutation, default-reset persistence, runtime apply, live output writes, Bridge lifecycle control, or support/diagnostics page rebuilds. Graph math remains deterministic preview math where exact runtime intermediates are not surfaced.

## runtime truth preservation statement

LCD-7R preserves runtime authority. No Recorder/Helm page was rebuilt. No Support/Diagnostics page was rebuilt. No radial menu behavior was added. No animations/page transitions/real blur were added. No hardware polling was added. No vJoy/output behavior was changed. No output verification behavior was changed. No Bridge lifecycle management was added. No cloud AI/LLM behavior was added. No auto-save was added.

Requirement trace: no Recorder/Helm page was rebuilt; no Support/Diagnostics page was rebuilt; no radial menu behavior was added; no animations/page transitions/real blur were added; no hardware polling was added; no vJoy/output behavior was changed; no output verification behavior was changed; no Bridge lifecycle management was added; no cloud AI/LLM behavior was added; no auto-save was added.
