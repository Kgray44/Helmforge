# Phase 19A Full Product Acceptance Inventory

Phase 19A begins Final Integration Kraken / Full Acceptance Sweep with an inventory-only pass. This document records current product coverage against the prompt-book and recovered rebuild expectations. It does not implement Phase 19B harness work, runtime behavior, new hardware polling, vJoy/output behavior changes, Bridge lifecycle management, driver/vJoy installer launch, recorder capture/encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or unsupported runtime activation.

Telemetry remains the truth surface. Simulation mode remains available. The Full Live Runtime Ready proof gate remains the only authority for full runtime readiness. vJoy detected does not equal output verified. Physical input alone is not full readiness. fake/test paths are not real readiness, and there is no fake readiness.

Acceptance status vocabulary:

- Pass
- Partial
- Deferred Truthfully
- Blocked
- Not Applicable

## Acceptance Matrix

| Area | Prompt-book expectation | Current implementation status | Evidence / files | Test coverage | Runtime truth / safety notes | Remaining gaps | Acceptance status |
|---|---|---|---|---|---|---|---|
| App shell | Desktop shell with sidebar pages, header status, ASSISTANT Helm launcher, footer Import/Revert/Save, scrollable page bodies, clear chips/actions | Main shell defines all expected pages, reuses page instances, exposes top header/status/assistant cluster, and keeps footer actions separate from status chips | `v3_app/ui/shell.py`, `v3_app/ui/header.py`, `v3_app/ui/status_chips.py`, `v3_app/theme/qss.py`, `README.md` | `tests/test_phase4_app_shell.py`, `tests/test_phase17a_product_polish_layout_qa.py`, `tests/test_phase17b_motion_performance_polish.py`, `tests/test_phase17c_final_product_qa_packaging_readiness.py` | Shell status is display-only and does not imply Bridge lifecycle control or runtime readiness | Phase 19B should smoke navigation from source and packaged app in one run | Pass |
| Runtime setup | Launch without HOTAS/vJoy, preserve simulation fallback, show missing hardware truth, keep Full Live Runtime Ready gate conservative | Runtime setup/preflight surfaces show physical input, Bridge telemetry, virtual output, output loop, runtime_frame, proof summary, blocked reason, and Full Live Runtime Ready proof gate | `v3_app/pages/mapping_page.py`, `v3_app/pages/perf_diagnostics_page.py`, `shared_core/runtime/runtime_orchestrator.py`, `shared_core/runtime/runtime_readiness.py`, `scripts/runtime_setup_check.ps1` | `tests/test_phase14d_input_boundary_freeze.py`, `tests/test_phase15d_output_boundary_freeze.py`, `tests/test_phase16d_full_live_runtime_ready_gate.py`, `tests/test_phase18d_final_packaging_qa.py` | vJoy detected does not equal output verified. Physical input alone is not full readiness. Output intent is not output write proof. Full Live Runtime Ready proof gate blocks fake or partial proof | Real hardware acceptance still needs live machine evidence in Phase 19B or later | Pass |
| Mapping | Axis/button/hat routes, physical input display, virtual output intent display, runtime setup/preflight truth, no fake output write claims | Mapping page contains axis routes, button routes, hat routes, physical input fields, output intent fields, output loop truth, and proof-gate copy | `v3_app/pages/mapping_page.py`, `v3_app/pages/live_monitor_data.py`, `shared_core/workspace.py`, `shared_core/runtime/output_backend.py` | `tests/test_phase5_mapping_page.py`, `tests/test_phase6b_mapping_editor_persistence.py`, `tests/test_phase14c_physical_input_ui_integration.py`, `tests/test_phase16b_runtime_frame_telemetry_ui.py`, `tests/test_phase16d_full_live_runtime_ready_gate.py` | Output intent is shown as intent only unless output loop/write proof exists; fake output verification cannot become real output verified | Phase 19B should exercise route editing plus diagnostics copy in one acceptance path | Pass |
| Modes / Base Tuning / Filtering / Combat Profile / Profiles | Core tuning pages exist, recovered fields are present, graphs render where applicable, linear reference remains y=x, workspace dirty/saved state works | Pages are present in the shell and keep simulation-first tuning values. Tuning and graph helpers are shared where practical | `v3_app/pages/modes_page.py`, `v3_app/pages/base_tuning_page.py`, `v3_app/pages/filtering_page.py`, `v3_app/pages/combat_profile_page.py`, `v3_app/pages/profiles_page.py`, `v3_app/pages/graph_widgets.py`, `v3_app/services/app_state.py` | `tests/test_phase6_core_tuning_pages.py`, `tests/test_phase3_tuning_math_pipeline.py`, `tests/test_phase17a_product_polish_layout_qa.py` | These pages shape pipeline intent and workspace state; they do not prove hardware input or output writes | Phase 19B should validate representative save/revert/dirty flows across all tuning pages | Pass |
| Conditional Rules | Example rule support, rule model, enable/disable/status counts, rule injections into stack metadata where implemented, no unintended Helm mutation | Conditional Rules page and evaluator exist, with metadata surfaced into downstream stack/runtime contexts where implemented | `v3_app/pages/conditional_rules_page.py`, `shared_core/rules.py`, `shared_core/runtime/runtime_orchestrator.py`, `v3_app/helm/helm_overlay.py` | `tests/test_phase7_conditional_rules_page.py`, `tests/test_phase7_rule_evaluation.py`, `tests/test_phase10c_helm_guided_review_apply_revert.py`, `tests/test_phase16a_runtime_orchestrator_simulation_path.py` | Helm recommendations are staged in memory and do not auto-save or silently mutate rules | Phase 19B should run a full conditional-rule acceptance scenario with stack preview | Pass |
| Effective Response Stack | One selected axis at a time, stage cards, raw/final graph, freeze behavior, metadata preview, no twitch/layout rebuild regression | Stack page has selected-axis stack cards, graph surfaces, freeze behavior, physical input preview, runtime_frame summary, and hidden update skip tracking | `v3_app/pages/effective_response_stack_page.py`, `v3_app/pages/graph_widgets.py`, `v3_app/services/perf_diagnostics.py` | `tests/test_phase8_effective_response_stack_page.py`, `tests/test_phase17b_motion_performance_polish.py`, `tests/test_phase17c_final_product_qa_packaging_readiness.py` | Stack preview is diagnostic pipeline truth, not output write proof or Full Live Runtime Ready proof | Phase 19B should verify freeze and routine update stability in the same app session | Pass |
| Live Monitor | Raw input trace, raw vs final overlay, axis levels, buttons/hats, runtime_frame truth, Live Overlay card, no fake vJoy output claims | Live Monitor shows simulation/physical input fields, raw/final traces, buttons/hats, runtime_frame/output truth, and Live Overlay controls with conservative labels | `v3_app/pages/live_monitor_page.py`, `v3_app/pages/live_monitor_data.py`, `v3_app/overlay/live_overlay_window.py`, `v3_app/overlay/overlay_renderer.py` | `tests/test_phase9_live_monitor_page.py`, `tests/test_phase12c_live_overlay_polish_boundary.py`, `tests/test_phase14c_physical_input_ui_integration.py`, `tests/test_phase16b_runtime_frame_telemetry_ui.py`, `tests/test_phase17b_motion_performance_polish.py` | Final output intent is not labeled as written output unless output loop/write proof exists | Real hardware trace acceptance remains dependent on available HOTAS/vJoy proof | Pass |
| Helm | Top-right ASSISTANT overlay, deterministic local intelligence, symptom chips, follow-ups, grouped recommendations, exact diffs, in-memory apply/revert, no cloud AI/LLM, no auto-save | Helm launches as an overlay/modal from the ASSISTANT cluster and keeps recommendations local, staged, and reversible in memory | `v3_app/helm/helm_overlay.py`, `v3_app/ui/header.py`, `v3_app/ui/shell.py`, `v3_app/services/help_docs.py` | `tests/test_phase10a_helm_overlay_foundation.py`, `tests/test_phase10b_helm_intelligence_expansion.py`, `tests/test_phase10c_helm_guided_review_apply_revert.py`, `tests/test_phase10e_helm_final_polish_boundary.py`, `tests/test_phase17a_product_polish_layout_qa.py`, `tests/test_phase17b_motion_performance_polish.py` | No cloud AI/LLM behavior. no auto-save. no conditional rule auto-editing beyond explicit in-memory draft application | Phase 19B should include a complete Helm apply/revert acceptance scenario | Pass |
| Live Overlay | Card, config dialog, detached app-owned Qt renderer, shared axis colors, truthful hotkey/click-through states, no game injection, no graphics API hooking, no screen capture | Live Overlay card, configuration dialog, and detached renderer exist; unsupported hotkey/click-through/game integration states are labeled conservatively | `v3_app/overlay/config_dialog.py`, `v3_app/overlay/live_overlay_window.py`, `v3_app/overlay/overlay_renderer.py`, `v3_app/pages/live_monitor_page.py` | `tests/test_phase12a_live_overlay_foundation.py`, `tests/test_phase12b_live_overlay_window_renderer.py`, `tests/test_phase12c_live_overlay_polish_boundary.py`, `tests/test_phase17b_motion_performance_polish.py` | App-owned overlay only. no game injection. no graphics API hooking. no screen capture. Hotkey/click-through are not claimed as verified unless implemented | Real global hotkey and verified click-through remain Deferred Truthfully | Pass |
| Flight Recorder | Recorder Settings, Axis Overlay, Recording Library, Clip Preview, simulated export, metadata-only preview, no real capture/video encoding/hotkey registration | Flight Recorder page and artifact/index preview exist with simulated export and metadata-only labels | `v3_app/pages/flight_recorder_page.py`, `shared_core/recording.py`, `v3_app/services/help_docs.py` | `tests/test_phase13a_flight_recorder_ui_foundation.py`, `tests/test_phase13b_recorder_backend_hindsight_foundation.py`, `tests/test_phase13c_recorder_compositor_simulated_export.py`, `tests/test_phase13d_flight_recorder_boundary_freeze.py`, `tests/test_phase17c_final_product_qa_packaging_readiness.py` | No real capture. no video encoding. no recorder hotkey registration. Simulated artifacts are never presented as real recordings | Real screen capture/video hindsight remains Deferred Truthfully | Pass |
| Help / Docs | Local deterministic search, categories/topics, runtime setup, runtime indicators, Helm, Live Overlay, Flight Recorder, Perf / Diagnostics, packaging/source truth, no cloud/web/LLM search | Help / Docs service contains local articles and deterministic search, with runtime and packaging truth carried forward | `v3_app/services/help_docs.py`, `v3_app/pages/help_docs_page.py`, `docs/HelmForge/help/`, `README.md` | `tests/test_phase11a_help_docs_foundation.py`, `tests/test_phase11c_help_perf_boundary_freeze.py`, `tests/test_phase17c_final_product_qa_packaging_readiness.py` | Search is local; docs distinguish output intent, output write proof, fake/test paths, and Full Live Runtime Ready | Phase 19B should do a final article search/readback sweep | Pass |
| Perf / Diagnostics | Active page, runtime truth, Bridge telemetry, physical input, virtual output, output loop, runtime_frame, Full Live Runtime Ready gate, timing summaries, hidden-page skips, Copy Diagnostics | Perf / Diagnostics includes runtime truth/proof fields, Bridge telemetry, output/input status, timing summaries, hidden-skip counters, and copy diagnostics text | `v3_app/pages/perf_diagnostics_page.py`, `v3_app/services/perf_diagnostics.py`, `bridge_app/main.py`, `shared_core/bridge_files.py` | `tests/test_phase11b_perf_diagnostics_page.py`, `tests/test_phase11c_help_perf_boundary_freeze.py`, `tests/test_phase16b_runtime_frame_telemetry_ui.py`, `tests/test_phase16d_full_live_runtime_ready_gate.py`, `tests/test_phase17b_motion_performance_polish.py` | Diagnostics are observational. Process presence is a hint only; telemetry/runtime_frame are truth surfaces | Phase 19B should copy diagnostics from source and packaged app if possible | Pass |
| Packaging | Source launch, PyInstaller one-folder build, packaged smoke, build script, Inno script, installer compile status, icon status, user data separation, no driver installer, no Bridge lifecycle management | Phase 18D reports one-folder output at `packaging/dist/HelmForge/`, packaged executable `packaging/dist/HelmForge/HelmForge.exe`, packaged smoke passed, Inno script exists, LocalAppData user data plan exists | `packaging/README.md`, `packaging/build_release.ps1`, `packaging/inno/helmforge.iss`, `packaging/pyinstaller/README.md`, `docs/HelmForge/phase-18d-final-packaging-qa-report.md`, `v3_app/services/app_paths.py` | `tests/test_phase18a_packaging_foundation.py`, `tests/test_phase18b_pyinstaller_packaged_smoke.py`, `tests/test_phase18c_icons_installer_metadata.py`, `tests/test_phase18d_final_packaging_qa.py` | Installer does not install drivers/vJoy, does not install services, does not configure login auto-start, and does not manage Bridge lifecycle | `assets/app_icon.ico is missing`; Inno compile is skipped if `ISCC.exe` is unavailable; installer install/uninstall execution is not verified | Partial |
| Layout / Performance | No obvious overlap/clipping, scrollable tall pages, stable graphs, hidden-page skip behavior, overlay timer discipline, no expensive hidden loops | Phase 17A-17C reports and tests cover layout polish, page reuse, hidden update skips, graph update discipline, overlay timer stop behavior, and offscreen smoke | `v3_app/ui/shell.py`, `v3_app/pages/graph_widgets.py`, `v3_app/pages/live_monitor_page.py`, `v3_app/pages/effective_response_stack_page.py`, `v3_app/services/perf_diagnostics.py` | `tests/test_phase17a_product_polish_layout_qa.py`, `tests/test_phase17b_motion_performance_polish.py`, `tests/test_phase17c_final_product_qa_packaging_readiness.py` | Performance instrumentation is diagnostic only and does not create runtime authority | Phase 19B should run common-size/offscreen smoke and packaged navigation if available | Pass |
| Safety boundaries | No Bridge lifecycle management, no driver/vJoy installer launch, no fake output verification, no fake Full Live Runtime Ready, no game injection, no graphics API hooking, no cloud AI/LLM, no auto-save, simulation mode remains available | Boundary tests and docs repeatedly preserve no unsupported authority across runtime, recorder, overlay, Helm, and packaging phases | `README.md`, `docs/HelmForge/phase-16d-full-live-runtime-ready-boundary-freeze-report.md`, `docs/HelmForge/phase-18d-final-packaging-qa-report.md`, `tests/test_phase16d_full_live_runtime_ready_gate.py`, `tests/test_phase18d_final_packaging_qa.py` | `tests/test_phase9k_boundary_freeze.py`, `tests/test_phase10e_helm_final_polish_boundary.py`, `tests/test_phase13d_flight_recorder_boundary_freeze.py`, `tests/test_phase15d_output_boundary_freeze.py`, `tests/test_phase16d_full_live_runtime_ready_gate.py` | no fake output verification. no fake Full Live Runtime Ready. no game injection. no graphics API hooking. no cloud AI/LLM. no auto-save. simulation mode remains available | Phase 19B should consolidate these into a single full acceptance sweep result | Pass |
| Phase 19B Kraken harness | A later phase may run a full end-to-end acceptance harness across source, packaged app, pages, docs, packaging, runtime truth, and boundaries | Not implemented in Phase 19A by design | This inventory document | `tests/test_phase19a_acceptance_inventory.py` | Phase 19A is inventory only and does not add runtime activation | Full Kraken execution remains next | Deferred Truthfully |
| Real hardware acceptance on this machine | Real HOTAS and real vJoy path proof require live hardware/software availability and the Phase 16 readiness gate | Existing code supports guarded physical input and guarded output verification semantics, but this inventory does not claim real Full Live Runtime Ready | `shared_core/runtime/physical_input.py`, `shared_core/runtime/vjoy_output.py`, `shared_core/runtime/runtime_readiness.py`, `scripts/runtime_setup_check.ps1` | `tests/test_phase14d_input_boundary_freeze.py`, `tests/test_phase15b_real_vjoy_detection_guarded_verification.py`, `tests/test_phase16c_verified_runtime_path.py`, `tests/test_phase16d_full_live_runtime_ready_gate.py` | Hardware detection alone is not readiness. Full Live Runtime Ready stays false unless all proof conditions pass | Live hardware acceptance may be Blocked if HOTAS/vJoy proof is unavailable | Blocked |
| Unsupported scope | Driver install, Bridge lifecycle automation, service/tray/autostart, cloud AI, real recorder capture, game injection, graphics API hooks | Not implemented and intentionally excluded | `README.md`, phase boundary reports, tests | Boundary tests across Phases 9-18 | Not Applicable to this product phase unless explicitly scoped later | None for Phase 19A | Not Applicable |

## App Shell Inventory

The app shell includes the expected sidebar pages: Mapping, Modes, Base Tuning, Filtering, Combat Profile, Profiles, Conditional Rules, Effective Response Stack, Live Monitor, Flight Recorder, Help / Docs, and Perf / Diagnostics. The header presents the HelmForge title/subtitle, STATUS cluster, and ASSISTANT/Helm launcher. Footer actions include Import, Revert, and Save. Page bodies are scrollable, and previous polish passes separated status chips from action buttons.

Evidence: `v3_app/ui/shell.py`, `v3_app/ui/header.py`, `v3_app/ui/status_chips.py`, `tests/test_phase4_app_shell.py`, `tests/test_phase17a_product_polish_layout_qa.py`.

## Runtime Setup Inventory

The current runtime setup is conservative. The app launches without HOTAS, without real vJoy output verification, without Bridge auto-launch, and without Full Live Runtime Ready proof. Simulation mode remains available. Missing HOTAS/vJoy states are shown through runtime/preflight diagnostics. The Full Live Runtime Ready proof gate exists and blocks partial, stale, fake, or detection-only proof.

Current truth:

- Telemetry remains the truth surface.
- Command files are requests, not success proof.
- Process presence is a hint only.
- Physical input sampling does not imply output.
- Output intent is not output write proof.
- vJoy detected does not equal output verified.
- Fake/mock output is not real output.
- Full Live Runtime Ready requires the Phase 16 proof gate.
- Simulation mode remains available.
- no Bridge lifecycle management.

## Mapping Inventory

Mapping covers axis, button, and hat route surfaces. It also displays physical input truth, virtual output intent truth, runtime setup/preflight status, output loop state, fake/real verification distinction, blocked reason, and Full Live Runtime Ready proof truth. It does not claim output writes from output intent alone.

## Modes / Base Tuning / Filtering / Combat Profile / Profiles Inventory

The core tuning pages remain present and participate in the simulation-first workspace and signal pipeline. Graphs and tuning controls remain UI/pipeline surfaces, not hardware readiness proof. Linear references remain testing targets for the tuning math and graph helpers. Workspace dirty/saved behavior remains covered by prior page and state tests.

## Conditional Rules Inventory

Conditional Rules provides the rule model and page UI expected by the recovered rebuild requirements. Rule enable/disable/status counts and rule evaluation metadata feed later diagnostics where implemented. Helm does not silently mutate rules and has no auto-save authority.

## Effective Response Stack Inventory

Effective Response Stack shows selected-axis signal stages, raw/final graph context, freeze behavior, runtime diagnostics, and physical input preview when available. Phase 17B performance work preserved stable stage cards and hidden-page update skip behavior to avoid layout twitch.

## Live Monitor Inventory

Live Monitor displays simulation/physical input truth, axis levels, raw/final traces, buttons/hats, runtime_frame truth, virtual output intent/write-loop truth, and the Live Overlay card. It does not claim written vJoy output unless output loop/write proof exists.

## Helm Inventory

Helm launches from the ASSISTANT cluster as an overlay/modal. It uses deterministic local analysis, symptom chips, follow-up questions, grouped recommendations, exact before/after diffs, and in-memory apply/revert. It does not use cloud AI/LLM behavior, does not auto-save, and does not silently edit conditional rules.

## Live Overlay Inventory

Live Overlay includes the Live Monitor card, configuration dialog, detached app-owned Qt renderer, and shared axis colors. Hotkey and click-through states remain truth-labeled and are not claimed as verified unless implemented. The overlay is app-owned; there is no game injection, graphics API hooking, or screen capture.

## Flight Recorder Inventory

Flight Recorder includes Recorder Settings, Axis Overlay, Recording Library, Clip Preview, simulated artifact/export pipeline, metadata-only preview, and telemetry hindsight wording. It does not implement real recorder capture, real video encoding, playable clip export, actual desktop video hindsight buffering, or recorder hotkey registration.

## Help / Docs Inventory

Help / Docs remains local and deterministic. Articles cover Runtime Setup / vJoy Setup, Runtime Indicators, Helm, Live Overlay, Flight Recorder, Perf / Diagnostics, packaging/source launch truth, and runtime boundaries. There is no cloud/web/LLM search.

## Perf / Diagnostics Inventory

Perf / Diagnostics includes active page, runtime truth, Bridge telemetry, physical input, virtual output, output loop, runtime_frame, Full Live Runtime Ready proof gate, timing summaries, hidden-page skip counters, and Copy Diagnostics. Diagnostic copy preserves the distinction between telemetry truth, process hints, output intent, and output writes.

## Packaging Inventory

Phase 18D records the current packaging truth:

- one-folder packaged output: `packaging/dist/HelmForge/`
- packaged executable: `packaging/dist/HelmForge/HelmForge.exe`
- packaged smoke command: `packaging/dist/HelmForge/HelmForge.exe --smoke-exit-ms 250`
- packaged smoke passed
- build script: `packaging/build_release.ps1`
- Inno script: `packaging/inno/helmforge.iss`
- Inno compile is skipped honestly if `ISCC.exe` is unavailable
- `assets/app_icon.ico is missing`
- user data is planned under `%LocalAppData%\HelmForge`
- install path is planned under `%LocalAppData%\Programs\HelmForge`
- no driver/vJoy installer launch
- no Bridge lifecycle management

## Layout / Performance Inventory

Phase 17A through Phase 17C covered visual QA, layout polish, page reuse, hidden-page update discipline, graph update discipline, Helm and Live Overlay smoothness, Flight Recorder interaction polish, and Perf / Diagnostics timing/skip counters. Phase 19B should re-run source and packaged navigation smoke, but Phase 19A records the existing coverage as accepted for inventory purposes.

## Safety Boundary Acceptance

Safety boundary acceptance is Pass for Phase 19A.

- no Bridge lifecycle management
- no driver/vJoy installer launch
- no fake output verification
- no fake Full Live Runtime Ready
- no fake readiness
- no game injection
- no graphics API hooking
- no screen capture
- no real recorder capture
- no video encoding
- no cloud AI/LLM
- no auto-save
- no automatic Bridge launch
- no UI-launched child process
- no Windows Service install
- no login auto-start
- no tray manager
- no StartBridge / StopBridge / RestartBridge behavior
- no unsupported runtime activation
- simulation mode remains available

## Known Gaps

- `assets/app_icon.ico is missing`; final EXE/installer/shortcut icon embedding remains incomplete until an ICO is supplied.
- Inno Setup compile depends on `ISCC.exe`; if unavailable, installer compile is skipped and documented rather than faked.
- Installer install/uninstall execution has not been performed.
- Real hardware Full Live Runtime Ready proof is not claimed by this inventory and may be blocked by missing HOTAS/vJoy availability.
- Real recorder capture/video encoding remain deferred truthfully.
- Live Overlay global hotkey and verified click-through remain deferred truthfully.
- Signed production installer/release-channel metadata remain future release work.

## Recommendation For Phase 19B

Phase 19B ran the Final Integration Kraken acceptance harness across source launch, packaged launch, all pages, Help / Docs search, Perf / Diagnostics copy text, runtime truth, the Full Live Runtime Ready proof gate, packaging smoke, and installer metadata. Phase 19C consumes that artifact set for final corrections, and Phase 19D should make the final acceptance / release-candidate freeze decision. Packaging success, process presence, physical input detection, vJoy detection, output intent, and fake/test paths still must not be treated as runtime readiness.

## Verification Results

Phase 19A verification run:

- `python -m pytest` passed: 398 passed.
- `python -m pytest tests\test_phase18d_final_packaging_qa.py` passed: 4 passed.
- `python -m pytest tests\test_phase19a_acceptance_inventory.py` passed: 4 passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -DryRun` passed. It reported PyInstaller available, `assets\app_icon.ico` missing, and no build or installer success claimed in dry-run mode.
- `.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250` passed.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` passed.
- `python -m bridge_app.main --once` passed.
- `python -m bridge_app.main --run-for-ms 250` passed.
- `python -m bridge_app.main --status` passed and reported `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` passed. It detected installed vJoy and Thrustmaster software, reported HOTAS not connected, and kept Full Live Runtime Ready governed by the Phase 16 proof gate.
- `git diff --check` passed.
