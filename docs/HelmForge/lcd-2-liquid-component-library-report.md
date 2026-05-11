# LCD-2 Liquid Component Library Report

## Scope

LCD-2 adds the shared Liquid component platform for the HelmForge Liquid Command Deck. This phase keeps the LCD-1/LCD-1R/LCD-1F shell and floating command surface direction intact while replacing one-off placeholder interiors with reusable static widgets.

No real page rebuilds were implemented. The updated placeholder pages are demonstrations of component families only.

## components added

Page/layout components:

- `LiquidPage`
- `LiquidPageHeader`
- `LiquidHeroPanel`
- `LiquidInstrumentPanel`
- `LiquidInspectorPanel`
- `LiquidDetailPanel`
- `LiquidAdvancedSection`
- `LiquidSplitPanel`
- `LiquidStatusRail`
- `LiquidFloatingPanel`
- `LiquidGlassCapsule`
- `LiquidCommandSurfaceSection`

Status/truth components:

- `StatusChip`
- `TruthBadge`
- `ReadinessGate`
- `MetricTile`
- `DraftStateIndicator`
- `TelemetryFreshnessRail`
- `StatusLight`

Flow components:

- `RouteFlowRow`
- `SignalPipelineStage`
- `ChecklistPanel`

Parameter and inspector components:

- `ParameterRow`
- `ParameterLabelWithInfo`
- `NumericParameterControl`
- `DropdownParameterControl`
- `AxisSelectorPills`
- `GuidanceBlock`
- `LiveSnapshotBlock`

Static instrument placeholders:

- `AxisBar`
- `AxisBarPair`
- `ButtonIlluminationGrid`
- `HatDirectionIndicator`
- `ControlMarker`
- `MiniCurvePreview`
- `CapabilityRail`

## module structure

The component library is split by purpose:

- `v3_app/liquid/components.py`: page composition, panel primitives, capsules, split panels, status rails, and floating panel seams.
- `v3_app/liquid/status_components.py`: readiness, truth, metric, draft, and telemetry freshness components with shared state-role semantics.
- `v3_app/liquid/flow_components.py`: route, signal pipeline, and checklist widgets.
- `v3_app/liquid/parameter_controls.py`: parameter labels, rows, validators, dropdowns, axis selector pills, guidance, and live snapshot placeholders.
- `v3_app/liquid/instruments.py`: static instrument placeholders for axis, buttons, hat, markers, curve previews, and capability rails.
- `v3_app/liquid/theme_tokens.py`: shared static Liquid QSS roles for the new component families.
- `v3_app/liquid/pages/placeholder_pages.py`: placeholder demonstrations using the new component library.

## Intended Use

The layout components give future pages stable regions for hero, inspector, detail/action, advanced, and status content. Status components keep readiness wording and color semantics consistent. Flow components provide compact signal and mapping language. Parameter components provide metadata-ready seams without creating a new registry. Instrument placeholders provide safe static foundations for later Live Monitor, Mapping, Tuning, Recorder, and Support pages.

## floating command surface

The components are designed to live inside the existing `liquid_command_surface`, `liquid_surface_glass_field`, floating mode dock, and floating footer strip. The placeholder pages keep hero-first composition, inspector/detail panels orbiting the hero, and advanced diagnostics visually secondary. LCD-2 does not return the shell to a sidebar, card-stack, or sectioned admin layout.

## runtime truth wording

Status wording is intentionally conservative. Components use approved language such as `Runtime blocked`, `Simulation mode`, `Telemetry stale`, `Output proof missing`, `Capture backend unavailable`, `Metadata-only artifact`, `Read-only visualization`, and `Draft change staged`.

Green roles are limited to ready, verified, saved, safe, and done states. Amber roles cover waiting, blocked, attention, unsaved, warning, and missing proof. Red roles cover error, unsafe, and failed. Blue/cyan roles cover info, simulation, and live-neutral wording. Disabled and unavailable states use a separate disabled tone and do not look ready.

No component asserts output proof by default. `RouteFlowRow` preserves `Output Intent:` wording for output targets.

## metadata integration

`ParameterLabelWithInfo` accepts supplied help text and optional metadata dictionaries with description/help/unit fields. `NumericParameterControl` exposes min/max/decimal seams and flags invalid non-numeric or out-of-range text. `DropdownParameterControl` rejects unsupported values. This keeps LCD-2 metadata-ready without creating a competing parameter metadata registry.

## Future Phase Preparation

LCD-2 prepares for LCD-3 by giving the shell stable component object names, panel roles, and page-region seams that mode/subpage routing can populate without reshaping the command surface.

LCD-2 prepares for LCD-4 through LCD-9 by giving each future page family reusable hero, inspector, detail, advanced, status, flow, parameter, and instrument primitives. Preflight can reuse readiness gates and checklists. Mapping can reuse route flows and control markers. Tuning can reuse axis pills, parameter rows, guidance blocks, and curve previews. Analysis can reuse signal stages, axis bars, and telemetry freshness rails. Recorder can reuse truth badges and capability rails. Support can reuse advanced sections, metric tiles, and guidance blocks.

LCD-2 prepares seams for LCD-10 through LCD-12 by centralizing static roles and state properties that later motion, reduced-motion, and atmosphere work can target. No motion behavior is active in LCD-2.

## Explicit deferred items

- no full page rebuilds were implemented
- no subpage navigation architecture was implemented
- no animations were added
- no radial menu behavior was added
- no real blur/distortion was added
- no runtime authority was changed
- no hardware polling was changed
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no recorder capture/encoding was added
- no cloud AI/LLM behavior was added
- no auto-save was added

## Runtime Truth Preservation Statement

LCD-2 changes only the Liquid UI component layer and placeholder demonstrations. It does not modify runtime authority, hardware polling, vJoy writes, output proof, Full Live Runtime Ready logic, Bridge ownership, recorder capture/encoding, Helm apply/revert semantics, workspace save/apply semantics, cloud behavior, or auto-save behavior.
