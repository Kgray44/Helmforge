# Cockpit UI V2 Full-App Static Refresh

## Why the previous prototype was rejected

The previous Cockpit prototype was undone because it broke the Preflight page, left an Advanced Diagnostics button floating outside the layout, rendered mostly blank content, and could freeze Windows with a Not Responding state. This refresh does not reuse that drawer pattern, animation approach, blur/opacity effects, or dynamic layout behavior.

## Legacy preservation strategy

Legacy UI is preserved as the stable interface. The existing page modules remain in place and are not deleted or moved.

- `HELMFORGE_UI_MODE=legacy` loads the Legacy shell and Legacy page presentation.
- `HELMFORGE_UI_MODE=cockpit` loads the new static Cockpit shell and wraps the existing page modules in Cockpit page frames.
- Default/unset mode: Cockpit.
- Invalid mode values fall back to Legacy.

The Cockpit implementation reuses the same page classes and existing callbacks for save, apply, revert, import, mapping edits, tuning controls, recorder review, Help / Docs, and diagnostics. Legacy is recoverable because the app mode selects either `HelmForgeShell` or `CockpitShell` at launch.

## Visual direction

Cockpit UI V2 is a full-app skin foundation for a modern glass cockpit, aircraft MFD, and command deck feel. It introduces layered dark panels, status hierarchy, readiness gates, metric tiles, route flow rows, checklist panels, and isolated advanced details while preserving current behavior.

## Static-first rule

No animations, drawers, blur effects, opacity effects, or graphics effects are used in this pass. Advanced sections are static and always visible. The implementation uses normal Qt layouts and QSS styling only.

## Design components

- `CockpitShell`: app-wide shell wrapper with the existing navigation, top status cluster, Helm entry, content viewport, and footer actions.
- `CockpitPage`: shared page frame with title, mission statement, optional banner, readiness rail, and content body.
- `CockpitStatusBanner`: page-level state, blocker/success summary, explanation, and next action.
- `ReadinessRail`: wrapped system gates such as Input, Telemetry, Workspace, vJoy, Output Proof, and Safety.
- `SystemTile`: cockpit module card for status, explanation, and key facts.
- `MetricTile`: compact instrument counter/value tile.
- `FlowRow`: route or pipeline display using source -> transform -> target.
- `ChecklistPanel`: warnings and next-action rows.
- `DataGridCard`: intentional detailed data surface.
- `AdvancedPanel`: static bottom area for Legacy internals and raw details.
- `CockpitActionStrip`: reusable action strip component for page/footer actions.

## App shell changes

The Cockpit shell keeps the existing sidebar, header, Helm entry, page stack, and footer action semantics. The navigation, status cluster, assistant cluster, scroll areas, footer action strip, cards, tables, chips, controls, and reused inner page widgets receive the Cockpit QSS treatment in Cockpit mode.

Footer actions remain the existing commands: Import Profile, Revert, Apply Workspace, and Save Workspace. The footer does not cover page content.

## Page-by-page first pass

| Page | Cockpit treatment |
| --- | --- |
| Preflight | Flagship dashboard with hero banner, readiness rail, input metrics, system tile grid, Warnings / Actions, and static Advanced Technical Details. |
| Mapping | Route-control surface with readiness metrics, route flow summary, HOTAS diagram status panel, and static routing tables/details. |
| Profiles | Profile bay with active profile banner, profile metrics, and Legacy profile controls styled below. |
| Modes | Mode control view with binding metrics, simple mode flow, and detailed mode controls. |
| Base Tuning | Selected-axis response instrument with curve/deadzone/output metrics and advisory panel. |
| Filtering | Filter instrument with smoothing/slew metrics and advisory panel. |
| Combat Profile | Combat response view with selected-axis combat metrics and trigger context. |
| Conditional Rules | Rule system summary with enabled/disabled metrics and condition -> state -> action rows. |
| Effective Response Stack | Pipeline view from Raw Input -> Base Tuning -> Filtering -> Modes -> Rules -> Final Output. |
| Live Monitor | Telemetry monitor with runtime status banner and instrument-style detailed monitor below. |
| Flight Recorder | Recorder bay with truth-labeled metadata/capability metrics and existing recorder library below. |
| Help / Docs | Support library frame around existing search, topic tree, article, and parameter-help surfaces. |
| Perf / Diagnostics | Dedicated diagnostic workbench where raw values are allowed and grouped intentionally. |

## Wording rules

Normal Cockpit UI uses polished wording such as HOTAS not connected, Live checks passed, Output verified, Workspace configuration, Verified, Not verified, and Draft mapping. Raw/internal values are allowed only in Perf / Diagnostics and Advanced panels.

## Known limitations

- This is not page-by-page deep polish; detailed Legacy controls are wrapped and restyled rather than reimplemented.
- The HOTAS diagram remains the stable existing diagram inside Mapping details for this pass.
- Advanced panels are always visible and static.
- No motion, blur, animated drawers, overlay editors, or dynamic cockpit effects are included yet.

## Next refinement phases

1. Replace the largest Legacy detail blocks with native Cockpit layouts page by page.
2. Promote the stable HOTAS diagram into a first-class Cockpit diagram panel after visual QA.
3. Add carefully tested micro-interactions only after static layout stability is proven.
4. Tighten wording and spacing through a manual walkthrough at the default window size and common resized states.
