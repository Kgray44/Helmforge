# LCD-6 Tuning Command Pages

Required coverage phrases: routes implemented; tuning page architecture; tuning presentation/edit model structure; data surfaces used; axis selector behavior; Base Tuning page behavior; Filtering page behavior; Combat Profile page behavior; Conditional Rules page behavior; parameter metadata usage; validation behavior; draft/staged edit behavior; live/current snapshot truth behavior; guidance block behavior; response preview/graph approach; advanced details behavior; output intent/preview differs from output proof; Legacy fallback/reference is preserved; limitations/deferred tuning features; runtime truth preservation statement.

## Why This Phase Exists

LCD-6 rebuilds the Tuning mode as real Liquid Command Deck pages instead of placeholder routes. The page family answers: how does this axis respond and feel?

This phase keeps the Liquid work bounded to Tuning. It does not wrap Legacy tuning pages, repaint Legacy layouts, or change runtime behavior.

## Routes Implemented

The following routes implemented real Liquid pages:

- `tuning.base_tuning`
- `tuning.filtering`
- `tuning.combat_profile`
- `tuning.conditional_rules`

The route registry now maps those routes to `TuningCommandPage` factories. Preflight and Mapping routes remain preserved.

## Tuning Page Architecture

Each tuning route follows the same instrument-first composition:

- Liquid page header with route title and tuning question
- response hero/instrument panel
- selected axis selector
- parameter or rule inspector
- LiveSnapshotBlock with passive truth wording
- structured GuidanceBlock
- advanced details as secondary content
- existing floating footer preserved

The pages are Liquid-native compositions and do not instantiate Legacy tuning layouts as the primary UI.

## Tuning Presentation/Edit Model Structure

`v3_app/liquid/models/tuning_command_model.py` adds a pure presentation/edit model:

- `TuningCommandModel`
- `TuningParameterModel`
- `TuningPreviewModel`
- `TuningRuleFlow`
- `TuningEditResult`
- `build_tuning_command_model`
- `stage_tuning_parameter_edit`

The model lists selectable axes, page-specific parameters, metadata-backed control type/range/options, preview values, passive snapshot labels, guidance text, advanced details, rule flows, draft state, and validation messages.

## Data Surfaces Used

LCD-6 uses existing non-visual data only:

- `WorkspaceConfig`
- `TuningConfig` / `AxisTuning`
- `FilteringConfig` / `AxisFiltering`
- `CombatProfileConfig` / `AxisCombatProfile`
- `RuleConfig` / `ConditionalRule`
- `AXIS_DISPLAY_NAMES` and axis IDs
- `PARAMETER_HELP` metadata
- existing `AppState` runtime snapshot labels

No hardware polling, output verification, Bridge command, or vJoy write path is used.

## Axis Selector Behavior

The axis selector exposes:

- Roll
- Pitch
- Throttle
- Yaw
- Aux 1
- Aux 2

Selection updates the visible selected-axis state and rebuilds only the active tuning page presentation. It does not edit workspace state, poll hardware, or write output.

## Base Tuning Page Behavior

Base Tuning includes a response preview hero and parameter inspector for:

- Curve Mode
- Curve Strength
- Deadzone
- Anti-Deadzone
- Hysteresis
- Output Scale
- Max Output

Curve Mode uses a dropdown when metadata exposes finite options. Numeric fields use metadata ranges and validators.

## Filtering Page Behavior

Filtering includes a smoothing/response preview hero and parameter inspector for:

- Center Alpha
- Edge Alpha
- Same Slew Limit
- Reverse Slew Limit

These edits are workspace/draft tuning edits only.

## Combat Profile Page Behavior

Combat Profile includes a combat response preview hero and parameter inspector for:

- Combat Curve
- Combat Scale
- Combat Center Alpha
- Combat Edge Alpha
- Combat Same Slew
- Combat Reverse Slew

The page does not claim combat mode is active from preview values.

## Conditional Rules Page Behavior

Conditional Rules is a real Liquid read-only rule visualization in LCD-6. It includes:

- rule system status hero
- enabled/disabled/warning metrics
- condition to action flow rows
- rule warning checklist
- selected axis context
- LiveSnapshotBlock
- guidance
- advanced details

Rule editing remains deferred because this phase only safely stages tuning parameter edits, not complex rule mutations.

## Parameter Metadata Usage

LCD-6 uses `PARAMETER_HELP` for labels, dropdown options, numeric min/max, units, and help text. Missing metadata is represented as a local label/help fallback instead of creating a competing registry.

## Validation Behavior

Numeric validation uses existing metadata and rejects:

- empty required values
- non-numeric text
- non-integer text for integer parameters
- below-range values
- above-range values

Dropdowns reject unsupported options. Invalid edits are not staged and do not alter runtime state.

## Draft/Staged Edit Behavior

Supported tuning edits stage into a new workspace draft:

- base tuning fields update `workspace.tuning`
- filtering fields update `workspace.filtering`
- combat fields update `workspace.combat`
- workspace state becomes dirty/unsaved
- top/footer saved state updates through existing AppState state

No auto-save was added. Save and Apply remain governed by the existing app semantics.

## Live/Current Snapshot Truth Behavior

Each page labels its snapshot as preview/passive:

- Preview only
- Current sample unavailable when no passive sample exists
- Simulation mode when the current runtime truth is simulated
- Output proof unchanged

The pages do not claim live values when values are preview-only.

## Guidance Block Behavior

Guidance is structured into:

- Current feel
- What this affects
- Suggested range
- Caution
- Selected axis note

The guidance is concise and user-facing, not a raw debug wall.

## Response Preview/Graph Approach

The response preview/graph approach is static and preview-only. LCD-6 uses simple bounded response preview values from workspace parameters and existing Liquid instrument widgets. It does not add continuous graph animation, timers, polling, or live marker loops.

## Advanced Details Behavior

Advanced details are marked secondary and subdued. They contain route key, selected axis key, workspace dirty/saved state, preview source notes, output proof notes, and raw parameter IDs.

## How Output Intent/Preview Differs From Output Proof

Preview and tuning edits describe workspace tuning intent. They do not prove that vJoy is writing or that output is verified. Output proof remains owned by the existing runtime truth surfaces and is unchanged by tuning edits.

## Legacy Fallback/Reference Is Preserved

Legacy tuning modules remain untouched as reference/fallback. The Liquid launch path remains separate, and default launch behavior is not changed by LCD-6.

## Limitations/Deferred Tuning Features

Deferred items include:

- full Effective Response Stack page
- live monitor page
- live telemetry marker loops
- complex rule editing
- new response runtime math
- output verification changes
- Bridge lifecycle management

## Runtime Truth Preservation Statement

LCD-6 preserves runtime authority and truth boundaries. It stages only workspace/draft/preview edits. It does not poll hardware, write vJoy, verify output, manage Bridge lifecycle, change telemetry proof rules, auto-save, or claim live readiness from tuning edits.

## Explicit Scope Statements

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
- tuning edits are workspace/draft/preview edits only unless existing save/apply semantics are explicitly used
