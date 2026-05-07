# HelmForge

**HOTAS Control Panel V3**

HelmForge is a safe rebuild of the lost HOTAS Control Panel project. The recovered HOTAS Control Panel V2 forensic notes, raw recovery chats, and PNG screenshot evidence are the governing reconstruction references for this repository.

The current rebuild state includes Phase 16C verified runtime-path proof semantics, Phase 16B runtime_frame telemetry/UI surfaces, Phase 16A runtime orchestrator contract and end-to-end simulation path, the Phase 15D output integration boundary freeze and Phase 16 readiness pass, Phase 15C controlled output write-loop integration, Phase 15B guarded real vJoy detection/write-path verification, Phase 15A virtual output backend contract, Phase 14C read-only physical input UI integration, Phase 14B physical input sampling/normalization foundation, Phase 14A physical HOTAS input backend/device-selection foundation, Phase 13D Flight Recorder library/preview polish and boundary freeze, Phase 13C overlay compositor and simulated export foundation, Phase 13B Flight Recorder backend-interface and telemetry hindsight foundation, Phase 13A Flight Recorder UI/state/settings/library/preview shell, Phase 12C Live Overlay polish and boundary freeze, Phase 12B detached Live Overlay window and renderer, Phase 12A Live Overlay core/config foundation, Phase 11C Help / Docs + Perf / Diagnostics polish and boundary freeze, Phase 11B Perf / Diagnostics page, Phase 11A Help / Docs foundation, Phase 10E Helm final polish and boundary freeze, Phase 10D Helm context integration, Phase 10C Helm guided review/apply/revert polish, Phase 10B Helm intelligence expansion, Phase 10A Helm Assistant Overlay foundation, Phase 9K final stabilization and boundary freeze, Phase 9J Live Monitor diagnostic UX polish, Phase 9I Bridge process presence diagnostics, Phase 9H Bridge-owned real device discovery dry-run, Phase 9G Bridge lifecycle ownership design record, Phase 9F Bridge lifecycle presence and health refinement, Phase 9E Bridge command acknowledgement/status refinement, Phase 9D safe UI-to-Bridge command seam, Phase 9C UI Bridge telemetry connection, Phase 9B Bridge background process skeleton, Phase 9 Live Monitor page, Phase 8 Effective Response Stack page, Phase 7 Conditional Rules page/evaluator, Phase 6B Mapping editor polish, Phase 6 core tuning pages, Phase 5 Mapping page, Phase 4 PySide6 visual shell, Phase 2B Bridge/UI architecture boundary contracts, Phase 2A local runtime setup tooling, and the Phase 3 tuning math and signal pipeline. Phase 9C lets the UI read Bridge telemetry JSON when fresh and fall back to simulation when telemetry is missing, stale, or invalid. Phase 9D lets the UI request safe Bridge status/config/preflight commands through a JSON command file without claiming command completion. Phase 9E echoes consumed Bridge commands through telemetry so the UI can distinguish requested, awaiting telemetry, completed, failed, and ignored-stale states by request ID. Phase 9F exposes compact Bridge health details such as connected/missing/stale/invalid/error, telemetry age, stale threshold, runtime truth, and output verification truth. Phase 9G is design-only and records lifecycle ownership options, wording rules, and safety gates before any launch/service/tray/autostart behavior. Phase 9H publishes read-only HOTAS discovery truth through Bridge telemetry. Phase 9I adds process-presence hints and conservative Live Monitor diagnosis text while keeping telemetry as the truth surface. Phase 9J tightens Live Monitor diagnostic labels, severity categories, manual-launch guidance, command matching display, and discovery-only wording. Phase 9K freezes the Phase 9 boundary with regression tests and documentation consistency checks. Phase 10 is Helm Assistant Overlay according to the prompt book; Phase 10A wires Helm from the top-right ASSISTANT cluster as an overlay/modal assistant, not a sidebar page. Phase 10B expands Helm into a deterministic, local diagnostic assistant with grouped recommendations, confidence scoring, follow-up questions, findings, risks, and richer before/after diffs. Phase 10C makes the review workflow clearer: recommendations are staged before apply, group selection cascades to diffs, selected counts update immediately, Apply Selected Changes only modifies the in-memory draft, and Revert Last Helm Changes restores the last Helm batch. Phase 10D adds read-only context extraction for workspace values, modes, conditional rules, optional response stack snapshots, and runtime diagnostics with evidence labels. Phase 10E finalizes Helm for Phase 10 with tighter copy, source-grouped findings, better edge states, final boundary tests, and documentation consistency. Phase 11A implements Help / Docs foundation only with local built-in documentation, category browsing, deterministic search, and the Runtime Setup / vJoy Setup article. Phase 11B implements Perf / Diagnostics page only with observational runtime truth, Bridge telemetry status, safe preflight refresh, timing summaries, hidden-page skip visibility, and copy diagnostics text. Phase 11C completes Phase 11 with cross-links, terminology cleanup, final boundary tests, and final documentation consistency. Phase 12A adds shared Live Overlay config/core models, axis colors, telemetry history buffering, trace building, a Live Monitor overlay card, and a configuration dialog shell. Phase 12B adds an app-owned detached overlay window and Qt renderer for those traces. Phase 12C finalizes Live Overlay copy, close-state status handling, truth labels, docs, and boundary tests. Phase 13A adds Flight Recorder UI/state/settings/library/preview shell only. Phase 13B adds capture backend interfaces, a missing backend, an injected simulated backend that can write clearly labeled non-video JSON manifests, a recorder artifact model, telemetry hindsight buffering, and a recorder controller. Phase 13C adds a simulated compositor/exporter that writes non-video export bundles with manifest, overlay trace JSON, summary, and preview metadata. Phase 13D finalizes the Recording Library artifact index, metadata-only Clip Preview, simulated export wording, Help / Docs copy, final report, and boundary tests. Phase 14A adds read-only physical input backend interfaces, fake/missing/Windows PnP discovery backends, centralized Thrustmaster HOTAS One matching, and in-memory device selection diagnostics. Phase 14B adds input sample models, deterministic normalization helpers, fake on-demand sample snapshots, and read-only sampling diagnostics. Phase 14C surfaces those read-only physical samples in Mapping, Live Monitor, Effective Response Stack preview when available, Perf / Diagnostics, Copy Diagnostics, and Help / Docs while preserving simulation fallback. Phase 15D finalizes virtual output terminology, fake/real verification truth, output-loop safety labels, diagnostics, and Phase 16 readiness notes. Phase 16A adds `shared_core.runtime.runtime_orchestrator`, which can build compact runtime frames from simulation or guarded physical samples, run the shared workspace pipeline, produce a final `VirtualOutputIntent`, and optionally hand that intent to an explicitly enabled fake output loop in tests. Phase 16B publishes the compact `runtime_frame` summary through Bridge telemetry and lets Mapping, Live Monitor, Perf / Diagnostics, and Help / Docs display runtime-frame truth. Phase 16C adds proof fields for input, pipeline, output verification, output-loop state, runtime candidate, and blocked reason. The current app still does not implement automatic output enablement, Full Live Runtime Ready, continuous output on startup, uncontrolled real vJoy output, real desktop capture, video encoding, playable clip export, actual desktop video hindsight buffering, recorder hotkey registration, game injection, graphics API hooking, screen capture, cloud AI, LLM tuning, or installer packaging.

Phase 15A adds the virtual output backend contract, output intent model, missing output backend, and fake output backend for deterministic tests. Fake/mock verification is not real vJoy verification, output intent is not output write proof, output_verified remains false in normal runtime, and Full Live Runtime Ready remains false.

Phase 15B adds guarded real vJoy detection and guarded write-path verification through an optional provider seam. App startup does not require a vJoy dependency, vJoy detection is not output verification, real output verification requires guarded write success and neutral restore, and no continuous output write loop is implemented. Full Live Runtime Ready remains false.

Phase 15C adds controlled output write-loop integration. The loop starts disabled, requires explicit enablement and a verified backend, rate-limits writes, records write/failure counts, attempts neutral restore on stop, and safety-stops on write failure. Fake output loops are test/dev only and are not real vJoy proof. Full Live Runtime Ready remains false unless a later end-to-end runtime phase proves both input and output.

Phase 15D completes Phase 15. Output intent is not output write proof, vJoy detection is not output verification, fake/mock output is not real vJoy output, real output verification requires guarded write success and neutral restore, and the output loop remains safety-gated.

Phase 16A begins Runtime End-to-End Live Mode by adding the runtime orchestrator contract and deterministic simulation path. It connects simulation input through mapping, tuning, filtering, modes, conditional rules, final output intent generation, and optional fake output-loop handoff for tests. Output intent is still not output write proof, real output remains gated by Phase 15 verification plus explicit enablement, and Full Live Runtime Ready remains false unless all proof conditions are met.

Phase 16B adds Bridge `runtime_frame` telemetry and UI runtime frame surfaces. The frame is compact and truth-labeled: it can be simulation-backed, output intent ready does not prove a vJoy write, output loop state is separate, stale/missing/malformed runtime_frame data falls back safely, and Full Live Runtime Ready remains false unless the complete proof chain is met.

Phase 16C connects verified input/output runtime path semantics. Physical input, pipeline success, guarded output verification, and output-loop state are separate proofs. A real-proof injected path can report `verified_runtime_candidate`, but Full Live Runtime Ready remains false because Phase 16D owns the final readiness gate. Fake/test output paths remain clearly labeled and never become real hardware readiness.

## Recovery Sources

The original app was lost. Reconstruction must be evidence-led:

- `HOTAS Control Panel Forensic Spec Set/` contains the normalized forensic documents, PDFs, raw recovered chats, and prompt book.
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/` contains screenshot evidence organized by feature area.
- `docs/recovery/` records how those sources are preserved and referenced for implementation.
- `docs/HelmForge/` is reserved for implementation notes, decisions, and phase reports.

The forensic documents and screenshots must not be destructively renamed or overwritten. If future phases need derived assets, create copies under an explicit generated or asset folder while keeping the recovered originals intact.

## Runtime Strategy

HelmForge is developed simulation-first so the UI, shared core, and tests can progress before hardware drivers are installed. Phase 14A adds optional read-only physical input detection and device selection, Phase 14B adds read-only sampling/normalization foundations with deterministic fake/test sampling, and Phase 14C displays those samples in UI surfaces when available. Phase 15A adds virtual output backend contracts and output intent models. Phase 15B adds guarded real vJoy detection and a bounded verification path. Phase 15C adds a controlled output write loop that remains disabled until explicitly enabled and requires a verified backend. Phase 15D freezes the output boundary and prepares Phase 16 readiness. Phase 16A adds a runtime orchestrator simulation path that produces final output intent without treating intent as a write. Phase 16B adds compact runtime_frame telemetry and UI display for that orchestrated path. Phase 16C adds verified-path proof fields and a conservative runtime-candidate policy while leaving final Full Live Runtime Ready to Phase 16D. Simulation mode remains valid with no HOTAS connected, no Bridge running, no input backend available, stale/error physical samples, no real virtual output backend, failed/not-attempted output verification, disabled output loop, missing runtime orchestrator telemetry, or stale/malformed runtime_frame telemetry.

Known physical HOTAS target: **Thrustmaster T-Flight HOTAS One**.

Phase 9H can run a read-only Bridge-owned discovery dry-run for that hardware. Phase 14A adds shared-core physical input backend and selection models that can recognize the supported Thrustmaster HOTAS One by VID/PID `044f:b68d` or conservative name matching. Phase 14B adds a read-only sample/snapshot model and normalization helpers, and Phase 14C lets Mapping, Live Monitor, Effective Response Stack preview, and Perf / Diagnostics show physical sample truth without output authority. Phase 15A adds output intent and virtual backend contracts, missing/fake output backends, and fake/mock verification that is explicitly not real vJoy verification. Phase 15B adds an optional guarded real vJoy backend and bounded verification path. Phase 15C adds a disabled-by-default output loop with explicit enable/disable, verification gates, bounded rate limiting, neutral restore, and safety-stop behavior. Phase 16A can build an end-to-end simulation frame and fake-output test handoff, but output writes still require the Phase 15 safety gates. These checks do not implement automatic output enablement, automatic Bridge launch, process spawning from the UI, Windows Service installation, login auto-start, installer launch, tray manager work, Start/Stop/Restart behavior, or unsupported runtime activation. No Full Live Runtime Ready support should be claimed until a later phase implements and verifies the end-to-end runtime.

The V3 workspace/config filename is `hotas_bridge_config_v3.json`. The recovered V2 notes referenced `hotas_bridge_config_v2.json`; that legacy name is preserved in schema documentation for provenance.

Official Thrustmaster setup guidance is documented in `docs/HelmForge/help/runtime-setup-hotas-driver.md`. Phase 2A local setup guidance is documented in `docs/HelmForge/phase-2a-local-driver-installation-and-runtime-verification.md`. The app links to the official Thrustmaster support page and a verified vJoy setup source; it does not silently download or run driver installers.

## Bridge/UI Split

HelmForge has two main parts:

- Bridge: owns real-time HOTAS input, workspace processing, virtual output, and telemetry.
- UI App: owns configuration, visualization, diagnostics, help/docs, recorder/overlay surfaces, and user interaction.

The Phase 9B Bridge process runs separately from the PySide6 UI and writes simulation-backed telemetry snapshots. Phase 9C adds a UI Bridge telemetry client and wires Live Monitor to use fresh Bridge telemetry, with simulation fallback for missing, stale, or invalid telemetry. Phase 9D adds safe command-file requests for `Status`, `RunPreflight`, `ReloadConfig`, `SwitchToSimulation`, and `ClearError`; unsafe commands such as `VerifyOutput`, `StartBridge`, and `StopBridge` are rejected by the UI. Phase 9E adds Bridge `last_command` telemetry, stale-command protection, and duplicate request protection so command status remains truthful. Phase 9F adds UI-visible Bridge health timing details and explanations without treating stale telemetry as live truth. Phase 9G keeps manual Bridge launch for now and documents a conservative path toward read-only presence hints, later tray/background management, and deferred Windows Service/login auto-start. Phase 9H adds Bridge-owned read-only device discovery telemetry and compact Live Monitor discovery wording. Phase 9I adds process-presence hints as diagnostics only; fresh telemetry remains stronger than any process hint, and the UI still does not own the Bridge lifecycle. Phase 9J polishes the Live State diagnostic hierarchy while preserving telemetry authority and request-id command matching. Phase 9K freezes the Phase 9 safety boundary and adds guard tests for command scope, diagnostic truth, docs consistency, and forbidden runtime authority. Phase 10A adds the Helm overlay foundation: Helm launches from the top-right ASSISTANT cluster, opens as a large overlay/modal, applies selected tuning changes only to the in-memory workspace draft, never auto-saves, and does not auto-edit conditional rules in Helm v1. Phase 10B expands Helm's deterministic engine with symptom definitions, follow-up questions, workspace findings, confidence bands, recommendation groups, expected outcomes, risks, and conflict warnings while preserving in-memory-only apply/revert behavior. Phase 10C adds guided review copy, selected-change counts, group selection, follow-up answer controls, clearer apply/revert messages, and staged/unapplied-change awareness while preserving the same in-memory-only safety model. Phase 10D adds `v3_app/helm/context.py`, a read-only context extractor that labels evidence from workspace values, mode settings, conditional rules, optional response stack snapshots, and runtime diagnostics. Phase 10E finalizes Helm for Phase 10, keeps Helm overlay/modal from the ASSISTANT cluster, preserves deterministic/local behavior, and freezes the no-runtime-authority boundary before Phase 11. Phase 11A implements Help / Docs foundation only, including the Runtime Setup / vJoy Setup article as local built-in documentation; Perf / Diagnostics page work is deferred to Phase 11B. Early phases may still use in-process simulation adapters for development views, but the final architecture should allow the Bridge to run without the PySide6 UI open. The Bridge/UI boundary is documented in `docs/HelmForge/bridge-ui-architecture.md`, the process skeleton is documented in `docs/HelmForge/bridge-service-design.md`, the Phase 9G decision record is documented in `docs/HelmForge/phase-9g-bridge-lifecycle-ownership-design.md`, the Phase 9H report is documented in `docs/HelmForge/phase-9h-real-device-discovery-dry-run-report.md`, the Phase 9I report is documented in `docs/HelmForge/phase-9i-bridge-process-presence-diagnostics-report.md`, the Phase 9J report is documented in `docs/HelmForge/phase-9j-live-monitor-diagnostic-ux-polish-report.md`, the Phase 9K report is documented in `docs/HelmForge/phase-9k-phase-9-stabilization-boundary-freeze-report.md`, the Phase 10A report is documented in `docs/HelmForge/phase-10a-helm-assistant-overlay-foundation-report.md`, the Phase 10B report is documented in `docs/HelmForge/phase-10b-helm-intelligence-expansion-report.md`, the Phase 10C report is documented in `docs/HelmForge/phase-10c-helm-guided-review-apply-revert-report.md`, the Phase 10D report is documented in `docs/HelmForge/phase-10d-helm-context-integration-report.md`, the Phase 10E report is documented in `docs/HelmForge/phase-10e-helm-final-polish-boundary-freeze-report.md`, and the Phase 11A report is documented in `docs/HelmForge/phase-11a-help-docs-foundation-report.md`.

Phase 11C supersedes the earlier Phase 11A deferral note: Phase 11A implemented Help / Docs, Phase 11B implemented Perf / Diagnostics, and Phase 11C freezes the combined Phase 11 boundary. The Phase 11B report is documented in `docs/HelmForge/phase-11b-perf-diagnostics-page-report.md`, and the Phase 11C report is documented in `docs/HelmForge/phase-11c-help-perf-diagnostics-boundary-freeze-report.md`.

## Phase 10A Helm Assistant Overlay

Phase 10 is Helm Assistant Overlay according to the prompt book. Phase 10A implements the overlay foundation:

- Helm is launched from the top-right `ASSISTANT` cluster.
- Helm behaves as an overlay/modal assistant, not a sidebar page.
- Helm analyzes the current in-memory workspace draft and presents exact before/after diffs.
- The first working symptom path is `Combat mode feels sluggish`.
- Apply Selected Changes updates only the in-memory workspace/draft.
- Revert Last Helm Changes restores the previous in-memory values from the last Helm apply.
- Helm never auto-saves to `hotas_bridge_config_v3.json`.
- Helm v1 does not create, edit, enable, disable, or delete conditional rules.
- Phase 10A does not add real HOTAS polling, vJoy writes, output verification, Bridge lifecycle control, or real runtime activation.

## Phase 10B Helm Intelligence Expansion

Phase 10B keeps Helm deterministic and local while making it behave more like a diagnosis-first tuning engineer:

- Helm now has a structured symptom library for aim/combat, flight, ground/racing, and general control feel issues.
- Supported symptom paths generate exact before/after diffs with reason, expected outcome, risk level, confidence score, reversibility, selected state, and applied state.
- Recommendations are grouped, for example `Fine Aim Control`, `Combat Responsiveness`, `Stability`, `Center Precision`, `High-Speed Tracking`, `Drift Reduction`, and `Overshoot Mitigation`.
- Ambiguous symptoms produce deterministic follow-up questions before Helm stages changes.
- Workspace analysis reports findings such as high deadzone, cross-axis curve mismatch, low combat yaw authority, or restrictive combat slew values.
- Apply Selected Changes still updates only the in-memory workspace draft and marks it unsaved.
- Revert Last Helm Changes still restores the last Helm-applied in-memory batch.
- Helm still never auto-saves, never mutates conditional rules, never calls cloud AI or an LLM, and never claims runtime evidence that telemetry does not prove.
- Phase 10B does not add real HOTAS polling, live physical input streaming, vJoy writes, output verification, automatic Bridge launch, process management, service install, login auto-start, tray manager work, installer launch, or real runtime activation.

## Phase 10C Helm Guided Review

Phase 10C polishes the review and apply/revert workflow:

- Analysis now shows a guided review summary with symptom confidence, tuning group count, selected-change count, affected axes, expected outcome, risk, and in-memory-only reminder.
- Recommendation group selection cascades to every diff in that group and selected counts update immediately.
- Individual diff selection remains available.
- Apply Selected Changes is inactive when no diffs are selected.
- Apply Selected Changes applies only selected diffs to the in-memory workspace draft and marks the workspace unsaved.
- Save Workspace remains the only persistence action.
- Revert Last Helm Changes restores exact before values from the most recent applied Helm batch and does not touch disk.
- Follow-up-required symptoms show deterministic questions and answer buttons before confident diffs are staged.
- Findings explicitly state that Helm is using workspace values only and live hardware analysis is not active.
- Phase 10C does not add Help / Docs, Perf / Diagnostics, Live Overlay, Flight Recorder, real HOTAS polling, live physical input streaming, vJoy writes, output verification, Bridge lifecycle control, cloud AI, LLM behavior, conditional-rule auto-editing, auto-save, or real runtime activation.

## Phase 10D Helm Context Integration

Phase 10D makes Helm context-aware without adding runtime authority:

- Helm extracts read-only context for workspace tuning, filtering, combat profile values, mode settings, conditional rules, optional Effective Response Stack snapshots, and Phase 9 runtime diagnostics.
- Evidence labels distinguish `Workspace values`, `Mode settings`, `Conditional rules`, `Response stack snapshot`, `Runtime diagnostics`, `Discovery-only status`, and `Unavailable`.
- What I Found now groups findings by source: workspace, modes, rules, stack, and runtime boundary.
- Helm can mention mode stacking, disabled rules, stack snapshot availability, output verification truth, and discovery-only device state.
- Context-aware recommendations can add caution when precision and combat stack by multiplication or when rules target the same axis.
- Helm does not mutate conditional rules, does not perform live hardware analysis, does not use cloud AI or LLM behavior, and does not claim output verification.
- Apply/Revert remains in-memory only and Save Workspace remains explicit.

## Phase 10E Helm Final Polish

Phase 10E finalizes Helm for Phase 10:

- Helm remains overlay/modal from the ASSISTANT cluster, not a sidebar page.
- Helm remains deterministic/local and uses evidence labels plus compact context summaries.
- Empty, ambiguous, staged, applied, reverted, no-rule, disabled-rule, stack-unavailable, blocked-runtime, and output-unverified states now use polished safety-aware copy.
- Apply Selected Changes modifies only the in-memory workspace draft.
- Save Workspace remains the only persistence action.
- Revert Last Helm Changes restores the last Helm batch.
- Helm does not mutate conditional rules.
- Helm does not use cloud AI or LLM behavior.
- Helm does not perform live hardware analysis.
- Phase 10E does not add hardware polling, vJoy writes, output verification, Bridge lifecycle control, process spawning, service install, auto-start, tray manager work, Help / Docs implementation, Perf / Diagnostics page work, Live Overlay, Flight Recorder, auto-save, or real runtime activation.

Next prompt-book phase: Phase 11: Help / Docs and Perf / Diagnostics.

## Phase 11A Help / Docs Foundation

Phase 11A implements Help / Docs foundation only:

- The Help / Docs page has local category browsing and deterministic search.
- The search field matches article title, category, keywords, and body text.
- Runtime Setup / vJoy Setup article is local built-in documentation.
- The Runtime Setup guide explains simulation mode, Bridge telemetry, manual Bridge launch, vJoy detection, missing HOTAS, output verification truth, Full Live Runtime Ready truth, safe command requests, and request_id command acknowledgement.
- The Helm article reflects Phase 10 behavior: overlay/modal, deterministic/local, in-memory apply/revert, evidence labels, no conditional-rule mutation, no cloud AI or LLM behavior, and no live hardware analysis.
- Runtime Indicators, Saving and Importing, and Tuning Glossary articles define the terms used across the app.
- Perf / Diagnostics page work is deferred to Phase 11B.
- Help / Docs does not add runtime authority.
- Help / Docs does not perform hardware polling, vJoy writes, output verification, Bridge lifecycle control, or runtime activation.
- Help / Docs does not use cloud AI or LLM behavior.

## Phase 11B Perf / Diagnostics

Phase 11B implements Perf / Diagnostics page only:

- The page shows runtime truth, Bridge lifecycle, telemetry status/age, process hint, HOTAS discovery, input device status, output/vJoy status, output_verified, Full Live Runtime Ready, selected axis, workspace/source file, and command acknowledgement fields.
- Timing metrics cover page switch/build visibility, heartbeat/update samples, graph/update samples, startup timing when available, and hidden-page skip counters or truthful unavailable/not-implemented states.
- Run Runtime Preflight remains safe and does not prove output verification.
- Copy Diagnostics prepares local text with runtime truth, output verification truth, telemetry status, timing summaries, hidden-page skip counts, and manual Bridge launch guidance.
- Diagnostics are observational and do not add runtime authority.
- Timing metrics are UI/app diagnostics, not live hardware proof.
- Process presence remains a hint.
- Telemetry remains the truth surface.
- Phase 11B does not add hardware polling, vJoy writes, output verification, Bridge lifecycle control, process spawning, installer launch, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 11C Help / Docs + Perf / Diagnostics Boundary Freeze

Phase 11 is now complete.

Phase 11C finalizes Help / Docs and Perf / Diagnostics together:

- Help / Docs articles now cross-reference Runtime Setup / vJoy Setup, Runtime Indicators, Performance / Diagnostics, Helm, Saving and Importing, Effective Response Stack, Graphs and Previews, and Conditional Rules consistently.
- Performance / Diagnostics documentation matches the implemented page: diagnostics are observational, timing metrics are app/UI diagnostics, hidden-page skips are instrumentation counters, Run Runtime Preflight is safe and does not verify output, and Copy Diagnostics creates local diagnostic text.
- Perf / Diagnostics page copy states that telemetry remains the truth surface, process presence is a hint only, HOTAS discovery is discovery-only, vJoy detected does not mean output verified, Output verified is false, and Full Live Runtime Ready is false.
- Phase 11C does not add runtime authority.

The next prompt-book phase is Phase 12 Live Overlay Foundation. Phase 12 must preserve the Phase 9K runtime boundary and Phase 10E Helm boundary.

## Phase 12A Live Overlay Foundation

Phase 12A implements Live Overlay core/config foundation only:

- `v3_app/overlay/axis_colors.py` stores the shared recovered axis colors for Roll, Pitch, Throttle, Yaw, Aux 1, and Aux 2.
- `v3_app/overlay/overlay_config.py` stores serializable Live Overlay configuration defaults, JSON round-tripping, restore-defaults behavior, and safe validation/clamping.
- `v3_app/overlay/telemetry_buffer.py` stores simulation/runtime snapshot history without polling hardware.
- `v3_app/overlay/trace_builder.py` converts buffered samples into plain trace data for later rendering.
- Live Monitor shows a Live Overlay card with Custom, Bottom strip, 66% opacity, Final output, runtime truth, Output verified false, and Full Live Runtime Ready false.
- The Live Overlay Configuration dialog shell exposes Placement, Appearance, Behavior, Data, and Axes settings.
- Detached overlay rendering was deferred from Phase 12A and is implemented in Phase 12B.
- Hotkey registration is not claimed.
- Click-through support is not claimed.
- Axis colors are shared for future Flight Recorder reuse, but Flight Recorder is not implemented in Phase 12A.
- Phase 12A does not add real HOTAS polling, live input streaming, vJoy writes, output verification, Bridge lifecycle control, game injection, graphics API hooking, auto-save, or runtime activation.

## Phase 12B Detached Live Overlay Window And Renderer

Phase 12B implements detached overlay rendering without adding runtime authority:

- `v3_app/overlay/live_overlay_window.py` owns a top-level frameless Qt overlay window with bottom-strip placement and safe Show/Hide behavior.
- `v3_app/overlay/overlay_renderer.py` draws axis traces, optional legend, optional live values, and an idle/runtime truth message from Phase 12A trace data.
- The Live Monitor Live Overlay card now opens and hides the detached overlay window. Status is Active only while the real overlay window is visible.
- The configuration dialog still applies changes only on OK. Cancel discards edits, and Restore Defaults remains draft-only until OK.
- The overlay can render simulation/final-output telemetry already available to the UI, but it does not poll real HOTAS input or write vJoy.
- Always-on-top uses Qt window flags when configured. Hotkey status remains Not registered, and click-through remains Not enabled - not verified.
- The overlay is app-owned and does not inject into games, hook graphics APIs, capture the screen, or implement Flight Recorder behavior.
- Phase 12B does not add real HOTAS polling, live input streaming, vJoy writes, output verification, Bridge lifecycle control, process spawning, game injection, graphics API hooking, cloud AI, LLM behavior, auto-save, or runtime activation.

## Phase 12C Live Overlay Boundary Freeze

Phase 12 is now complete.

Phase 12C finalizes Live Overlay behavior:

- Directly closing the detached overlay updates the Live Monitor card back to Inactive.
- The configuration dialog uses final Phase 12 wording for hotkey and click-through truth labels.
- Hotkey status remains Not registered.
- Click-through remains Not enabled - not verified.
- Always-on-top remains config-backed through Qt window flags.
- Help / Docs now states that Live Overlay is app-owned and detached, does not inject into games, does not use graphics API hooking, and does not capture the screen.
- Phase 12C does not add runtime authority.

The next prompt-book phase is Phase 13: Flight Recorder, Clip Library, and Hindsight Buffer. Phase 13 should reuse shared overlay colors and trace concepts where appropriate, and it must not claim real clip capture, video encoding, or hindsight buffering until those behaviors are implemented and verified.

## Phase 13A Flight Recorder UI Foundation

Phase 13A implements the Flight Recorder foundation shell only:

- `v3_app/recorder/recorder_settings.py` stores default recorder settings, restore-defaults behavior, serialization, validation/clamping, backend truth flags, and shared axis overlay colors.
- `v3_app/recorder/recorder_state.py` stores truthful recorder states such as capture backend missing, buffering unavailable, saving unavailable, compositor unavailable, and error.
- `v3_app/recorder/clip_library.py` provides a read-only clip library shell for future clip metadata.
- `v3_app/pages/flight_recorder_page.py` replaces the placeholder with Recorder Settings, Axis Overlay, Recording Library, and Clip Preview cards.
- Recorder status chips use truthful labels: UI Ready, Capture backend missing, Hotkey not registered, Final output source, Buffering unavailable, and Recording unavailable.
- Record Now and Save Last Clip are disabled and report backend/buffer unavailability if invoked.
- Axis Overlay uses the shared Phase 12 Live Overlay colors.
- Phase 13A does not add real desktop capture, video encoding, clip export, actual hindsight video buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, vJoy writes, output verification, Bridge lifecycle control, auto-save, or runtime activation.

## Phase 13B Recorder Backend And Hindsight Foundation

Phase 13B adds recorder backend seams without adding real capture or encoding:

- `v3_app/recorder/capture_backend.py` defines missing and simulated capture backends plus capability/status reporting.
- `v3_app/recorder/recorder_artifacts.py` defines round-trippable recorder artifact metadata.
- `v3_app/recorder/hindsight_buffer.py` adds telemetry-only hindsight buffering with deterministic timestamps.
- `v3_app/recorder/recorder_controller.py` coordinates settings, backend truth, telemetry hindsight, and simulated manifest creation.
- The Flight Recorder page now reports telemetry hindsight as available while keeping video hindsight unavailable.
- With the default missing backend, Record Now and Save Last Clip write no files and report unavailable truth.
- With an explicitly injected simulated backend, the recorder can write a clearly labeled JSON manifest marked simulated, non-video, and not real capture.
- Simulated artifacts may appear in the Recording Library and Clip Preview as metadata-only manifests. Play stays disabled.
- Phase 13B does not add real desktop capture, video encoding, real clip export, actual desktop video hindsight buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, vJoy writes, output verification, Bridge lifecycle control, auto-save, or runtime activation.

## Phase 13C Overlay Compositor And Simulated Export

Phase 13C adds simulated compositor/export architecture only:

- `v3_app/recorder/compositor.py` defines missing and simulated compositor capability/status types.
- `SimulatedRecorderCompositor` can generate a simulated export folder with `manifest.json`, `overlay_trace.json`, `summary.md`, and `preview_metadata.json`.
- Export metadata round-trips through JSON and tracks simulated/non-video truth, telemetry sample count, included axes, capture backend, compositor backend, and warnings.
- Simulated export traces reuse Phase 12 `build_overlay_traces` and the shared recovered axis colors.
- The recorder controller can use an injected simulated capture backend plus injected simulated compositor to produce simulated export bundles.
- The Recording Library labels simulated export bundles as simulated/no-video artifacts.
- Clip Preview shows metadata-only export details, telemetry sample count, overlay source, included axes, and artifact path. Play remains disabled.
- Telemetry hindsight can feed simulated overlay trace exports; desktop video hindsight buffering remains unavailable.
- Phase 13C does not add real desktop capture, video encoding, playable clip export, actual desktop video hindsight buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, vJoy writes, output verification, Bridge lifecycle control, auto-save, or runtime activation.

## Phase 13D Flight Recorder Boundary Freeze

Phase 13 is now complete.

Phase 13D finalizes Flight Recorder library and preview behavior:

- Recording Library indexes simulated export manifests and ignores unknown files.
- Missing destination folders show a safe empty state.
- Library rows use Artifact or Clip, Created/Recorded, Duration, and Opened labels.
- Simulated export rows are labeled simulated/no-video/metadata-only.
- Clip Preview shows metadata-only simulated export details and keeps Play/timeline disabled.
- Help / Docs states that simulated exports are not real recordings, no screen capture or video encoding is implemented, telemetry hindsight is separate from video hindsight, and Ctrl+Shift+F10 is hotkey text only/not registered.
- Phase 13D does not add real desktop capture, video encoding, playable clip export, actual desktop video hindsight buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, vJoy writes, output verification, Bridge lifecycle control, auto-save, or runtime activation.

## Phase 14A Physical Input Backend And Device Selection

Phase 14A starts Real HOTAS Input Integration without adding output authority:

- `shared_core/runtime/hotas_input.py` now defines physical input backend capabilities/status, device info, device selection results, missing/fake backends, and a read-only Windows PnP discovery backend.
- Supported HOTAS matching is centralized for Thrustmaster T-Flight / T.Flight HOTAS One, including VID/PID `044f:b68d` and conservative name matching.
- Device selection is in-memory for Phase 14A and reports no selection, backend unavailable, selected device available, selected device missing, and unsupported selected device states.
- Perf / Diagnostics shows Physical input backend, Supported HOTAS, Selected input device, Input sampling, and Input selection status while keeping Output verified false and Full Live Runtime Ready false.
- Help / Docs explains that physical input selection does not write output, does not make vJoy active, and does not make Full Live Runtime Ready true.
- Simulation mode remains available with no HOTAS connected, no Bridge running, and no physical input backend dependency installed.
- Phase 14A does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, automatic Bridge launch, process spawning, recorder capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 14B Physical Input Sampling And Normalization

Phase 14B extends Real HOTAS Input Integration without adding output authority:

- `shared_core/runtime/input_normalization.py` normalizes signed, unsigned-centered, already-normalized, and one-sided axis values with deterministic clamping and invalid-value handling.
- `shared_core/runtime/hotas_input.py` now includes `PhysicalInputSnapshot`, axis/button/hat sample models, read-only sampling status, logical HOTAS channel hints, and `PhysicalInputSampler`.
- The fake backend can return deterministic read-only sample frames for tests/dev injection and can emulate disconnect/error states.
- The missing and Windows PnP discovery backends remain safe when sampling is unavailable.
- Perf / Diagnostics shows input sampling status, last sample, sample source, axis/button/hat counts, sampling warnings, and sampling errors.
- Help / Docs explains that physical input sampling is read-only, does not imply vJoy output, and falls back safely on disconnect/error.
- Output verified remains false and Full Live Runtime Ready remains false even when read-only input samples are available.
- Phase 14B does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, end-to-end vJoy runtime loops, automatic Bridge launch, process spawning, recorder capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 14C Physical Input UI Integration

Phase 14C integrates read-only physical input samples into user-facing surfaces while keeping output authority frozen:

- `v3_app/services/physical_input_ui.py` exposes a UI-facing source/status model for Simulation, physical sample active, physical unavailable, stale, and error states.
- Mapping displays physical input backend/device/sample status, labels fresh physical values as Live Raw physical input samples, and falls back to simulation safely.
- Live Monitor can show read-only physical axis/button/hat sample values while still stating that output path remains unverified and vJoy writes are not active.
- Effective Response Stack can use a physical normalized sample for a diagnostic-only preview when available, otherwise it reports simulation fallback.
- Perf / Diagnostics and Copy Diagnostics include input source, physical input read-only truth, sample source, sample counts, warnings, and errors.
- Help / Docs explains that physical samples may appear in Mapping and Live Monitor, sample stale/error states fall back safely, final output is not written to vJoy in Phase 14, and Phase 15 remains the virtual output/vJoy phase.
- Output verified remains false and Full Live Runtime Ready remains false even when read-only physical samples are visible.
- Phase 14C does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, end-to-end vJoy runtime loops, automatic Bridge launch, process spawning, recorder capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 14D Physical Input Boundary Freeze

Phase 14 is now complete.

Phase 14D finalizes Real HOTAS Input Integration as an input-only boundary:

- Simulation fallback remains available with no physical backend, no selected device, a missing selected device, stale samples, sample errors, backend disconnects, and missing/stale/invalid Bridge telemetry.
- Mapping, Live Monitor, Effective Response Stack, Perf / Diagnostics, Copy Diagnostics, and Help / Docs consistently label physical input samples as read-only.
- Output verified remains false and Full Live Runtime Ready remains false even when read-only fake or physical samples are available.
- Phase 14D prepares Phase 15 readiness notes for the selected device state, normalized axis/button/hat snapshots, Mapping/Live Monitor display paths, and simulation fallback guardrails.
- Phase 14D does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, end-to-end live output runtime loops, automatic Bridge launch, process spawning, recorder capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 15A Virtual Output Backend Contract

Phase 15A starts vJoy / Virtual Output Integration conservatively:

Phase 15: vJoy / Virtual Output Integration remains the active prompt-book phase. Phase 15A is the contract-only opening slice.

Full Live Runtime Ready must remain false until both input and output are verified.

- `shared_core/runtime/vjoy_output.py` now defines virtual output backend capabilities/status, output device info, output intent/frame types, write results, verification results, and recovered axis route intent.
- MissingVirtualOutputBackend is the safe default and never attempts output writes or verification.
- FakeVirtualOutputBackend records intents in memory for deterministic tests/dev injection and can report `fake_verified` only as fake/mock proof, not real vJoy proof.
- Mapping, Live Monitor, Perf / Diagnostics, Copy Diagnostics, and Help / Docs expose virtual output backend, output device, write status, verification status/source, fake output verified, and real output verified truth.
- Output intent is not output write proof.
- vJoy detected does not equal output verified.
- output_verified remains false in normal runtime.
- Real output verified remains false.
- Full Live Runtime Ready remains false.
- Phase 15A does not add real vJoy writes, real output verification, end-to-end live output loops, automatic Bridge launch, process spawning, recorder capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 15B Real vJoy Detection And Guarded Verification

Phase 15B adds guarded real vJoy detection and write-path verification without enabling continuous output:

- RealVJoyOutputBackend is optional and guarded.
- App startup does not require a vJoy dependency.
- Missing dependency, missing device, busy device, acquisition failure, write failure, neutral restore failure, unsupported provider, and errors are typed verification results.
- Guarded verification uses a bounded verification intent, not arbitrary user profile output.
- Neutral restore is attempted after a real verification write.
- Real output verified can become true only after guarded write success and neutral restore success.
- vJoy detected does not equal output verified.
- Fake/mock verification remains separate from real output verification.
- Full Live Runtime Ready remains false.
- Continuous output write loop is not implemented.
- Phase 15B does not add automatic output enablement, automatic Bridge launch, process spawning, service install, login auto-start, tray manager, installer launch, Start/Stop/Restart behavior, real process scanner, recorder capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

Next prompt-book slice: Phase 15C may add runtime output-loop integration only after guarded verification remains stable and simulation fallback is preserved.

## Phase 9 Status Snapshot

Phase 9C through Phase 9K establish the Bridge/UI truth seam without adding live runtime authority:

- telemetry remains the truth surface.
- command files are requests, not success proof.
- Bridge command acknowledgement must use matching request_id.
- process presence is a hint only.
- HOTAS discovery is discovery-only.
- supported_device_detected does not mean polling/live runtime/output verified.
- manual Bridge launch remains the current lifecycle model.
- UI does not start, stop, restart, spawn, install, or manage the Bridge.
- output_verified remains false until a future output verification phase.
- Full Live Runtime Ready remains false until future phases prove input and output.
- live device/runtime work remains deferred.

Current conservative truth:

- Runtime truth: `blocked_missing_device` unless fresh telemetry truth says otherwise.
- Bridge lifecycle: `Simulated`.
- Device discovery: `no_supported_device` unless read-only discovery sees a supported device.
- Process presence: diagnostic hint only.
- `output_verified`: `false`.
- Full Live Runtime Ready: `false`.

Current paths:

- Telemetry: `%TEMP%\helmforge_bridge_telemetry.json`
- Commands: `%TEMP%\helmforge_bridge_command.json`
- Manual Bridge launch: `python -m bridge_app.main --run-for-ms 250`

Safe UI command requests:

- `Status`
- `RunPreflight`
- `ReloadConfig`
- `SwitchToSimulation`
- `ClearError`

Rejected/out-of-scope commands:

- `StartBridge`
- `StopBridge`
- `RestartBridge`
- `SuspendBridge`
- `VerifyOutput`

## Project Layout

```text
shared_core/          Shared models, runtime contracts, math pipeline, rules evaluator, and non-UI core code.
bridge_app/           Simulation-only Bridge background process skeleton and file IPC entry point.
v3_app/               PySide6 application package, app shell, theme, Mapping editor, tuning/rules/stack/live-monitor pages, and remaining placeholder pages.
docs/HelmForge/       Implementation notes, decisions, and phase reports.
docs/recovery/        Recovery-source preservation notes and evidence inventory.
tests/                Phase smoke and contract tests.
```

## Development

Initial dependencies are declared in `pyproject.toml`:

- PySide6
- pyqtgraph
- pytest

Install the declared project dependencies in editable mode:

```powershell
python -m pip install -e .
```

Run tests:

```powershell
python -m pytest
```

Launch the app shell:

```powershell
python -m v3_app.main
```

Run one simulation-only Bridge tick:

```powershell
python -m bridge_app.main --once
```

Run a bounded Bridge loop:

```powershell
python -m bridge_app.main --run-for-ms 250
```

Automated smoke launch:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m v3_app.main --smoke-exit-ms 250
Remove-Item Env:\QT_QPA_PLATFORM
```

Run the Phase 2A runtime setup dry-run checklist:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/runtime_setup_check.ps1 -DryRun
```
