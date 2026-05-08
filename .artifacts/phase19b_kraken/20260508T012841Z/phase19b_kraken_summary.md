# Phase 19B Kraken Summary

Generated at: 2026-05-08T01:28:41.642535+00:00
Dry run: false
Artifacts: `C:\Users\kkids\Documents\HOTAS-Control-Panel\.artifacts\phase19b_kraken\20260508T012841Z`

## Pass / Fail / Skipped

- pass: 19
- fail: 0
- skipped: 1

## Sections

- `source_app_smoke`: pass
- `packaged_app_smoke`: pass
- `bridge_smoke`: pass
- `runtime_setup_dry_run`: pass
- `page_navigation_smoke`: pass
- `help_docs_search_smoke`: pass
- `perf_diagnostics_copy_smoke`: pass
- `helm_overlay_smoke`: pass
- `live_overlay_smoke`: pass
- `flight_recorder_smoke`: pass
- `packaging_metadata_smoke`: pass
- `installer_metadata_smoke`: pass
- `runtime_truth_boundary_smoke`: pass
- `full_live_runtime_ready_gate_smoke`: pass
- `safety_boundary_smoke`: pass

## Rows

- `source_app_smoke` / `offscreen_source_launch`: pass - Command exited 0.
- `packaged_app_smoke` / `packaged_executable_exists`: pass - Packaged executable exists.
- `packaged_app_smoke` / `packaged_smoke_launch`: pass - Command exited 0.
- `bridge_smoke` / `bridge_once`: pass - Command exited 0.
- `bridge_smoke` / `bridge_run_for_250ms`: pass - Command exited 0.
- `bridge_smoke` / `bridge_status`: pass - Command exited 0.
- `bridge_smoke` / `bridge_conservative_truth`: pass - Bridge status kept conservative simulated truth.
- `runtime_setup_dry_run` / `runtime_setup_dry_run`: pass - Runtime setup dry-run preserved installer/runtime boundaries.
- `page_navigation_smoke` / `navigate_registered_pages`: pass - Check passed.
- `help_docs_search_smoke` / `required_local_queries`: pass - Check passed.
- `perf_diagnostics_copy_smoke` / `copy_diagnostics_truth`: pass - Check passed.
- `helm_overlay_smoke` / `overlay_sections_and_symptom_path`: pass - Check passed.
- `live_overlay_smoke` / `dialog_and_detached_overlay`: pass - Check passed.
- `flight_recorder_smoke` / `page_truth_and_metadata_only_copy`: pass - Check passed.
- `packaging_metadata_smoke` / `packaging_docs_and_icon_truth`: pass - Check passed.
- `installer_metadata_smoke` / `installer_metadata_boundaries`: pass - Check passed.
- `installer_metadata_smoke` / `installer_compile`: skipped - ISCC.exe unavailable; Inno compile skipped by harness.
- `runtime_truth_boundary_smoke` / `runtime_truth_docs_and_boundaries`: pass - Check passed.
- `full_live_runtime_ready_gate_smoke` / `missing_input_and_output_unverified_block_gate`: pass - Check passed.
- `safety_boundary_smoke` / `no_forbidden_runtime_authority`: pass - Check passed.

## Safety Boundary Notes

- no fake readiness
- no Bridge lifecycle management
- no driver/vJoy installer launch
- no cloud AI/LLM
- no auto-save
- Full Live Runtime Ready proof gate remains the readiness authority
