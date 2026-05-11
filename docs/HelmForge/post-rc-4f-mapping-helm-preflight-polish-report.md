# Post-RC 4F Mapping / Helm / Preflight Polish Report

## Summary

This pass implements the first page-by-page walkthrough fixes for Global Shell, Mapping, Preflight, and Helm.

## Fixed

- Sidebar runtime status now refreshes from Bridge telemetry instead of staying on the startup label.
- Header/top status chips use success tone when the runtime is live verified.
- Footer now shows a saved/unsaved workspace chip and includes Apply Workspace next to Save Workspace.
- Apply Workspace writes a temporary applied draft and sends a Bridge `ReloadConfig` command without saving the main workspace file.
- The default app width is reduced to 1152 while preserving the 800 default height.
- Setup now starts with a dedicated Preflight page.
- Mapping no longer embeds the Runtime Setup / Preflight card.
- Mapping status chips show the active workspace name, Live Verified, and vJoy Verified when verified.
- Axis Routing removes Live Raw and Final Intent columns.
- Button Routing removes Raw and Output columns.
- Routing rows are taller for easier scanning.
- HOTAS diagram marker geometry is clamped inside the diagram bounds.
- Clicking a HOTAS diagram marker opens a graphical remap card with the existing inspector/editor data.
- Helm now opens as an in-app right pane with scrim, blur, slide, and LED pulse hooks instead of a top-level dialog-style window.
- Helm wide layout puts What I'd Change in a second column and Apply / Revert across the bottom.

## Preflight Data Review

Device Info:
- Target hardware is real workspace metadata and is useful.
- Input device currently comes from runtime preflight status. If it says Waiting for HOTAS input while hardware is connected, the issue is upstream discovery or live sampler state, not the page.
- Output backend comes from runtime output status. vJoy detected without output verification is intentionally not shown as ready.
- Output proof is truthful but depends on guarded verification; no UI-only fix should mark it verified.

Pipeline Info:
- Runtime truth and runtime mode are live runtime fields and useful.
- Workspace is the active workspace/profile id and is useful.
- Readiness gate is derived from live output verification only in this page; full Phase 16 readiness proof remains the deeper gate.

Data:
- Axis, button, and hat route counts are real workspace data and useful.
- Rules enabled is real workspace data and useful.

Debugging:
- Warnings and errors are real runtime status fields.
- Source config is real shell state.
- Saved state is real shell state.

Items that still need runtime-side work if they remain blank or stale during live use:
- Physical HOTAS input detection freshness.
- Runtime frame source, proof, and safety details beyond the summary gate.
- Real output verification proof and last output write details.
- Bridge config match details after Apply Workspace until the next telemetry tick confirms the reload.

## Verification

- `python -m pytest -q tests/test_post_rc_4f_mapping_helm_preflight_walkthrough.py`
- `python -m pytest -q tests/test_phase5_mapping_page.py tests/test_post_rc_4c_global_helm_walkthrough_polish.py tests/test_post_rc_4d_control_pages_polish.py tests/test_live_runtime_hardware_bridge.py tests/test_phase10a_helm_overlay_foundation.py tests/test_phase10c_helm_guided_review_apply_revert.py tests/test_phase10e_helm_final_polish_boundary.py`
- `python -m pytest -q tests/test_post_rc_1a_global_ui_foundation.py tests/test_phase17a_product_polish_layout_qa.py tests/test_phase17b_motion_performance_polish.py tests/test_phase17c_final_product_qa_packaging_readiness.py`

## Runtime Truth Preservation

Mapping edits remain workspace draft changes. Apply Workspace reloads a temporary draft for trial use, while Save Workspace remains the explicit persistent write. vJoy detected is not treated as output verification, and Full Live Runtime Ready remains gated by the existing runtime proof chain.
