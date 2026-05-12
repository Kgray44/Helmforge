# LCD-7T / LCD-7S Command Surface Reality Pass Report

## Why This Pass Was Needed

LCD-7T corrected core Liquid pages that were drifting toward attractive but passive dashboards. Mapping, Tuning, Effective Response Stack, and Live Monitor now expose clearer command surfaces, larger primary instruments, and truthful safe actions without adding runtime authority.

## Mapping Visual-Map Editor

HOTAS Visual Map marker clicks now select the physical control and open an inline Liquid mapping editor card on the map surface. The editor shows physical control label, control type, raw channel, logical function, Output Intent target, mapped state, validation/draft truth, and safe command buttons.

Enabled editor actions:
- Stage mapping change as a workspace draft edit.
- Validate route locally.
- Copy route details.
- Open full Route Details.
- Open Advanced Route Tables.
- Close editor.

Deferred/disabled editor behavior:
- Revert depends on shell-owned draft ownership.
- Physical hardware identity, raw channel, and route type remain read-only unless the existing workspace model safely represents them.

No marker click scrolls to Advanced Route Details as the primary response.

## Route Details vs Advanced Route Tables

Mapping / Route Details is now marked and composed as a focused single-route editor. It keeps the existing editable field rows while clearly representing one selected route.

Mapping / Advanced Route Tables is now marked and composed as a bulk route-table manager. It uses compact grouped rows for Axis routes, Button routes, Hat / POV routes, and Unmapped / warnings rather than a 22-card wall or another copy of Route Details.

## Mapping Edit And Draft Behavior

Supported Mapping edits continue to stage through the existing Liquid mapping edit model and shell draft path. Valid edits mark workspace state unsaved through existing AppState ownership. Invalid edits are rejected by the model and do not mutate runtime truth.

## Page Action Clusters

The pass preserves and extends the command-button approach from the prior wiring audit.

Mapping actions include edit/navigation/copy/validate/revert affordances. Tuning pages keep stage/reset/copy/revert/navigation action clusters. Analysis pages expose copy, stage selection, open-related-route, overlay toggle, pause/resume visual monitor, and clear local graph history actions.

Disabled/deferred actions carry reason text. Navigation actions are labeled as navigation. Copy actions copy useful text to the Qt clipboard. Draft actions remain workspace/view-local draft actions only.

## Square Glyph Replacement

Status indicators remain non-checkbox status lights. Non-interactive informational rows use status-dot semantics instead of checkbox-looking square roles so read-only status rows do not look like clickable toggles.

## Base Tuning Graph

Base Tuning now uses a prominent response graph in the hero region. It shows a Default/reference line and the selected axis Current tuning curve over the -1..1 input and -1..1 output domain. The graph is large enough to dominate the tuning surface and updates when selected axis or staged tuning parameters change.

## Filtering Step-Response Graph

Filtering now uses a prominent preview-only step-response graph with a complete signed pattern: neutral, positive step, held positive response, reversal to negative step, held negative response, then return/final step. The graph exposes Input step and Filtered output series. Exact live runtime proof is not implied.

## Combat Profile Graph

Combat Profile now uses a prominent multi-line graph showing Default/reference, Base tuning, and Combat profile response. It updates with selected axis and combat/tuning parameters while remaining preview-only unless existing runtime truth supplies passive data.

## Axis Selection Dependency Updates

Axis selection continues to update model-backed graph data, selected-axis labels, live/current snapshot, guidance, advanced details, and page status chips. Regression coverage now asserts visible dependent sections change when moving from Roll to Throttle.

## Conditional Rules Status

Conditional Rules remains a real structured Liquid tuning page with rule system hero, metrics, condition-to-action rows, selected rule inspector, warning/validation panel, and command cluster. Editing remains disabled where existing workspace rule semantics do not safely support mutation.

## Effective Response Stack Chain

Effective Response Stack now centers a dominant vertical stage chain:
1. Raw Input
2. Base Tuning
3. Filtering
4. Modes / Combat Profile
5. Conditional Rules
6. Final Output Intent

Output Proof remains a separate truth concept in status/summary surfaces, not a substitute for Final Output Intent. Stage cards include selectable controls; selecting a stage updates the detail panel with source, value, summary, and truth notes.

## Live Monitor Time-Series

Live Monitor now centers a large right-to-left passive axis time-series graph. It displays Roll, Pitch, Throttle, Yaw, Aux 1, and Aux 2 with bounded local history. The raw/final overlay toggle is UI-only and does not touch runtime output. Pause/resume only pauses local visual history updates; clearing history clears local display state only.

Button and Hat / POV state remain secondary panels. Telemetry missing/stale/simulation labels remain visible.

## Route And Page Stability Protections

The pass preserves bounded route switching and hidden-page protections from LCD-4F/LCD-7R. Mapping route switching across HOTAS Map, Route Details, and Advanced Route Tables remains stable in regression tests. Live Monitor hidden pages do not rebuild on telemetry bursts routed to another active page.

## Data Surfaces Used

The pass uses:
- Existing workspace MappingConfig routes and Liquid mapping edit model.
- Existing AppState saved/draft status.
- Existing tuning workspace models and preview math.
- Existing passive Bridge telemetry snapshots for Analysis.
- Existing Liquid route host and shell-owned route selection callbacks.

## Runtime Truth Preservation

No runtime authority was added. Mapping and Tuning edits are workspace/draft or preview actions only. Analysis and Live Monitor remain passive visualization surfaces. Output Intent remains distinct from output proof.

Explicitly:
- no Recorder/Helm page was rebuilt
- no Support/Diagnostics page was rebuilt
- no radial menu behavior was added
- no animations/page transitions/real blur were added
- no hardware polling was added
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no cloud AI/LLM behavior was added
- no auto-save was added

## Deferred

Deferred work remains:
- Full physical-route reassignment and raw-channel editing.
- Rule creation/editing until workspace rule mutation semantics are safely represented.
- Live Monitor continuous motion/easing.
- Real output proof actions.
- Later Recorder, Helm, Support, Diagnostics, radial navigation, and motion phases.
