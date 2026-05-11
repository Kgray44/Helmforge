# Post-RC 4F Mapping / Helm / Preflight Visual Repair Report

This repair pass responds to the rejected screenshot walkthrough for Global Shell, Mapping, Preflight, and Helm. It stays inside UI presentation, layout, and focused tests. It does not add runtime authority, hardware polling, vJoy behavior, Bridge lifecycle ownership, output verification semantics, recorder behavior, auto-save, Profiles, or Modes implementation.

## Screenshot Issues Observed

| Area | Screenshot problem | Repair |
|---|---|---|
| Helm overlay | Right column clipped, nested scrollbars, cards outside pane, Apply / Revert partly hidden | Widened the in-app pane, raised the two-column breakpoint, kept a single main vertical scroll area, and forced horizontal scrolling off |
| Helm content | Dense debug paragraphs with raw runtime strings | Replaced findings with structured rows: Active axis, Evidence used, Runtime boundary, Workspace findings, Mode findings, Rule findings, Warnings, Recommendation summary |
| HOTAS diagram | Markers could disappear or appear behind other layers | Markers are shown, raised, clamped, and updated after filter/resize/model refresh |
| Remap editor | Embedded page-flow card pushed content down and read like Route Inspector | Remap now opens as a floating Mapping overlay with a scrim, fade animation, draft status, selected control, current mapping, editable target, Apply to Draft, Cancel, and Revert Route |
| Routing overview | Count/status cards still looked like text blocks | Rebuilt as route count badges and status chips for route counts, conflicts, unmapped posture, saved state, and workspace |
| Live route summary | Raw internal route strings dominated the card | Rebuilt as physical input -> function -> virtual output route rows |
| Routing tables | Repeated square combo/editor affordances and cramped rows | Main tables now use read-only text cells, row spacing is increased, unwanted columns are removed, and per-row repeated info widgets are gone |
| Preflight | Dashboard was reduced to four vague cards | Restored a detailed dashboard with readiness, device/driver, vJoy/output, bridge/telemetry, workspace/config, input data, safety gates, warnings/actions, and advanced details |
| Shell/footer/status | Raw preflight footer wording and generic workspace chip | Footer/status copy is polished, saved/unsaved is prominent, and the workspace chip shows the active workspace name |

## Files Changed

- `v3_app/helm/helm_overlay.py`
- `v3_app/pages/mapping_page.py`
- `v3_app/pages/preflight_page.py`
- `v3_app/widgets/hotas_diagram.py`
- `v3_app/ui/header.py`
- `v3_app/ui/shell.py`
- `v3_app/services/app_state.py`
- `v3_app/theme/qss.py`
- `tests/test_post_rc_4f_mapping_helm_preflight_walkthrough.py`
- `tests/test_phase5_mapping_page.py`
- `tests/test_phase4_app_shell.py`
- `tests/test_phase6b_mapping_editor_persistence.py`
- `tests/test_phase10d_helm_context_integration.py`
- `tests/test_phase10e_helm_final_polish_boundary.py`
- `tests/test_phase14c_physical_input_ui_integration.py`
- `tests/test_phase14d_input_boundary_freeze.py`
- `tests/test_phase16b_runtime_frame_telemetry_ui.py`
- `tests/test_phase16c_verified_runtime_path.py`
- `tests/test_phase16d_full_live_runtime_ready_gate.py`
- `tests/test_post_rc_1c_parameter_help_coverage.py`
- `tests/test_post_rc_2a_mapping_hotas_diagram.py`
- `tests/test_post_rc_2b_mapping_diagram_interaction.py`
- `tests/test_post_rc_2c_mapping_diagram_editing.py`
- `tests/test_post_rc_4b_page_by_page_polish.py`
- `tests/test_post_rc_4d_control_pages_polish.py`
- `tests/test_phase10a_helm_overlay_foundation.py`
- `tests/test_phase10c_helm_guided_review_apply_revert.py`
- `docs/HelmForge/post-rc-4f-preflight-data-audit.md`
- `docs/HelmForge/post-rc-4f-mapping-helm-preflight-visual-repair-report.md`

## Acceptance Matrix

| Requirement | Status | Notes |
|---|---|---|
| Helm layout/clipping fixed | Done | Two-column mode now requires a wide enough pane; 1280px stacks vertically |
| Helm overlay/pane behavior fixed | Done | Opens as an in-app right pane with scrim/blur/fade behavior, not a dialog/window |
| Helm content readability fixed | Done | Raw debug paragraphs moved into structured readable rows |
| HOTAS diagram blank/missing marker issue fixed or root-caused | Done | Marker visibility, z-order, resize, and filter handling are covered by tests |
| Remap card changed to overlay | Done | Floating Mapping overlay replaces embedded page-flow inspector |
| Routing Overview redesigned | Done | Visual count badges and status chips replace the plain text block |
| Live Route Summary redesigned | Done | Route-flow rows replace raw route dumps |
| Routing repeated square/info issue fixed | Done | Main tables use read-only text cells; repeated combo/editor widgets are removed |
| Debug wording removed from main UI | Done | Main visible strings are audited for the forbidden phrases |
| Preflight restored as detailed dashboard | Done | 9 dashboard sections and 60+ visible/audited data rows |
| Preflight detailed data audit completed | Done | See `docs/HelmForge/post-rc-4f-preflight-data-audit.md` |
| Footer/status wording polished | Done | Footer and header status use product wording and actual workspace identity |
| Runtime-side telemetry enrichment | Deferred | VID/PID, telemetry tick/age, last output write, and command ack require runtime/shell data exposure |

Summary: 12 Done, 1 Deferred, 0 Partial.

## Preflight Data Audit

Detailed audit: `docs/HelmForge/post-rc-4f-preflight-data-audit.md`

The table restores and audits 64 data rows. The main dashboard now separates user-readable values from raw support details. Fields still showing missing/unknown states are mostly valid unavailable states or missing telemetry/UI wiring, not fake values. The highest-value follow-up wiring is VID/PID, input sample timestamp, Bridge telemetry tick/age, last output write proof, and last Apply Workspace acknowledgement.

## UI Strings Removed Or Polished

- `Post-RC 2D Advanced Mapping Editor is not merged here...` removed from Mapping.
- `Route Inspector` changed to `Selected Control`.
- `Source of truth` changed to `Boundary` / `Workspace draft`.
- `Output intent only - not live output proof` changed to `Draft mapping only`.
- `workspace/config` changed to `workspace` or `Workspace configuration`.
- `live_verified` changed to `Live checks passed`.
- `no_supported_device` changed to `no supported HOTAS detected` or hidden from main UI.
- `Bridge telemetry unavailable` changed to `Live device details are not available right now`.
- Raw booleans and raw config filenames are confined to Advanced/Diagnostics contexts.

## Tests Run

- `python -m pytest tests\test_phase5_mapping_page.py tests\test_post_rc_4f_mapping_helm_preflight_walkthrough.py -q` - passed, 17 tests
- `python -m pytest tests\test_post_rc_2b_mapping_diagram_interaction.py tests\test_post_rc_2c_mapping_diagram_editing.py tests\test_post_rc_4b_page_by_page_polish.py tests\test_post_rc_4c_global_helm_walkthrough_polish.py tests\test_post_rc_4d_control_pages_polish.py tests\test_phase10a_helm_overlay_foundation.py tests\test_phase10c_helm_guided_review_apply_revert.py -q` - passed, 59 tests
- `python -m pytest` - passed, 671 tests
- `python -m compileall -q v3_app` - passed
- `git diff --check` - passed
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed
- `python -m bridge_app.main --status` - passed and returned `lifecycle=LiveVerified truth=blocked_missing_device output_verified=True`

## Known Limitations

- Preflight still cannot show VID/PID, telemetry tick/age, last output write detail, or command acknowledgement until those values are exposed to this UI surface by existing runtime/shell data paths.
- Offscreen Qt screenshots can render fonts differently from a live Windows desktop; layout tests check widget geometry and scroll behavior instead of relying on text raster fidelity.
- Existing unrelated live-runtime/stall files were already dirty before this visual pass and were not used as a basis for this UI repair.
