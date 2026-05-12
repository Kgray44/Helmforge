# LCD-7U Live Stability and Interaction Fixes Report

## Why LCD-7U Was Needed

LCD-7U addresses remaining product-reality bugs after the first live-control pass. The visible failures were intermittent blank pages during passive telemetry updates, tuning graph current dots not matching displayed curves, HOTAS map marker clicks and editor close actions shifting the scroll position, and missing LCD-7U visual QA evidence.

## Blank-Page Root Causes

The primary blanking risk came from telemetry updates triggering full page slot replacement. Base Tuning, Filtering, Combat Profile, and Effective Response Stack were rebuilding large hero/detail surfaces when passive input changed. During real HOTAS movement, repeated replacement of graph and chain widgets could briefly leave the route surface empty or destroy widgets still in active use.

Route factory failures were already guarded for construction-time errors; LCD-7U kept that behavior and added/update-path guards so live sync exceptions leave the previous visible content intact.

## Telemetry Update Stability Fix

Tuning pages now distinguish structural changes from passive telemetry changes. If the selected route, axis, parameters, rules, and draft state are unchanged, telemetry updates refresh the response graph, response instrument, and live snapshot in place.

Analysis pages now update Effective Response Stack stage widgets in place rather than rebuilding the full vertical chain during telemetry bursts. Live Monitor continues to append to bounded local graph history and update the existing graph widget rather than replacing it.

Hidden live pages still cache only the latest shell telemetry state through existing AppState/shell paths; they do not rebuild on telemetry bursts.

## Base Tuning Output-Dot Fix

The Base Tuning `Output intent` marker now uses the same curve function used to draw the `Current tuning` line. It no longer uses passive final telemetry as the marker y-value, because passive final values may represent later runtime stages and do not necessarily lie on the base tuning curve.

The marker remains an Output Intent preview marker and does not imply output proof.

## Combat Profile Dot and Curve Consistency Fix

Combat Profile markers now align with their displayed lines:

- `Current input` sits on the default/reference line.
- `Base tuning current` sits on the displayed Base tuning curve.
- `Combat profile current` sits on the displayed Combat profile curve.

The combat curve preview remains monotonic for monotonic response modes.

## Mapping Scroll-To-Bottom Root Cause and Fix

The scroll jump was caused by marker selection and editor close paths rebuilding the HOTAS page while the parent `QScrollArea` was free to adjust around changed content/focus. LCD-7U now preserves the parent scroll position during marker selection, editor open, inline edit staging, shell mapping sync, and editor close.

Marker clicks select the control and open the route editor overlay without advancing to the Advanced Route Details area.

## Editor Close Scroll Fix

Closing the mapping editor now captures and restores the current scroll position synchronously. Closing the editor does not route, focus the advanced section, or scroll the page down.

## Effective Response Stack Blanking Fix

Effective Response Stack now keeps the vertical stage chain mounted during passive telemetry updates. Stage summaries, values, detail panels, and advanced details can update, but the dominant chain widget is not destroyed and recreated on every input frame.

## Live Monitor Glitching Fix

Live Monitor keeps its existing right-to-left graph widget during HOTAS movement. Incoming passive samples append to the bounded local history and update the graph in place. Button/hat panels remain visible; unavailable data remains labeled instead of producing empty boxes.

## Route Stability Protections

LCD-7U preserves these route stability behaviors:

- same-route updates do not clear the page host
- route factory exceptions show `liquidRouteErrorFallback`
- telemetry update exceptions are stored on the shell and do not blank the current route
- mapping route switching among HOTAS Map, Route Details, and Advanced Route Tables remains bounded

## Visual QA Artifacts

LCD-7U regenerated visual QA artifacts under:

- `artifacts/liquid-ui/lcd-7u/`

Required screenshot outputs:

- `01-preflight-command-readiness.png`
- `02-mapping-hotas-map.png`
- `03-mapping-route-details.png`
- `04-mapping-advanced-route-tables.png`
- `05-tuning-base-tuning.png`
- `06-tuning-filtering.png`
- `07-tuning-combat-profile.png`
- `08-tuning-conditional-rules.png`
- `09-tuning-profiles-library.png`
- `10-analysis-effective-response-stack.png`
- `11-analysis-live-monitor.png`
- `mapping-editor-overlay-open.png`

PDF visual report path:

- `artifacts/liquid-ui/lcd-7u/liquid-ui-lcd-7u-visual-report.pdf`

## Remaining Limitations

This was not a broad declutter or redesign pass. Some pages still carry dense advanced sections from earlier LCD phases. That cleanup remains deferred. Live displays remain bounded passive telemetry visualizations and do not introduce new runtime control authority.

## Runtime Truth Preservation

LCD-7U preserved runtime boundaries:

- no Recorder/Helm page was rebuilt
- no Support/Diagnostics page was rebuilt
- no radial menu behavior was added
- no page transition animations were added
- no hardware polling was added
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no cloud AI/LLM behavior was added
- no auto-save was added
- live displays remain passive visualizations of existing runtime/Bridge telemetry
- tuning and mapping UI changes remain workspace draft/preview behavior only
