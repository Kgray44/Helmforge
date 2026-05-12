# LCD-4 Preflight Command Page Report

## Scope

LCD-4 replaces only the Liquid route `preflight.command_readiness` with a real Preflight Command Page. Other Liquid routes remain LCD-3/LCD-3F placeholder routes.

This is a new Liquid Command Deck page composition, not a Legacy Preflight wrapper, reskin, or card repaint.

## Preflight page architecture

The page lives in `v3_app/liquid/pages/preflight_command_page.py` and is built from the LCD-2 component library:

- `LiquidPage`
- `LiquidPageHeader`
- `LiquidHeroPanel`
- `LiquidStatusRail`
- `ReadinessGate`
- `StatusChip`
- `ChecklistPanel`
- `LiquidInspectorPanel`
- `LiquidDetailPanel`
- `LiquidAdvancedSection`

The page is hero-first. The go/no-go hero answers the primary question, readiness gates sit directly inside that hero region, compact system details and next actions sit below, and advanced diagnostics stay visually secondary.

## route replaced

The route registry now maps `preflight.command_readiness` to `create_preflight_command_page`.

All other route keys still use the generic placeholder factory:

- `mapping.*`
- `tuning.*`
- `analysis.*`
- `recorder.*`
- `support.*`

## readiness model

The pure presentation model lives in `v3_app/liquid/models/preflight_readiness_model.py`.

It produces:

- `overall_state`
- `overall_label`
- `short_explanation`
- `next_recommended_action`
- `readiness_gates`
- `system_details`
- `checklist_items`
- `advanced_diagnostics`
- `truth_source_notes`

The model accepts deterministic `AppState`, `RuntimePreflightStatus`, and optional passive `BridgeTelemetrySnapshot` inputs. Tests can build blocked, simulation, and live verified fixtures without connected hardware.

## actual truth data surfaces used

LCD-4 uses existing non-visual truth surfaces only:

- `v3_app.services.app_state.AppState`
- `AppState.runtime.header_truth_label`
- `RuntimePreflightStatus.truth`
- `RuntimePreflightStatus.input.status`
- `RuntimePreflightStatus.output.status`
- `RuntimePreflightStatus.live_output_writes_verified`
- `AppState.active_profile`
- `AppState.saved`
- `AppState.source_config`
- optional passive `BridgeTelemetrySnapshot`
- optional telemetry `runtime_frame` fields when already supplied

LCD-4 does not call hardware discovery, runtime setup checks, output verification, vJoy writes, Bridge commands, recorder capture, or save/apply behavior.

## hero go/no-go behavior

The hero answers:

`Can I safely use live output right now?`

Supported labels include:

- `Ready for live output`
- `Runtime blocked`
- `HOTAS not connected`
- `Telemetry missing`
- `Telemetry stale`
- `Output proof missing`
- `Workspace unsaved`
- `Simulation mode`
- `Hard error`

The hero also shows next recommended action, runtime truth, output proof, telemetry/source, and source/config chips.

## readiness gates

The Preflight page implements these gates:

- Input
- Telemetry
- Workspace
- vJoy
- Output Proof
- Safety

Important distinctions are preserved:

- vJoy detected is not output write proof.
- physical HOTAS input proof is not the same as the full live gate.
- output intent is not output write proof.
- stale telemetry does not look live.
- simulation mode remains explicitly labeled.
- unavailable states do not look ready.

## system details

The compact system details panel shows:

- HOTAS/device state
- Bridge telemetry state
- telemetry freshness/source
- workspace state
- saved/unsaved state
- vJoy state
- output proof state
- runtime truth label
- Full Live Runtime Ready state if available, shown as the page's `Full live gate`
- current data source/config

Concise product labels stay in the main details panel. Raw/internal values are reserved for advanced diagnostics.

## checklist behavior

The next-action checklist includes:

- Connect HOTAS controller
- Confirm Bridge telemetry is fresh
- Load or verify workspace
- Save workspace changes
- Confirm vJoy is detected
- Confirm output proof exists
- Continue in simulation mode
- Open setup/runtime check

LCD-4 does not wire new runtime actions. Items that would require runtime commands are marked informational or unavailable.

## advanced diagnostics

Advanced diagnostics are present but secondary. They include raw runtime truth, raw mode, raw input/output status, output proof boolean, telemetry source/freshness details, config/source filename, Bridge lifecycle state if supplied, runtime frame proof fields if supplied, current blocker reason, warnings, and errors.

The page does not dump a giant debug wall as the primary view.

## truth consistency with top bar

The Preflight model uses the same `AppState.runtime` and `RuntimePreflightStatus` surfaces that drive the top command/status bar.

If the top bar reports `Live Verified`, the Preflight page reports `Ready for live output` only when output proof is also present. If output proof is missing, the page reports `Output proof missing` and does not show live readiness.

## layout/overlap preservation

The page remains inside the LCD-3F route host, scroll area, command surface, and footer clearance strategy. The floating footer remains `liquid_floating_footer_strip`, the page host remains `liquid_page_host`, and `liquid_footer_clearance` still reserves footer space.

The page uses the existing floating command surface direction: hero-first, gates near the hero, details/checklist orbiting the hero, and secondary advanced diagnostics.

## package note

LCD-4 changed source UI files and tests only. Packaged output was not rebuilt, and packaged smoke was not rerun, so any existing packaged artifact should not be treated as refreshed by this pass.

## Legacy fallback/reference is preserved

Legacy remains the default app shell. Liquid can still be launched with:

```powershell
python -m v3_app.main --ui-shell liquid
```

`HELMFORGE_UI_SHELL=liquid` remains supported through the existing launch selector. No Legacy page module was edited or removed.

## LCD-5 through LCD-12

LCD-4 prepares later phases by adding a deterministic readiness model and a route-level replacement pattern. LCD-5 through LCD-9 can replace one route at a time without changing dock selection, subpage memory, top bar truth, footer clearance, or the Legacy fallback path.

LCD-10 through LCD-12 still own microinteractions, page transitions, live motion, real blur/distortion, atmosphere, and radial navigation.

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

## runtime truth preservation

LCD-4 changes only the Liquid Preflight presentation layer and route factory mapping. It does not alter runtime authority, hardware polling, vJoy writes, output proof generation, Full Live Runtime Ready logic, Bridge ownership, recorder capture/encoding, Helm apply/revert semantics, workspace save/apply semantics, cloud behavior, or auto-save behavior.
