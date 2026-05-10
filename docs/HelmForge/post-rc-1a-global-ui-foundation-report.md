# Post-RC 1A Global UI Foundation Report

Post-RC 1A is a post-release-candidate polish pass based on manual product walkthrough notes. It is not a new prompt-book runtime phase. This pass adds no runtime behavior and does not add hardware polling, vJoy/output behavior changes, output verification changes, Bridge lifecycle management, driver/vJoy installer launch, recorder capture/encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or unsupported runtime activation.

## User Walkthrough Issues Addressed

The user walkthrough issues addressed in this pass were global shell, control, dropdown, and layout foundation problems rather than feature-specific work.

- Shortened the default main window height while preserving horizontal and vertical resize behavior.
- Added sane minimum window dimensions so the shell remains usable when resized.
- Made the left sidebar read as a floating bordered card and fit every page name at the default vertical scale.
- Added clearer card treatment for STATUS and ASSISTANT clusters.
- Added a visible page body border through the shared page scroll area.
- Reworked global button state styling so normal, hover, pressed, checked/active, and disabled states are distinct.
- Added global QComboBox popup styling so dropdown text and menu options remain readable on the dark theme.
- Added a reusable top-aligned card-grid helper so two-column cards can size to content instead of filling neighboring card height.
- Removed Page / Axis / Profile / Source detail text from the bottom bar.
- Strengthened shared text hierarchy for labels, values, helper text, and form labels.

## Files Changed

- `v3_app/app.py`
- `v3_app/theme/tokens.py`
- `v3_app/theme/qss.py`
- `v3_app/ui/footer.py`
- `v3_app/pages/page_helpers.py`
- `v3_app/pages/modes_page.py`
- `v3_app/pages/base_tuning_page.py`
- `v3_app/pages/filtering_page.py`
- `v3_app/pages/combat_profile_page.py`
- `v3_app/pages/conditional_rules_page.py`
- `v3_app/pages/effective_response_stack_page.py`
- `v3_app/pages/live_monitor_page.py`
- `v3_app/pages/flight_recorder_page.py`
- `v3_app/pages/perf_diagnostics_page.py`
- `tests/test_phase4_app_shell.py`
- `tests/test_post_rc_1a_global_ui_foundation.py`

## Global Style/Layout Changes

The global style/layout changes are shared across the shell, sidebar, header clusters, page boundary, buttons, dropdowns, and common card grids.

The app now defaults to a shorter 1440 x 800 window with a 1120 x 650 minimum. The shell remains resizable in both axes. The sidebar, STATUS cluster, ASSISTANT cluster, page scroll surface, and shared cards now have clearer dark-engineering borders and separation. The sidebar is compact enough to show the full page menu at default height, including the long Effective Response Stack and Perf / Diagnostics labels. The page scroll area carries the outer page boundary while preserving vertical scroll behavior for tall pages.

The new `add_card_to_grid` helper top-aligns grid cards and marks them as content-sized. It has been applied to the main two-column card grids in Modes, Effective Response Stack, Live Monitor, Flight Recorder, and Perf / Diagnostics, with lower paired cards in Base Tuning, Filtering, and Combat Profile aligned to top.

## Dropdown/Button Fixes

The dropdown/button fixes are global QSS and helper-level changes rather than per-page feature behavior changes.

Global button rules now define separate normal, hover, pressed, checked/active, focus, and disabled states for QPushButton and QToolButton. The Helm launcher no longer has a permanent pressed-looking object-name style. Save Workspace remains slightly emphasized, but its pressed state is distinct from normal.

Global QComboBox rules now style the closed control, disabled state, popup menu, popup items, hover, and selected rows. This keeps axis selectors and sort dropdowns readable across Effective Response Stack, Live Monitor, Help / Docs, Flight Recorder, Mapping, Modes-style controls, and Conditional Rules.

## Bottom Bar Change

The bottom bar change is intentionally narrow: remove noisy page/axis/profile/source text while keeping global actions.

The bottom bar no longer displays Page / Axis / Profile / Source. It keeps the global status message plus Import Profile, Revert, and Save Workspace actions. Detailed page, axis, profile, and source information remains available on relevant pages and diagnostics surfaces.

## Runtime Truth Preservation

No runtime authority changed. Packaged smoke is not runtime readiness. vJoy detection is not output verification. Physical input alone is not readiness. Fake/test paths are not real readiness. Full Live Runtime Ready remains governed by the Phase 16 proof gate.

## Remaining Known Page-Specific Issues

The remaining known page-specific issues are deferred to later post-RC passes.

- Mapping still needs a dedicated HOTAS diagram pass.
- Flight Recorder still has no real capture or encoding backend.
- Help / Docs still needs a deeper content overhaul later.
- Parameter info icons and richer per-field explanations remain deferred.
- Some dense page-specific rows may still benefit from targeted typography and spacing in later post-RC passes.

## Recommendation for Post-RC 1B

Post-RC 1B should focus on one product surface at a time, starting with Mapping's HOTAS diagram and route clarity, while preserving the global styling foundation from this pass and keeping all runtime truth gates unchanged.
