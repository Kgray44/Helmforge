# HOTAS Control Panel V2 — Codex Prompt Book

## Purpose

This document is a highly detailed implementation prompt book for rebuilding **HOTAS Control Panel V2** from the recovered forensic spec set.

The original software was erased, so this prompt book is designed to help rebuild the application in controlled phases using Codex or another coding agent. It is based on the recovered multi-document spec set:

1. `01-hotas-control-panel-master-recovery-index.md`
2. `02-product-vision-and-visual-design-system.md`
3. `03-core-tuning-engine-mapping-and-modes.md`
4. `04-conditional-rules-system.md`
5. `05-graphs-and-effective-response-stack.md`
6. `06-helm-assistant-specification.md`
7. `07-flight-recorder-live-monitor-and-live-overlay.md`
8. `08-architecture-performance-rebuild-roadmap-and-unknowns.md`

This prompt book is not meant to be pasted all at once. Use one phase prompt at a time. Each phase should end with tests, visible acceptance criteria, and a short implementation report before moving forward.

---

# Global Rebuild Rules

These rules apply to every phase.

## Product Identity Rules

HOTAS Control Panel V2 must feel like:

- premium engineering/tuning software,
- a serious HOTAS/vJoy control workspace,
- a control-console / signal-lab / avionics-style diagnostic tool,
- polished desktop software, not a prototype,
- fast, smooth, and trustworthy.

It must **not** feel like:

- a generic SaaS dashboard,
- a toy utility,
- a bubbly mobile-style app,
- a rough Tkinter control panel,
- a debug test harness,
- a pretty UI with no actual runtime wiring.

Target reaction:

> “DAMN THIS IS NICE SOFTWARE.”

Yes, that is an official acceptance criterion. Engineering standards are serious business. Also dramatic.

## Technical Direction

Build the modern V2 app using:

- Python
- PySide6 / Qt Widgets
- pyqtgraph for live and interactive graphs
- a safe parallel V2 architecture
- shared backend/core modules for domain logic
- preserved legacy app where possible, without destructive rewrites

V2 must be a **safe parallel app**, not a destructive replacement of any recovered/legacy material.

## Runtime Reality Rule

Do **not** fake live HOTAS/vJoy behavior.

The rebuilt app must eventually support a real physical HOTAS and a real virtual joystick output path, but the user currently does **not** have vJoy or the runtime bridge installed. Therefore the build must support these distinct runtime states:

1. **Demo / Simulated Runtime**
   - No physical HOTAS required.
   - No vJoy required.
   - Useful for UI, graphs, rules, Helm, and recorder development.

2. **Hardware Detected, Output Missing**
   - Physical HOTAS may be present.
   - vJoy or output driver is missing.
   - App should show clear setup guidance.

3. **vJoy Installed, HOTAS Missing**
   - Output path exists.
   - Input device missing.
   - App should allow configuration and simulated testing.

4. **Full Live Runtime**
   - Physical HOTAS detected.
   - vJoy/output backend detected.
   - Runtime bridge active.
   - Live Monitor, Effective Response Stack, mappings, modes, rules, and output telemetry should reflect real data.

The app must clearly distinguish these states in the UI. No “it says live but nothing is wired” goblin nonsense.

## No Fake Success Rule

Codex must never claim something is working live unless it is actually verified.

Examples:

- Do not say “vJoy output working” unless a vJoy device was detected and an output write succeeded.
- Do not say “HOTAS connected” unless a physical device was enumerated.
- Do not say “recorder saved clip” unless a real file was written and verified.
- Do not say “overlay click-through works” unless the platform/window flags were applied and the overlay behavior is testable.

Use truth-labeled statuses:

- `Simulated`
- `Configured`
- `Detected`
- `Missing Driver`
- `Missing Device`
- `Live`
- `Output Verified`
- `Output Unverified`
- `Recording Ready`
- `Recording Blocked`

## UI Quality Rules

Every phase must preserve:

- dark premium visual style,
- rounded corners through Qt/QSS/native styling,
- strong spacing discipline,
- no overlap,
- no clipping,
- scrollable tall pages,
- clear distinction between status chips and action buttons,
- no ugly dark strips behind every text region,
- no prototype copy like “safe parallel frontend” in final user-facing text,
- no visible full-page redraw jank,
- no random status chips that look clickable.

## Performance Rules

Every phase must respect:

- hidden pages skip expensive work,
- graph updates are scoped locally,
- retained/reused widgets where possible,
- no constant widget rebuilds on heartbeat,
- central scheduler/heartbeat for runtime refresh,
- diagnostic metrics available in Perf / Diagnostics,
- no UI work blocking runtime input/output processing.

## Persistence Rules

The app must use a safe workspace model:

- edit current workspace/draft in memory,
- write only when the user saves,
- support Revert,
- support Import Profile,
- keep user data separate from binaries,
- eventually store user data in AppData/LocalAppData,
- avoid overwriting original/recovered configs silently.

Use `hotas_bridge_config_v2.json` as the known recovered workspace/config name unless a better schema is created and documented.

---

# Suggested Repository Structure

Codex should create or migrate toward this structure:

```text
HOTAS-Control-Panel-V2/
  README.md
  pyproject.toml
  requirements.txt
  .gitignore

  shared_core/
    __init__.py
    models/
      __init__.py
      axes.py
      mappings.py
      modes.py
      tuning.py
      filtering.py
      combat.py
      rules.py
      profiles.py
      runtime.py
      workspace.py
    math/
      __init__.py
      curves.py
      deadzone.py
      filtering.py
      stack.py
    runtime/
      __init__.py
      device_discovery.py
      simulated_runtime.py
      hotas_input.py
      vjoy_output.py
      runtime_bridge.py
      runtime_status.py
    persistence/
      __init__.py
      workspace_store.py
      profile_store.py
      schema.py
    diagnostics/
      __init__.py
      perf.py
      logging.py

  v2_app/
    __init__.py
    main.py
    app.py
    theme/
      __init__.py
      tokens.py
      qss.py
    ui/
      __init__.py
      shell.py
      sidebar.py
      header.py
      footer.py
      status_chips.py
    widgets/
      __init__.py
      cards.py
      fields.py
      graphs.py
      tables.py
      dialogs.py
      axis_widgets.py
    pages/
      __init__.py
      mapping_page.py
      modes_page.py
      base_tuning_page.py
      filtering_page.py
      combat_profile_page.py
      profiles_page.py
      conditional_rules_page.py
      effective_response_stack_page.py
      live_monitor_page.py
      flight_recorder_page.py
      help_docs_page.py
      perf_diagnostics_page.py
    helm/
      __init__.py
      helm_overlay.py
      helm_engine.py
      symptom_library.py
      recommendation_library.py
      diff_model.py
    overlay/
      __init__.py
      telemetry_buffer.py
      overlay_config.py
      trace_builder.py
      live_overlay_window.py
      overlay_renderer.py
    recorder/
      __init__.py
      capture_backend.py
      encoder.py
      compositor.py
      clip_library.py
      clip_preview.py
    services/
      __init__.py
      app_state.py
      scheduler.py
      runtime_service.py
      workspace_service.py

  legacy_app/
    README.md

  assets/
    app_icon.ico
    app_icon_detailed.png
    app_icon_taskbar.png
    helm_wheel_icon.png

  packaging/
    README.md
    build_release.ps1
    inno/
      hotas_control_panel_v2.iss

  tests/
    test_curves.py
    test_deadzone.py
    test_filtering.py
    test_rules.py
    test_stack.py
    test_workspace_store.py
    test_runtime_status.py
    test_simulated_runtime.py
    test_vjoy_detection.py
    test_mapping_models.py
    test_overlay_config.py
    test_helm_diff_model.py
```

This structure can be adjusted if needed, but Codex must keep the same separation of concerns:

- shared domain/core logic outside UI,
- V2 UI in PySide6,
- runtime/hardware code isolated,
- simulation runtime available from the beginning,
- recorder/overlay separated from tuning engine,
- Helm separated from main UI file.

---

# Phase 0 — Evidence Lock and Project Setup

## Goal

Create a safe rebuild environment and preserve the recovered documentation before writing app code.

This phase exists because the original software was erased. The first job is to make sure the recovery data itself does not become another sacrifice to the file-goblin volcano.

## Codex Prompt

```text
You are starting the HOTAS Control Panel V2 rebuild from forensic recovery notes.

Before writing application logic, create a safe project foundation.

Requirements:

1. Create a clean repository/project structure for HOTAS Control Panel V2.
2. Add a `/docs/recovery/` folder.
3. Copy or create placeholders for these recovered spec documents:
   - 01-hotas-control-panel-master-recovery-index.md
   - 02-product-vision-and-visual-design-system.md
   - 03-core-tuning-engine-mapping-and-modes.md
   - 04-conditional-rules-system.md
   - 05-graphs-and-effective-response-stack.md
   - 06-helm-assistant-specification.md
   - 07-flight-recorder-live-monitor-and-live-overlay.md
   - 08-architecture-performance-rebuild-roadmap-and-unknowns.md
4. Add a `/docs/rebuild/` folder for implementation notes, phase reports, and decisions.
5. Add `README.md` explaining:
   - this is a safe V2 rebuild,
   - the old app was lost,
   - recovered docs are governing references,
   - hardware/vJoy runtime will be implemented in phases,
   - simulation mode exists so development can proceed before drivers are installed.
6. Add `.gitignore` for Python, virtual environments, build output, logs, local user data, recordings, and temporary artifacts.
7. Add `pyproject.toml` or `requirements.txt` with initial dependencies:
   - PySide6
   - pyqtgraph
   - pytest
8. Add an initial `shared_core` package and `v2_app` package with empty `__init__.py` files.
9. Add a simple `python -m v2_app.main` entry point that opens a minimal PySide6 window titled `HOTAS Control Panel V2`.
10. Do not implement real HOTAS/vJoy yet.
11. Do not claim runtime support is working yet.

Acceptance criteria:
- Project imports cleanly.
- Minimal PySide6 app launches.
- Recovery docs folder exists.
- README clearly explains simulation-first rebuild.
- `pytest` runs, even if only a smoke test exists.

After implementation, report:
- files created,
- commands run,
- whether the app launched,
- any missing dependencies,
- next recommended phase.
```

## Acceptance Checklist

- [ ] Project has stable folder structure.
- [ ] Recovery docs are preserved.
- [ ] Minimal PySide6 app opens.
- [ ] Dependencies documented.
- [ ] Simulation-first runtime strategy is clearly stated.
- [ ] No fake hardware claims.

---

# Phase 1 — Runtime Preflight, HOTAS Detection, vJoy Detection, and Simulation Mode

## Goal

Add the missing practical foundation: the app must know whether a physical HOTAS and vJoy/output backend are installed. Since the user currently does **not** have vJoy installed, this phase must make that visible and non-blocking.

The app should be useful in simulation mode before any hardware driver is installed.

## Why This Phase Is Critical

The recovered docs describe HOTAS/vJoy mapping, raw input, final vJoy output, Live Monitor, Effective Response Stack, Flight Recorder telemetry, and Helm diagnostics. But none of those can honestly be “live” unless the app can detect and report runtime status.

This phase prevents the app from becoming a beautiful cockpit with the wiring harness sitting on the floor making raccoon noises.

## Required Runtime States

Implement a typed runtime status model with at least:

```text
RuntimeMode:
- SIMULATED
- HARDWARE_ONLY
- OUTPUT_ONLY
- FULL_LIVE
- UNAVAILABLE

InputStatus:
- NOT_CHECKED
- MISSING
- DETECTED
- ERROR

OutputStatus:
- NOT_CHECKED
- VJOY_MISSING
- VJOY_DETECTED
- OUTPUT_VERIFIED
- OUTPUT_ERROR

RuntimeTruth:
- simulated
- detected_unverified
- live_verified
- blocked_missing_driver
- blocked_missing_device
- error
```

Use names that fit the codebase, but preserve the semantics.

## Codex Prompt

```text
Implement the runtime preflight foundation for HOTAS Control Panel V2.

Context:
The user does not currently have vJoy or a real HOTAS runtime bridge installed. The app must not fail because of this. It must support simulation mode and clearly report missing runtime pieces.

Build the following:

1. Runtime status models in `shared_core/models/runtime.py`.
   Include typed status enums/classes for:
   - input device detection,
   - output/vJoy detection,
   - runtime mode,
   - runtime truth label,
   - error/warning messages,
   - detected device names,
   - detected output backend name,
   - whether live output writes are verified.

2. Device discovery module in `shared_core/runtime/device_discovery.py`.
   It should provide safe discovery functions:
   - `detect_input_devices()`
   - `detect_output_backends()`
   - `build_runtime_preflight_status()`

3. vJoy output adapter placeholder in `shared_core/runtime/vjoy_output.py`.
   Requirements:
   - Do not require vJoy to be installed for imports to succeed.
   - Detect missing vJoy gracefully.
   - Provide a clear status object when vJoy is unavailable.
   - Provide placeholder methods for future output writes.
   - Never claim output writes are verified unless a real backend confirms them.

4. HOTAS input adapter placeholder in `shared_core/runtime/hotas_input.py`.
   Requirements:
   - Do not require physical hardware for imports to succeed.
   - Provide safe enumeration hooks.
   - Return missing/detected/error states clearly.

5. Simulation runtime in `shared_core/runtime/simulated_runtime.py`.
   Requirements:
   - Generate simulated axis values for Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2.
   - Generate simulated button states B1-B15.
   - Generate simulated hat state.
   - Allow deterministic mode for tests.
   - Allow live animated mode for UI graphs.

6. Runtime bridge in `shared_core/runtime/runtime_bridge.py`.
   Requirements:
   - Select SIMULATED mode by default if hardware/vJoy is missing.
   - Provide latest raw axis values.
   - Provide latest final output values.
   - Provide button/hat states.
   - Provide runtime status/truth labels.
   - Keep simulated and future real runtime behind the same interface.

7. Add tests:
   - missing vJoy does not crash imports,
   - missing HOTAS does not crash imports,
   - simulation runtime returns all six axes,
   - runtime preflight reports simulation fallback correctly,
   - no status says FULL_LIVE when vJoy/HOTAS are missing.

8. Add a documentation file:
   `/docs/rebuild/runtime-preflight-and-vjoy-setup.md`

This doc should explain:
- the app can run without vJoy in simulation mode,
- what vJoy/output backend is for,
- how the app reports missing drivers/devices,
- what must be installed later for full live output,
- that installation steps are intentionally separated from detection code.

Do not implement actual vJoy writes yet unless a safe library/backend is already available. This phase is about truth, detection, and simulation.

Acceptance criteria:
- App can start without vJoy.
- App can start without HOTAS connected.
- Simulation runtime produces plausible data.
- Tests pass.
- Runtime status makes missing driver/device obvious.
- No fake live output claims.

Report files changed, tests run, and current runtime truth behavior.
```

## Acceptance Checklist

- [ ] App does not require vJoy to launch.
- [ ] App does not require HOTAS to launch.
- [ ] Simulation runtime works.
- [ ] Runtime status distinguishes simulation from live.
- [ ] vJoy missing state is clear and non-fatal.
- [ ] Physical HOTAS missing state is clear and non-fatal.
- [ ] Tests prove no fake live status.

---

# Phase 2 — Core Domain Models and Workspace Schema

## Goal

Create the shared data model for axes, mappings, modes, tuning parameters, filtering, combat profile, conditional rules, profiles, and workspace state.

This phase should not focus on UI polish yet. It creates the app’s brain bones. A sentence no one wanted but everyone needed.

## Recovered Facts To Preserve

Axis set:

- Roll
- Pitch
- Throttle
- Yaw
- Aux 1
- Aux 2

Mapping examples:

- Roll: Raw axis 1 -> X -> X(axis1)
- Pitch: Raw axis 2 -> Y -> Y(axis2)
- Throttle: Raw axis 3 -> Z -> Z(axis3)
- Yaw: Raw axis 6 -> RZ -> RX(axis4)
- Aux 1: Raw axis 7 -> SL0 -> RY(axis5)
- Aux 2: Raw axis 8 -> RX -> RZ(axis6)

Mode examples:

- Precision button: 0
- Zoom button: 5
- Stack mode: multiply

Base tuning parameters:

- Curve Mode
- Curve Strength / k
- Deadzone
- Anti-Deadzone
- Hysteresis
- Output Scale
- Max Output
- Precision scale if retained from legacy model
- Invert if retained from mapping/tuning model

Filtering parameters:

- Center Alpha
- Edge Alpha
- Same Slew Limit
- Reverse Slew Limit

Combat profile parameters:

- Combat Curve
- Combat Scale
- Combat Center Alpha
- Combat Edge Alpha
- Combat Same Slew
- Combat Reverse Slew

## Codex Prompt

```text
Implement the shared domain models and workspace schema for HOTAS Control Panel V2.

Use the recovered spec documents as governing references.

Create strongly typed Python models/dataclasses for:

1. Axes
   - Roll
   - Pitch
   - Throttle
   - Yaw
   - Aux 1
   - Aux 2

2. Axis mapping
   Fields should support:
   - function/display name
   - raw axis channel
   - logical output
   - runtime vJoy output
   - invert
   - live raw value
   - live output value

3. Button mapping
   Fields should support:
   - HOTAS button number
   - vJoy/output button number
   - raw state
   - output state

4. Hat mapping
   Fields should support:
   - HOTAS hat number
   - vJoy POV number
   - optional Up/Right/Down/Left mapped button values
   - live hat state

5. Modes
   Fields should support:
   - Precision Hold Buttons
   - Combat Trigger Buttons
   - Combat Zoom/Aim Buttons
   - Combat Extra Buttons
   - Precision + Combat Stack Mode, including multiply

6. Base tuning per axis
   Fields should support:
   - Curve Mode
   - Curve Strength / k
   - Deadzone
   - Anti-Deadzone
   - Hysteresis
   - Output Scale
   - Max Output
   - Precision scale if needed
   - Invert if appropriate

7. Filtering per axis
   Fields should support:
   - Center Alpha
   - Edge Alpha
   - Same Slew Limit
   - Reverse Slew Limit

8. Combat profile per axis
   Fields should support:
   - Combat Curve
   - Combat Scale
   - Combat Center Alpha
   - Combat Edge Alpha
   - Combat Same Slew
   - Combat Reverse Slew

9. Conditional rule model placeholder
   Include fields recovered from the rules spec:
   - title
   - enabled
   - target axis
   - parameter
   - operation
   - value
   - injection stage
   - mode gate
   - buttons
   - button test
   - reference axis
   - stage
   - measure
   - comparator
   - threshold
   - threshold high

10. Profile model
    Include built-in profile names:
    - Balanced Flight
    - Precision Tracking
    - Aggressive Combat
    - Smooth Cinematic
    - Current Workspace

11. Workspace model
    Include:
    - mappings
    - modes
    - tuning
    - filtering
    - combat
    - rules
    - active profile
    - dirty/saved state metadata
    - source path such as `hotas_bridge_config_v2.json`

12. Persistence layer
    Implement load/save to JSON using a versioned schema.
    Use safe defaults when the file is missing.
    Do not silently overwrite original configs.

13. Tests
    Add tests proving:
    - default workspace creates all six axes,
    - recovered mapping defaults are present,
    - workspace can save/load round trip,
    - missing/corrupt JSON falls back safely or reports useful error,
    - profile names exist,
    - conditional example rule can be represented.

Acceptance criteria:
- Shared models are UI-independent.
- Workspace JSON round-trips.
- Defaults reflect recovered specs.
- Tests pass.
- No runtime hardware required.

Report files changed and schema decisions.
```

## Acceptance Checklist

- [ ] All six axes represented.
- [ ] Mapping defaults represented.
- [ ] Workspace JSON exists.
- [ ] Save/load works.
- [ ] Rule model can represent recovered Yaw/Roll rule.
- [ ] No UI dependency in shared core.

---

# Phase 3 — Tuning Math and Signal Pipeline

## Goal

Implement the actual control transformation pipeline used by Base Tuning, Filtering, Combat Profile, Modes, Conditional Rules, Effective Response Stack, Live Monitor, and Helm.

This should be testable without UI and without real hardware.

## Required Pipeline

The recovered stack is:

1. Raw Input
2. Center Conditioning
   - Deadzone
   - Anti-deadzone
   - Hysteresis
3. Curve / Shape
4. Base Output Limits
5. Filtering
6. Mode Modifiers
7. Conditional Rule Injections
8. Final Output

## Important Math Notes

Recovered representative curve formula:

```text
y = (1-k)x + kx^3
```

for centered S-curve axes.

Also preserve:

- deadzone remapping to preserve full output after deadzone,
- one-sided / J-curve throttle concept if applicable,
- center/edge alpha filtering,
- same-direction slew limit,
- reverse-direction slew limit,
- precision/combat stack mode multiply.

## Codex Prompt

```text
Implement the tuning math and signal pipeline for HOTAS Control Panel V2.

This must live in shared_core and must be fully testable without PySide6, HOTAS hardware, or vJoy.

Implement modules:

- `shared_core/math/curves.py`
- `shared_core/math/deadzone.py`
- `shared_core/math/filtering.py`
- `shared_core/math/stack.py`

Requirements:

1. Curve processing
   - Implement S-curve behavior using the recovered representative formula `y = (1-k)x + kx^3` or a clearly documented equivalent.
   - Preserve odd symmetry for centered axes.
   - Clamp outputs safely to configured max.
   - Support scale and max output.
   - Do not transform the graph's linear reference line; graph reference must remain true `y=x`.

2. Deadzone processing
   - Apply deadzone around center.
   - Apply anti-deadzone if configured.
   - Remap remaining range so full stick travel can still reach full output.
   - Handle positive and negative values symmetrically for centered axes.

3. Hysteresis
   - Add a simple stateful hysteresis mechanism for near-center jitter suppression.
   - Keep it testable and deterministic.

4. Filtering
   - Implement center alpha and edge alpha behavior.
   - Implement same-direction slew limit.
   - Implement reverse-direction slew limit.
   - Return both output and diagnostic details.

5. Modes
   - Apply precision scaling when precision mode is active.
   - Apply combat profile modifiers when combat mode is active.
   - Support multiply stack mode when precision and combat overlap.

6. Stack result model
   - For each axis sample, produce a structured stage-by-stage result:
     - stage name
     - input value
     - output value
     - delta
     - active/inactive status
     - explanation text
     - injected rules if any
   - This result will power Effective Response Stack and Helm.

7. Simulation integration
   - Allow the simulated runtime to feed raw values through this pipeline and produce final outputs.

8. Tests
   Add tests for:
   - S-curve symmetry,
   - deadzone zeroing near center,
   - full-range remap after deadzone,
   - scale/max clamp,
   - filtering same-direction slew,
   - filtering reverse-direction slew,
   - precision/combat multiply mode,
   - stack result includes expected stages,
   - linear reference helper returns true `y=x` data.

Acceptance criteria:
- Pipeline works without UI/hardware.
- Stage results are detailed enough for Effective Response Stack.
- Tests pass.
- Graph reference line bug is prevented by test.

Report formulas used, assumptions, tests run, and any deviations from recovered notes.
```

## Acceptance Checklist

- [ ] Curve math implemented.
- [ ] Deadzone/anti-deadzone implemented.
- [ ] Filtering/slew implemented.
- [ ] Precision/combat mode application implemented.
- [ ] Stage-by-stage stack results produced.
- [ ] Linear reference test exists.
- [ ] No hardware dependency.

---

# Phase 4 — PySide6 App Shell, Theme, Sidebar, Header, Footer

## Goal

Build the premium V2 shell around the already-created models and runtime status layer.

This is the phase where it starts looking like the recovered V2 app instead of an empty Python window that wandered into a cockpit factory.

## Required Shell Details

Left sidebar:

- Title: `HOTAS V2`
- Subtitle: `Control workspace`
- Navigation:
  - Mapping
  - Modes
  - Base Tuning
  - Filtering
  - Combat Profile
  - Profiles
  - Conditional Rules
  - Effective Response Stack
  - Live Monitor
  - Flight Recorder
  - Help / Docs
  - Perf / Diagnostics
- Runtime card at bottom:
  - `Runtime`
  - status such as `Simulated`, `Idle`, `Live`, `Missing vJoy`, etc.

Header:

- Title: `HOTAS Control Panel V2`
- Subtitle: `Professional tuning, live inspection, and assistant-guided diagnostics in one modern control workspace.`
- Top-right `STATUS` cluster:
  - `Workspace Copy`
  - `Saved` / `Unsaved`
  - runtime truth: `Simulated`, `Idle`, `Live`, etc.
- Top-right `ASSISTANT` cluster:
  - `Helm`

Footer:

- left status message,
- center page/axis/profile/source details,
- right buttons:
  - `Import Profile`
  - `Revert`
  - `Save Workspace`

## Codex Prompt

```text
Build the HOTAS Control Panel V2 PySide6 shell and visual design system.

Use the recovered visual spec as governing reference.

Requirements:

1. Create a QMainWindow-based app shell.
2. Use a left sidebar, top header, central stacked page area, and bottom footer.
3. Implement a theme system using QSS/tokens.
4. Do not use custom canvas-rounded rendering. Use Qt/QSS/native styling.
5. Use a premium dark engineering-control aesthetic:
   - deep navy background,
   - slate-blue cards,
   - cyan/blue accents,
   - green live/active states,
   - amber caution/unsaved states,
   - red destructive states,
   - white headings,
   - pale blue-gray secondary text.
6. Implement sidebar navigation with correct active state.
7. Add pages as placeholders initially:
   - Mapping
   - Modes
   - Base Tuning
   - Filtering
   - Combat Profile
   - Profiles
   - Conditional Rules
   - Effective Response Stack
   - Live Monitor
   - Flight Recorder
   - Help / Docs
   - Perf / Diagnostics
8. Add runtime status card using Phase 1 runtime status.
   If no vJoy/HOTAS is installed, show simulation/missing-driver truthfully.
9. Add top-right STATUS cluster.
   Status chips must not look like action buttons.
10. Add top-right ASSISTANT cluster with Helm button.
11. Add footer with Import Profile, Revert, Save Workspace.
12. Add page switching with reused page instances.
13. Avoid visible rebuild/jank on page switch.
14. Add scroll support for tall pages.
15. Add basic Perf / Diagnostics values for page switch timing.

Acceptance criteria:
- App launches to full V2 shell.
- Sidebar active state updates correctly.
- Header/footer match recovered labels.
- Runtime status truthfully reports simulation/missing runtime pieces.
- No page content overlaps.
- Placeholder pages are scroll-safe.
- Status chips look non-clickable; action buttons look clickable.
- Tests or smoke checks cover app construction and page registration.

Report screenshots if possible, files changed, tests run, and any visual deviations.
```

## Acceptance Checklist

- [ ] Shell matches recovered structure.
- [ ] Sidebar exists and works.
- [ ] Header/status/assistant clusters exist.
- [ ] Footer actions exist.
- [ ] Runtime status includes simulation/missing vJoy truth.
- [ ] Active page highlight works.
- [ ] No clipping/overlap.

---

# Phase 5 — Mapping Page and Runtime Setup Guidance

## Goal

Build the Mapping page and include clear runtime setup/preflight guidance because the user does not yet have vJoy installed.

This phase bridges the recovered mapping UI with the real-world setup problem.

## Required Page Content

Mapping page title:

- `Mapping`

Recovered copy:

- `Map raw HOTAS axes, buttons, and hats to the bridge outputs that drive vJoy.`

Sections:

1. Runtime Setup / Preflight
2. Routing Overview
3. Live Route Summary
4. Axis Routing
5. Button Routing
6. Hat Routing

Routing Overview values:

- Axis Routes: 6
- Button Routes: 15
- Hat Routes: 1

Tables:

Axis Routing columns:

- Function
- Raw Axis
- Logical Output
- Runtime vJoy
- Invert
- Live Raw
- Live Output

Button Routing columns:

- HOTAS Button
- vJoy Button
- Raw
- Output

Hat Routing columns:

- HOTAS Hat
- vJoy POV
- Up
- Right
- Down
- Left
- Live

## Runtime Setup Card

Add a card that explains current runtime state:

Examples:

- `Simulation Mode Active`
- `vJoy Missing`
- `HOTAS Missing`
- `Ready for Live Runtime`

Actions:

- `Run Preflight Check`
- `Use Simulation Mode`
- `Open Runtime Setup Guide`

The setup guide should not pretend to install drivers automatically unless explicitly implemented safely later.

## Codex Prompt

```text
Implement the Mapping page and Runtime Setup / Preflight UI for HOTAS Control Panel V2.

Context:
The user currently does not have vJoy installed. The Mapping page must show this truthfully while still allowing simulation-mode development and configuration.

Requirements:

1. Build `MappingPage` in PySide6.
2. Add title `Mapping`.
3. Add copy: `Map raw HOTAS axes, buttons, and hats to the bridge outputs that drive vJoy.`
4. Add a Runtime Setup / Preflight card at the top.
   It must show:
   - input device status,
   - output/vJoy status,
   - runtime mode/truth label,
   - detected device names if any,
   - clear messages when vJoy or HOTAS is missing.
5. Add actions:
   - `Run Preflight Check`
   - `Use Simulation Mode`
   - `Open Runtime Setup Guide`
6. Add Routing Overview card:
   - Axis Routes: 6
   - Button Routes: 15
   - Hat Routes: 1
   - Include recovered note about Battlefield-safe runtime routing remapping RX / RY / RZ / SL0 behind the scenes when needed.
7. Add Live Route Summary with recovered mappings:
   - Roll: Raw axis 1 -> X -> X(axis1)
   - Pitch: Raw axis 2 -> Y -> Y(axis2)
   - Throttle: Raw axis 3 -> Z -> Z(axis3)
   - Yaw: Raw axis 6 -> RZ -> RX(axis4)
   - Aux 1: Raw axis 7 -> SL0 -> RY(axis5)
   - Aux 2: Raw axis 8 -> RX -> RZ(axis6)
8. Add Axis Routing table with columns:
   - Function
   - Raw Axis
   - Logical Output
   - Runtime vJoy
   - Invert
   - Live Raw
   - Live Output
9. Add Button Routing table with actions:
   - Add Route
   - Remove Selected
   - Reset 1:1
10. Add Hat Routing table with actions:
   - Add Hat
   - Remove Selected
11. Wire the page to the workspace model and simulation runtime.
12. In simulation mode, Live Raw and Live Output values should update with simulated values.
13. If vJoy is missing, Runtime vJoy columns still show intended outputs, but status must say output is unverified/missing.
14. Add tests or smoke checks for:
   - Mapping page construction,
   - default axis rows,
   - preflight status display logic,
   - simulation values can populate table models.

Acceptance criteria:
- Mapping page matches recovered content.
- vJoy missing is visible and non-fatal.
- Simulation mode populates live values.
- Axis/button/hat tables exist.
- No fake live output claims.
- No clipping/overlap at common window sizes.

Report files changed, tests run, and current runtime setup behavior.
```

## Acceptance Checklist

- [ ] Mapping page implemented.
- [ ] Runtime setup card added.
- [ ] vJoy missing status visible.
- [ ] Simulation mode works.
- [ ] Recovered mappings present.
- [ ] Tables present.
- [ ] No fake full-live claim.

---

# Phase 6 — Modes, Base Tuning, Filtering, Combat Profile, and Profiles Pages

## Goal

Build the core tuning pages and profile library using the shared models and pyqtgraph.

This phase brings back the main tuning surface.

## Required Pages

### Modes

Sections:

- Precision Mode
- Combat Mode
- Live Mode State
- Mode Notes

Recovered values:

- Precision button: `0`
- Zoom button: `5`
- Stack Mode: `multiply`

### Base Tuning

Sections:

- Mapped Axes
- Parameters
- Response Preview
- Live Snapshot
- Guidance

Parameters:

- Curve Mode
- Curve Strength
- Deadzone
- Anti-Deadzone
- Hysteresis
- Output Scale
- Max Output

Important bug prevention:

- Linear reference line must be true `y=x`, never transformed by curve math.

### Filtering

Parameters:

- Center Alpha
- Edge Alpha
- Same Slew Limit
- Reverse Slew Limit

Graph:

- Step preview showing input vs filtered output.

### Combat Profile

Parameters:

- Combat Curve
- Combat Scale
- Combat Center Alpha
- Combat Edge Alpha
- Combat Same Slew
- Combat Reverse Slew

### Profiles

Built-in presets:

- Balanced Flight
- Precision Tracking
- Aggressive Combat
- Smooth Cinematic

Personal profile:

- Current Workspace

Actions:

- Save Current As New
- Import JSON
- Duplicate
- Export JSON
- Use This Profile
- Rename
- Delete

## Codex Prompt

```text
Implement the Modes, Base Tuning, Filtering, Combat Profile, and Profiles pages for HOTAS Control Panel V2.

Use the shared workspace/domain models and pyqtgraph.

General requirements:
- Use the premium V2 dark theme.
- Use rounded cards and disciplined spacing.
- Use scroll areas where needed.
- Use simulation runtime values for live snapshots when real hardware is missing.
- Changes update the current workspace/draft immediately but only persist when Save Workspace is pressed.
- Keep pages responsive and avoid full-page graph redraw jank.

Implement Modes page:
1. Title: `Modes`.
2. Copy: `Configure precision and combat activation without diving into raw tuning values.`
3. Cards:
   - Precision Mode
   - Combat Mode
   - Live Mode State
   - Mode Notes
4. Fields:
   - Precision Hold Buttons, default `0`
   - Combat Trigger Buttons
   - Combat Zoom/Aim Buttons, default `5`
   - Combat Extra Buttons
   - Stack Mode, default `multiply`
5. Live Mode State should show Precision/Combat/Trigger/Zoom/Extra/Stack states from runtime or simulation.

Implement Base Tuning page:
1. Title: `Base Tuning`.
2. Copy: `Shape the underlying axis response before mode-specific modifiers get involved.`
3. Mapped Axes list: Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2.
4. Parameters:
   - Curve Mode
   - Curve Strength
   - Deadzone
   - Anti-Deadzone
   - Hysteresis
   - Output Scale
   - Max Output
5. Response Preview graph using pyqtgraph.
6. Linear reference line must be true `y=x` and tested.
7. Adjusted curve line should reflect selected axis settings.
8. Add Live Snapshot and Guidance cards.

Implement Filtering page:
1. Title: `Filtering`.
2. Copy: `Control damping and slew behavior without rebuilding the whole response curve.`
3. Parameters:
   - Center Alpha
   - Edge Alpha
   - Same Slew Limit
   - Reverse Slew Limit
4. Step preview graph showing input vs filtered output.
5. Add Live Snapshot and Guidance cards.

Implement Combat Profile page:
1. Title: `Combat Profile`.
2. Copy: `Tune the more constrained combat/zoom layer without disturbing the baseline response.`
3. Parameters:
   - Combat Curve
   - Combat Scale
   - Combat Center Alpha
   - Combat Edge Alpha
   - Combat Same Slew
   - Combat Reverse Slew
4. Combat response graph.
5. Guidance should support normal/caution/extreme states.

Implement Profiles page:
1. Title: `Profiles`.
2. Copy: `Keep built-in presets and personal profiles in one library. The selected profile becomes the live workspace for the rest of V2.`
3. Built-In Presets:
   - Balanced Flight
   - Precision Tracking
   - Aggressive Combat
   - Smooth Cinematic
4. Personal Profiles:
   - Current Workspace
5. Buttons:
   - Save Current As New
   - Import JSON
   - Duplicate
   - Export JSON
   - Use This Profile
   - Rename
   - Delete
6. Profile Detail, Setup Summary, Profile Feel, Profile Actions cards.

Tests/smoke checks:
- each page constructs,
- axis selection updates graph,
- Base Tuning linear reference is true y=x,
- editing a value marks workspace unsaved,
- Revert restores prior saved/draft state,
- simulation runtime values appear in live snapshots.

Acceptance criteria:
- Pages visually match recovered V2 direction.
- Graphs work with pyqtgraph.
- No missing scrollbars or clipped content.
- Workspace dirty/saved state works.
- Tests pass.

Report files changed, tests run, screenshots if possible, and any deviations.
```

## Acceptance Checklist

- [ ] Modes implemented.
- [ ] Base Tuning implemented.
- [ ] Filtering implemented.
- [ ] Combat Profile implemented.
- [ ] Profiles implemented.
- [ ] pyqtgraph previews work.
- [ ] Linear reference bug prevented.
- [ ] Workspace dirty state works.

---

# Phase 7 — Conditional Rules System

## Goal

Build the Conditional Rules page and underlying rule model/evaluation layer.

This is the advanced logic cabinet. Open carefully. Wear gloves. Maybe bring snacks.

## Recovered Rule Example

Rule title:

- `Yaw 0.75 | Roll > 0.35`

Meaning:

- Set Yaw Output Scale to 0.75 when absolute Roll final output is greater than 0.35.

Fields:

- Target Axis: Yaw
- Parameter: Output Scale
- Operation: Set
- Value: 0.75
- Injects At: Base Output Limits
- Mode Gate: Always
- Reference Axis: Roll
- Stage: Final Output
- Comparator: greater than
- Threshold: 0.35
- Status: Disabled in recovered screenshots

Status chips:

- `1 rules`
- `0 active`
- `0 blocked`
- `1 disabled`

Actions:

- Add Rule
- Edit Selected
- Duplicate
- Enable
- Delete

## Codex Prompt

```text
Implement the Conditional Rules system for HOTAS Control Panel V2.

Use the recovered Conditional Rules spec as governing reference.

Requirements:

1. Implement rule evaluation in shared_core.
   A rule must support:
   - enabled/disabled
   - target axis
   - target parameter
   - operation, including Set
   - value
   - injection stage
   - mode gate
   - button gate/buttons
   - button test
   - reference axis
   - reference stage
   - measure, including absolute value
   - comparator
   - threshold
   - threshold high for future range/band support

2. Implement runtime rule statuses:
   - Disabled
   - Inactive
   - Active
   - Blocked
   - optionally Armed/Eligible if useful.

3. Implement the recovered example rule by default or as sample data:
   - Title: `Yaw 0.75 | Roll > 0.35`
   - Target: Yaw
   - Parameter: Output Scale
   - Operation: Set
   - Value: 0.75
   - Injects At: Base Output Limits
   - Mode Gate: Always
   - Reference Axis: Roll
   - Stage: Final Output
   - Measure: absolute
   - Comparator: greater than
   - Threshold: 0.35
   - Initial status: Disabled

4. Implement Conditional Rules page UI.
   Title: `Conditional Rules`.
   Copy: `Build responsive modifier rules, track their live state, and see exactly where they inject into the response stack.`

5. Add status chips:
   - rules count
   - active count
   - blocked count
   - disabled count

6. Add action buttons:
   - Add Rule
   - Edit Selected
   - Duplicate
   - Enable
   - Delete

7. Layout:
   - Rule List on left.
   - Rule Detail on right.
   - Rule Logic explanatory card.

8. Rule Detail should show:
   - title,
   - status badge,
   - target axis,
   - parameter,
   - operation,
   - value,
   - injects at,
   - mode gate,
   - reference condition,
   - plain-English preview sentence.

9. Editor behavior:
   If full editing is too large for this phase, implement safe basic edit dialog for the recovered fields and mark any advanced fields as future work in UI copy only if necessary.
   Do not leave the page looking placeholder-only.

10. Integrate with signal pipeline:
   - Rule injections must be available to the Effective Response Stack.
   - Rule evaluation should use current runtime/simulated stage values.

11. Tests:
   - disabled rule does not apply,
   - enabled rule applies when condition true,
   - enabled rule inactive when condition false,
   - rule status counts are correct,
   - example rule serializes/deserializes,
   - stack can receive rule injection metadata.

Acceptance criteria:
- Conditional Rules page is usable and product-like.
- Example rule appears correctly.
- Rule statuses work in simulation.
- Rule injections can be shown later in Effective Response Stack.
- Tests pass.

Report files changed, tests run, and any rule-schema decisions.
```

## Acceptance Checklist

- [ ] Rule model complete enough.
- [ ] Example rule represented.
- [ ] Rule page implemented.
- [ ] Status chips implemented.
- [ ] Basic rule evaluation tested.
- [ ] Pipeline can receive injections.

---

# Phase 8 — Effective Response Stack

## Goal

Rebuild the crown-jewel diagnostic page showing one selected axis through the full processing pipeline.

This page must explain **why** an axis feels the way it does.

## Required Layout

Title:

- `Effective Response Stack`

Copy:

- `Inspect one selected axis at a time from raw HOTAS input through shaping, filtering, mode modifiers, rule injections, and final output.`

Controls:

- Axis selector
- Live status
- Freeze / Resume
- Copy Snapshot optional
- Show All / Changed Only optional

Left:

- Signal Chain stage cards

Right:

- Raw vs Final graph
- Mode State
- Current Stack Summary
- Selected Stage
- Rule Driver Values

Stages:

1. Raw Input
2. Center Conditioning
3. Curve / Shape
4. Base Output Limits
5. Filtering
6. Mode Modifiers
7. Inline Rule Injections
8. Final Output

Each stage card:

- title
- status chip
- IN
- OUT
- DELTA
- input/output bars
- explanation line
- selected state

## Important Bug Prevention

Recovered issue:

- Signal Chain had a periodic twitch/micro-seizure.

Avoid by:

- reusing widgets,
- updating values in place,
- avoiding layout rebuilds on heartbeat,
- avoiding graph/container sync loops,
- supporting real freeze state.

## Codex Prompt

```text
Implement the Effective Response Stack page for HOTAS Control Panel V2.

This is a crown-jewel diagnostic page. It must show one selected axis at a time through the full live processing chain.

Requirements:

1. Page title: `Effective Response Stack`.
2. Page copy: `Inspect one selected axis at a time from raw HOTAS input through shaping, filtering, mode modifiers, rule injections, and final output.`
3. Controls:
   - Axis selector with Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2.
   - Live status pill.
   - Freeze / Resume.
   - Copy Snapshot if feasible.
4. Main layout:
   - Left Signal Chain panel.
   - Right Raw vs Final graph.
   - Lower/right cards: Mode State, Current Stack Summary, Selected Stage, Rule Driver Values.
5. Signal Chain stage cards:
   - Raw Input
   - Center Conditioning
   - Curve / Shape
   - Base Output Limits
   - Filtering
   - Mode Modifiers
   - Rule Injections, only when relevant or visible as inactive placeholder if useful
   - Final Output
6. Stage cards show:
   - IN
   - OUT
   - DELTA
   - input/output bars
   - live/active/inactive status badge
   - short explanation
   - selected state
7. Raw vs Final graph:
   - pyqtgraph.
   - Raw input on X.
   - Effective output on Y.
   - True reference line if shown.
   - Processed effective response line.
   - Live marker riding on effective response line.
   - Caption: `Raw input on X, effective output on Y.`
8. Rule injection handling:
   - Conditional rule effects must appear inline at the stage they affect.
   - External axis values used by rules go in Rule Driver Values, not as full extra stacks.
9. Freeze behavior:
   - Freeze captures and displays actual stage data at freeze time.
   - It must not merely pause repaint while underlying selected data changes.
10. Performance behavior:
   - Create stage widgets once and update values in place.
   - Do not rebuild stage cards every heartbeat.
   - Do not trigger layout churn every few seconds.
   - Avoid the recovered micro-seizure bug.
11. Tests/smoke checks:
   - stack page constructs,
   - selecting axis updates stack data,
   - freeze freezes actual displayed stage result,
   - stage card count remains stable across heartbeats,
   - rule injection metadata appears when rule applies,
   - no full widget rebuild on routine update if testable.

Acceptance criteria:
- Stack page is visually premium and stable.
- Stage values update from simulation runtime.
- Rule injections are represented.
- Freeze works truthfully.
- No periodic twitch from layout rebuild.
- Tests pass.

Report files changed, tests run, and any performance instrumentation added.
```

## Acceptance Checklist

- [ ] Effective Response Stack page implemented.
- [ ] Stage cards implemented.
- [ ] Raw vs Final graph implemented.
- [ ] Rule injections visible.
- [ ] Freeze works.
- [ ] No periodic twitch/layout churn.

---

# Phase 9 — Live Monitor Page

## Goal

Implement the Live Monitor page showing raw HOTAS input, final output, buttons, hats, axis levels, and live trace graphs.

This phase should work in simulation mode first, then later use real runtime.

## Required Content

Title:

- `Live Monitor`

Copy:

- `Watch raw HOTAS input, final vJoy output, buttons, hats, and axis levels in one dedicated live workspace.`

Monitor Controls:

- Axis dropdown
- Show raw and output together checkbox
- Live status

Graphs:

- `Raw Input Trace · Roll`
- `Raw vs Final Overlay · Roll`

Cards:

- Live State
- Buttons / Hats
- Axis Levels
- HOTAS Buttons B1-B15
- Mapped Output Buttons Out1-Out20

## Codex Prompt

```text
Implement the Live Monitor page for HOTAS Control Panel V2.

Requirements:

1. Page title: `Live Monitor`.
2. Page copy: `Watch raw HOTAS input, final vJoy output, buttons, hats, and axis levels in one dedicated live workspace.`
3. Monitor Controls card:
   - Axis dropdown, default Roll.
   - Checkbox: `Show raw and output together`.
   - Live/simulation/runtime status pill.
4. Graph 1:
   - Title: `Raw Input Trace · <Axis>`.
   - Copy: `Recent raw HOTAS input for the selected axis.`
   - Time-series pyqtgraph line.
   - Newest samples on right edge.
5. Graph 2:
   - Title: `Raw vs Final Overlay · <Axis>`.
   - Copy: `Recent processed output leaving the bridge for the selected axis.`
   - Overlay raw and final values.
   - Caption: `Raw and final output are overlaid for direct comparison.`
6. Live State card:
   - Precision state.
   - Combat state.
   - Trigger state.
   - Zoom state.
   - Extra state.
   - Active rules summary.
7. Buttons / Hats card:
   - HOTAS Hat state.
   - Output Hat state.
   - Explanation text.
8. Axis Levels card:
   - Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2.
   - Raw and final bars.
   - Raw blue / final green concept.
   - +1.0 to -1.0 scale.
9. HOTAS Buttons:
   - B1 through B15.
10. Mapped Output Buttons:
   - Out 1 through Out 20.
11. Use simulation runtime if real hardware/vJoy is missing.
12. Runtime truth must be visible. If simulated, do not label it as real live hardware.
13. Hidden-page behavior:
   - When Live Monitor is not visible, throttle or stop expensive graph updates.
14. Tests/smoke checks:
   - page constructs,
   - axis selector updates graph titles,
   - simulation runtime populates axes/buttons/hats,
   - hidden-page update throttling recorded in diagnostics if available.

Acceptance criteria:
- Live Monitor visually matches recovered V2 behavior.
- Works without hardware using simulation.
- Clearly distinguishes simulated vs live runtime.
- Graph updates are smooth and scoped.
- No overlap/clipping.

Report files changed, tests run, and current runtime truth shown in UI.
```

## Acceptance Checklist

- [ ] Live Monitor implemented.
- [ ] Raw Input Trace implemented.
- [ ] Raw vs Final Overlay implemented.
- [ ] Axis Levels implemented.
- [ ] Buttons/hats displayed.
- [ ] Simulation runtime drives UI.
- [ ] Runtime truth visible.

---

# Phase 10 — Helm Assistant Overlay

## Goal

Implement Helm as the built-in diagnostic assistant.

Helm must be launched from the top-right assistant cluster, not as a normal sidebar page.

## Rebuild Decision For Ambiguity

Recovered notes include both:

- large right-side slide-out workspace around 70% width,
- final modal/overlay behavior with dimmed/de-emphasized background.

Rebuild decision:

> Implement Helm as a large overlay launched from the top-right `ASSISTANT` cluster. It may visually slide in from the right and occupy roughly 70% width, but it behaves as an overlay assistant, not a normal navigation tab.

## Required Helm UI

Top:

- `Helm`
- `Diagnosis-first tuning guidance for the current workspace.`
- green pulse indicator
- `Helm is active`
- `Context-linked assistant`
- close button
- safety pill: `In-memory only`

Cards:

- `What’s wrong?`
- `What I’d change`
- `What I found`
- `Apply / Revert`

Text box placeholder:

- `Example: Can't hold aim steady on target.`

Symptom chips:

- Can’t hold aim steady
- Too twitchy near center
- Overshoots target
- Combat mode feels sluggish
- Reversals feel sticky
- Hard to track smoothly

Actions:

- Analyze
- Review Changes
- Cancel
- Apply Selected Changes
- Revert Last Helm Changes

## Behavior

Helm must:

- inspect workspace/tuning/modes/rules/stack data,
- propose exact before/after diffs,
- allow selected changes,
- apply only to in-memory workspace/draft,
- never auto-save,
- allow revert last Helm changes,
- use first-person voice,
- avoid cold third-person phrases.

V1 should **not** automatically edit/create/disable conditional rules.

## Codex Prompt

```text
Implement the Helm assistant overlay for HOTAS Control Panel V2.

Helm is a built-in tuning/diagnostic assistant. It is not a normal sidebar page.

Requirements:

1. Add top-right ASSISTANT cluster button `Helm` if not already wired.
2. Clicking Helm opens a large overlay assistant.
3. Overlay behavior:
   - Background app dimmed/de-emphasized.
   - Optional blur if practical without jank.
   - Overlay visually slides in from right or appears as large modal.
   - Width around 70% of main app if using slide-in layout.
   - Close button.
4. Header:
   - Title: `Helm`.
   - Subtitle: `Diagnosis-first tuning guidance for the current workspace.`
   - Green pulse indicator.
   - `Helm is active`.
   - `Context-linked assistant`.
   - Safety pill: `In-memory only`.
5. Main sections/cards:
   - `What’s wrong?`
   - `What I’d change`
   - `What I found`
   - `Apply / Revert`
6. Input area:
   - Text box placeholder: `Example: Can't hold aim steady on target.`
   - Symptom chips:
     - Can’t hold aim steady
     - Too twitchy near center
     - Overshoots target
     - Combat mode feels sluggish
     - Reversals feel sticky
     - Hard to track smoothly
7. Action buttons:
   - Analyze
   - Review Changes
   - Cancel
   - Apply Selected Changes
   - Revert Last Helm Changes
8. Tone:
   - First person.
   - Confident.
   - Concise.
   - Calm.
   - Premium.
   - Helpful.
   - Not robotic.
   - Not a raw machine diff dump.
   Avoid phrasing like `Helm will now...`.
9. Build Helm engine scaffolding:
   - symptom parser/matcher,
   - recommendation library,
   - diff model,
   - confidence/status model,
   - current context extraction from workspace/stack/rules/modes.
10. Implement at least one real symptom path:
    `Combat mode feels sluggish`.
    It should produce recovered example-style diffs such as:
    - Yaw Combat Center Alpha 0.52 -> 0.68
    - Pitch Combat Center Alpha 0.56 -> 0.68
    - Yaw Combat Reverse Slew 0.06 -> 0.09
    - Yaw Combat Same Slew 0.06 -> 0.09
    - Yaw Combat Scale 0.68 -> 0.79
    Use actual current workspace values if different, but keep the same spirit.
11. Apply selected changes only to current workspace/draft.
12. Do not save permanently.
13. Implement Revert Last Helm Changes.
14. Helm v1 must not automatically edit/create/disable conditional rules.
    It may mention if a rule appears relevant.
15. Tests:
    - Helm overlay opens/closes.
    - symptom chip fills or triggers analysis.
    - sluggish combat symptom produces diffs.
    - applying diffs changes workspace dirty state.
    - revert restores prior values.
    - no auto-save occurs.

Acceptance criteria:
- Helm overlay matches recovered final direction.
- Helm uses first-person polished text.
- Diffs are exact before/after values.
- Apply/revert works safely.
- No rule auto-editing in v1.
- Tests pass.

Report files changed, tests run, screenshots if possible, and any UX deviations.
```

## Acceptance Checklist

- [ ] Helm launches from top-right.
- [ ] Helm is overlay, not sidebar tab.
- [ ] Green active status exists.
- [ ] Symptom chips exist.
- [ ] At least one symptom path works.
- [ ] Apply selected changes works.
- [ ] Revert last Helm changes works.
- [ ] No auto-save.

---

# Phase 11 — Help / Docs and Perf / Diagnostics

## Goal

Implement built-in documentation and performance diagnostics.

The recovered app had both, and they are critical for making the software feel shippable and debuggable.

## Help / Docs Requirements

Title:

- `Help / Docs`

Copy:

- `Search the built-in guide, browse by category, and keep the details you use most close at hand.`

Controls:

- Search field placeholder: `Search features, pages, or tuning terms`
- Sort dropdown: `By Category`

Topics:

- Advanced Pages
  - Conditional Rules
  - Effective Response Stack
  - Helm
- Analysis
  - Graphs and Previews
  - Runtime Indicators
- Core Pages
  - Base Tuning
  - Combat Profile
  - Filtering
  - Modes
  - Profiles
- Diagnostics
  - Performance / Diagnostics
- Getting Started
  - Quick Start
  - Runtime Setup / vJoy Setup
- Reference
  - Tuning Glossary
- Workflow
  - Saving and Importing

Add a new important topic:

- `Runtime Setup / vJoy Setup`

This topic must explain:

- simulation mode,
- physical HOTAS detection,
- output/vJoy detection,
- missing driver/device states,
- why full live output requires vJoy/output backend,
- how to run preflight.

Do not include brittle external links unless intentionally maintained later.

## Perf / Diagnostics Requirements

Show:

- active page,
- runtime state,
- selected axis,
- source file,
- hidden page skips,
- runtime preflight status,
- input device status,
- output/vJoy status,
- page build/switch times,
- heartbeat timing,
- graph draw timings,
- startup timings,
- simulation vs live truth label.

## Codex Prompt

```text
Implement Help / Docs and Perf / Diagnostics pages for HOTAS Control Panel V2.

Requirements for Help / Docs:

1. Page title: `Help / Docs`.
2. Copy: `Search the built-in guide, browse by category, and keep the details you use most close at hand.`
3. Add search field placeholder: `Search features, pages, or tuning terms`.
4. Add sort dropdown: `By Category`.
5. Add topics tree with categories:
   - Advanced Pages
     - Conditional Rules
     - Effective Response Stack
     - Helm
   - Analysis
     - Graphs and Previews
     - Runtime Indicators
   - Core Pages
     - Base Tuning
     - Combat Profile
     - Filtering
     - Modes
     - Profiles
   - Diagnostics
     - Performance / Diagnostics
   - Getting Started
     - Quick Start
     - Runtime Setup / vJoy Setup
   - Reference
     - Tuning Glossary
   - Workflow
     - Saving and Importing
6. Add guide pane with real product documentation text.
7. Add Runtime Setup / vJoy Setup article explaining:
   - simulation mode works without hardware,
   - physical HOTAS input detection,
   - vJoy/output backend detection,
   - full live runtime requires both input and output paths,
   - missing driver/device statuses,
   - Run Preflight Check,
   - no fake live output claims.

Requirements for Perf / Diagnostics:

1. Page title: `Perf / Diagnostics`.
2. Show diagnostic fields:
   - active page,
   - runtime mode/truth,
   - input device status,
   - output/vJoy status,
   - selected axis,
   - source file,
   - hidden page skips,
   - runtime path checks,
   - page build/switch timings,
   - heartbeat average/max,
   - graph draw average/max,
   - startup total/config/widget timing if available.
3. Add controls:
   - Collect live timings toggle if useful.
   - Clear timings.
   - Run Runtime Preflight.
4. Ensure hidden pages skip expensive updates and diagnostics reflect that.
5. Tests/smoke checks:
   - Help page constructs and contains topics.
   - Runtime Setup article exists.
   - Perf page constructs and receives diagnostic values.
   - Runtime preflight action updates status.

Acceptance criteria:
- Help / Docs feels like integrated product documentation.
- Runtime/vJoy setup is clearly documented.
- Perf page makes runtime and performance claims verifiable.
- Tests pass.

Report files changed, tests run, and sample diagnostic output.
```

## Acceptance Checklist

- [ ] Help / Docs implemented.
- [ ] Runtime/vJoy setup article added.
- [ ] Perf / Diagnostics implemented.
- [ ] Runtime truth shown in diagnostics.
- [ ] Hidden-page skips tracked.

---

# Phase 12 — Live Overlay Foundation

## Goal

Implement the shared telemetry/overlay engine and detached Live Overlay window.

Do this before Flight Recorder export/compositing so live overlay can prove the shared overlay core.

## Recovered Live Overlay Details

Live Overlay belongs in Live Monitor.

Main card:

- `Live Overlay`
- `Hide Overlay`
- `Configure`
- Preset: `Custom`
- Status: `Active`
- `Attached to NE160QDM-NYJ (2048x1280)`
- `Toggle: Ctrl+Shift+F9`
- `Custom | Bottom strip | 66% opacity | Final output`

Overlay config:

- Position: Bottom strip
- Margin: 18 px
- Attach: Attach to display
- Width: Standard
- Height: 0.60
- Display: NE160QDM-NYJ (2048x1280)
- Opacity: 0.66
- Background: 0.82
- Line thickness: 2.80
- FPS cap: 60 fps
- Toggle hotkey: Ctrl+Shift+F9
- Source: Final output
- History: 7.50 s

Axis colors:

- Roll #58B8FF
- Pitch #6FDB9F
- Throttle #F0C46A
- Yaw #CF95FF
- Aux 1 #FF9B6B
- Aux 2 #6ED9D0

## Codex Prompt

```text
Implement the Live Overlay foundation for HOTAS Control Panel V2.

Context:
The recovered app had a detached live telemetry strip rendered over the desktop/gameplay. It belonged in Live Monitor, not Flight Recorder. Advanced settings lived behind Configure. The overlay must use shared telemetry/overlay core that Flight Recorder can reuse later.

Requirements:

1. Create overlay core modules:
   - telemetry history ring buffer,
   - overlay config/style model,
   - trace builder / layout logic,
   - shared axis color model,
   - renderer abstraction usable by live overlay and later recorder compositor.

2. Default axis colors:
   - Roll #58B8FF
   - Pitch #6FDB9F
   - Throttle #F0C46A
   - Yaw #CF95FF
   - Aux 1 #FF9B6B
   - Aux 2 #6ED9D0

3. Add Live Overlay card to Live Monitor page.
   It should show:
   - title `Live Overlay`,
   - description `Launch the detached telemetry strip, choose a preset, and adjust advanced behavior only when needed.`,
   - buttons `Show Overlay` / `Hide Overlay`,
   - button `Configure`,
   - preset `Custom`,
   - status `Active` when visible,
   - attached display text,
   - toggle hint `Toggle: Ctrl+Shift+F9`,
   - summary `Custom | Bottom strip | 66% opacity | Final output`.

4. Implement Live Overlay Configuration dialog.
   Title: `Live Overlay Configuration - HOTAS Control Panel V2`.
   Intro text: `Fine-tune placement, appearance, and data behavior for the detached live telemetry overlay. Axis colors are shared with Flight Recorder so replays and live telemetry stay consistent.`

5. Configuration sections:
   Placement:
   - Position: Bottom strip
   - Margin: 18 px
   - Attach: Attach to display
   - Width: Standard
   - Height: 0.60
   - Display selector

   Appearance:
   - Opacity: 0.66
   - Background: 0.82
   - Line thickness: 2.80
   - Show legend
   - Show live values

   Behavior:
   - Auto-hide when target loses focus
   - Always on top
   - Click-through
   - FPS cap: 60 fps
   - Toggle hotkey: Ctrl+Shift+F9

   Data:
   - Source: Final output
   - History: 7.50 s

   Axes:
   - Axis / Include / Color table

   Buttons:
   - Restore Defaults
   - OK
   - Cancel

6. Implement detached overlay window.
   Requirements:
   - separate top-level window,
   - frameless/borderless,
   - transparent or semi-transparent background,
   - always-on-top when configured,
   - click-through when configured if supported safely,
   - bottom-strip default,
   - driven by simulation runtime if no hardware is installed,
   - no graphics API hooking,
   - no game injection.

7. Global hotkey:
   - Implement toggle hotkey if feasible.
   - If global hotkey is not safely implemented yet, include clear status `Hotkey not registered` and keep button toggle working.
   - Do not fake hotkey registration.

8. Tests/smoke checks:
   - overlay config defaults serialize/deserialize,
   - axis colors shared,
   - trace buffer stores history,
   - Live Overlay card reflects active/inactive state,
   - overlay can show/hide without crashing,
   - missing click-through support reports warning rather than fake success.

Acceptance criteria:
- Live Overlay can show simulated telemetry.
- Configure dialog matches recovered settings.
- Overlay is external/detached.
- Runtime truth remains visible.
- No game injection/hooking.
- Tests pass.

Report files changed, tests run, supported/unsupported overlay platform features, and any limitations.
```

## Acceptance Checklist

- [ ] Shared overlay core created.
- [ ] Live Overlay card added.
- [ ] Configure dialog implemented.
- [ ] Detached overlay shows.
- [ ] Simulated telemetry displayed.
- [ ] Hotkey status truthful.
- [ ] Click-through status truthful.

---

# Phase 13 — Flight Recorder, Clip Library, and Hindsight Buffer

## Goal

Implement the Flight Recorder page, forward capture mode, buffered/hindsight mode, clip library, clip preview, and shared overlay export path.

This may be a large phase. If needed, split into:

- 13A — UI and state model
- 13B — capture backend
- 13C — overlay compositor
- 13D — clip preview/library

## Recovered Flight Recorder Details

Title:

- `Flight Recorder`

Description:

- `Capture the desktop on demand, then composite a time-matched axis trace overlay into the finished video.`
- `Use the hotkey when you want a clean replay of what happened on-screen with the matched HOTAS signal history baked into the clip.`

Status chips:

- Ready
- Hotkey armed
- Final output
- Buffering
- Clip hotkey armed
- Recording

Buttons:

- Record Now
- Save Last Clip

Settings:

- Destination
- Browse
- Open Folder
- Length: 20 s
- Frame Rate: 30 fps
- History: 6.00 s
- Overlay Source: Final output
- Capture Source: Current display
- Display: NE160QDM-NYJ (2048x1280)
- Hotkey: Ctrl+Shift+F10
- Record the cursor
- Trigger Mode: Press to save previous interval

Cards:

- Recorder Settings
- Axis Overlay
- Recording Library
- Clip Preview

## Codex Prompt

```text
Implement the Flight Recorder system for HOTAS Control Panel V2.

Context:
Recovered screenshots show a polished Flight Recorder page that captures the desktop and composites time-matched HOTAS telemetry traces into the finished video. It supports forward capture and hindsight/buffered capture.

Important:
If full video capture/encoding is too large for one pass, split implementation into safe substeps, but do not fake completed recording. Use truthful states like Recording Backend Missing, Capture Ready, Clip Saved, or Preview Unavailable.

Requirements:

1. Implement Flight Recorder page.
   Title: `Flight Recorder`.
   Description:
   - `Capture the desktop on demand, then composite a time-matched axis trace overlay into the finished video.`
   - `Use the hotkey when you want a clean replay of what happened on-screen with the matched HOTAS signal history baked into the clip.`

2. Status chips:
   - Ready
   - Hotkey armed
   - Final output
   - Buffering
   - Clip hotkey armed
   - Recording
   Use only truthful statuses.

3. Buttons:
   - `Record Now` for forward capture.
   - `Save Last Clip` for buffered/hindsight mode.

4. Recorder Settings card fields:
   - Destination, default folder ending in `hotas_recordings_v2`.
   - Browse.
   - Open Folder.
   - Length: 20 s.
   - Frame Rate: 30 fps.
   - History: 6.00 s.
   - Overlay Source: Final output.
   - Capture Source: Current display.
   - Display selector.
   - Hotkey: Ctrl+Shift+F10.
   - Record the cursor.
   - Trigger Mode, including `Press to save previous interval`.

5. Axis Overlay card:
   - Axis / Include / Color table.
   - Use shared axis colors from Live Overlay.
   - Axis colors must stay consistent between live overlay and exported clips.

6. Recording Library card:
   - Sort dropdown, default Newest First.
   - Refresh button.
   - Table columns:
     - Clip
     - Recorded
     - Duration
     - Opened

7. Clip Preview card:
   - video/frame preview area,
   - play button,
   - timeline/scrubber,
   - time indicator,
   - Reveal File button,
   - metadata line including filename, overlay source, resolution, length.

8. Implement recorder state model:
   - idle/ready,
   - recording forward clip,
   - buffering/hindsight active,
   - saving last clip,
   - encoding/compositing,
   - saved,
   - error.

9. Implement capture backend abstraction.
   - If actual desktop capture is not implemented yet, create backend interface and a simulation/test backend that writes a placeholder test clip/artifact clearly labeled as simulated.
   - Do not claim real desktop capture until a real backend captures frames.

10. Implement overlay compositor abstraction.
   - Reuse the Live Overlay trace builder/renderer.
   - Export/bake telemetry overlay into output clip when backend supports it.
   - If compositor not complete, status must say compositor unavailable.

11. Implement hindsight buffer model.
   - Continuously buffer telemetry and capture frames where possible.
   - Pressing trigger saves last configured interval.
   - If video frame buffering not implemented yet, telemetry buffer should still be testable separately.

12. Hotkey:
   - Ctrl+Shift+F10 recovered recorder hotkey.
   - Register only if safely implemented.
   - Otherwise show truthful `Hotkey not registered` status.

13. Tests:
   - recorder settings default correctly,
   - axis overlay colors match Live Overlay colors,
   - clip library indexes sample clips,
   - hindsight telemetry buffer returns previous interval,
   - recorder state transitions are valid,
   - fake/simulated backend cannot be mislabeled as real capture,
   - missing capture backend produces useful UI status.

Acceptance criteria:
- Flight Recorder page matches recovered UI structure.
- Forward and hindsight modes exist at state/model level.
- Clip library and preview shell exist.
- Overlay color sharing works.
- Recording status is truthful.
- Tests pass.

Report files changed, tests run, what is real vs simulated, and next steps for full capture/encoding if incomplete.
```

## Acceptance Checklist

- [ ] Flight Recorder page implemented.
- [ ] Recorder settings present.
- [ ] Axis Overlay present.
- [ ] Recording Library present.
- [ ] Clip Preview present.
- [ ] Forward capture model exists.
- [ ] Hindsight buffer model exists.
- [ ] Real vs simulated recording status truthful.

---

# Phase 14 — Real HOTAS Input Integration

## Goal

Add real physical HOTAS input detection and reading.

This phase should happen only after simulation mode and UI are stable.

## Important Rule

Do not remove simulation mode. Simulation mode is essential for testing, development, and running the app without hardware.

## Codex Prompt

```text
Implement real physical HOTAS input integration for HOTAS Control Panel V2.

Context:
The user uses a Thrustmaster Flight/T.Flight HOTAS One, but the app should be written generically enough to support similar joystick/throttle devices.

Requirements:

1. Keep simulation runtime intact.
2. Add physical input backend in `shared_core/runtime/hotas_input.py` or adapter module.
3. Device enumeration:
   - detect connected joystick/HOTAS-like devices,
   - expose device name/vendor/product info when available,
   - list axes/buttons/hats available,
   - do not crash if no devices are connected.
4. Device selection:
   - support choosing detected HOTAS device,
   - persist selected device identity if practical,
   - gracefully handle missing previously selected device.
5. Input sampling:
   - read raw axis values,
   - normalize to -1.0 to +1.0 where appropriate,
   - read buttons B1-B15 or available count,
   - read hat state.
6. Mapping integration:
   - feed raw values into mapping model,
   - feed mapped logical values into tuning pipeline,
   - feed final values into Live Monitor and Effective Response Stack.
7. Runtime status:
   - update input status to DETECTED only when a device is actually detected,
   - update runtime mode according to output/vJoy availability.
8. UI integration:
   - Runtime Setup / Preflight card shows detected device.
   - Live Monitor shows real raw values when physical runtime is selected.
   - If output/vJoy is missing, clearly show that output is not live/verified.
9. Tests:
   - use mock input backend for deterministic tests,
   - no-device case is safe,
   - mock device values flow through mapping and stack,
   - physical backend import does not crash if dependencies are missing.

Acceptance criteria:
- App still runs with no HOTAS.
- App can detect/use HOTAS when available.
- Simulation mode still works.
- Live Monitor can show real input when backend is available.
- Runtime truth remains accurate.

Report files changed, dependencies introduced, tests run, and whether real hardware was available during verification.
```

## Acceptance Checklist

- [ ] Real input backend added.
- [ ] No-device case safe.
- [ ] Device detection status truthful.
- [ ] Live Monitor can consume real input.
- [ ] Simulation remains available.

---

# Phase 15 — vJoy / Virtual Output Integration

## Goal

Add actual vJoy or virtual joystick output support.

This phase should happen after real/simulated input and the tuning pipeline are stable.

## Important Rule

Do not require vJoy to be installed for the app to launch.

If vJoy is missing:

- show setup guidance,
- allow simulation mode,
- allow UI editing,
- block live output writes truthfully.

## Output Verification

A runtime state may only say `Output Verified` if:

- output backend is detected,
- target virtual device is available,
- at least one safe write/test succeeds,
- errors are captured and displayed.

## Codex Prompt

```text
Implement vJoy / virtual joystick output integration for HOTAS Control Panel V2.

Context:
The recovered app maps HOTAS input to final vJoy outputs. The user currently does not have vJoy installed, so this integration must be optional and truth-labeled.

Requirements:

1. Keep app launch independent from vJoy installation.
2. Implement output backend adapter in `shared_core/runtime/vjoy_output.py`.
3. If vJoy library/driver is missing:
   - imports must not crash,
   - output status must be VJOY_MISSING or equivalent,
   - UI must show setup guidance,
   - simulation mode remains usable.
4. If vJoy is installed:
   - detect available virtual device(s),
   - expose device ID/name/status,
   - verify output device can receive writes if safe.
5. Implement output mapping:
   - final Roll -> runtime X(axis1),
   - final Pitch -> runtime Y(axis2),
   - final Throttle -> runtime Z(axis3),
   - final Yaw -> runtime RX(axis4),
   - final Aux 1 -> runtime RY(axis5),
   - final Aux 2 -> runtime RZ(axis6),
   while preserving the recovered Battlefield-safe routing note around RX/RY/RZ/SL0 remapping.
6. Implement button output mapping.
7. Implement hat/POV output mapping where backend supports it.
8. Add runtime write loop carefully:
   - no blocking UI thread,
   - rate-limited/scheduled,
   - error handling,
   - safe stop on app exit.
9. Add UI status:
   - Output Missing,
   - vJoy Detected,
   - Output Verified,
   - Output Error.
10. Add a safe test output feature only if appropriate:
   - `Test Output` action in Runtime Setup card or diagnostics,
   - must warn user before moving live output if needed,
   - must clearly report success/failure.
11. Tests:
   - mock vJoy backend receives final axis values,
   - missing vJoy backend does not crash,
   - output status transitions are correct,
   - write failures report Output Error,
   - no status claims verified without mock/real write success.

Acceptance criteria:
- App still runs without vJoy.
- vJoy missing state is clear.
- Mock output backend tests pass.
- Real vJoy output works only when detected and verified.
- Runtime truth remains accurate.

Report files changed, dependencies, tests run, and whether real vJoy was available during verification.
```

## Acceptance Checklist

- [ ] vJoy adapter optional.
- [ ] Missing vJoy safe.
- [ ] Output mappings implemented.
- [ ] Mock output tests pass.
- [ ] Output verified only after real/mock write success.

---

# Phase 16 — Runtime End-to-End Live Mode

## Goal

Connect physical input, tuning pipeline, modes, conditional rules, Effective Response Stack, Live Monitor, and vJoy output into one full runtime loop.

This is where the cockpit gets the wires plugged in and stops being a very expensive screensaver.

## Codex Prompt

```text
Implement the end-to-end live runtime loop for HOTAS Control Panel V2.

Prerequisites:
- Simulation runtime exists.
- Real HOTAS input adapter exists or is safely optional.
- vJoy/output adapter exists or is safely optional.
- Tuning pipeline exists.
- Mapping/modes/rules/stack models exist.

Requirements:

1. Runtime service:
   - reads raw input from selected backend,
   - applies mapping,
   - applies base tuning,
   - applies filtering,
   - applies modes/combat modifiers,
   - applies conditional rule injections,
   - produces final output,
   - writes to vJoy/output backend if available and enabled,
   - publishes telemetry snapshots to UI.
2. Threading/scheduling:
   - do not block UI thread,
   - use a safe timer/thread model,
   - rate-limit runtime loop appropriately,
   - expose heartbeat metrics.
3. Runtime modes:
   - Simulation only,
   - Input only,
   - Output only/testing,
   - Full live verified.
4. Live Monitor:
   - uses runtime snapshots.
5. Effective Response Stack:
   - uses stage-by-stage runtime results.
6. Conditional Rules:
   - statuses update from runtime values.
7. Mapping page:
   - Live Raw and Live Output update.
8. Header/sidebar/footer:
   - runtime truth updates globally.
9. Perf / Diagnostics:
   - runtime loop timing,
   - input sample timing,
   - output write timing,
   - dropped/error counts,
   - hidden-page skips.
10. Safety:
   - if output errors occur, stop or degrade safely,
   - do not continue writing bad output silently,
   - show Output Error.
11. Tests:
   - end-to-end mock runtime maps raw input to final output,
   - conditional rule can alter final output,
   - vJoy mock receives expected output,
   - missing vJoy leaves final output visible but not written,
   - UI snapshot model receives data.

Acceptance criteria:
- Simulation end-to-end works.
- Mock live output end-to-end works.
- Real live mode can be tested when hardware/drivers exist.
- Runtime truth is globally visible.
- No UI blocking.
- Tests pass.

Report files changed, tests run, timing metrics, and current verified runtime level.
```

## Acceptance Checklist

- [ ] Runtime service implemented.
- [ ] End-to-end simulation works.
- [ ] Mock output works.
- [ ] Conditional rules affect output.
- [ ] UI receives snapshots.
- [ ] Perf diagnostics include runtime metrics.

---

# Phase 17 — Product Polish, Layout QA, and Motion

## Goal

Make the app feel finished, smooth, and premium.

This is where we hunt clipping, overlap, muddy text strips, confusing chips, janky transitions, and any UI goblin with a tiny wrench.

## Codex Prompt

```text
Perform a product polish and layout QA pass for HOTAS Control Panel V2.

Use the recovered Product Vision and Visual Design System document as governing reference.

Requirements:

1. Visual polish:
   - dark premium engineering theme,
   - consistent rounded corners,
   - clean card hierarchy,
   - disciplined spacing,
   - no muddy dark strips behind every text field,
   - status chips visually distinct from buttons,
   - action buttons visibly clickable.
2. Layout QA:
   - test common window sizes,
   - no overlap,
   - no clipping,
   - all tall pages scroll,
   - footer does not cover content,
   - dialogs fit on screen,
   - Helm overlay fits and scrolls if needed,
   - Live Overlay config dialog fits.
3. Motion:
   - subtle page transition if already safe,
   - sidebar active-state transition,
   - green pulse for live/Helm indicator,
   - avoid graph animation that causes jank,
   - avoid expensive blur if it hurts performance.
4. Copy polish:
   - remove debug/prototype wording,
   - preserve product-grade copy,
   - make runtime missing-driver/device messages clear and calm,
   - make Helm text first-person and non-robotic.
5. Performance:
   - page switches smooth,
   - hidden pages skip expensive updates,
   - graphs update locally,
   - no Effective Response Stack micro-seizure,
   - Perf / Diagnostics verifies claims.
6. Add screenshots or visual QA notes if possible.
7. Tests/smoke checks:
   - construct every page,
   - navigate every page,
   - resize window,
   - open/close Helm,
   - open Live Overlay Config,
   - open Flight Recorder page,
   - verify no obvious exceptions.

Acceptance criteria:
- The app looks like premium shippable software.
- No known overlap/clipping remains.
- No obvious jank in normal navigation.
- Copy no longer sounds like a development prototype.
- Diagnostics support performance claims.

Report polish changes, screenshots if possible, tests run, and remaining visual issues.
```

## Acceptance Checklist

- [ ] No overlap/clipping.
- [ ] Smooth page switching.
- [ ] Status chips/buttons distinct.
- [ ] Runtime setup copy polished.
- [ ] Helm copy polished.
- [ ] Layout QA performed.

---

# Phase 18 — Packaging, Installer, Icons, and User Data Locations

## Goal

Package the app like real Windows software.

The recovered docs explicitly say the user wants a real app installation, not a shortcut pointing into a folder full of random support files like a software junk drawer.

## Requirements

- One-folder release build is acceptable.
- Inno Setup installer or equivalent.
- Real `.ico` icon embedded in EXE/installer/shortcuts.
- Start Menu shortcut.
- Optional Desktop shortcut.
- Uninstaller entry.
- App files installed to:
  - `%ProgramFiles%\HOTAS Control Panel V2`
  - or `%LocalAppData%\Programs\HOTAS Control Panel V2`
- User data stored separately in:
  - `%AppData%\HOTASControlPanelV2`
  - or `%LocalAppData%\HOTASControlPanelV2`

Icons:

1. Detailed icon
   - best for installer/about/large size
2. Simplified taskbar icon
   - dark navy rounded square
   - white joystick silhouette
   - cyan gauge/curve arc
   - cyan bar indicators
   - no tiny text
   - convert to multi-size `.ico`

## Codex Prompt

```text
Package HOTAS Control Panel V2 as real Windows desktop software.

Requirements:

1. Build release output.
   - Use PyInstaller one-folder, pyside6-deploy, or another documented approach.
   - Do not require the user to run from source for normal use.
2. Installer.
   - Use Inno Setup or equivalent if available.
   - Create installer script under `packaging/inno/`.
   - Add Start Menu shortcut.
   - Add optional Desktop shortcut if configured.
   - Add uninstall entry.
3. Installation paths.
   App binaries/support files should install to one of:
   - `%ProgramFiles%\HOTAS Control Panel V2`
   - `%LocalAppData%\Programs\HOTAS Control Panel V2`

   User data/config/profiles/logs/recordings should go to:
   - `%AppData%\HOTASControlPanelV2`
   - or `%LocalAppData%\HOTASControlPanelV2`

4. Icons.
   - Preserve detailed icon asset for large sizes.
   - Preserve simplified bold taskbar icon.
   - Convert simplified icon to multi-size `.ico` with sizes such as 16, 24, 32, 48, 64, 128, 256 if feasible.
   - Save final icon as `assets/app_icon.ico`.
   - Embed icon in EXE, installer, Start Menu shortcut, and taskbar.
5. Build scripts.
   - Add `packaging/build_release.ps1` or equivalent.
   - Document steps in `packaging/README.md`.
6. Runtime/driver note.
   - Installer should not pretend to install vJoy unless explicitly implemented.
   - App should still guide user through Runtime Setup / vJoy Setup after launch.
7. Tests/smoke checks:
   - packaged app launches,
   - icon appears if testable,
   - config/user data folder created separately,
   - uninstall/install notes documented,
   - app still launches with no vJoy.

Acceptance criteria:
- User can install and launch app like normal Windows software.
- App icon appears correctly.
- User data is separate from binaries.
- Missing vJoy does not break packaged launch.
- Packaging steps are documented.

Report build commands, output paths, installer path, icon status, and remaining packaging issues.
```

## Acceptance Checklist

- [ ] Release build created.
- [ ] Installer script created.
- [ ] App icon embedded.
- [ ] Start Menu shortcut planned/created.
- [ ] User data path separate.
- [ ] Packaged app launches without vJoy.

---

# Phase 19 — Final Integration Kraken / Full Acceptance Sweep

## Goal

Run a full acceptance sweep across all recovered features and rebuild requirements.

This phase should catch the “one tiny thing is broken but only after clicking three buttons while breathing diagonally” bugs.

## Codex Prompt

```text
Run a full integration and acceptance sweep for HOTAS Control Panel V2.

Use the eight recovered spec documents and this prompt book as acceptance references.

Verify:

1. App shell
   - Sidebar pages all present.
   - Header title/subtitle correct.
   - STATUS cluster correct.
   - ASSISTANT/Helm launcher correct.
   - Footer Import/Revert/Save correct.

2. Runtime setup
   - App launches with no vJoy.
   - App launches with no HOTAS.
   - Simulation mode works.
   - Missing vJoy status visible.
   - Missing HOTAS status visible.
   - No fake Full Live status.

3. Mapping
   - Axis routes correct.
   - Button routes exist.
   - Hat routes exist.
   - Live values update in simulation.

4. Modes/Base/Filtering/Combat/Profiles
   - Pages exist.
   - Fields match recovered specs.
   - Graphs render.
   - Linear reference line is true y=x.
   - Workspace dirty/saved state works.

5. Conditional Rules
   - Example rule exists.
   - Status counts correct.
   - Rule can apply in simulation when enabled.
   - Rule injections reach stack metadata.

6. Effective Response Stack
   - One selected axis at a time.
   - Stage cards stable.
   - Freeze works.
   - Rule injections visible.
   - No twitch/micro-seizure.

7. Live Monitor
   - Raw Input Trace works.
   - Raw vs Final Overlay works.
   - Axis Levels work.
   - Buttons/hats visible.

8. Helm
   - Opens from top-right.
   - Overlay/modal, not sidebar page.
   - Uses first-person product-grade text.
   - Symptom chips exist.
   - Combat sluggish path produces diffs.
   - Apply/revert safe.
   - No auto-save.

9. Live Overlay
   - Card exists in Live Monitor.
   - Configure dialog exists.
   - Defaults match recovered values.
   - Overlay shows/hides.
   - Simulation telemetry visible.
   - Hotkey/click-through statuses truthful.

10. Flight Recorder
    - Page exists.
    - Recorder Settings card exists.
    - Axis Overlay exists.
    - Recording Library exists.
    - Clip Preview exists.
    - Forward/hindsight states exist.
    - Real vs simulated capture status truthful.

11. Help / Docs
    - Runtime Setup / vJoy Setup article exists.
    - Topics tree exists.
    - Conditional Rules guide exists.

12. Perf / Diagnostics
    - active page shown.
    - runtime truth shown.
    - hidden page skips shown.
    - graph timings shown.
    - runtime preflight shown.

13. Layout/performance
    - no overlap/clipping at common sizes.
    - tall pages scroll.
    - footer does not cover content.
    - page switching smooth.
    - hidden pages skip expensive work.

14. Packaging if implemented
    - packaged app launches.
    - app icon present.
    - user data separate.
    - app launches without vJoy.

Deliverables:
- Full acceptance report in `/docs/rebuild/final-acceptance-report.md`.
- List of pass/fail items.
- Screenshots if possible.
- Test commands and results.
- Known remaining gaps.
- Next recommended fixes.

Acceptance criteria:
- Every major recovered feature is either implemented, truthfully stubbed, or explicitly listed as remaining work.
- No fake claims.
- The app can be run and used in simulation mode.
- Missing vJoy/HOTAS setup is handled cleanly.
```

## Acceptance Checklist

- [ ] Full acceptance report created.
- [ ] Simulation mode verified.
- [ ] Missing vJoy handled.
- [ ] All major pages accounted for.
- [ ] No fake live runtime claims.
- [ ] Remaining gaps documented.

---

# Recommended Build Order Summary

## Core-first order

1. Phase 0 — Evidence Lock and Project Setup
2. Phase 1 — Runtime Preflight, HOTAS Detection, vJoy Detection, and Simulation Mode
3. Phase 2 — Core Domain Models and Workspace Schema
4. Phase 3 — Tuning Math and Signal Pipeline
5. Phase 4 — PySide6 App Shell, Theme, Sidebar, Header, Footer
6. Phase 5 — Mapping Page and Runtime Setup Guidance
7. Phase 6 — Modes, Base Tuning, Filtering, Combat Profile, and Profiles Pages
8. Phase 7 — Conditional Rules System
9. Phase 8 — Effective Response Stack
10. Phase 9 — Live Monitor Page
11. Phase 10 — Helm Assistant Overlay
12. Phase 11 — Help / Docs and Perf / Diagnostics
13. Phase 12 — Live Overlay Foundation
14. Phase 13 — Flight Recorder, Clip Library, and Hindsight Buffer
15. Phase 14 — Real HOTAS Input Integration
16. Phase 15 — vJoy / Virtual Output Integration
17. Phase 16 — Runtime End-to-End Live Mode
18. Phase 17 — Product Polish, Layout QA, and Motion
19. Phase 18 — Packaging, Installer, Icons, and User Data Locations
20. Phase 19 — Final Integration Kraken / Full Acceptance Sweep

## Practical MVP order

If the user wants a usable app sooner:

1. Evidence/project setup
2. Runtime preflight + simulation
3. Core models/schema
4. Tuning math
5. Shell/theme
6. Mapping + runtime setup card
7. Base/Filtering/Combat/Modes
8. Live Monitor
9. Effective Response Stack
10. Save/Revert/Profile basics
11. Helm shell
12. vJoy/HOTAS real integration
13. Conditional Rules advanced editor
14. Live Overlay
15. Flight Recorder
16. Packaging

## Why runtime setup is early

Because the user currently does not have vJoy installed, the app must support development and simulation first while clearly guiding the path to full live runtime. Runtime truth must exist before the UI starts claiming anything is live.

This is the “wire the cockpit before declaring takeoff” rule. Very technical. Very sacred. Very much preventing software clownery.

---

# Final Notes For Codex

When using these prompts:

- Do one phase at a time.
- Do not skip tests.
- Do not claim live hardware support unless verified.
- Keep simulation mode forever.
- Keep missing-driver/missing-device states clear.
- Preserve recovered labels and UI structure.
- Preserve the premium dark engineering identity.
- Keep Helm separate and polished.
- Keep Flight Recorder and Live Overlay architecture shared but UI-separated.
- Keep user data separate from binaries.
- Always report files changed, tests run, known gaps, and next step.

The rebuild is allowed to improve the original implementation, but not erase the recovered product identity.

The original app was lost. This prompt book is the scaffolding for rebuilding it cleaner, safer, and more documented than before.

A phoenix, but with pyqtgraph and vJoy preflight. Which is honestly much cooler than regular mythology.

