# HelmForge Remaining Post-RC Phase Plan

## Purpose

This document captures the remaining HelmForge / HOTAS Control Panel V3 post-RC phases after the completed parallel tracks:

- Post-RC 1A — Global UI Foundation
- Post-RC 1B — Parameter Metadata and Info Icons
- Post-RC 1C-ish — Parameter Help Coverage
- Post-RC 2A — Mapping HOTAS Diagram Foundation
- Post-RC 2B — Mapping Diagram Interaction
- Post-RC 3A — Flight Recorder Capture Backend Seam
- Post-RC 3B-ish — Flight Recorder Review / Export Diagnostics
- Post-RC 4A — Tuning Page Usability

The remaining work should be treated as product refinement, truth-preserving capability expansion, and final release hardening.

This is no longer the “rebuild the ship from driftwood after the Kraken ate the repo” era. This is now the “make the ship so polished the Kraken asks for a demo license” era.

---

# Global Rules for Every Remaining Phase

## Preserve Runtime Truth

No future phase may weaken HelmForge’s runtime truth model.

The following must remain true:

- Telemetry remains the truth surface.
- Command files are requests, not success proof.
- Process presence is a hint only.
- Physical input alone is not full readiness.
- Output intent is not output write proof.
- vJoy detected does not equal output verified.
- Fake/mock output is not real output.
- Packaged app launch is not runtime readiness.
- Simulation mode remains available.
- Full Live Runtime Ready requires the existing complete proof chain.

## Do Not Add Runtime Authority Unless Explicitly Scoped

Unless a phase specifically says otherwise, do not add:

- Bridge auto-launch.
- UI-launched Bridge child process behavior.
- Service installation.
- Login auto-start.
- Tray/background manager behavior.
- StartBridge / StopBridge / RestartBridge controls.
- Driver/vJoy installer launch.
- New hardware polling.
- vJoy output behavior changes.
- Output verification changes.
- Game injection.
- Graphics API hooking.
- Cloud AI / LLM behavior.
- Auto-save.

## Keep Simulation Mode First-Class

Every remaining phase must still work when:

- HOTAS is not connected.
- vJoy is not verified.
- Bridge telemetry is missing, stale, simulated, or invalid.
- The app is launched from source.
- The app is launched as a packaged executable.

## Preserve Premium Product Identity

Every UI change should keep moving HelmForge toward:

- premium engineering/tuning software;
- serious HOTAS/vJoy control workspace;
- avionics/control-console/signal-lab feel;
- readable, polished desktop software;
- clear distinction between status and action;
- no fake readiness or fake live claims.

The target reaction remains:

> “DAMN THIS IS NICE SOFTWARE.”

---

# Current Immediate Gate — Integrate Post-RC 1C / 2B / 3B

## Status

Before starting the remaining phases, the completed 1C / 2B / 3B branches should be integrated into the current clean integrated branch that already contains 1A / 1B / 2A / 3A / 4A.

## Goal

Create one stable post-RC integration baseline containing:

- 1A global UI foundation;
- 1B parameter metadata/info icons;
- 1C parameter help coverage;
- 2A Mapping diagram foundation;
- 2B Mapping diagram interaction;
- 3A recorder capture seam;
- 3B recorder review/export diagnostics;
- 4A tuning page usability.

## Recommended Merge Order

1. Merge Post-RC 1C first.
2. Merge Post-RC 2B second.
3. Merge Post-RC 3B third.
4. Run focused tests after each merge.
5. Run full validation.
6. Run visible desktop QA.

## Major Conflict Zones

Likely conflict files:

- `v3_app/services/parameter_metadata.py`
- `v3_app/pages/page_helpers.py`
- `v3_app/pages/mapping_page.py`
- `v3_app/pages/flight_recorder_page.py`
- `v3_app/theme/qss.py`
- `docs/HelmForge/*`
- Post-RC test files

## Integration Acceptance Criteria

The merged baseline should preserve:

- 1C metadata/helper/tooltips across pages;
- 2B Mapping diagram selection and Route Inspector behavior;
- 3B Flight Recorder review card, timeline summary, and JSON/CSV exports;
- 4A tuning page axis selection, validators, guidance blocks, and live graph markers;
- 1A global styling and dropdown/button fixes;
- all runtime truth boundaries.

## Final Integration Validation

Run:

```powershell
python -m pytest -q
python -m pytest tests/test_post_rc_1c_parameter_help_coverage.py -q
python -m pytest tests/test_post_rc_2b_mapping_diagram_interaction.py -q
python -m pytest tests/test_post_rc_3b_flight_recorder_review_export.py -q
python -m pytest tests/test_phase13d_flight_recorder_boundary_freeze.py -q
python -m pytest tests/test_phase19d_final_acceptance_report.py -q
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
python -m bridge_app.main --status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
git diff --check
```

Manual visible QA:

```powershell
python -m v3_app.main
```

Inspect:

- Base Tuning
- Filtering
- Combat Profile
- Mapping
- Flight Recorder
- Help / Docs
- Live Monitor
- Perf / Diagnostics

## Integration Deliverable

Add:

```text
docs/HelmForge/post-rc-integration-1c-2b-3b-report.md
```

---

# Recommended Remaining Phase Order

## Best Practical Order

1. Post-RC 1D — Real Help / Docs Full Overhaul
2. Post-RC 3C — Explicit One-Frame Capture Proof
3. Post-RC 2C — Mapping Diagram Editing / Advanced Interaction
4. Post-RC 4B — Page-by-Page Polish Corrections
5. Post-RC 3D — Hindsight Frame Buffer and Capture Pipeline
6. Post-RC 3E — Encoding, Export, and Preview Integration
7. Post-RC 5A — Final Visible Desktop QA and RC2 Freeze

## Why This Order

Post-RC 1D should happen next because the completed 1C was parameter help coverage, not the full Help / Docs overhaul. The metadata registry is now ready, so the docs pass can build a real manual from it.

Post-RC 3C should happen before heavier recorder work because the recorder still has no real frame capture proof. A single explicit frame capture proof should land before rolling buffers, hindsight video, or encoders.

Post-RC 2C should happen before 4B because Mapping editing is now a desired product feature, not a vague someday sparkle. 4B can then polish the finished Mapping edit workflow instead of polishing a read-only version that is about to change.

Post-RC 4B should wait until Help / Docs, the narrow recorder proof, and Mapping diagram editing are stable, because 4B touches many pages and should polish stable surfaces rather than moving lava. Nobody wants to wax a volcano.

Post-RC 3D and 3E should be carefully separated so the app does not claim playable video before buffering and encoding are truly proven.

Post-RC 5A should only happen when the major UI/docs/recorder/polish tracks are accepted or intentionally deferred.

---

# Post-RC 1D — Real Help / Docs Full Overhaul

## Status

Not done yet.

The completed Post-RC 1C expanded parameter metadata/help coverage across more controls, but it explicitly did not complete the original full Help / Docs overhaul.

## Goal

Turn Help / Docs into a rich, organized, searchable, dark-themed in-app manual with structured articles, parameter references, collapsible topic folders, sort modes, and page navigation buttons.

This should make HelmForge feel like serious product-grade software instead of “the docs gremlin left index cards in a drawer.”

## Scope

This phase should focus on:

- Help / Docs UI structure;
- article data model;
- topic tree behavior;
- local deterministic search;
- sorting;
- metadata-powered parameter reference content;
- buttons that navigate to relevant app pages;
- dark theme consistency.

## Required Work

### 1. Dark-Themed Article Pane

Fix any remaining visual issues in Help / Docs:

- no white article backgrounds;
- dark card surfaces matching the app;
- readable body text;
- clear headings;
- section dividers;
- good spacing;
- no giant blank layout holes.

### 2. Collapsible Topic Tree

Implement a polished topic tree:

- categories as collapsible folders;
- categories not directly selectable;
- topics selectable;
- clear active topic highlight;
- search filtering that preserves category context;
- no goofy “flat list pretending to be a manual” energy.

Recommended categories:

- Getting Started
- Runtime Truth
- Mapping
- Tuning
- Filtering
- Combat Profile
- Modes
- Conditional Rules
- Effective Response Stack
- Live Monitor
- Live Overlay
- Flight Recorder
- Helm Assistant
- Profiles
- Perf / Diagnostics
- Packaging / Setup
- Troubleshooting
- Parameter Reference

### 3. Sort Dropdown

Implement visible, working sort options:

- By Category
- By Last Opened
- Alphabetical A-Z
- Alphabetical Z-A
- By Importance

Sort dropdown text must be readable in dark theme.

### 4. Rich Article Structure

Each article should support sections such as:

- What this is
- What it does
- When to use it
- Key parameters
- Suggested ranges
- Examples
- Common mistakes
- Runtime truth notes
- Related topics
- Open page button

### 5. Parameter Registry Integration

Consume the existing parameter metadata registry to generate or enrich Help / Docs parameter content.

Parameter reference entries should include:

- display name;
- page/category;
- support scope;
- value type;
- min/max or options;
- default value;
- examples;
- warnings;
- related page/topic.

Do not duplicate hardcoded lore if the metadata registry already has it.

The registry should be the single source of truth where practical.

### 6. Page Navigation Buttons

At the bottom of relevant articles, add buttons like:

- Open Mapping
- Open Base Tuning
- Open Filtering
- Open Combat Profile
- Open Modes
- Open Conditional Rules
- Open Effective Response Stack
- Open Live Monitor
- Open Flight Recorder
- Open Perf / Diagnostics
- Open Helm

These buttons should navigate inside the app. They should not launch external websites.

### 7. Expanded Article Coverage

Add or expand articles for:

- HelmForge overview
- Simulation mode
- Runtime truth model
- Full Live Runtime Ready
- vJoy/output verification
- Bridge telemetry
- Mapping overview
- HOTAS diagram
- Mapping Route Inspector
- Axis routing
- Button routing
- Hat routing
- Base Tuning overview
- Curve modes
- Deadzone / anti-deadzone
- Hysteresis
- Output scale / max output
- Filtering overview
- Slew limits
- Combat Profile overview
- Modes overview
- Precision mode
- Combat mode
- Stack mode
- Conditional Rules overview
- Rule stages
- Comparators
- Effective Response Stack
- Live Monitor
- Live Overlay
- Flight Recorder overview
- Recorder review/export diagnostics
- Real capture limitations
- Helm Assistant
- Profiles
- Perf / Diagnostics
- Packaging and setup
- Troubleshooting

## Non-Goals

Do not add:

- web/cloud docs;
- LLM docs generation;
- runtime authority;
- Bridge lifecycle behavior;
- recorder capture/encoding;
- Mapping editing;
- auto-save.

## Tests

Add focused tests, for example:

```text
tests/test_post_rc_1d_help_docs_full_overhaul.py
```

Coverage should include:

- Help / Docs has dark article styling markers/properties;
- categories are collapsible/non-selectable;
- sort dropdown includes required options;
- search remains deterministic/local;
- articles have structured sections;
- parameter reference entries consume metadata;
- page navigation buttons exist and route correctly;
- no runtime authority was introduced.

## Documentation Deliverable

Add:

```text
docs/HelmForge/post-rc-1d-help-docs-full-overhaul-report.md
```

Report should include:

- UI changes;
- topic tree model;
- article data model;
- metadata integration;
- navigation buttons;
- articles added;
- known limitations;
- runtime truth preservation.

## Acceptance Criteria

- Help / Docs looks premium and dark-themed.
- Topic tree is collapsible and usable.
- Sort dropdown works.
- Articles are structured and useful.
- Parameter docs use metadata.
- Relevant articles include page navigation buttons.
- Search is local/deterministic.
- Runtime truth is preserved.

---

# Post-RC 3C — Explicit One-Frame Capture Proof

## Status

Not done yet.

Post-RC 3A created the safe capture backend seam. Post-RC 3B added recorder review/export diagnostics, but no real desktop frame capture exists yet.

## Goal

Add a narrow, explicit one-frame capture proof behind the existing 3A capture backend seam.

This phase should prove whether a backend can capture one frame safely. It must not jump directly to video recording, hindsight buffering, encoding, preview, or global hotkeys.

Tiny step. Big truth. No recorder goblin declaring “cinematic masterpiece” because it exported a JSON file.

## Scope

This phase should focus on:

- explicit manual capture attempt;
- one frame only;
- typed capture result;
- failure-safe backend behavior;
- UI truth labels;
- optional local diagnostic frame artifact if truly captured.

## Required Work

### 1. Extend Capture Backend Interface

Add or refine a method such as:

```python
capture_one_frame(source: CaptureSource) -> FrameCaptureResult
```

The result should include:

- success flag;
- backend name;
- source/display id;
- timestamp;
- image/frame dimensions if successful;
- pixel format or format label if known;
- optional artifact path if saved;
- warnings;
- errors;
- truth label.

### 2. Guarded Backend Implementation

Use the existing conservative backend candidate from 3A.

Possible initial path:

- Qt screen grab candidate;
- explicit call only;
- no automatic capture loop;
- no recording;
- no encoder;
- no game hooking;
- no admin requirement.

If the desktop/offscreen context cannot capture, return unavailable/error truthfully instead of crashing.

### 3. Capture Source Selection

Use the display/capture source model from 3A.

Support:

- primary display if available;
- selected display if already modeled;
- unavailable/offscreen fallback state.

Do not add window picking unless explicitly scoped.

### 4. Flight Recorder UI Update

Add a small proof section/card:

- Capture Proof
- Backend status
- Display/source
- Last one-frame proof result
- Last frame dimensions if successful
- Last error/warning if failed
- Try One-Frame Capture button if safe

Button must be disabled when:

- backend dependency unavailable;
- app is in offscreen/test-only mode;
- backend reports real capture unsupported;
- display source unavailable.

### 5. Optional Diagnostic Artifact

If a frame is truly captured, allow saving a diagnostic still frame or metadata record.

Rules:

- local-only;
- deterministic folder;
- no silent overwrite;
- clear label that this is a still-frame proof, not a recording;
- no video claims.

### 6. Preserve 3B Review/Export

Do not break:

- review session summary;
- timeline summary;
- JSON summary export;
- CSV sample export;
- clear reviewed session behavior.

## Non-Goals

Do not add:

- continuous capture;
- ring buffer;
- hindsight video;
- video encoding;
- MP4/WebM export;
- preview playback;
- global recorder hotkeys;
- game injection;
- graphics API hooking;
- Bridge lifecycle behavior;
- hardware polling;
- output verification changes.

## Tests

Add focused tests, for example:

```text
tests/test_post_rc_3c_one_frame_capture_proof.py
```

Coverage should include:

- backend exposes one-frame capability truth;
- unavailable backend returns typed unavailable result;
- no capture starts automatically;
- offscreen/test contexts do not crash;
- successful fake/test backend can return frame metadata;
- Flight Recorder page displays one-frame proof state;
- UI does not claim recording/encoding/preview;
- existing 3B review/export tests still pass;
- no runtime authority was introduced.

## Documentation Deliverable

Add:

```text
docs/HelmForge/post-rc-3c-one-frame-capture-proof-report.md
```

Report should include:

- backend method added;
- candidate backend behavior;
- UI proof behavior;
- artifact behavior if any;
- unavailable/error handling;
- what remains for frame buffering;
- runtime truth preservation.

## Acceptance Criteria

- App can attempt one explicit frame proof only when safe.
- Failure reports unavailable/error instead of crashing.
- Success, if possible, is truthfully labeled as still-frame proof.
- No video recording or encoding is claimed.
- Flight Recorder review/export still works.
- Runtime truth remains conservative.

---

# Post-RC 4B — Page-by-Page Polish Corrections

## Status

Not done yet.

Post-RC 4A fixed Base Tuning / Filtering / Combat Profile usability. 4B is the broad page-specific polish pass across the rest of the app.

## Goal

Apply remaining page-by-page corrections from the manual walkthrough and the new post-RC surfaces.

This phase should make the app feel cohesive, polished, premium, and genuinely pleasant to use.

This is the “make it expensive” phase. Not fake expensive. Real expensive. Like a control panel that drinks espresso and files its taxes early.

## Scope

Covers targeted UI/UX cleanup across:

- Helm Assistant overlay
- Mapping
- Profiles
- Modes
- Conditional Rules
- Effective Response Stack
- Live Monitor
- Flight Recorder
- Help / Docs
- Perf / Diagnostics
- Global layout regression cleanup

## Required Work By Page

## Helm Assistant

Polish items:

- Make Helm feel like a premium right-side overlay.
- Consider slide-in animation from the right if feasible and test-safe.
- Add or improve app-behind dim/blur treatment if feasible.
- Fix card background inconsistencies.
- Improve recommendation/finding card layout.
- Resize symptom prompt chips.
- Make symptom input auto-resize or better proportioned.
- Keep Apply/Revert buttons grouped clearly near the bottom of relevant cards.
- Polish active indicator, possibly with a subtle pulsing green bulb effect.
- Make in-memory-only boundary clear.
- Keep Helm deterministic and local.

Non-goals:

- no cloud AI;
- no live hardware authority;
- no auto-apply;
- no auto-save.

## Mapping

Polish items:

- Ensure 2B diagram interaction feels integrated, not bolted on.
- Improve Route Inspector layout.
- Improve warning/conflict display readability.
- Ensure diagram labels do not overlap badly.
- Ensure table columns fit route text.
- Consider route-filter chips if small and safe.
- Consider moving Runtime Setup / Preflight into a clearer tab/dashboard area.
- Keep diagram read-only unless 2C is explicitly also implemented later.

Non-goals:

- no drag-to-remap;
- no live route capture;
- no output verification changes.

## Profiles

Polish items:

- Make profile row selection work clearly.
- Make selected profile visually obvious.
- Make default profiles actually differ in useful ways if currently identical.
- Widen profile name/summary column by default.
- Improve profile details card readability.
- Clearly distinguish workspace draft vs saved profile.
- Make import/revert/save workflow clearer.

Non-goals:

- no auto-save;
- no cloud profile sync;
- no hardware runtime claims.

## Modes

Polish items:

- Convert menu-like text fields to dropdowns where metadata supports options.
- Remove forced equal-height card gaps.
- Improve stack mode explanation.
- Improve precision/combat trigger button field readability.
- Add metadata tooltips where missing.
- Make mode enable/disable state obvious.
- Make active/inactive mode labels visually distinct but not fake-live unless telemetry proves it.

Non-goals:

- no new mode behavior unless already supported;
- no fake live mode activation claims.

## Conditional Rules

Polish items:

- Polish rule list spacing and readability.
- Expand columns so values are not cramped.
- Move Rule Logic above Rule Detail if that improves scan flow.
- Ensure dropdowns are populated and readable.
- Add all valid parameter targets that are supported.
- Improve rule detail readability.
- Add metadata tooltips for rule editor fields.
- Make validation warnings clearer.
- Ensure unsupported or invalid rule shapes are labeled as config issues, not runtime device failures.

Non-goals:

- no new runtime evaluator authority;
- no fake rule firing claims.

## Effective Response Stack

Polish items:

- Add subtle downward chain/flow visual if feasible.
- Add Total Change block.
- Highlight most impactful stage.
- Resize lower cards to content.
- Improve axis selector visibility.
- Improve explanation of each stage.
- Make raw-to-final transformation easier to understand.
- Preserve performance and avoid animation jank.

Non-goals:

- no pipeline behavior changes unless explicitly tested;
- no fake live output claims.

## Live Monitor

Polish items:

- Ensure graph updates target 30–60 Hz where existing refresh model supports it.
- Last ~7 seconds should scroll left if that is the intended design.
- Move command/control buttons into their own block.
- Rotate or redesign Axis Levels to be more readable.
- Improve Live State readability.
- Add or polish Live Overlay presets if already supported.
- Improve source chip clarity.
- Make Bridge missing/stale/simulated/fresh states immediately understandable.

Non-goals:

- no new hardware polling;
- no output verification changes;
- no Bridge lifecycle controls.

## Flight Recorder

Polish items:

- Integrate 3B review/export card cleanly.
- If 3C is already done, integrate one-frame proof card cleanly.
- Make recorder settings visually editable where supported.
- Fix Record Cursor checkbox behavior if still awkward.
- Fix Axis Overlay include checkboxes if still awkward.
- Improve recorder status display.
- Clarify simulated metadata/export vs real recording.
- Make JSON/CSV export buttons clear and disabled until valid.
- Improve empty states.

Non-goals:

- no real video unless 3C/3D/3E scopes it;
- no encoding;
- no preview;
- no global hotkey registration.

## Help / Docs

If 1D is done before 4B:

- Polish topic tree spacing.
- Polish article typography.
- Improve page navigation buttons.
- Improve parameter reference display.
- Fix any remaining white-background or layout regressions.

If 1D is not done before 4B:

- Do not attempt the full Help / Docs overhaul inside 4B.
- Only fix obvious visual regressions.
- Defer structured docs work.

## Perf / Diagnostics

Polish items:

- Improve Runtime Truth sorting.
- Reduce blank space in Bridge / Telemetry cards.
- Expand Performance Timings readability.
- Make dry-run/preflight controls clear.
- Improve distinction between diagnostics, hints, and proof.
- Keep process presence as a hint only.
- Make “Full Live Runtime Ready: false” explanations clearer.

Non-goals:

- no driver installation;
- no Bridge start/stop;
- no output verification changes.

## Global Regression Cleanup

Check across all pages:

- no blank dropdowns;
- no permanently pressed-looking buttons;
- no white article/card backgrounds;
- no giant equal-height card gaps;
- no clipped table text;
- no unreadable helper text;
- no broken dark theme popups;
- no bottom bar Page / Axis / Profile / Source noise regression.

## Tests

Add focused tests, for example:

```text
tests/test_post_rc_4b_page_by_page_polish.py
```

Coverage should include:

- key pages construct offscreen;
- no known white-background object regressions where testable;
- Mapping inspector still exists after polish;
- Flight Recorder review/export still exists after polish;
- Help / Docs page still works if 1D exists;
- Modes/Rules dropdowns have options;
- Profiles row selection works if implemented;
- Effective Response Stack total-change/impact blocks exist if implemented;
- no runtime authority was introduced.

## Documentation Deliverable

Add:

```text
docs/HelmForge/post-rc-4b-page-by-page-polish-report.md
```

Report should include:

- pages changed;
- issues fixed;
- issues deferred;
- screenshots if practical;
- tests run;
- runtime truth preservation.

## Acceptance Criteria

- Manual walkthrough issues are fixed or explicitly deferred.
- App feels more polished and cohesive.
- No new runtime authority is added.
- No major layout regressions.
- Tests pass.

---

# Post-RC 2C — Mapping Diagram Editing / Advanced Interaction

## Status

Planned, not done yet.

Post-RC 2B made the Mapping diagram operable for selection and inspection, but not editing. This phase promotes the diagram from a read-only inspector into a safe workspace mapping editor.

## Goal

Add a safe, intentional Mapping diagram edit workflow from the Route Inspector without implying live output writes.

This is now a desired product phase, not merely optional. The goal is to make the HOTAS diagram feel genuinely useful: click a control, inspect its route, press Change Mapping, edit the workspace draft, preview conflicts, apply or revert safely, and still never pretend that workspace intent equals live vJoy output.

## Scope

This phase should focus on:

- edit affordances from the Route Inspector;
- route editing workflow;
- apply/revert of workspace draft changes;
- conflict preview;
- keyboard navigation/filtering improvements.

## Required Work

### 1. Route Edit Workflow From Inspector

Add a controlled edit flow from the selected diagram control / Route Inspector.

The normal user flow should be:

1. User clicks a HOTAS diagram marker.
2. Route Inspector shows the current route.
3. User clicks `Change Mapping`.
4. An edit panel or modal opens for that route type.
5. User changes the mapping target or options.
6. UI previews warnings/conflicts before applying.
7. User chooses Apply to Draft, Cancel, or Revert.

Possible UI fields:

- selected physical input;
- current mapped output intent;
- route type;
- Change Mapping button;
- output target dropdown;
- logical function dropdown if supported;
- invert checkbox for axes;
- hat direction mapping controls;
- button output target selector;
- Apply to Draft;
- Cancel;
- Revert Route.

All edits should remain workspace/config edits.

### 2. Safe Apply/Revert

Rules:

- editing changes workspace draft only;
- no vJoy writes;
- no output verification claims;
- no auto-save;
- dirty state should update;
- Save Workspace remains the explicit save action.

### 3. Conflict Preview and Clear Overlay Markers

Show config warnings before applying:

- duplicate exclusive output targets;
- missing output targets;
- unsupported route shape;
- invalid control/output pairing;
- unmapped important controls;
- route target already used by another control.

Warnings must remain workspace/config warnings, not live runtime errors.

Add clearer visual conflict indicators on the diagram:

- small warning badge on affected markers;
- warning color/ring around conflicting controls;
- inspector warning summary;
- table row warning marker where practical.

The overlay must not imply device failure. It should say workspace/config conflict, not live runtime failure.

### 4. Keyboard Navigation

Improve accessibility if feasible:

- tab through diagram markers;
- arrow-key movement between markers;
- inspector updates on focus;
- visible focus ring.

### 5. Route Filter Chips

Add compact route-filter chips above or beside the diagram/inspector:

- All
- Axes
- Buttons
- Hats
- Mapped
- Unmapped
- Warnings
- Selected Profile

Filter chips should only affect the visual diagram/table focus. They must not mutate mappings.

### 6. Safe Edit / Apply / Revert Behavior

Editing must be safe and reversible:

- Apply updates the in-memory workspace draft only.
- Save Workspace remains the explicit save action.
- Cancel leaves the draft unchanged.
- Revert Route restores the route to its pre-edit draft value.
- Revert All Mapping Edits may be added if already supported by draft history.
- Dirty state should update clearly.
- No edit should write to vJoy or claim live hardware success.

### 7. Read-Only vs Edit Mode Clarity

The Mapping diagram should clearly distinguish:

- Inspect Mode — click/hover to inspect only.
- Edit Mode — route changes are allowed but still draft-only.

Suggested UI copy:

- `Inspecting workspace route`
- `Editing workspace draft`
- `Output intent only — not live output proof`
- `Save Workspace required to persist changes`

## Non-Goals

Do not add:

- drag-to-remap unless explicitly scoped and testable;
- live hardware capture;
- “press a button to bind” behavior;
- vJoy output writes;
- output verification;
- Bridge lifecycle behavior.

## Tests

Add focused tests, for example:

```text
tests/test_post_rc_2c_mapping_diagram_editing.py
```

Coverage should include:

- inspector exposes Change Mapping affordance;
- edit panel populates valid route options;
- axis edit supports output target and invert fields where applicable;
- button edit supports output button target where applicable;
- hat edit supports POV/direction mapping where applicable;
- apply changes workspace draft only;
- dirty state updates after apply;
- cancel preserves previous route;
- revert restores previous draft route;
- filter chips change visual/filter state only;
- keyboard navigation can focus/select markers if implemented;
- conflict preview catches duplicates/missing targets;
- conflict markers appear on affected controls where testable;
- no output write claims;
- no runtime authority was introduced.

## Documentation Deliverable

Add:

```text
docs/HelmForge/post-rc-2c-mapping-diagram-editing-report.md
```

Report should include:

- edit workflow;
- conflict preview;
- accessibility improvements;
- deferred live binding behavior;
- runtime truth preservation.

## Acceptance Criteria

- User can safely edit mappings from diagram/inspector.
- `Change Mapping` opens a clear route-specific edit workflow.
- Edits remain workspace-draft-only until Save Workspace.
- Apply, cancel, and revert behavior are clear and safe.
- Route-filter chips help focus the diagram/table without changing mappings.
- Keyboard navigation is improved if feasible.
- Conflicts are shown before save and marked clearly on the diagram/inspector.
- No fake live output claims.

---

# Post-RC 3D — Hindsight Frame Buffer and Capture Pipeline

## Status

Not done yet.

This should happen after Post-RC 3C proves a one-frame capture path.

## Goal

Implement the actual rolling frame buffer and telemetry synchronization needed for hindsight capture.

This is where the recorder starts becoming a real recorder pipeline, but still should not claim playable video until encoding exists.

## Scope

This phase should focus on:

- repeated frame capture loop only if 3C proof succeeded;
- ring buffer;
- timestamps;
- memory limits;
- telemetry synchronization;
- Save Last Clip intermediate artifact;
- truth labels for buffer state.

## Required Work

### 1. Frame Ring Buffer

Add a frame buffer model:

- max duration;
- target FPS;
- max memory budget;
- timestamps;
- display/source id;
- frame dimensions;
- dropped-frame tracking;
- oldest/newest frame timestamps;
- buffer health.

### 2. Capture Loop Controller

Add safe capture loop behavior:

- explicit start/stop only;
- no automatic background recording unless user starts it;
- no global hotkeys yet unless separately scoped;
- no crash on backend failure;
- backoff if repeated failures occur;
- stop cleanly on app exit.

### 3. Telemetry Buffer Alignment

Synchronize telemetry samples with frame timestamps.

Track:

- axis samples;
- button/hat samples if available;
- runtime truth snapshot;
- source type;
- output verification truth;
- Full Live Runtime Ready truth.

### 4. Save Last Clip Intermediate Artifact

Implement Save Last Clip as an intermediate artifact only.

Artifact may include:

- frame sequence metadata;
- captured still frames or temporary frame references if truly captured;
- telemetry samples;
- timeline summary;
- runtime truth snapshot;
- warnings/errors.

Do not call it a playable video yet.

### 5. Flight Recorder UI Updates

Add truth labels:

- frame buffer active/unavailable/error;
- buffer duration;
- stored frame count;
- dropped frame count;
- memory estimate;
- telemetry samples aligned;
- last save state;
- not encoded / not playable.

### 6. Preserve Review/Export

3B review/export should still work and may consume the new buffer metadata.

## Non-Goals

Do not add:

- video encoding;
- MP4/WebM export;
- playable preview;
- global hotkeys;
- game injection;
- graphics API hooking;
- output verification changes;
- Bridge lifecycle behavior.

## Tests

Add focused tests, for example:

```text
tests/test_post_rc_3d_hindsight_frame_buffer.py
```

Coverage should include:

- ring buffer retains only max duration;
- timestamps are monotonic;
- dropped frame tracking works;
- telemetry aligns to frame interval;
- Save Last Clip creates intermediate artifact;
- UI says not encoded/not playable;
- backend failure reports unavailable/error;
- no runtime authority was introduced.

## Documentation Deliverable

Add:

```text
docs/HelmForge/post-rc-3d-hindsight-frame-buffer-report.md
```

Report should include:

- buffer model;
- capture loop behavior;
- telemetry sync;
- intermediate artifact format;
- memory/performance limits;
- what remains for encoding;
- runtime truth preservation.

## Acceptance Criteria

- Hindsight buffer collects frames only when explicitly started and supported.
- Save Last Clip exports an intermediate artifact.
- UI does not claim playable video.
- Failure modes are clear.
- Runtime truth remains conservative.

---

# Post-RC 3E — Encoding, Export, and Preview Integration

## Status

Not done yet.

This should happen after 3D produces stable intermediate frame/telemetry artifacts.

## Goal

Add real encoding/export and preview behavior, producing actual playable clips only when the encoding pipeline truly succeeds.

This is the phase where the recorder can finally say, “Yes, this is a video,” without the truth goblin throwing a wrench through the window.

## Scope

This phase should focus on:

- safe encoder backend;
- overlay compositor;
- playable clip export;
- preview/reveal integration;
- metadata and truth labels.

## Required Work

### 1. Encoder Backend Selection

Choose a safe encoder path.

Possible options:

- ffmpeg subprocess if binary discovery/bundling is safe;
- OpenCV VideoWriter if dependency is accepted;
- image sequence plus external encoder;
- another safe, testable encoder.

The chosen backend must report:

- dependency available;
- encoder version if applicable;
- supported formats;
- output path;
- failure reason;
- whether output was verified playable enough to claim success.

### 2. Packaging Safety

If ffmpeg or another binary dependency is used:

- define discovery behavior;
- define bundled vs external behavior;
- include license/release notes if needed;
- ensure packaged smoke covers missing dependency;
- fail gracefully if unavailable.

### 3. Overlay Compositor

Implement frame compositing:

- bake axis overlay trace into frames;
- align telemetry to frame timestamp;
- show raw/final/output-intent labels truthfully;
- preserve source/final output distinction;
- reuse Live Overlay visual language where practical.

### 4. Export Format

Support one primary format first.

Recommended initial target:

- MP4 if ffmpeg path is chosen;
- AVI or another safe format if OpenCV path is chosen;
- no fake extension if output is not playable.

### 5. Preview Integration

Add safe preview/reveal behavior:

- preview card;
- thumbnail if available;
- reveal file button;
- metadata display;
- optional playback if feasible and reliable.

If playback is not reliable, reveal-file plus metadata is acceptable.

### 6. Failure States

Clearly distinguish:

- encoding unavailable;
- encoding failed;
- clip exported;
- clip playable/verified if verification exists;
- intermediate artifact only.

## Non-Goals

Do not add:

- game injection;
- graphics API hooking;
- admin capture;
- cloud upload;
- auto-share;
- output verification changes;
- Bridge lifecycle behavior.

## Tests

Add focused tests, for example:

```text
tests/test_post_rc_3e_encoding_export_preview.py
```

Coverage should include:

- missing encoder reports unavailable;
- fake/test encoder can create deterministic output artifact;
- no playable claim when encoder fails;
- successful encoded artifact is labeled correctly;
- overlay compositor aligns telemetry to frames;
- preview/reveal state appears only after export;
- no runtime authority was introduced.

## Documentation Deliverable

Add:

```text
docs/HelmForge/post-rc-3e-encoding-export-preview-report.md
```

Report should include:

- encoder chosen;
- dependency/packaging behavior;
- overlay compositor behavior;
- export format;
- preview behavior;
- failure states;
- runtime truth preservation.

## Acceptance Criteria

- Encoded clip is truly generated before UI claims success.
- Failed encoding is reported honestly.
- Preview/reveal behavior works if claimed.
- Intermediate artifacts remain distinct from playable videos.
- Runtime truth remains conservative.

---

# Post-RC 5A — Final Visible Desktop QA and RC2 Freeze

## Status

Final phase, not done yet.

This should happen only after the major remaining work is complete or explicitly deferred.

## Goal

Run a final visible desktop QA pass and freeze a second release candidate.

This is the “Kraken walks around the ship with a clipboard” phase.

## Required Work

### 1. Full Manual Page Walkthrough

Inspect every major page:

- Dashboard / Home if present
- Mapping
- Profiles
- Modes
- Base Tuning
- Filtering
- Combat Profile
- Conditional Rules
- Effective Response Stack
- Live Monitor
- Live Overlay config
- Flight Recorder
- Help / Docs
- Perf / Diagnostics
- Helm Assistant

### 2. Window Size Testing

Test common sizes:

- 1280 x 720
- 1440 x 900
- 1920 x 1080
- 2048 x 1280 if available

Check:

- no clipped controls;
- scroll areas work;
- tables remain usable;
- diagrams remain readable;
- dialogs fit;
- bottom bar remains clean;
- no major overlap.

### 3. Packaged App Visual Smoke

Rebuild package if needed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean
```

Smoke-test packaged app:

```powershell
.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250
```

If packaged smoke is not run, report that honestly.

### 4. Help / Docs QA

Check:

- topic tree;
- search;
- sorting;
- article readability;
- parameter references;
- page navigation buttons;
- no white-background regressions.

### 5. Mapping QA

Check:

- diagram renders;
- markers are readable;
- marker selection works;
- table selection syncs;
- Route Inspector updates;
- warnings are clear;
- no fake live-output claims.

### 6. Flight Recorder QA

Depending on completed recorder phases, check:

- backend truth;
- one-frame proof if implemented;
- buffer state if implemented;
- review card;
- JSON/CSV exports;
- video export if implemented;
- preview/reveal if implemented;
- no fake recording/encoding claims.

### 7. Runtime Truth QA

Check wording across:

- Live Monitor;
- Flight Recorder;
- Mapping;
- Perf / Diagnostics;
- footer/status areas;
- Help / Docs runtime articles.

Required truth boundaries:

- vJoy detected is not output verification.
- Output intent is not output write proof.
- Physical input alone is not Full Live Runtime Ready.
- Simulation mode is clearly labeled.
- Fake/test paths are not real readiness.
- Packaged smoke is not runtime readiness.

### 8. Regression Test Run

Run:

```powershell
python -m pytest -q
python -m pytest tests/test_phase19d_final_acceptance_report.py -q
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
python -m bridge_app.main --status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
git diff --check
```

Run additional focused test files for all completed post-RC phases.

### 9. Kraken / Harness Rerun

If the project has a Kraken/full acceptance harness, rerun it and attach artifacts.

The RC2 report should classify:

- pass;
- blocked;
- pass with known issues;
- defer specific features.

## Documentation Deliverable

Add:

```text
docs/HelmForge/post-rc-5a-final-visible-desktop-qa-rc2-freeze-report.md
```

Report should include:

- build/branch info;
- completed post-RC phases;
- deferred work;
- manual QA results;
- screenshots if practical;
- test commands and results;
- packaged smoke result;
- runtime truth audit;
- known issues;
- RC2 classification;
- tag recommendation.

## Acceptance Criteria

- No major UI readability blockers.
- No severe layout issues.
- Dropdowns are readable.
- Buttons have correct states.
- Help / Docs is usable if 1D is included.
- Mapping diagram is usable.
- Flight Recorder truth is clear.
- Runtime truth gates remain unchanged.
- Full regression tests pass or failures are explicitly classified.
- RC2 status is clearly stated.

---

# Possible Final Phase Dependency Map

## Minimum RC2 Path

If you want the fastest responsible RC2 while still including the desired Mapping editor:

1. Integrate 1C / 2B / 3B.
2. Post-RC 1D — Help / Docs Full Overhaul.
3. Post-RC 2C — Mapping Diagram Editing / Advanced Interaction.
4. Post-RC 4B — Page-by-Page Polish.
5. Post-RC 5A — Final QA / RC2 Freeze.

This defers real recorder video work beyond RC2.

## Recorder-Forward RC2 Path

If Flight Recorder is a major release selling point:

1. Integrate 1C / 2B / 3B.
2. Post-RC 1D — Help / Docs Full Overhaul.
3. Post-RC 3C — One-Frame Capture Proof.
4. Post-RC 3D — Hindsight Frame Buffer.
5. Post-RC 3E — Encoding / Export / Preview.
6. Post-RC 4B — Page-by-Page Polish.
7. Post-RC 5A — Final QA / RC2 Freeze.

This is more ambitious and riskier.

## Balanced Recommended Path

Best balance:

1. Integrate 1C / 2B / 3B.
2. Post-RC 1D — Help / Docs Full Overhaul.
3. Post-RC 3C — One-Frame Capture Proof.
4. Post-RC 2C — Mapping Diagram Editing / Advanced Interaction.
5. Post-RC 4B — Page-by-Page Polish.
6. Decide whether 3D/3E are RC2 blockers or post-RC2.
7. Post-RC 5A — Final QA / RC2 Freeze.

This gives you:

- excellent docs;
- polished product feel;
- honest first capture proof;
- no risky fake recorder claims;
- a sane RC2 target.

---

# Suggested Next Move

After the 1C / 2B / 3B integration passes, run:

## Next Phase

```text
Post-RC 1D — Real Help / Docs Full Overhaul
```

Why:

- The metadata registry is ready.
- Help / Docs is still not the full manual originally requested.
- 4B will benefit from stable docs/navigation surfaces.
- It is lower runtime risk than recorder capture work.
- It makes the app feel much more complete.

## Then

```text
Post-RC 3C — Explicit One-Frame Capture Proof
```

Why:

- Recorder still has no real capture proof.
- One-frame proof is the safe next step.
- It avoids jumping straight into video buffer chaos.

## Then

```text
Post-RC 4B — Page-by-Page Polish Corrections
```

Why:

- Once docs and the recorder proof surfaces exist, 4B can polish the full visible app.
- This prevents polishing temporary UI that will immediately change.

---

# Final Remaining Phase Checklist

```text
[ ] Integrate Post-RC 1C / 2B / 3B
[ ] Post-RC 1D — Real Help / Docs Full Overhaul
[ ] Post-RC 3C — Explicit One-Frame Capture Proof
[ ] Post-RC 2C — Mapping Diagram Editing / Advanced Interaction
[ ] Post-RC 4B — Page-by-Page Polish Corrections
[ ] Post-RC 3D — Hindsight Frame Buffer and Capture Pipeline
[ ] Post-RC 3E — Encoding, Export, and Preview Integration
[ ] Post-RC 5A — Final Visible Desktop QA and RC2 Freeze
```

The goblins are no longer feral. They now have clipboards, branch names, and just enough supervision to be dangerous in a productive way.

