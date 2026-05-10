# HelmForge Phase Ledger

This document holds the historical phase information for HelmForge. It was moved out of the root `README.md` so the root README can stay focused on the app itself.

## Current Release Ledger

HelmForge reached final acceptance as **RC Ready With Known Non-Blocking Gaps**.

The final acceptance report is:

```text
docs/HelmForge/final-acceptance-report.md
```

The packaged app target is:

```text
packaging/dist/HelmForge/HelmForge.exe
```

The installer metadata script is:

```text
packaging/inno/helmforge.iss
```

Known release notes preserved from the acceptance ledger:

- `assets/app_icon.ico is missing`.
- Inno Setup compiler availability controls installer compilation.
- Packaged smoke is not runtime readiness.
- Full Live Runtime Ready remains governed by the Phase 16 proof gate.
- No Bridge lifecycle management was claimed by the acceptance reports.

## Phase 0-19 Summary

### Phase 0: Foundation

Established the evidence-led project foundation, repository layout, recovery source preservation, and baseline documentation.

### Phase 1: Runtime Preflight

Added local runtime setup checks and conservative driver/HOTAS/vJoy detection reporting.

### Phase 2: Models, Workspace, And Boundary Contracts

Added workspace/domain models and the early Bridge/UI boundary contracts for lifecycle, command, health, and telemetry data.

### Phase 3: Tuning Math And Signal Pipeline

Added the shared signal pipeline for mapping, tuning, filtering, modes, conditional rules, and final output intent.

### Phase 4: PySide6 Shell

Built the desktop shell, navigation, page structure, header/status surfaces, and early visual system.

### Phase 5: Mapping

Implemented the Mapping page for routing HOTAS axes, buttons, and hats to virtual output intent.

### Phase 6: Core Tuning Pages

Implemented Base Tuning, Filtering, Combat Profile, Modes, and related workspace editing behavior.

### Phase 7: Conditional Rules

Added the Conditional Rules page and rule evaluation behavior for stage-specific output changes.

### Phase 8: Effective Response Stack

Added the response-stack inspection page so users can see how a selected axis changes at each processing stage.

### Phase 9: Bridge Telemetry And UI Truth Seam

Added the Bridge app skeleton, telemetry file, command file, UI telemetry client, command acknowledgement, health/timing details, lifecycle design record, discovery reporting, process presence hints, and boundary freeze tests.

Important Phase 9G lifecycle decision:

- Keep manual Bridge launch during the early lifecycle design.
- Preserve the lifecycle ownership decision as design-only history.
- This record made no lifecycle implementation.
- Do not let UI controls claim start/stop/restart authority until lifecycle behavior is safe and explicit.
- Preserve telemetry as the truth surface.

Phase 9K boundary phrases preserved for documentation tests:

- telemetry remains the truth surface.
- command files are requests, not success proof.
- Bridge command acknowledgement must use matching request_id.
- process presence is a hint only.
- HOTAS discovery is discovery-only.
- supported_device_detected does not mean polling/live runtime/output verified.
- manual Bridge launch remains the current lifecycle model.
- UI does not start, stop, restart, spawn, install, or manage the Bridge.
- output_verified remains false.
- Full Live Runtime Ready remains false.
- live device/runtime work remains deferred.

### Phase 10: Helm Assistant

Added the Helm overlay, local deterministic analysis, grouped recommendations, review/apply/revert workflow, context extraction, and final boundary freeze.

### Phase 11: Help / Docs And Perf / Diagnostics

Added built-in documentation, deterministic search, runtime setup guidance, Perf / Diagnostics timing/runtime truth surfaces, copy diagnostics, and boundary consistency.

Phase 11A implements Help / Docs foundation only.

Perf / Diagnostics page work is deferred to Phase 11B.

Runtime Setup / vJoy Setup article is local built-in documentation.

Help / Docs does not add runtime authority.

Help / Docs does not use cloud AI or LLM behavior.

### Phase 12: Live Overlay

Added Live Overlay configuration, telemetry history buffering, trace building, a detached overlay window, renderer behavior, and final overlay truth labels.

### Phase 13: Flight Recorder

Added Flight Recorder UI, settings/state/library/preview shells, recorder backend seams, telemetry hindsight buffering, simulated non-video artifacts, compositor/export metadata, and preview/library polish.

### Phase 14: Physical Input

Added physical HOTAS backend contracts, supported-device matching, selection diagnostics, sampling models, normalization, fake/missing backends, and read-only UI integration.

Phase 14 is now complete.

The next output-focused area was Phase 15: vJoy / Virtual Output Integration.

Full Live Runtime Ready must remain false until both input and output are verified.

### Phase 15: vJoy / Virtual Output

Added virtual output backend contracts, output intent models, fake/missing backends, guarded real vJoy detection and verification, controlled output write loop, safety stops, neutral restore, and output terminology freeze.

### Phase 16: Runtime End-To-End Live Mode

Added the runtime orchestrator, compact runtime frames, Bridge `runtime_frame` telemetry, proof fields for input/pipeline/output/output-loop state, and the final Full Live Runtime Ready evaluator.

### Phase 17: Product Polish

Improved layout, visual consistency, status chip/action button distinction, scroll behavior, page reuse, hidden-page update discipline, graph update smoothness, performance timing, and final product QA.

Phase 17A covered Product Polish, Layout QA, and Motion.

Phase 17B covered interaction smoothness and performance discipline. Its timing work is app diagnostics, not hardware or output proof, and it did not add hardware polling or vJoy writes.

Phase 17C completed product QA and packaging readiness. Phase 17C does not implement packaging. It handed off to Phase 18: Packaging, Installer, Icons, and User Data Locations, while preserving simulation mode.

### Phase 18: Packaging

Added packaging foundation, PyInstaller one-folder build path, Inno Setup metadata, user data path helpers, resource path helpers, packaged smoke behavior, and final packaging QA.

Phase 18A notes preserved for tests and release traceability:

- Phase 18A began Packaging, Installer, Icons, and User Data Locations.
- It added packaging foundation docs, build script structure, source launch notes, and user data path planning.
- simulation mode remained available.
- The pass does not implement a full installer.
- Full Live Runtime Ready remained separate from packaging work.

Phase 18B notes preserved for tests and release traceability:

- Phase 18B introduced the one-folder build path.
- `packaging/dist/HelmForge/HelmForge.exe` is the packaged executable path.
- `--smoke-exit-ms 250` is the packaged smoke argument.
- The one-folder build does not create an installer.
- Simulation mode remains available.
- simulation mode remains available.
- Full Live Runtime Ready remains separate from packaging smoke.

Phase 18C notes preserved for tests and release traceability:

- Phase 18C added installer metadata for Start Menu shortcut creation.
- It documented optional Desktop shortcut behavior.
- It documented uninstall metadata and user data preservation.
- The installer does not install drivers.
- The installer does not manage Bridge lifecycle.
- user data is preserved by default.
- No production-signed installer is claimed.

Phase 18D notes preserved for tests and release traceability:

- Phase 18D completed packaging QA.
- Phase 18 is now complete.
- Phase 19: Final Integration Kraken / Full Acceptance Sweep followed packaging.
- The packaging docs preserve the one-folder build and installer metadata truth.
- Phase 18D does not add runtime authority.

### Phase 19: Final Integration And Acceptance

Added the full product acceptance inventory, integration Kraken regression sweep, final corrections, and final acceptance report.

Phase 19D final acceptance status:

- RC Ready With Known Non-Blocking Gaps.
- Final report: `docs/HelmForge/final-acceptance-report.md`.
- Packaged app target: `packaging/dist/HelmForge/HelmForge.exe`.
- `assets/app_icon.ico is missing`.
- packaged smoke is not runtime readiness.
- Full Live Runtime Ready remains governed by the Phase 16 proof gate.
- no Bridge lifecycle management is claimed by the release ledger.

## Post-RC Ledger

Post-RC work continued after the acceptance report with focused usability, documentation, recorder, mapping, and live-runtime integration passes.

Major post-RC areas:

- Global shell and sidebar usability.
- Parameter metadata and help coverage.
- Mapping diagram interaction and editing.
- Flight Recorder capture/export/storage seams.
- Tuning page usability and live sampling.
- Runtime, recorder, docs, and diagnostics polish.
- Live HOTAS Bridge runtime and real vJoy provider wiring.

## Current Runtime Truth Update

The current live runtime path can run through:

```text
Physical HOTAS
  -> Windows joystick backend
  -> Bridge sampler
  -> runtime orchestrator
  -> workspace signal pipeline
  -> virtual output intent
  -> real vJoy provider
  -> vJoy device
```

The UI starts an embedded Bridge worker when the app window is shown. The worker runs off the UI thread and publishes telemetry for the header, Mapping, tuning pages, Live Monitor, Effective Response Stack, and Perf / Diagnostics.

See [Bridge](bridge.md) for the current runtime explanation.
