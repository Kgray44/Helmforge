# LCD-7T Live Control Reality and Visual QA Report

## Why LCD-7T Was Needed

LCD-7T corrects Liquid pages that were still behaving too much like static dashboards. The pass focused on passive live telemetry propagation, large readable tuning and monitor instruments, stable route switching, a graphical HOTAS route editor overlay, restored tuning profile navigation, and repeatable visual QA artifacts.

## Live Data Propagation Fixes

Liquid tuning and analysis pages now accept existing passive Bridge telemetry snapshots through the Liquid shell. Base Tuning, Filtering, Combat Profile, Effective Response Stack, and Live Monitor derive current raw/final sample display from the latest snapshot when available.

The update path remains passive:

- no HOTAS hardware polling was added
- no Bridge commands were added
- hidden pages are not rebuilt on every telemetry frame
- identical frame signatures are coalesced where the existing page model supports it
- current values are labeled as passive telemetry/output intent rather than output proof

## Live Monitor Redesign

The Live Monitor now centers on a dominant stacked time-series monitor. It exposes six vertical lanes for Roll, Pitch, Throttle, Yaw, Aux 1, and Aux 2, with bounded local history and a raw/final overlay mode. Current numeric values are shown near the graph, while button and hat/POV data are secondary panels that either show available sample state or explicit unavailable wording.

The monitor supports UI-only display actions such as raw/final overlay, pause/resume display, clear local graph history, copy current sample, copy telemetry summary, and navigation back to the Effective Response Stack. These actions do not mutate runtime state.

## Tuning Graph Fixes

Base Tuning, Filtering, and Combat Profile now use large primary graphs. Axis selectors are placed at the top of axis-based pages so axis changes do not require scrolling.

Base Tuning shows:

- default/reference line
- current tuning curve
- current input marker
- output intent marker

Combat Profile shows:

- default/reference line
- base tuning curve
- combat profile curve
- current markers on displayed curves

Filtering shows:

- high-resolution filtered response
- 90-degree input step reference
- neutral, positive hold, negative reversal, held negative response, and return sequence

All tuning graph updates are preview/passive only and do not claim runtime output proof.

## Combat Curve Math Fix

The combat preview curve now clamps magnitude after applying the selected combat scale and preserves sign from the base curve. This keeps monotonic response modes monotonic and prevents impossible repeated center crossings in the visual preview.

## Filtering Step-Response Resolution Fix

Filtering preview generation now samples a higher-resolution response and uses explicit duplicate x coordinates for the input reference step, producing true vertical step edges instead of sloped reference lines.

## Axis Selector Placement Fix

Axis selectors are now top-level controls on axis-based Liquid tuning and analysis pages. Changing the selected axis updates the selected-axis chip, graph model, current markers, snapshot values, guidance, advanced details, and page action context.

## HOTAS Editor Overlay Behavior

Clicking a HOTAS visual-map marker selects the control and opens a graphical route editor pane over the map. The editor includes physical control identity, route flow, logical function/output intent controls where safely supported, validation state, draft state, and route commands.

The overlay uses a bounded static frosted/dim scrim behind the editor pane. It does not apply an expensive app-wide blur effect. Opening or closing the editor does not scroll the page to the bottom.

## Profiles Library Restoration

Tuning / Profiles Library was restored as `tuning.profiles_library`. The page shows the active workspace profile, profile summary, base/filtering/combat/rule counts, mapping relationship context, navigation actions, and disabled/deferred profile-management actions with reasons where no safe workspace operation exists yet.

## Blank Page Protections

The Liquid route host now wraps page construction with an error fallback panel instead of allowing factory errors to silently clear the page. Same-route and repeated route switching keep the current page non-empty, and the route cache avoids unnecessary hidden rebuild loops.

## Clutter Reduction Approach

LCD-7T keeps the primary instrument dominant on Mapping, Tuning, and Analysis pages:

- advanced/raw details are secondary
- repeated truth pills were reduced where they were redundant
- action clusters are grouped by page purpose
- large empty panels were replaced with active instruments, explicit unavailable states, or compact summaries

## Visual QA Artifacts

Two scripts were added:

- `scripts/capture_liquid_ui_screenshots.py`
- `scripts/build_liquid_visual_report.py`

Generated local artifacts:

- `artifacts/liquid-ui/lcd-7t/01-preflight-command-readiness.png`
- `artifacts/liquid-ui/lcd-7t/02-mapping-hotas-map.png`
- `artifacts/liquid-ui/lcd-7t/03-mapping-route-details.png`
- `artifacts/liquid-ui/lcd-7t/04-mapping-advanced-route-tables.png`
- `artifacts/liquid-ui/lcd-7t/05-tuning-base-tuning.png`
- `artifacts/liquid-ui/lcd-7t/06-tuning-filtering.png`
- `artifacts/liquid-ui/lcd-7t/07-tuning-combat-profile.png`
- `artifacts/liquid-ui/lcd-7t/08-tuning-conditional-rules.png`
- `artifacts/liquid-ui/lcd-7t/09-tuning-profiles-library.png`
- `artifacts/liquid-ui/lcd-7t/10-analysis-effective-response-stack.png`
- `artifacts/liquid-ui/lcd-7t/11-analysis-live-monitor.png`
- `artifacts/liquid-ui/lcd-7t/liquid-ui-lcd-7t-visual-report.pdf`

The artifacts were generated locally for QA. They are intentionally not required as committed source artifacts unless the repository policy later chooses to track visual outputs.

## Remaining Limitations

- Live displays depend on existing passive runtime/Bridge telemetry surfaces; they do not create new telemetry sources.
- Profile import/export/duplicate/rename/delete remains disabled where no safe workspace operation is available.
- The HOTAS editor stages only fields that the existing mapping edit model can safely represent.
- Filtering and tuning graphs remain preview instruments and are not output verification.
- Full real blur, transitions, radial behavior, Recorder/Helm, and Support/Diagnostics remain deferred.

## Runtime Truth Preservation

LCD-7T preserved runtime boundaries:

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
- live displays are passive visualizations of existing runtime/Bridge telemetry
- route, tuning, and profile edits remain workspace draft/preview behavior unless existing save/apply semantics are explicitly invoked elsewhere
