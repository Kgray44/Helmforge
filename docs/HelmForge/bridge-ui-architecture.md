# Bridge/UI Architecture

Status: Phase 16D adds the final Full Live Runtime Ready gate and Runtime End-to-End Live Mode boundary freeze on top of Phase 16C verified runtime-path proof semantics, Phase 16B compact `runtime_frame` Bridge telemetry/UI surfaces, and Phase 16A runtime orchestrator simulation path. Phase 15D completes the vJoy / Virtual Output Integration boundary freeze and prepares Phase 16 readiness. Phase 15C adds controlled output write-loop integration on top of Phase 15B guarded real vJoy detection/write-path verification and Phase 15A output contracts. The loop starts disabled, requires explicit enablement and verified backend proof, rate-limits writes, records write/failure counts, attempts neutral restore on stop, and safety-stops on failures. Phase 14C integrates read-only physical input sample visibility into Mapping, Live Monitor, Effective Response Stack preview, Perf / Diagnostics, Copy Diagnostics, and Help / Docs on top of the Phase 14B sampling/normalization foundation and Phase 14A physical HOTAS input backend/device-selection foundation. Phase 13D finalized the Flight Recorder library, metadata-only preview, simulated export wording, Help / Docs copy, and Phase 13 boundary tests. Phase 13C implemented the overlay compositor abstraction and simulated non-video export bundles. Phase 13B implemented backend interfaces, telemetry hindsight buffering, simulated non-video artifacts, and controller wiring. Phase 13A implemented the Flight Recorder UI/state/settings/library/preview shell. Phase 12C finalized Live Overlay polish and boundary freeze. Phase 11C completed the Help / Docs + Perf / Diagnostics boundary freeze. Phase 10E finalized Helm for Phase 10, and Phase 9K froze the Bridge/UI boundary. Shared contracts exist, `bridge_app` can run as a separate simulation-only Python process, the PySide6 Live Monitor can consume fresh Bridge telemetry JSON with safe simulation fallback, and the UI can request safe Bridge commands through a JSON command file. The Bridge echoes the most recently consumed command request in telemetry, and the UI shows compact Bridge health/timing details, runtime_frame truth, device discovery truth, process-presence hints, physical input selection/sampling truth, virtual output verification truth, output loop truth, verified-path proof fields, central readiness-gate proof, and a stable diagnostic hierarchy. Helm remains overlay/modal from the ASSISTANT cluster, analyzes local workspace values through deterministic/local symptom paths, reads mode/rule/stack/runtime context without mutating it, labels evidence sources, groups recommendations, asks deterministic follow-up questions when a symptom is ambiguous, shows staged-review counts and risk/outcome copy, and only mutates the in-memory workspace draft when the user applies selected changes. Help / Docs adds local built-in documentation, category browsing, deterministic search, and cross-links for Phase 11 topics. Perf / Diagnostics adds observational runtime, telemetry, timing, hidden-skip, preflight, physical input selection/sampling, virtual output backend kind/status, virtual output verification, output loop, runtime_frame diagnostics, runtime proof diagnostics, readiness-gate diagnostics, and copy-summary visibility. Live Overlay has shared config/core models, axis colors, telemetry history buffering, trace building, a Live Monitor card, a configuration dialog shell, an app-owned detached Qt overlay renderer, finalized hotkey/click-through truth labels, and final boundary tests. Flight Recorder now has a page shell, settings model, state model, axis overlay settings, recording library shell, clip preview shell, backend interface, missing backend, injected simulated backend, recorder artifact metadata, telemetry hindsight buffer, controller, compositor abstraction, missing compositor, simulated compositor, simulated export metadata, polished artifact indexing, and metadata-only preview. Phase 14A adds missing/fake/Windows PnP physical input discovery backends, centralized Thrustmaster HOTAS One matching, and in-memory device selection diagnostics. Phase 14B adds input sample models, deterministic normalization helpers, fake on-demand sample snapshots, and read-only sampling diagnostics. Phase 14C makes those samples useful in the UI while labeling them read-only and preserving simulation fallback. Phase 16A can produce compact runtime frames, final VirtualOutputIntent, and optional fake output-loop handoff for tests; Phase 16B publishes a compact runtime_frame summary from that path; Phase 16C separates input proof, pipeline proof, output proof, output-loop proof, runtime candidate, blocked reason, and proof summary; Phase 16D centralizes the final readiness evaluator. Automatic Bridge launch, process spawning from the UI, Windows Service install, tray manager work, login auto-start, game injection, graphics API hooking, global hotkey registration, click-through support, real desktop capture, video encoding, playable clip export, and actual desktop video hindsight buffering are not implemented.

Phase 15B update: the UI now has virtual output contract and guarded verification surfaces for output intents, missing/fake/real output backends, fake/mock verification labels, real guarded verification labels, vJoy dependency status, vJoy device status, and last verification details.

Phase 15C update: the shared-core output loop can write only after explicit enablement and fake or real verification proof. It is bounded by a write-rate limiter, records last write/result/error and write/failure counts, attempts neutral restore on stop, and safety-stops on write failure. Fake loops remain test/dev-only and do not prove real vJoy. Full Live Runtime Ready remains false unless a later end-to-end runtime phase proves both input and output.

Phase 15D update: Phase 15 is now complete. The next prompt-book phase is Phase 16: Runtime End-to-End Live Mode. Phase 16 may build on Phase 14 physical input sampling, Phase 15 output intents, guarded output verification, the controlled output write loop, diagnostics, and simulation fallback. Phase 16 must preserve simulation mode, keep output writes safety-gated, require both input and output proof for Full Live Runtime Ready, and avoid fake readiness from detection-only signals.

Phase 16A update: `shared_core/runtime/runtime_orchestrator.py` defines the first runtime orchestrator contract. It can build deterministic simulation frames, accept guarded physical samples when fresh, fall back to simulation for missing/stale/error samples, run the shared workspace signal pipeline, produce final `VirtualOutputIntent`, and optionally tick an explicitly enabled fake output loop in tests. Output intent remains separate from output write proof, real output remains behind Phase 15 verification and enable gates, and Full Live Runtime Ready remains false in this slice.

Phase 16B update: Bridge telemetry now includes a compact `runtime_frame` section with schema version, frame sequence, input source/status, pipeline status, compact rule/mode summary, final output axes, output intent readiness, output backend, output loop state, verification truth, runtime truth, blocked reason, warnings, and errors. The UI telemetry client accepts missing runtime_frame for backward compatibility and treats malformed runtime_frame as an unavailable parse state. Mapping, Live Monitor, and Perf / Diagnostics display runtime frame truth without treating output intent as output write proof.

Phase 16C update: `runtime_frame` now carries compact proof fields for input, pipeline, output verification, output-loop enabled/running/safety-stop state, runtime candidate, and proof summary. Physical input, pipeline success, guarded output verification, and output-loop state are separate proofs. A fully proven injected real path may report `verified_runtime_candidate`, but Full Live Runtime Ready remains false because Phase 16D owns the final readiness gate. Fake/test paths remain test-only and cannot become real output verified.

Phase 16D update: `shared_core/runtime/runtime_orchestrator.py` now owns the central Full Live Runtime Ready evaluator and readiness proof object. Full Live Runtime Ready requires fresh physical input, successful pipeline processing, guarded real output verification, explicit output loop enable/running according to policy, fresh runtime_frame/Bridge telemetry, and no safety stop or blocking errors. It is never inferred from vJoy detection alone, physical HOTAS detection alone, output intent generation alone, fake/mock verification, fake output loop, stale telemetry, or UI process presence. Phase 16 is now complete. The next prompt-book phase is Phase 17: Product Polish, Layout QA, and Motion; Phase 17 must preserve this runtime truth/readiness gate.

## Core Rule

The Bridge owns real-time input/output. The UI App owns configuration, visualization, diagnostics, and user interaction.

HelmForge is two-part software:

- Bridge: lightweight runtime/background control component.
- UI App: PySide6 desktop configuration, diagnostics, monitoring, and user interaction surface.

The UI App should not be required to stay open for configured HOTAS-to-vJoy processing once the Bridge is installed, configured, and running.

## Bridge Responsibilities

The future Bridge owns the low-latency runtime path:

- detect the Thrustmaster T-Flight HOTAS One / Thrustmaster T.Flight Hotas One;
- read physical HOTAS axes, buttons, and hats;
- load the active `hotas_bridge_config_v3.json` workspace;
- apply mappings, tuning, filtering, modes, and conditional rules;
- produce final output values;
- write final output to vJoy or the selected virtual output backend;
- publish telemetry snapshots;
- reload configuration when the UI saves and requests reload;
- truthfully report missing drivers, missing HOTAS, missing output backend, unverified output, and runtime errors;
- eventually auto-start or wake when the HOTAS is plugged in;
- eventually suspend, stop, or safe-idle when the HOTAS is unplugged.

The Bridge must not depend on PySide6, graph rendering, overlay rendering, Helm analysis, or expensive UI refresh work to maintain real-time output.

Phase 9H adds a Bridge-owned read-only discovery boundary for the supported HOTAS. This boundary can identify whether a supported device is visible to the operating system, but it is not the live polling path and it does not activate vJoy output.

## UI App Responsibilities

The UI App owns the human-facing surface:

- present HelmForge branding and the HOTAS Control Panel V3 technical subtitle;
- edit mappings, modes, base tuning, filtering, combat profile, profiles, workspaces, and conditional rules;
- save and load `hotas_bridge_config_v3.json`;
- request future Bridge lifecycle actions only after later safety gates are implemented;
- request current safe Bridge status/config/preflight commands through the Phase 9D command seam;
- display Bridge telemetry in Live Monitor and Effective Response Stack views;
- display runtime setup and Help / Docs guidance;
- display performance and diagnostics as observational UI/app truth;
- host Helm assistant overlay plus future Flight Recorder and Live Overlay UI;
- show truthful runtime state rather than fake live claims.

The UI may run Bridge-like adapters in-process during early development, but real-time processing should remain behind shared-core contracts so it can move to a background component later.

## Communication Boundary

The final IPC mechanism is still intentionally undecided. Phase 9B uses a simple local JSON telemetry file and JSON command file as the first development IPC seam. Phase 9C reads the telemetry JSON from the UI and falls back when it is missing, stale, or invalid. Phase 9D writes safe UI command requests to the command file. Candidate later mechanisms include:

- local process IPC;
- named pipe;
- localhost API;
- shared state file plus a command channel;
- direct in-process adapter during early phases;
- background service or tray process in later phases.

Required boundary:

```text
UI writes configuration and sends commands.
Bridge reads configuration, processes input/output, and publishes telemetry.
```

## Configuration Flow

1. User edits a workspace in the UI.
2. UI updates its current workspace draft.
3. User saves the workspace.
4. UI writes `hotas_bridge_config_v3.json`.
5. UI sends `ReloadConfig`, or the Bridge detects the safe configuration update later.
6. Bridge applies the new configuration to future runtime samples.

The Bridge should never rely on the settings window staying open to keep processing once the real background runtime exists.

## Telemetry Flow

1. Bridge samples raw HOTAS input.
2. Bridge applies the active workspace transformation pipeline.
3. Bridge publishes raw axes, final axes, buttons, hats, active modes, rule counts, output verification state, compact runtime_frame summary, device discovery status, warnings, and errors.
4. UI reads and renders telemetry in monitor, graph, diagnostics, overlay, recorder, and assistant surfaces.

Phase 2B telemetry contracts are defined in `shared_core/runtime/telemetry.py`. Phase 9B Bridge telemetry is written as JSON shaped from those contracts. Phase 9C validates the JSON in `v3_app/services/bridge_client.py`; telemetry older than 5 seconds is treated as stale and not live.

Phase 9F exposes explicit UI health fields from the Bridge telemetry client:

- telemetry path;
- last read time;
- telemetry generated time;
- age in seconds;
- stale threshold;
- status and reason.

The Live Monitor shows these compactly in the Live State card. Missing, stale, invalid, and error telemetry all remain simulation fallback states; stale telemetry is not treated as live Bridge truth.

Phase 9H adds `device_discovery` to telemetry. The UI may display:

- HOTAS discovery not checked;
- no supported device found;
- supported HOTAS detected, polling not active;
- discovery error;
- discovery backend unavailable.

The UI must not scan hardware directly and must not translate discovery into live runtime readiness. A supported-device discovery result only means the Bridge dry-run can see a matching device identity.

## Process Presence Diagnostics

Phase 9I adds UI-side process presence hints. Presence hints are diagnostic only:

- telemetry remains the truth surface;
- fresh telemetry is stronger than a process hint;
- process presence never becomes runtime truth;
- process presence never proves output verification;
- process presence never permits Full Live Runtime Ready wording.

Initial presence states:

- unavailable;
- unknown;
- not found;
- maybe running;
- seen but telemetry missing;
- seen but telemetry stale;
- fresh telemetry confirmed;
- telemetry invalid;
- telemetry error.

The Live Monitor can now show compact text such as:

- `Bridge telemetry: Connected`;
- `Process hint: Fresh telemetry confirmed`;
- `Bridge telemetry missing; manual Bridge launch may be required`;
- `Bridge process may be running, but telemetry is stale`;
- `Manual Bridge launch expected: python -m bridge_app.main --run-for-ms 250`.

The UI does not execute the manual-launch command and does not add Start, Stop, Restart, Service, Auto Start, or Verify Output controls.

## Live Monitor Diagnostic UX

Phase 9J organizes the Live Monitor Live State diagnostics in this stable order:

- Telemetry
- Lifecycle
- Runtime
- Output verified
- HOTAS discovery
- Process hint
- Last command
- Diagnosis
- Manual launch, only when telemetry is missing or stale

The display uses diagnostic-only severities:

- `ok`
- `info`
- `warning`
- `error`
- `muted`

These severities do not change runtime truth. They only help the UI present edge states clearly.

Command status follows the Phase 9E request-id rule. Old or unrelated `last_command` telemetry never completes the current UI request. Missing or stale telemetry keeps the current UI request in an awaiting-telemetry state.

Manual launch guidance remains text only:

```powershell
python -m bridge_app.main --run-for-ms 250
```

The UI does not add a button or background process launch path for that command.

## Helm Assistant Overlay

Phase 10 is Helm Assistant Overlay according to the prompt book. Phase 10A establishes the foundation:

- Helm launches from the top-right `ASSISTANT` cluster.
- Helm is overlay/modal behavior, not a sidebar page.
- Helm applies changes only to the in-memory workspace/draft.
- Helm never auto-saves.
- Helm v1 does not auto-edit conditional rules.
- Phase 10A does not add real HOTAS polling, vJoy writes, output verification, Bridge lifecycle control, or real runtime activation.

The first deterministic symptom path is `Combat mode feels sluggish`. It produces combat-profile diffs with exact before/after values, applies selected diffs only in memory, marks the workspace unsaved through the existing shell dirty-state path, and can revert the last Helm-applied batch. The helper engine and diff model live under `v3_app/helm/` so Helm logic stays out of the shell file and remains testable without PySide6 where practical.

Phase 10B expands that foundation without adding runtime authority:

- symptom definitions live in `v3_app/helm/symptom_library.py`;
- recommendation tables live in `v3_app/helm/recommendation_library.py`;
- analysis, confidence, follow-up, grouping, and finding models live in `v3_app/helm/helm_engine.py`;
- exact before/after diffs and in-memory apply/revert behavior live in `v3_app/helm/diff_model.py`;
- the overlay renders grouped recommendations, confidence labels, expected outcomes, risk notes, and small "Why?" sections.

Helm remains deterministic, local, and recommendation-only. It does not use cloud AI, an LLM, runtime control, live telemetry authority, real HOTAS polling, vJoy writes, output verification, Bridge launch, or process management. Helm also does not create, edit, enable, disable, or delete conditional rules in Phase 10B.

Phase 10C keeps the same authority boundary and improves the guided review workflow:

- review summaries show group count, selected-change count, affected axes, expected result, risk, and in-memory-only state;
- group checkboxes select or deselect all diffs in that recommendation group;
- individual diff checkboxes remain available for narrower apply batches;
- Apply Selected Changes is inactive when nothing is selected;
- applying changes records a revert batch and marks the workspace unsaved through the shell draft path;
- Revert Last Helm Changes restores the exact before values from the most recent Helm batch;
- follow-up questions render deterministic answer buttons before confident diffs are staged;
- findings state that Helm is using workspace values only and live hardware analysis is not active.

Save Workspace remains the only persistence action. Phase 10C does not add Help / Docs, Perf / Diagnostics, Live Overlay, Flight Recorder, cloud AI, LLM behavior, conditional-rule auto-editing, auto-save, hardware polling, vJoy writes, output verification, Bridge lifecycle control, or real runtime activation.

Phase 10D adds read-only context integration:

- `v3_app/helm/context.py` extracts `HelmContext`, `HelmAxisContext`, `HelmModeContext`, `HelmRuleContext`, `HelmStackContext`, and `HelmRuntimeContext`;
- context extraction covers workspace tuning/filtering/combat values, mode settings, conditional rule summaries, optional response stack snapshots, and Phase 9 runtime diagnostics;
- every new context finding includes an evidence label such as `Workspace values`, `Mode settings`, `Conditional rules`, `Response stack snapshot`, `Runtime diagnostics`, or `Unavailable`;
- Helm may mention disabled rules, mode multiplication, stack snapshot availability, output verification truth, and discovery-only device state;
- context-aware recommendations can add caution when mode stacking compounds scale changes or rules target the same axis.

Phase 10D is read-only context integration. It does not mutate rules, does not perform live hardware analysis, does not use cloud AI or an LLM, does not poll hardware, does not write vJoy, does not verify output, and does not change Bridge lifecycle ownership.

Phase 10E finalizes Helm for Phase 10:

- Helm remains overlay/modal from the ASSISTANT cluster and is not a sidebar page.
- Helm remains deterministic/local.
- Helm uses evidence labels and context summaries for workspace values, mode settings, conditional rules, optional stack snapshots, runtime diagnostics, discovery-only status, and unavailable evidence.
- Empty, ambiguous, staged, applied, reverted, no-rule, disabled-rule, stack-unavailable, runtime-blocked, and output-unverified states use calm safety-aware copy.
- Apply Selected Changes modifies only the in-memory workspace draft.
- Save Workspace remains the only persistence action.
- Revert Last Helm Changes restores the last Helm batch.
- Helm does not mutate conditional rules.
- Helm does not use cloud AI or LLM behavior.
- Helm does not perform live hardware analysis.
- Phase 10E does not add Help / Docs implementation, Perf / Diagnostics page work, Live Overlay, Flight Recorder, hardware polling, live physical input streaming, vJoy writes, output verification, Bridge lifecycle control, process spawning, service install, login auto-start, tray manager work, installer launch, auto-save, or real runtime activation.

The next prompt-book phase is Phase 11: Help / Docs and Perf / Diagnostics. Phase 11 should preserve the Phase 9K runtime freeze and the Phase 10E Helm boundary.

## Help / Docs and Perf / Diagnostics

Phase 11A implements Help / Docs foundation only:

- `v3_app/services/help_docs.py` stores local built-in articles and deterministic search.
- `v3_app/pages/help_docs_page.py` renders category browsing, a search field, a By Category dropdown, a topic list, and a scrollable guide pane.
- The Runtime Setup / vJoy Setup article is local built-in documentation and explains simulation mode, Bridge telemetry truth, manual Bridge launch, missing HOTAS, vJoy detection, output verification false, Full Live Runtime Ready false, safe command requests, and request_id command acknowledgement.
- The Helm article documents Phase 10 behavior: overlay/modal, deterministic/local, in-memory apply/revert, evidence labels, no conditional-rule mutation, no cloud AI or LLM behavior, and no live hardware analysis.
- Runtime Indicators, Saving and Importing, and Tuning Glossary articles define the app vocabulary.

Help / Docs does not add runtime authority, hardware polling, vJoy writes, output verification, Bridge lifecycle control, process spawning, auto-start, cloud AI or LLM behavior, auto-save, or runtime activation.

Phase 11B implements Perf / Diagnostics page only:

- `v3_app/services/perf_diagnostics.py` stores lightweight timing summaries, hidden-page skip counters, diagnostics snapshots, and pure copy diagnostics text building.
- `v3_app/pages/perf_diagnostics_page.py` displays Runtime Truth, Bridge / Telemetry, Workspace / UI State, Performance Timings, Hidden Page Skips, Commands / Preflight, and Diagnostic Actions.
- Run Runtime Preflight remains safe and does not prove output verification.
- Timing metrics are UI/app diagnostics, not live hardware proof.
- Process presence remains a hint.
- Telemetry remains the truth surface.
- Copy Diagnostics prepares text locally; clipboard integration is not required for Phase 11B.

Diagnostics are observational and do not add runtime authority. Phase 11B does not add hardware polling, vJoy writes, output verification, Bridge lifecycle control, process spawning, installer launch, cloud AI/LLM behavior, auto-save, or runtime activation.

Phase 11C completes Phase 11 with polish and a boundary freeze:

- Help / Docs related-topic labels connect Runtime Setup / vJoy Setup, Runtime Indicators, Performance / Diagnostics, Helm, Saving and Importing, Effective Response Stack, Graphs and Previews, and Conditional Rules.
- Perf / Diagnostics page copy states that telemetry remains the truth surface, process presence is a hint only, HOTAS discovery is discovery-only, vJoy detected does not mean output verified, Output verified is false, and Full Live Runtime Ready is false.
- Run Runtime Preflight is a safe check/request, not runtime activation.
- Copy Diagnostics is local diagnostic text, not a runtime command.
- Phase 11 is now complete.
- Phase 11C does not add runtime authority.

The next prompt-book phase is Phase 12 Live Overlay Foundation. Phase 12 must preserve the Phase 9K runtime boundary and Phase 10E Helm boundary.

## Live Overlay Foundation

Phase 12A implements the Live Overlay foundation:

- `v3_app/overlay/axis_colors.py` centralizes the recovered six-axis color model.
- `v3_app/overlay/overlay_config.py` stores the serializable Live Overlay configuration with defaults, restore-defaults behavior, and validation/clamping.
- `v3_app/overlay/telemetry_buffer.py` keeps a bounded simulation/runtime snapshot history for overlay traces.
- `v3_app/overlay/trace_builder.py` converts history samples into plain trace series without depending on PySide6 drawing.
- Live Monitor includes a Live Overlay card that shows preset, status, attached display, hotkey text, summary, runtime truth, Output verified false, and Full Live Runtime Ready false.
- The Live Overlay Configuration dialog shell exposes Placement, Appearance, Behavior, Data, and Axes sections.

Phase 12B adds detached rendering on top of that foundation:

- `v3_app/overlay/live_overlay_window.py` creates an app-owned top-level frameless Qt window for the overlay strip.
- `v3_app/overlay/overlay_renderer.py` draws trace lines, legend, live values, and idle/runtime truth text from Phase 12A trace data.
- Show Overlay creates/shows the detached overlay window; Hide Overlay hides it. The Live Monitor card says Active only when that window is visible.
- Bottom-strip placement uses the current display where Qt can identify one, with safe fallback sizing if screen geometry is unavailable.
- Configuration changes apply to the visible overlay on OK and are discarded on Cancel.

Hotkey registration is not claimed. Click-through support is not claimed. Always-on-top uses Qt window flags only when configured. The overlay can consume simulation/runtime snapshots already available to the UI, but it does not create live hardware runtime, poll real HOTAS input, write vJoy, verify output, manage Bridge lifecycle, hook graphics APIs, inject into games, capture the screen, auto-save, or activate runtime.

Phase 12C freezes the Live Overlay boundary:

- Direct overlay-window close events notify Live Monitor so Status returns to Inactive.
- Dialog copy no longer carries Phase 12A renderer-pending language.
- Hotkey status remains `Not registered`.
- Click-through status remains `Not enabled - not verified`.
- Always-on-top status is config-backed through Qt window flags.
- Help / Docs states that Live Overlay is app-owned and detached, does not inject into games, does not use graphics API hooking, and does not capture the screen.
- Final Phase 12 tests guard against Flight Recorder, recorder hotkey `Ctrl+Shift+F10`, real HOTAS polling, live input streaming, vJoy writes, output verification, process spawning, global-hotkey fake success, click-through fake success, game injection, graphics API hooking, screen capture, cloud AI/LLM behavior, auto-save, and runtime activation.

Axis colors are shared for future Flight Recorder reuse. Flight Recorder is not implemented in Phase 12A, Phase 12B, or Phase 12C.

Phase 12 is complete. The next prompt-book phase is Phase 13: Flight Recorder, Clip Library, and Hindsight Buffer. Phase 13 should reuse shared overlay colors and trace concepts where appropriate, but it must not claim real clip capture, video encoding, or hindsight buffering until implemented and verified.

## Flight Recorder

Phase 13A implements Flight Recorder UI/state/settings/library/preview shell only:

- `v3_app/recorder/recorder_settings.py` stores serializable default settings, validation/clamping, backend availability flags, and axis overlay settings using shared Live Overlay colors.
- `v3_app/recorder/recorder_state.py` stores truthful UI states including capture backend missing, buffering unavailable, saving unavailable, compositor unavailable, and error.
- `v3_app/recorder/clip_library.py` provides a read-only clip library shell and empty-state copy.
- `v3_app/pages/flight_recorder_page.py` provides Recorder Settings, Axis Overlay, Recording Library, and Clip Preview cards.
- The page defaults to capture backend missing and hotkey not registered.
- Record Now and Save Last Clip are disabled because capture, encoding, and hindsight video buffering are not active.
- Clip Preview is a shell and does not play video.

Phase 13A does not add real desktop capture, video encoding, clip export, actual hindsight video buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, live input streaming, vJoy writes, output verification, Bridge lifecycle control, process spawning, cloud AI/LLM behavior, auto-save, or runtime activation.

Phase 13B adds backend-interface foundations without changing runtime authority:

- `v3_app/recorder/capture_backend.py` defines capture backend capability/status types, a default missing backend, and a deterministic simulated backend for tests/dev injection.
- `v3_app/recorder/recorder_artifacts.py` defines JSON-round-trippable artifact metadata.
- `v3_app/recorder/hindsight_buffer.py` stores telemetry-only hindsight samples and can return the previous interval.
- `v3_app/recorder/recorder_controller.py` coordinates settings, backend truth, telemetry hindsight, and simulated artifact operations.
- The default backend remains missing/unavailable, so Record Now and Save Last Clip do not write files.
- The injected simulated backend may write a JSON manifest clearly labeled as a simulated non-video artifact. It is not a playable recording.
- The Recording Library can list simulated manifests as metadata-only artifacts, and Clip Preview shows metadata only with Play disabled.
- Telemetry hindsight is available; desktop video hindsight buffering remains unavailable/deferred.

Phase 13B does not add real desktop capture, real screen capture APIs, video encoding, real clip export, actual desktop video hindsight buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, live input streaming, vJoy writes, output verification, Bridge lifecycle control, process spawning, cloud AI/LLM behavior, auto-save, or runtime activation.

Phase 13C adds overlay compositor/export foundations without adding real capture or encoding:

- `v3_app/recorder/compositor.py` defines compositor capability/status types, a missing compositor, and a deterministic simulated compositor.
- `RecorderExportMetadata` tracks simulated export bundles, manifest path, telemetry sample count, included axes, capture backend, compositor backend, and warnings.
- Simulated export bundles contain `manifest.json`, `overlay_trace.json`, `summary.md`, and `preview_metadata.json`.
- Simulated export traces reuse Phase 12 `build_overlay_traces` and shared recovered axis colors.
- The recorder controller can produce simulated export bundles when both simulated capture and simulated compositor backends are explicitly injected.
- The default missing backend/compositor path still writes no files.
- The Recording Library labels simulated export bundles as simulated/no-video artifacts.
- Clip Preview shows metadata-only simulated export details and keeps Play disabled.
- Telemetry hindsight can feed simulated overlay traces. Desktop video hindsight buffering remains unavailable/deferred.

Phase 13C does not add real desktop capture, real screen capture APIs, video encoding, playable clip export, actual desktop video hindsight buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, live input streaming, vJoy writes, output verification, Bridge lifecycle control, process spawning, cloud AI/LLM behavior, auto-save, or runtime activation.

Phase 13D freezes the Flight Recorder boundary:

- Recording Library indexes simulated export manifests, ignores unknown files, handles missing folders, and labels simulated/no-video/metadata-only rows truthfully.
- Clip Preview shows metadata-only simulated export details and keeps Play/timeline disabled.
- Help / Docs states simulated exports are not real recordings, no screen capture or video encoding is implemented, telemetry hindsight is separate from video hindsight, and the recorder hotkey text is not registered.
- Phase 13 is now complete.
- The next prompt-book phase is Phase 14 Real HOTAS Input Integration. Phase 14 must preserve simulation mode and must not add vJoy writes/output verification unless a later output phase explicitly scopes that work.

Phase 13D does not add real desktop capture, real screen capture APIs, video encoding, playable clip export, actual desktop video hindsight buffering, recorder global hotkey registration, screen capture, game injection, graphics API hooking, real HOTAS polling, live input streaming, vJoy writes, output verification, Bridge lifecycle control, process spawning, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 14A Physical Input Backend And Selection

Phase 14A starts Real HOTAS Input Integration while keeping output/runtime authority frozen:

- `shared_core/runtime/hotas_input.py` defines `PhysicalInputBackend`, backend capabilities/status, device info, selection results, a missing backend, a fake backend for tests, and a read-only Windows PnP discovery backend.
- Supported device matching is centralized for Thrustmaster T-Flight / T.Flight HOTAS One using VID/PID `044f:b68d` and conservative name matching.
- Device selection is in-memory in Phase 14A and reports backend unavailable, no device selected, selected device available, selected device missing, and unsupported selected device.
- Perf / Diagnostics adds a Physical Input card with Physical input backend, Supported HOTAS, Selected input device, Input sampling, and Input selection status.
- Help / Docs states that supported HOTAS detection/selection does not mean vJoy output is active, output_verified remains false, Full Live Runtime Ready remains false, and Phase 15 remains the virtual output/vJoy phase.

Phase 14A does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, end-to-end live runtime loops, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 14B Physical Input Sampling And Normalization

Phase 14B adds read-only sampling and normalization foundations while keeping output/runtime authority frozen:

- `shared_core/runtime/input_normalization.py` normalizes signed, unsigned-centered, already-normalized, and one-sided axis values.
- `shared_core/runtime/hotas_input.py` now includes physical input snapshots, axis/button/hat sample models, sampling statuses, logical HOTAS hints, fake deterministic sample frames, and `PhysicalInputSampler`.
- Fake/test backends can return deterministic samples and emulate disconnect/error states. Missing and Windows PnP discovery backends report sampling unavailable truthfully.
- Perf / Diagnostics adds Last sample, Sample source, Axis/button/hat counts, Sampling warnings, and Sampling errors.
- Physical input sampling is read-only, on-demand, and not a vJoy/output path.
- Output verified remains false and Full Live Runtime Ready remains false even when read-only input samples are available.

Phase 14B does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, end-to-end vJoy runtime loops, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 14C Physical Input UI Integration

Phase 14C surfaces read-only physical input samples in the UI while keeping Bridge/runtime authority frozen:

- `v3_app/services/physical_input_ui.py` provides the UI-facing input source/status model for Simulation, Physical input, stale, unavailable, and error states.
- Mapping shows Physical input backend, Selected input device, Supported HOTAS, Input sampling, sample age/source/counts, Output verified false, and Full Live Runtime Ready false. Fresh physical samples can label Live Raw values as physical input samples.
- Live Monitor can display read-only physical raw axis values, button states, and hat state when a fresh sample is injected or available. It still labels the output path as unverified and states that vJoy writes are not active.
- Effective Response Stack can consume a physical normalized sample for a diagnostic-only preview when available. It does not write final output anywhere.
- Perf / Diagnostics and Copy Diagnostics include Input source and Physical input read-only truth plus sample source/counts/warnings/errors.
- Help / Docs explains that physical samples may appear in Mapping and Live Monitor, final output is not written to vJoy in Phase 14, stale/error samples fall back safely, and Phase 15 remains the virtual output/vJoy phase.

Phase 14C does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, end-to-end live output runtime loops, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 14D Real Input Boundary Freeze

Phase 14 is now complete.

Phase 14D freezes Real HOTAS Input Integration as an input-only boundary:

- Physical input detection, selection, sampling, normalization, and UI display are available through shared-core and UI seams.
- Simulation fallback remains available for no backend, no selected device, selected device missing, stale sample, sample error, backend disconnect, and missing/stale/invalid Bridge telemetry.
- Mapping and Live Monitor may show read-only physical input samples; Effective Response Stack may use those samples for diagnostic-only preview.
- Perf / Diagnostics and Copy Diagnostics include physical input backend/device/sample truth and simulation fallback state.
- Output verified remains false and Full Live Runtime Ready remains false.

## Phase 15A Virtual Output Backend Contract

Phase 15A starts vJoy / Virtual Output Integration without adding real output authority:

Phase 15: vJoy / Virtual Output Integration remains the active prompt-book phase. Phase 15A is the contract-only opening slice.

Full Live Runtime Ready must remain false until both input and output are verified.

- `shared_core/runtime/vjoy_output.py` defines virtual output backend capabilities/status, virtual output device info, output intents, virtual axes/buttons/hats, write results, verification results, and recovered axis route intent.
- Recovered route intent is Roll -> X, Pitch -> Y, Throttle -> Z, Yaw -> RX, Aux 1 -> RY, and Aux 2 -> RZ.
- MissingVirtualOutputBackend remains the safe default and reports backend missing, no output devices, write unavailable, and output verification unverified.
- FakeVirtualOutputBackend is deterministic and test/dev injectable. It records the last intent in memory and can return `fake_verified`, but it also reports Not real vJoy and never sets real output verified.
- Mapping, Live Monitor, Perf / Diagnostics, Copy Diagnostics, and Help / Docs surface virtual output backend, output device status, output write status, output verification status/source, fake output verified, and real output verified truth.

Output intent is not output write proof. vJoy detected does not equal output verified. Fake/mock verification is not real vJoy verification. In normal runtime, output_verified remains false and Full Live Runtime Ready remains false.

Phase 15A does not add real vJoy writes, real output verification, end-to-end live output loops, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 15B Real vJoy Detection And Guarded Verification

Phase 15B adds an optional guarded real vJoy backend without enabling continuous output:

- `RealVJoyOutputBackend` reports dependency, driver/backend, device, write, and verification capability truth.
- The default provider is safe for app startup and does not require a vJoy dependency.
- Provider-injected guarded verification can acquire a selected output device, write a bounded verification intent, attempt neutral restore, and release the device.
- Verification results distinguish dependency missing, backend missing, device missing, device busy, acquisition failure, write failure, neutral restore failure, real verified, unsupported, and error.
- vJoy detection alone is not output verification.
- Fake/mock verification is not real output verification.
- Real output verified can become true only after guarded write success and neutral restore success.
- Full Live Runtime Ready remains false in Phase 15B.

Phase 15B does not add a continuous vJoy output loop, end-to-end live output runtime loop, automatic output enablement, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

Next prompt-book slice: Phase 15C may add runtime output-loop integration only after the guarded verification layer is stable and simulation fallback is preserved.

Phase 14D does not add vJoy writes, virtual output writes, output verification, Full Live Runtime Ready, end-to-end live output runtime loops, automatic Bridge launch, UI-launched child processes, service install, login auto-start, tray manager work, installer launch, StartBridge/StopBridge/RestartBridge behavior, real process scanning, recorder screen capture, video encoding, game injection, graphics API hooking, cloud AI/LLM behavior, auto-save, or runtime activation.

## Phase 9K Boundary Freeze

Phase 9K is a stabilization and regression-gate pass for the Phase 9 truth layer:

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

Phase 9K adds guard tests around forbidden UI controls, unsafe commands, stale telemetry, discovery-only wording, process-hint wording, command acknowledgement matching, and forbidden runtime-authority imports or APIs. It does not add new UI panels or move the Live Monitor layout away from the recovered graph-first design.

## Command Flow

Phase 9D added `v3_app/services/bridge_commands.py`, which writes safe command requests to `%TEMP%\helmforge_bridge_command.json` using atomic JSON writes. Phase 9E adds request IDs, schema versioning, Bridge `last_command` telemetry, stale-command protection, and in-memory duplicate request protection.

Allowed UI commands in Phase 9D:

- `Status`
- `RunPreflight`
- `ReloadConfig`
- `SwitchToSimulation`
- `ClearError`

Disallowed UI commands in Phase 9D:

- `StartBridge`
- `StopBridge`
- `RestartBridge`
- `SuspendBridge`
- `VerifyOutput`

Writing a command file is a request, not a success response. UI labels must use wording such as "command requested" and "awaiting Bridge telemetry" until a later fresh telemetry snapshot provides the actual state.

Phase 9E acknowledgement rules:

- UI command writes include `schema_version`, `request_id`, `command`, `created_at`, and `source`.
- Bridge telemetry includes `last_command` when it consumes, completes, fails, or ignores a command.
- The UI shows acknowledged/completed/failed/ignored only when telemetry `last_command.request_id` matches the latest UI-written request ID.
- Stale command files older than 30 seconds are ignored and reported as `ignored_stale`.
- Re-reading the same request ID on later ticks does not re-execute the command.

## Runtime Truth Rules

- `Full Live Runtime Ready` is allowed only when the central readiness gate sees fresh physical input, successful pipeline processing, guarded real output verification, an explicitly enabled/running output loop according to policy, fresh runtime_frame/Bridge telemetry, and no safety stop or blocking errors.
- vJoy detected is not the same thing as output verified.
- HOTAS detected is not the same thing as real polling implemented.
- Supported-device discovery is not the same thing as a live HOTAS input stream.
- Process presence is not the same thing as Bridge runtime truth.
- Manual launch help text is not a UI-owned launch mechanism.
- Simulation mode remains valid for development, tests, graph previews, and no-hardware states.
- Missing devices or drivers must be visible and non-fatal when simulation can continue.
- The Bridge should fail safe and publish typed errors instead of pretending live output works.

## Lifecycle Goal

Future lifecycle target:

```text
HOTAS plugged in -> Bridge starts or wakes.
HOTAS unplugged -> Bridge suspends, stops, or safe-idles.
UI opened -> UI connects to Bridge and displays current truth.
UI closed -> Bridge may continue if configured and safe.
Config saved -> Bridge reloads config or receives a reload command.
Runtime error -> Bridge enters error/safe-idle and reports the reason.
```

Phase 2B lifecycle contracts are defined in `shared_core/runtime/bridge_lifecycle.py`. Phase 9B exercises `Starting`, `Simulated`, and `Stopping` in tests, with `WaitingForHotas`, `WaitingForOutput`, and `LiveUnverified` preserved for the future real runtime.

## Phase 9G Lifecycle Ownership Decision

Phase 9G records the lifecycle ownership decision in `docs/HelmForge/phase-9g-bridge-lifecycle-ownership-design.md`.

Conservative staged path:

1. Keep manual Bridge launch for now.
2. Add read-only process presence hints later if needed.
3. Prefer a tray/background Bridge manager later for user-session ownership.
4. Defer UI-launched child process until crash/log/stale-state behavior is safe.
5. Defer Windows Service until there is a strong reason.
6. Defer login auto-start until Bridge behavior is stable, user-controlled, and opt-in.
7. Never imply runtime readiness without fresh telemetry and output verification.

Phase 9G is design-only. No lifecycle implementation, process spawning, automatic Bridge launch, tray manager, Windows Service, login auto-start, or real runtime activation was added.

## Current Early-Phase Status

Implemented:

- shared runtime status/preflight models;
- simulation-first runtime snapshots;
- Thrustmaster/vJoy setup detection;
- workspace/config schema;
- Phase 3 shared-core math pipeline from earlier work;
- Phase 2B Bridge lifecycle, command, health, and telemetry contracts.
- Phase 9B separate `bridge_app` package;
- `python -m bridge_app.main --once`;
- `python -m bridge_app.main --run-for-ms <milliseconds>`;
- `python -m bridge_app.main --status`;
- local telemetry JSON output;
- local command JSON parsing for initial Bridge commands.
- Phase 9C UI telemetry client;
- Live Monitor consumption of fresh Bridge telemetry;
- simulation fallback for missing, stale, corrupt, or invalid Bridge telemetry.
- Phase 9D UI command writer for safe commands;
- compact Live Monitor command request controls;
- UI rejection of unsafe commands such as `VerifyOutput` and `StartBridge`.
- Phase 9E Bridge `last_command` telemetry;
- UI command status matching by request ID;
- stale-command and duplicate-request protection.
- Phase 9K boundary-freeze tests and documentation consistency checks.
- Phase 9F telemetry health/timing details;
- compact Live Monitor Bridge health display;
- explicit missing/stale/invalid/error explanation text.
- Phase 9G lifecycle ownership decision record;
- lifecycle wording and safety gates before launch/service/tray work.
- Phase 9H Bridge-owned read-only HOTAS discovery dry-run;
- Live Monitor discovery status wording that preserves output-unverified truth.
- Phase 9I UI-side process presence diagnostics;
- compact Live Monitor diagnosis text that preserves manual Bridge launch ownership.
- Phase 9J stable Live Monitor diagnostic rows;
- discovery-only and command-request wording cleanup.
- Phase 9K final Phase 9 stabilization and boundary freeze.

Current local precheck for the Phase 9J pass:

- Thrustmaster driver/software detected: yes.
- vJoy detected: yes.
- HOTAS device detected: no, at precheck time.
- Runtime mode: `simulated`.
- Runtime truth: `blocked_missing_device`.
- Full Live Runtime Ready: false.
- Live output writes verified: false.

Deferred:

- real Bridge input/output implementation;
- Windows service/tray behavior;
- device-event auto-start/auto-stop;
- real HOTAS polling;
- continuous physical input streaming;
- real vJoy writes;
- socket/named-pipe/streaming IPC;
- UI pages for Bridge control;
- UI-launched Bridge process management;
- diagnostic UX that implies live readiness before output verification.
