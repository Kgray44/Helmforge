# LCD-4P Preflight Visual Hierarchy and Layout Polish

## why LCD-4P was needed

LCD-4 made `preflight.command_readiness` real and runtime-truthful. LCD-4F fixed the interactive startup freeze by preventing hidden or semantically identical Preflight telemetry frames from rebuilding the page. LCD-4P keeps that behavior intact while improving the page's visual hierarchy so it feels more like a premium command-deck instrument surface and less like stacked diagnostic trays.

## top command/status compression fix

The top command/status bar keeps the same truth sources, but its proportions were adjusted:

- the status capsule has clearer width bounds;
- the source chip now uses human-readable labels such as `Source: Bridge Config`, `Source: Workspace Config`, `Source: Simulation`, and `Source: Telemetry`;
- the full source/config path remains in tooltip, status tip, and accessibility text;
- the Helm action cluster is capped as a compact control well instead of a wide empty command area.

## Preflight route strip/subpage selector weight fix

The LCD-3 navigation model is preserved. For single-subpage modes like Preflight, the subpage selector now marks itself as `singleRouteMode`, uses a compact height, and presents a subtle `Preflight / Command Readiness` breadcrumb. Multi-subpage modes keep the segmented route behavior for later LCD pages.

## page banding reduction

The old separate Preflight status rail is structurally present for testability, but visually collapsed and marked `mergedIntoHero`. Proof chips live in the hero, and the page header is a softer route/source context layer. This reduces repetitive full-width bands without removing truth information.

## hero hierarchy improvements

The go/no-go hero is marked as `preflightVisualRole=primary_go_no_go` and remains the dominant answer to:

`Can I safely use live output right now?`

It keeps the overall readiness label, explanation, next action, grouped runtime/output/telemetry/source proof chips, and readiness gates in one command-status composition.

## readiness gate visual hierarchy improvements

The six LCD-4 gates are preserved:

- Input
- Telemetry
- Workspace
- vJoy
- Output Proof
- Safety

The gates now use `preflightGateVisual=compact_scan`. Ready/verified/safe gates are marked with subtler emphasis so an all-green state does not become six equally loud green cards. The model still distinguishes vJoy detection from output proof and telemetry freshness from output verification.

## system details refinement

System details are now grouped as a compact system map:

- Input / Device
- Telemetry / Bridge
- Workspace / Config
- Output / vJoy
- Runtime / Safety

Rows use softer detail styling inside groups. Raw/internal values remain in Advanced Diagnostics.

## checklist refinement

The next-action checklist now uses action-oriented rows with clearer label/reason hierarchy and `actionRowStyle=breathing`. No new runtime action was wired. Unavailable or informational actions remain labeled as such.

## advanced diagnostics secondary treatment

Advanced Diagnostics remains present but is marked `visualWeight=subdued` with a compact summary before the raw diagnostics grid. It still exposes the LCD-4 raw truth details, but it no longer competes with the go/no-go hero and readiness gates.

## footer background/scrim fix

The actual floating footer strip was preserved, including:

- `Workspace ready.`
- `Apply`
- `Save`
- `Revert`

The oversized footer clearance/backplate was reduced and marked `footerBackdrop=transparent_compact`. The footer remains floating, while the background around it no longer reads as a large opaque bottom curtain.

## scrollbar/spacing/border hierarchy refinements

Liquid scrollbars are thinner and lower contrast at rest, with a muted hover state. Preflight-specific QSS now gives the hero the strongest depth, readiness gates medium/subtle status emphasis, details/checklist subordinate grouping, and advanced diagnostics subdued styling. Spacing was adjusted without shrinking text or relying on a larger window.

## truth consistency preservation

The Preflight page still uses the same `AppState`, `RuntimePreflightStatus`, and passive `BridgeTelemetrySnapshot` surfaces as LCD-4 and LCD-4F. A live verified fixture still shows `Ready for live output` and `Output proof verified`; a missing-proof fixture still shows `Output proof missing`; simulation remains clearly labeled simulation.

## LCD-4F freeze fix preservation

LCD-4P preserved the LCD-4F passive snapshot/cache/coalescing behavior:

- hidden Preflight does not rebuild on telemetry bursts;
- active Preflight skips semantically identical readiness frames;
- route switching avoids redundant same-route `setCurrentWidget()` calls;
- no timer or refresh loop was added.

## runtime truth preservation

LCD-4P changes only static presentation, QSS, layout properties, and structural grouping for the existing Liquid Preflight page. It does not change runtime authority, hardware polling, vJoy writes, output verification logic, Full Live Runtime Ready logic, Bridge lifecycle ownership, Bridge auto-start/stop behavior, recorder behavior, simulation fallback truth, Helm apply/revert semantics, workspace save/apply semantics, cloud behavior, or auto-save behavior.

## what remains for LCD-5

LCD-5 can begin Mapping from the same route-host/component foundation. This pass prepares the visual hierarchy language for later pages, but it does not implement any Mapping page, HOTAS map, route editor, live monitor, tuning instrument, recorder surface, Helm deck, support page, or motion system.

## explicit deferred items

- no Mapping page was rebuilt
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
