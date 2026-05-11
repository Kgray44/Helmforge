# LCD-3 Navigation and Mode Architecture Report

## Scope

LCD-3 turns the Liquid Command Deck from mode-only placeholders into a real navigation architecture with major modes, subpages, stable route keys, route-hosted placeholder pages, and session-local navigation state.

No real page rebuilds were implemented. Legacy pages remain reference/fallback only.

## navigation model structure

The model lives in `v3_app/liquid/models/nav_model.py` and is pure/testable:

- `LiquidMode`: mode id, display name, glyph, short description, accent role, route prefix, subpages, and default subpage.
- `LiquidSubpage`: subpage id, display name, purpose/question, route key, parent mode id, availability state, tooltip, and accessibility text.
- `LiquidRoute`: resolved route key plus mode/subpage display metadata for page hosting.
- `LiquidNavigationModel`: immutable route lookup and uniqueness validation.
- `LiquidNavigationState`: session-local current mode/subpage plus last selected subpage per mode.

## required major modes

LCD-3 implements the required major modes:

- Preflight
- Mapping
- Tuning
- Analysis
- Recorder
- Support

## required subpages

LCD-3 implements the required subpages:

- Preflight: Command Readiness
- Mapping: HOTAS Map, Route Details, Advanced Route Tables
- Tuning: Base Tuning, Filtering, Combat Profile, Conditional Rules
- Analysis: Effective Response Stack, Live Monitor
- Recorder: Flight Recorder, Clip Library / Artifacts, Capture Backend Truth
- Support: Help / Docs, Perf / Diagnostics, Setup / Runtime Check

## route key strategy

Route keys use stable `mode.subpage` strings:

- `preflight.command_readiness`
- `mapping.hotas_map`
- `mapping.route_details`
- `mapping.advanced_route_tables`
- `tuning.base_tuning`
- `tuning.filtering`
- `tuning.combat_profile`
- `tuning.conditional_rules`
- `analysis.effective_response_stack`
- `analysis.live_monitor`
- `recorder.flight_recorder`
- `recorder.clip_library`
- `recorder.capture_backend_truth`
- `support.help_docs`
- `support.perf_diagnostics`
- `support.setup_runtime_check`

These keys are the registry seam later LCD-4 through LCD-9 page rebuilds can replace one route at a time.

## dock selection behavior

The floating dock remains `liquid_floating_mode_dock`. It stays compact and glyph-first, exposes full mode names through accessible names/tooltips, keeps selected visual state, and switches the route host when a mode is selected.

On first visit to a mode, the default subpage is selected. If the user selected another subpage earlier in the same session, returning to that mode restores the last selected subpage.

## subpage selector behavior

LCD-3 adds `liquid_subpage_selector` as a static compact chip row above the page host. It shows only the subpages for the selected major mode. Each chip has display text, route key property, subpage id property, tooltip, accessible name, and selected visual state.

No drawer, flyout animation, radial menu, or page transition was added.

## page host routing behavior

The Liquid page host now keys pages by route rather than mode. Each route currently maps to a distinct Liquid placeholder page built from LCD-2 components. Selecting a dock mode or subpage chip updates:

- current mode id
- current subpage id
- current route key
- selected dock state
- selected subpage chip state
- page host content
- visible page title/subpage/purpose text

The page host remains scroll-safe inside the existing floating command surface.

## session state behavior

`LiquidNavigationState` keeps session-local selected mode/subpage state. It remembers the last selected subpage per major mode for the current app session only. LCD-3 does not persist navigation state to disk and does not add auto-save.

## Legacy fallback/reference is preserved

Legacy fallback/reference is preserved. `legacy` remains the default app shell, `--ui-shell liquid` still launches the Liquid shell, and `HELMFORGE_UI_SHELL=liquid` remains supported through the existing launch path. LCD-3 does not remove or wrap Legacy pages as primary Liquid routes.

## radial anchor remains future-only

The `liquid_radial_anchor_orb` remains present as a future quick switch anchor. It has tooltip/accessibility text that says the radial quick switch is planned later. It does not open a radial menu, add interactions, bind shortcuts, or animate.

## LCD-4 through LCD-9 preparation

LCD-3 prepares LCD-4 through LCD-9 by giving each future page rebuild a stable route key, route metadata, title/purpose contract, and registry target. Future phases can replace placeholder factories with real Liquid page factories without changing dock state or shell routing.

## LCD-10 through LCD-12 preparation

LCD-3 preserves LCD-10 through LCD-12 motion/radial/atmosphere seams without implementing them. The dock, subpage selector, route host, selected-state properties, and radial anchor have stable object names that later motion and radial phases can target.

## layout/overlap preservation

LCD-3 keeps the LCD-2F layout/overlap preservation contract. The selector is a compact row above the route host, route pages remain inside the scroll area, and existing footer clearance remains in place.

## demo truth consistency

Navigation placeholders continue to label sample states as static/demo/example/placeholder content. Route placeholder chips use wording such as `Placeholder route`, `Future page rebuild placeholder`, and `Static route`, so page-level demo states do not look like current runtime truth.

## runtime truth preservation

LCD-3 changes only Liquid navigation and placeholder routing. Existing runtime truth data, top bar truth chips, workspace state, and disabled footer action placeholders remain the source of visible truth. LCD-3 does not alter hardware polling, output proof, live runtime readiness, recorder capability, Bridge ownership, Helm apply/revert semantics, or workspace save/apply semantics.

## verification and package note

Source tests and offscreen source launch smokes were run for LCD-3. Packaged smoke was not rerun after these source UI changes, so existing package output should not be treated as refreshed by LCD-3.

## explicit deferred items

- no real page rebuilds were implemented
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
