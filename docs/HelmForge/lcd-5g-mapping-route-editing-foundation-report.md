# LCD-5G Mapping Route Editing Foundation

Scope phrase index: route editing architecture; routes implemented; editable fields supported; read-only fields; validation behavior; draft/staged edit behavior; save/apply/revert relationship; output intent is distinguished from output proof; HOTAS Map links to editing routes; Advanced Route Tables avoids the 22-card wall; data surfaces used; limitations/deferred editing features; runtime truth preservation statement.

## Why This Phase Exists

LCD-5 built Mapping / HOTAS Map as a read-only visualization. LCD-5G adds the first safe editing foundation for Mapping route tables while preserving the runtime truth boundary: route changes are workspace/draft mapping edits only, not live output writes, not output proof, and not Bridge/runtime authority.

## Route Editing Architecture

LCD-5G adds `v3_app/liquid/models/mapping_edit_model.py` as the pure presentation/edit model. It derives route records from the existing workspace mapping config and HOTAS diagram presentation model, exposes editable metadata, validates edits, and returns a replacement workspace dataclass when a supported edit is staged.

The Liquid shell owns the staged workspace draft for the new Liquid editing routes. `LiquidCommandShell.stage_mapping_route_edit()` accepts a route id, field id, and value, calls the pure edit model, updates the shell workspace only on valid edits, marks the Liquid app state unsaved, refreshes the top/footer saved state, and updates the Mapping pages. It does not persist automatically and does not change runtime truth.

## Routes Implemented

- `mapping.hotas_map` remains the visual overview and selection-only HOTAS map.
- `mapping.route_details` is now a real Liquid Route Details page for focused route editing.
- `mapping.advanced_route_tables` is now a real Liquid Advanced Route Tables page for grouped bulk route review/editing.

The old generic placeholders are no longer used for the two Mapping edit routes.

## Editable Fields Supported

Supported LCD-5G fields are intentionally narrow:

- Axis routes: logical function and Output Intent target.
- Button routes: Output Intent target.

Valid options come from the existing workspace mapping shape. Axis Output Intent targets are vJoy intent labels such as `vJoy X(axis1)` and `vJoy SL1(axis8)`. Button targets are bounded `Button 1` through `Button 20` intent labels.

## Read-Only Fields

Several fields remain visible but read-only:

- Raw channel / physical control assignment remains read-only because changing the physical control route shape is deferred.
- Enabled/disabled route state remains read-only because the current workspace schema does not represent per-route enabled flags.
- Button logical labels remain read-only because they are derived from physical button route shape in the current model.
- Hat / POV complex editing remains read-only because directional POV/button fallback editing needs a focused future phase.
- Unmapped route creation remains deferred.

## Validation Behavior

Edits are validated before staging. LCD-5G rejects:

- Unknown route ids.
- Unknown fields.
- Read-only fields.
- Empty required values.
- Unsupported logical functions.
- Unsupported Output Intent targets.
- Duplicate axis Output Intent targets.
- Duplicate button Output Intent targets.
- Route type mismatches and unsupported complex routes.

Invalid edits return a validation message, do not change workspace state, and do not alter runtime state.

## Draft/Staged Edit Behavior

Valid edits replace the in-memory Liquid workspace draft with a new frozen workspace dataclass and mark workspace state as dirty/unsaved. The top saved chip changes to Unsaved where existing Liquid shell state supports it. The footer message reports that the draft mapping change is staged and reminds the user to save workspace to persist.

Revert restores the Liquid shell's original Mapping workspace draft for this session. LCD-5G does not add automatic persistence.

## Save/Apply/Revert Relationship

Save and Apply remain governed by the existing application semantics. LCD-5G stages route edits in the Liquid workspace draft and marks the state unsaved, but the Liquid footer persistence buttons remain the existing disabled shell placeholders. No new save, apply, Bridge command, output write, or auto-save path was added.

Revert is limited to the Liquid Mapping edit session baseline and clears staged route edits in memory.

## Output Intent vs Output Proof

Every editing surface uses Output Intent wording. Editing an output target means changing workspace mapping intent only. Output proof remains separate runtime truth and is reported as unchanged after edits. A staged route edit does not imply live output, vJoy writes, or verified output.

## HOTAS Map Links to Editing Routes

The HOTAS Map remains read-only for visual selection. It now includes navigation-only affordances:

- Open Route Details.
- Open Advanced Route Tables.

Selecting a HOTAS marker updates the selected control and selected route for inspection. Navigation buttons switch Liquid routes only and do not stage edits by themselves.

## Advanced Route Tables Avoids the 22-Card Wall

The new Advanced Route Tables route presents compact editable rows grouped by:

- Axis routes.
- Button routes.
- Hat routes.
- Unmapped / warnings when present.

The HOTAS Map advanced section remains a compact preview rather than rendering every route record as primary content.

## Data Surfaces Used

LCD-5G uses:

- `shared_core.models.workspace.WorkspaceConfig`
- `shared_core.models.mappings.MappingConfig`, `AxisMapping`, and `ButtonMapping`
- `v3_app.services.hotas_diagram_model.build_hotas_diagram_model`
- `v3_app.liquid.models.mapping_command_model.build_mapping_command_model`
- `v3_app.services.app_state.AppState` saved/status presentation state

No hardware state, Bridge command channel, output backend writer, or output verification service is used.

## Limitations/Deferred Editing Features

Deferred items:

- No live route application was added.
- No real workspace save button behavior was added to the Liquid footer.
- No route creation was added.
- No physical control reassignment was added.
- No complex Hat / POV editor was added.
- No mode/profile binding editor was added.
- No Route Details advanced conflict resolver UI was added.
- No tuning, analysis, recorder, support, or diagnostics pages were rebuilt.

## Runtime Truth Preservation Statement

LCD-5G preserves runtime truth boundaries. Route edits are workspace/draft mapping edits only. They do not poll hardware, do not write vJoy, do not verify output, do not start/stop or manage Bridge lifecycle, do not alter Full Live Runtime Ready logic, do not change simulation fallback truth, and do not change workspace persistence semantics beyond marking staged edits as unsaved in the Liquid draft.

Explicit non-goals confirmed:

- no hardware polling was added
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no recorder capture/encoding was added
- no cloud AI/LLM behavior was added
- no auto-save was added
- no animations/page transitions/radial menu/real blur were added
- route edits are workspace/draft mapping edits only
