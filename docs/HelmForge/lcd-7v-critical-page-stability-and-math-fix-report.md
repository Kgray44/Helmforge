# LCD-7V Critical Page Stability and Math Fix Report

## Why LCD-7V Was Needed

LCD-7V fixes the remaining critical blockers reported after LCD-7T/LCD-7U: Effective Response Stack axis/telemetry instability, Filtering graph resolution, Combat Profile curve consistency, Profiles Library route stability, HOTAS editor overlay reflow, Live Monitor idle duplicate updates, and intermittent blank-page risks.

## Effective Response Stack Fixes

Effective Response Stack now keeps axis selection visually consistent across all axis selectors. Axis pill state is refreshed when the selected axis changes, so stale/multiple-looking selections are cleared. Selecting an axis updates the stage chain, live snapshot, selected stage detail, advanced details, and copy-context model.

The selected stage detail panel now explicitly includes the selected axis. Stage rows always include stage name, value/status, selected axis, source/truth text, and summary text. Unavailable data remains labeled rather than blank.

Passive telemetry updates continue to update stage widgets in place. The vertical stage chain is kept mounted during telemetry bursts instead of being destroyed and recreated.

## Filtering Step-Response Fix

Filtering response generation now uses a higher-resolution calculated series. The input/reference line keeps duplicate x coordinates at transitions so the reference has true vertical step edges, while the filtered output line has enough samples to read as a smooth response.

The graph exposes `stepResponseDetail=high_resolution_step_response` for tests and future visual QA.

## Combat Curve Math Fix

Combat Profile curve generation preserves sign and uses consistent coordinates for the base tuning and combat profile lines. Monotonic modes remain monotonic, the curve crosses center only near zero, and current dots are calculated from the displayed lines rather than later-stage passive final telemetry.

## Profiles Library Blank/Freeze Fix

`tuning.profiles_library` now tracks a small render signature and render count. Telemetry updates that do not change profile/workspace summary data no longer rebuild the page. The route remains non-empty and stable when switching to and from Base Tuning and Filtering.

Profiles Library continues to show active profile, saved/draft context, profile summary, tuning/filtering/combat/rule counts, copy/navigation actions, and disabled/deferred profile mutation actions with reasons.

## HOTAS Map Editor Layout Stability Fix

The HOTAS map editor overlay no longer changes the map surface minimum height when opened. The overlay/card sits over the map region, and the frosted/dim scrim does not consume layout space. Marker click and editor close continue to preserve the parent scroll position.

## Live Monitor Idle Glitch Fix

Live Monitor now coalesces identical passive live samples. It does not append duplicate local-history entries or repaint the graph repeatedly when identical frames arrive while idle. Overlay toggles and clear-history actions still update the graph explicitly, and hidden Live Monitor pages remain inactive during telemetry bursts.

## Blank Page Protections

LCD-7V preserves and strengthens existing route protections:

- route factory failures display `liquidRouteErrorFallback`
- same-route navigation does not clear the page host
- live update exceptions are non-destructive
- required Liquid routes retain non-empty widgets after repeated switching
- hidden live pages do not rebuild continuously

## Visual QA Artifacts

LCD-7V artifacts are generated under:

- `artifacts/liquid-ui/lcd-7v/`

Expected screenshots include:

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

PDF report:

- `artifacts/liquid-ui/lcd-7v/liquid-ui-lcd-7v-visual-report.pdf`

## Deferred

Broad visual simplification and clutter reduction remain deferred. LCD-7V intentionally did not redesign the pages, rebuild adjacent modes, or add new runtime authority.

## Runtime Truth Preservation

LCD-7V preserved runtime boundaries:

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
- graph markers and previews remain Output Intent/preview surfaces, not output proof
