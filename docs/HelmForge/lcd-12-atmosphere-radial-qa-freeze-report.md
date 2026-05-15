# LCD-12 Atmosphere, Radial Menu, Accessibility, and QA Freeze

## Summary

LCD-12 adds the final Liquid Command Deck polish layer without changing runtime authority. The work is limited to optional route-accent atmosphere, an optional navigation-only quick switch wheel, reduced-motion/accessibility hardening, and final QA documentation.

## atmosphere effects added

- Shell-level static route accents are applied from the active Liquid mode.
- OFF disables optional atmosphere entirely.
- REDUCED keeps atmosphere static and minimal.
- STANDARD uses static accent glow and no background drift.
- CINEMATIC exposes safe slow-drift metadata only; no heavy effect is required for the default experience.
- Diagnostics/raw panels are kept calm and are not placed on high-frequency atmosphere loops.

## radial menu status

The optional radial menu is implemented as the Liquid quick switch wheel. It is disabled by default and can be enabled through the internal quick-wheel seam. It lists major modes only: Preflight, Mapping, Tuning, Analysis, Recorder, and Support.

The wheel is navigation only. It does not apply, save, revert, manage Bridge state, write vJoy, verify output, or start recorder capture.

## motion intensity behavior

- OFF: no optional atmosphere animation, no radial animation, no shimmer/glare loops, and navigation remains immediate.
- REDUCED: static/minimal atmosphere, no drift, no shimmer loops, and the quick switch wheel opens without animation.
- STANDARD: LCD-11 page/live motion remains active; atmosphere is static and cheap; quick switch motion is modest style-only metadata.
- CINEMATIC: safe polish metadata may enable slow drift/shimmer hooks, still without risky blur, distortion, or layout animation.

## reduced-motion/accessibility behavior

Motion OFF and REDUCED preserve readable status text, visible focus states, direct dock navigation, deterministic route state, and Escape dismissal for the optional quick switch wheel. Critical state is represented through text and status roles, not animation alone.

## performance safeguards

- No full-app real-time blur.
- No QGraphicsBlurEffect on root/app/page containers.
- No QGraphicsOpacityEffect on root/page containers.
- No QPropertyAnimation on complex layout geometry.
- No animated layout width/height.
- No hidden-page atmosphere work.
- No high-frequency atmosphere timer.
- Live Monitor visual frame discipline from LCD-9/LCD-11 is preserved.
- Graph/model rebuilds remain dirty/data-driven.
- Diagnostics remain low cadence/on demand.

## Final QA Checklist

See `docs/HelmForge/liquid-command-deck-final-qa-checklist.md`.

## packaged smoke result

Passed.

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean`
- `.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250`

The clean one-folder PyInstaller build completed. The packaged executable smoke exited successfully. Inno Setup was not available, so no installer was created.

## physical HOTAS validation

Physical/manual continuous HOTAS-axis movement was not performed. The runtime setup dry run reported HOTAS Not Connected and vJoy Detected.

## Files Changed

- `v3_app/liquid/motion.py`
- `v3_app/liquid/atmosphere.py`
- `v3_app/liquid/quick_switch_wheel.py`
- `v3_app/liquid/app_shell.py`
- `v3_app/liquid/theme_tokens.py`
- `tests/test_lcd_12_atmosphere_radial_qa_freeze.py`
- `docs/HelmForge/lcd-12-atmosphere-radial-qa-freeze-report.md`
- `docs/HelmForge/liquid-command-deck-final-qa-checklist.md`

## Tests Run

- `python -m pytest`
- `python -m pytest tests/test_lcd_12_atmosphere_radial_qa_freeze.py`
- `python -m pytest tests/test_lcd_12_atmosphere_radial_qa_freeze.py tests/test_lcd_11_page_transitions_live_motion.py tests/test_lcd_10_microinteractions.py tests/test_lcd_9_support_help_diagnostics.py tests/test_phase19d_final_acceptance_report.py tests/test_lcd_3_navigation_mode_architecture.py tests/test_lcd_7_analysis_command_pages.py tests/test_lcd_7w_performance_live_monitor_profiles.py tests/test_post_rc_perf_1a_live_ui_scheduler.py tests/test_post_rc_perf_1a_live_monitor_cadence.py tests/test_post_rc_perf_1a_liquid_analysis_cadence.py tests/test_post_rc_perf_1a_effective_stack_cadence.py tests/test_post_rc_perf_1a_graph_preview_efficiency.py tests/test_post_rc_perf_1a_tuning_page_cadence.py tests/test_post_rc_perf_1a_shell_telemetry_dirty_gating.py tests/test_hf_lrdc_1c_live_monitor_frame_dedupe.py tests/test_hf_lrdc_6d_periodic_live_graph_stall_repair.py`
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- `python -m bridge_app.main --status`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- `git diff --check`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean`
- `.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250`
- Bounded normal-display route sweep across 17 routes in OFF, REDUCED, and STANDARD.

## Remaining Known Risks

- Optional quick switch wheel is an internal seam, not a full settings UI.
- CINEMATIC atmosphere is intentionally conservative and does not add broad background drift by default.
- Physical HOTAS validation depends on hardware availability.

## Final LCD Track Acceptance Summary

The LCD track remains a full Liquid Command Deck recomposition. Legacy pages remain fallback/reference surfaces, not the primary Liquid page compositions.

## runtime truth preservation

LCD-12 adds no runtime authority. It adds no hardware polling changes, no vJoy/output behavior changes, no output verification changes, no Full Live Runtime Ready shortcut, no Bridge lifecycle management, no recorder capture/encoding changes, no cloud AI/LLM behavior, no auto-save, and no fake readiness/recording/output claims.

Explicit freeze statements:

- no runtime authority added
- no hardware polling changes
- no vJoy/output behavior changes
- no output verification changes
- no Full Live Runtime Ready shortcut
- no Bridge lifecycle management
- no recorder capture/encoding changes
- no cloud AI/LLM behavior
- no auto-save
- no fake readiness/recording/output claims
