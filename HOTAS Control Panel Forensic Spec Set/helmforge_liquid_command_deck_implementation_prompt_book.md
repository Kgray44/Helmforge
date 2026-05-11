# HelmForge Liquid Command Deck Implementation Prompt Book

## Purpose

This prompt book converts the two governing design documents into an implementation-ready Codex plan for a full HelmForge UI rebuild.

This is not another visual polish pass. This is not a QSS repaint. This is not “make the current UI glassy.” This is a full interface recomposition into a new product experience:

# Liquid Glass Command Deck

The current HelmForge UI may remain as a reference, fallback, or data source, but it is not the layout source. The new interface should be built as a new command-deck UI system that uses only the proven non-visual application foundations where they are still useful.

The goal is to create a premium, modern, smooth, glass-cockpit interface for HOTAS mapping, tuning, monitoring, validation, recording, and assistant-guided configuration.

The final app should feel like serious engineering software that accidentally wandered onto the bridge of an expensive spaceship and decided to become gorgeous.

---

# 0. Governing Rule

## This is a full UI redo.

The implementation must not treat the current UI as something to restyle.

Bad approach:

```text
Existing pages + new QSS + translucent cards + prettier borders
```

Good approach:

```text
New Liquid Glass Command Deck shell + new page compositions + existing proven data/services/runtime truth where useful
```

## Magic sentence for every Codex phase

Use this sentence near the top of every implementation prompt:

```text
Do not wrap, reskin, or cosmetically patch the existing Legacy UI. Build a new Liquid Glass Command Deck interface from first principles, using existing non-visual services, workspace/runtime data, and truth boundaries only where they are useful. Legacy pages are reference/fallback, not the design source.
```

If Codex starts turning old pages into glass cards, stop the phase and redirect.

---

# 1. Product Identity

## Product Name

HelmForge — Liquid Command Deck

## Design Direction

The UI should feel inspired by:

- modern aircraft glass cockpits
- premium flight-control software
- high-end HOTAS configuration tools
- futuristic workstation dashboards
- Liquid Glass-style layered surfaces
- engineering instrumentation
- cockpit MFD mode-switching
- dark, dimensional, precision-focused command surfaces

It should not feel like:

- a normal Qt settings app
- an enterprise dashboard
- a sidebar-and-card admin panel
- a developer diagnostics dump
- a random neon gamer overlay
- Legacy UI wearing glass pants

The new UI should communicate:

- command
- trust
- status truth
- precision
- physical signal flow
- configuration clarity
- premium control
- calm readiness

---

# 2. Hard Boundary: UI Redo vs Backend Reuse

## Reuse Allowed

The new UI may reuse existing non-visual systems where they are clean, tested, and truthful:

- workspace data models
- bridge telemetry model
- bridge command seam
- runtime truth states
- mapping data
- tuning parameter values
- filtering/combat profile state
- conditional rules data
- recorder state models
- Helm recommendation/apply/revert logic
- parameter metadata
- help metadata
- packaging/smoke infrastructure
- tests that validate runtime truth
- constants/enums where still correct

## Reuse Not Allowed As Design Source

The following should not drive the new design:

- existing page layout structure
- existing sidebar layout
- old card stacks
- old grid/scroll arrangement
- repeated label/value rows everywhere
- existing page hierarchy if it conflicts with the new mode architecture
- old visual component assumptions
- old status placement
- old footer/header clutter
- old diagnostics-first composition

## Potentially Replaceable UI Backend

The current UI backend/widget layer may be replaced or bypassed where necessary.

Codex should be free to create:

- new shell classes
- new navigation system
- new page container system
- new component library
- new layout primitives
- new command-deck pages
- new visual widgets
- new theme token module
- new glass rendering helpers
- new page routing architecture

The old UI can remain available as a safety fallback while the new system matures.

---

# 3. Runtime Truth Boundaries

The new UI must preserve HelmForge truth boundaries.

Do not change:

- hardware polling behavior
- vJoy write behavior
- output verification logic
- Full Live Runtime Ready logic
- Bridge lifecycle ownership
- Bridge auto-start/stop behavior
- recorder capture/encoding claims
- simulation fallback truth
- telemetry proof rules
- Helm apply/revert semantics
- workspace save/apply semantics

The UI may look like a spaceship. It may not lie like a politician in a toaster factory.

## Forbidden Claims Unless Truly Implemented

Do not show or imply:

- output verified unless output write proof exists
- live output active unless runtime proof exists
- full live runtime ready unless all gates are satisfied
- real recording available unless real capture/encoding exists
- HOTAS connected unless actual telemetry/device proof exists
- vJoy writing unless writes are actually verified
- Bridge managed by UI unless lifecycle management is implemented

## Approved Truth Language

Use wording like:

- Output intent
- Mapping intent
- Runtime blocked
- Simulation mode
- Telemetry missing
- Telemetry stale
- Workspace loaded
- Workspace unsaved
- vJoy detected
- Output proof missing
- Capture backend unavailable
- Metadata-only artifact
- Read-only visualization
- Draft change staged

---

# 4. Design Laws

## Law 1: Data is not layout.

Existing data should not automatically determine visual structure.

## Law 2: Every page needs a dominant purpose.

Each page should answer one main question immediately.

## Law 3: Fewer containers, stronger hierarchy.

Avoid endless equal-weight cards.

## Law 4: Status is sacred.

Green, amber, red, and cyan must mean consistent things.

## Law 5: Advanced data is secondary.

Diagnostics should be available, but not visually dominant except on diagnostics pages.

## Law 6: Static first.

The static UI must be beautiful and stable before animation.

## Law 7: Motion serves meaning.

Animation must communicate state, relationship, change, or interaction.

## Law 8: Controls remain precise.

No effect may make tuning, mapping, or monitoring feel inaccurate.

## Law 9: Glass is more than blur.

Liquid Glass is built from layering, tint, edge light, shadow, highlights, grain, depth, and restrained glow.

## Law 10: No raccoon engineering.

If something looks cool but risks stability, readability, truth, or control precision, it waits.

---

# 5. Target Global Layout

The new app should be built around a command-deck shell.

## Primary Layout Regions

```text
┌───────────────────────────────────────────────────────────────┐
│ Top Command Bar                                                │
│ HelmForge | Workspace | Save State | Runtime Truth | Helm      │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Compact      ┌───────────────────────────────────────────┐   │
│  Glass        │ Page Hero / Primary Instrument            │   │
│  Mode Dock    │                                           │   │
│               └───────────────────────────────────────────┘   │
│                                                               │
│               ┌────────────────────┐ ┌────────────────────┐   │
│               │ Context Inspector  │ │ Actions / Details  │   │
│               └────────────────────┘ └────────────────────┘   │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│ Footer Action Strip: status note | Apply | Save | Revert      │
└───────────────────────────────────────────────────────────────┘
```

## Required Global Elements

1. Top command/status bar
2. Compact glass mode dock
3. Main workspace glass slab
4. Page hero / primary instrument region
5. Context inspector region
6. Secondary action/detail region
7. Footer action strip
8. Advanced diagnostics area where appropriate
9. Optional legacy fallback switch during migration

## Avoid

- full-height text sidebar as main nav
- old page card stacks
- dense scroll-first pages
- page-long settings forms
- giant debug grids
- copy-pasted old components
- everything having the same visual importance

---

# 6. Navigation Architecture

## Major Modes

The new app should use major operating modes rather than a long sidebar page list.

Recommended major modes:

1. Preflight
2. Mapping
3. Tuning
4. Analysis
5. Recorder
6. Support

## Subpage Structure

```text
Preflight
  - Command Readiness

Mapping
  - HOTAS Map
  - Route Details
  - Advanced Route Tables

Tuning
  - Base Tuning
  - Filtering
  - Combat Profile
  - Conditional Rules

Analysis
  - Effective Response Stack
  - Live Monitor

Recorder
  - Flight Recorder
  - Clip Library / Artifacts
  - Capture Backend Truth

Support
  - Help / Docs
  - Perf / Diagnostics
  - Setup / Runtime Check
```

## Compact Glass Dock

The main nav should be a compact icon dock.

It may be vertical or horizontal, but should feel like a mode selector, not a website sidebar.

Each mode should have:

- icon
- selected state
- hover label
- status accent if relevant
- tooltip
- keyboard navigability if practical

## Radial Command Wheel

The radial menu is a later enhancement, not first implementation.

It should be optional and used for quick switching only.

Possible trigger:

- click HelmForge orb
- Ctrl + Space
- long-click dock center

Do not implement radial navigation until the static command shell and dock are stable.

---

# 7. Liquid Glass Visual System

## Base Materials

Use a dark premium base:

- dark navy
- near-black blue
- deep slate
- subtle cyan/teal accents
- occasional violet/amber page accents

## Glass Panel Layers

Each major glass surface should feel layered using:

1. base tint
2. translucent fill
3. border highlight
4. inner shadow
5. top-edge shine
6. status rail when relevant
7. soft outer glow only for important states
8. subtle grain/texture if safe

## Status Colors

Use consistent meaning:

- Green: ready, verified, saved, safe
- Amber: attention, waiting, setup blocked, unsaved, missing proof
- Red: hard error, unsafe, failed
- Cyan/Blue: information, simulation, live neutral state
- White/Bright: primary text
- Muted blue-gray: secondary text

Avoid RGB soup. This is a command deck, not a haunted gaming keyboard.

## Page Accent Suggestions

- Preflight: amber/cyan
- Mapping: cyan/blue
- Base Tuning: blue/violet
- Filtering: teal/cyan
- Combat Profile: amber/red
- Conditional Rules: purple/amber
- Effective Response Stack: cyan/green
- Live Monitor: green/cyan
- Flight Recorder: red/amber
- Helm: teal/green
- Diagnostics: blue/gray

---

# 8. Shared Component System

Before rebuilding individual pages, create a reusable Liquid component layer.

## Component Categories

### 8.1 Command Shell Components

- LiquidCommandShell
- LiquidTopCommandBar
- LiquidModeDock
- LiquidModeButton
- LiquidWorkspaceFrame
- LiquidFooterActionStrip
- LiquidLegacyFallbackHost if needed

### 8.2 Page Layout Components

- LiquidPage
- LiquidPageHeader
- LiquidHeroPanel
- LiquidInstrumentPanel
- LiquidInspectorPanel
- LiquidDetailPanel
- LiquidAdvancedSection
- LiquidSplitPanel
- LiquidStatusRail

### 8.3 Status Components

- ReadinessGate
- StatusChip
- StatusLight
- MetricTile
- TruthBadge
- DraftStateIndicator
- TelemetryFreshnessRail

### 8.4 Data/Flow Components

- RouteFlowRow
- SignalPipelineStage
- ControlMarker
- AxisGauge
- AxisBarPair
- ButtonIlluminationGrid
- HatDirectionIndicator
- ChecklistPanel

### 8.5 Form/Inspector Components

- ParameterRow
- ParameterLabelWithInfo
- NumericParameterControl
- DropdownParameterControl
- AxisSelectorPills
- GuidanceBlock
- LiveSnapshotBlock

### 8.6 Overlay Components

- HelmAssistantDeck
- FloatingFlyout
- ModeSubpageFlyout
- GlassPopover
- TooltipPanel

---

# 9. Testing Philosophy

Every phase should include tests that prove:

- the new UI constructs offscreen
- runtime truth was not weakened
- pages use new Liquid components rather than wrapping old pages
- important text/status appears
- no forbidden runtime behavior was introduced
- no unsupported claims appear
- layout is smoke-testable
- component models are pure/testable where possible

## Required Common Test Types

1. Pure data/model tests
2. Widget construction tests with offscreen Qt
3. Page composition tests
4. Truth-boundary text tests
5. Regression tests for old runtime gates
6. Smoke launch test
7. Git diff hygiene check

## Common Verification Commands

Each Codex phase should normally run:

```powershell
python -m pytest
python -m pytest tests/<phase_test_file>.py
python -m pytest tests/test_phase19d_final_acceptance_report.py
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
python -m bridge_app.main --status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
git diff --check
```

If package output becomes stale:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean
.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250
```

If package is not rebuilt, the Codex report must say so. No fake packaged smoke. Fake smoke is how you get haunted toast.

---

# 10. Branch Strategy

Use a dedicated branch for each phase.

Suggested naming:

```text
lcd-0-prompt-book
lcd-1-static-shell
lcd-2-component-library
lcd-3-navigation-architecture
lcd-4-preflight-page
lcd-5-mapping-page
lcd-6-tuning-pages
lcd-7-analysis-pages
lcd-8-recorder-helm-pages
lcd-9-support-diagnostics
lcd-10-microinteractions
lcd-11-transitions-live-motion
lcd-12-atmosphere-qa-freeze
```

Merge one phase at a time.

Run tests after every merge.

## Conflict Magnets

Be careful with:

```text
README.md
v3_app/main.py
v3_app/ui/shell.py
v3_app/theme/qss.py
v3_app/pages/page_helpers.py
v3_app/pages/mapping_page.py
v3_app/pages/base_tuning_page.py
v3_app/pages/filtering_page.py
v3_app/pages/combat_profile_page.py
v3_app/pages/live_monitor_page.py
v3_app/pages/flight_recorder_page.py
v3_app/services/help_docs.py
```

The new UI track should preferably create new modules rather than heavily mutate old page modules in early phases.

---

# 11. Suggested New File Structure

Codex may adapt this if the repository architecture suggests a better fit.

```text
v3_app/liquid/
  __init__.py
  app_shell.py
  layout.py
  navigation.py
  theme_tokens.py
  glass.py
  components.py
  status_components.py
  flow_components.py
  parameter_controls.py
  instruments.py
  overlays.py
  motion.py
  reduced_motion.py

v3_app/liquid/pages/
  __init__.py
  preflight_command_page.py
  mapping_command_page.py
  tuning_command_pages.py
  analysis_command_pages.py
  recorder_command_page.py
  helm_command_deck.py
  support_command_pages.py

v3_app/liquid/models/
  __init__.py
  nav_model.py
  page_state.py
  readiness_model.py
  liquid_page_contracts.py

v3_app/liquid/tests_helpers/
  __init__.py
```

Alternative acceptable approach:

```text
v3_app/command_deck/
```

The exact folder name matters less than the architecture separation.

The key requirement is that the new UI must be visibly and architecturally separate from Legacy page repainting.

---

# 12. Implementation Phase Overview

## LCD-0 — Prompt Book / Ground Rules

Create and accept this implementation prompt book.

Deliverables:

- implementation strategy
- phase list
- Codex rules
- runtime truth boundaries
- branch strategy
- testing strategy
- acceptance criteria

No code required unless adding docs only.

---

## LCD-1 — Static Liquid Shell Foundation

Goal:

Build the new static Liquid Command Deck shell without rebuilding every page yet.

This is the first real code phase.

Includes:

- new Liquid app shell
- top command/status bar
- compact mode dock
- main workspace frame
- page host region
- footer action strip
- theme tokens
- static glass material styling
- placeholder pages for each major mode
- optional legacy fallback route

Does not include:

- animations
- radial menu
- real blur
- page-specific rebuilds
- runtime behavior changes

---

## LCD-2 — Shared Liquid Component Library

Goal:

Create reusable command-deck components so later pages are composed consistently.

Includes:

- glass panels
- hero panels
- inspector panels
- status chips
- readiness gates
- metric tiles
- route flow rows
- checklist panels
- advanced sections
- axis selectors
- parameter rows
- live snapshot blocks
- guidance blocks

Does not include:

- full page rebuilds
- live data animation
- old page restyling

---

## LCD-3 — Navigation and Mode Architecture

Goal:

Implement real mode/subpage navigation for the new Liquid UI.

Includes:

- major mode model
- subpage model
- compact dock behavior
- hover labels/flyouts if static/simple
- keyboard navigation if practical
- current page state
- selected mode/subpage persistence during session
- page title/subtitle routing

Does not include:

- radial wheel
- complex animations
- old sidebar reuse

---

## LCD-4 — Preflight Command Page

Goal:

Rebuild Preflight as the first fully composed Liquid page.

Question answered:

```text
Can I safely use live output right now?
```

Includes:

- go/no-go hero
- readiness gates
- next-action checklist
- compact system map
- runtime truth details
- advanced diagnostics section
- simulation/missing/stale/verified states

Does not include:

- changing runtime proof logic
- changing Bridge lifecycle behavior
- faking output verification

---

## LCD-5 — Mapping Command Page

Goal:

Rebuild Mapping around a physical/control-flow visual experience.

Question answered:

```text
What is each physical control doing?
```

Includes:

- HOTAS visual map hero
- control markers
- selected control inspector
- route flow summary
- output intent display
- compact metrics
- advanced route table section

Does not include in first mapping pass:

- complex interactive remapping unless already safely implemented
- hardware polling
- vJoy write changes
- output verification changes

---

## LCD-6 — Tuning Command Pages

Goal:

Rebuild Base Tuning, Filtering, Combat Profile, and Conditional Rules as instrument-style pages.

Question answered:

```text
How does this axis respond and feel?
```

Includes:

- response graph hero
- selected axis pills
- parameter inspector
- metadata/info icons
- dropdowns where appropriate
- numeric validation where appropriate
- live snapshot block
- structured guidance block
- advanced details section

Does not include:

- runtime behavior changes
- new curve math unless explicitly scoped
- unstable graph animations

---

## LCD-7 — Analysis Pages

Goal:

Rebuild Effective Response Stack and Live Monitor.

Questions answered:

```text
How does raw input become final output?
What is the HOTAS doing right now?
```

Includes:

- signal pipeline layout
- raw → tuned → filtered → ruled → final flow
- live axis gauges/meters
- raw vs final paired bars
- button illumination grid
- hat indicator
- telemetry freshness rail
- stale telemetry behavior
- advanced raw telemetry section

Does not include:

- changing polling
- hiding latency problems
- pretending stale values are live

---

## LCD-8 — Recorder and Helm Command Pages

Goal:

Rebuild Flight Recorder and Helm into command-deck tools.

Recorder answers:

```text
What can I capture, buffer, and review?
```

Helm answers:

```text
What is wrong, what would improve it, and what can I safely apply?
```

Includes:

- recorder status hero
- backend capability truth rail
- capture/buffer/encoding state display
- metadata-only vs real recording clarity
- clip/artifact panel
- Helm assistant deck
- findings cards
- proposed change cards
- apply/revert review
- evidence/confidence display

Does not include:

- fake capture claims
- fake video encoding
- cloud AI behavior
- unsafe auto-apply

---

## LCD-9 — Support, Help, and Diagnostics

Goal:

Rebuild Help / Docs and Perf / Diagnostics in the new design language.

Includes:

- topic cards
- parameter help modules
- page-specific help
- setup guide links
- diagnostic status banner
- Bridge/device/vJoy diagnostics
- raw/internal values where appropriate
- copy/export actions if existing support allows

Diagnostics is one of the few places where raw detail is allowed, but it should still look intentional.

---

## LCD-10 — Microinteractions

Goal:

Add safe, meaningful UI responsiveness after static geometry is stable.

Includes:

- button hover/press states
- card hover/focus states
- status chip transitions
- status light pulses
- saved/unsaved pulse
- selected card rim light
- subtle focus rings

Avoid:

- layout geometry animation
- full-page opacity effects on large containers
- real blur
- continuous animation on many widgets

---

## LCD-11 — Page Transitions and Live Data Motion

Goal:

Add motion that communicates navigation and live data changes.

Includes:

- page fade/slide
- panel stagger
- graph marker easing
- axis meter easing
- route trace animation
- telemetry pulse
- stale data dim/freeze behavior
- recorder timeline sweep if recorder state supports it

Avoid:

- rebuilding graphs every heartbeat
- delaying live truth
- animating form fields while typing
- animating large scroll layouts continuously

---

## LCD-12 — Atmosphere, Radial Menu, Accessibility, QA Freeze

Goal:

Add late-stage polish and freeze the RC.

Includes:

- subtle background drift
- cursor-following glare if safe
- soft parallax if safe
- glass shimmer if safe
- optional radial command wheel
- motion intensity setting
- reduced motion mode
- performance pass
- visual QA checklist
- packaged smoke
- final docs
- RC freeze report

---

# 13. Codex Prompt Template

Use this template at the top of every phase-specific Codex prompt.

```text
Implement LCD-<PHASE> only: <PHASE NAME>.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Do not wrap, reskin, or cosmetically patch the existing Legacy UI. Build a new Liquid Glass Command Deck interface from first principles, using existing non-visual services, workspace/runtime data, and truth boundaries only where they are useful. Legacy pages are reference/fallback, not the design source.

Before editing:
- run git status --short
- inspect the relevant existing modules
- identify reusable non-visual services/models
- avoid touching unrelated files
- avoid modifying unrelated untracked documents

Do not implement adjacent LCD phases.
Do not change runtime authority.
Do not change hardware polling.
Do not change vJoy write behavior.
Do not change output verification logic.
Do not change Full Live Runtime Ready logic.
Do not add Bridge lifecycle management.
Do not claim real recording/capture/encoding unless actually implemented and verified.
Do not add game injection or graphics API hooking.
Do not add cloud AI/LLM behavior.
Do not add auto-save.

At the end:
- report files changed
- report tests run
- report likely merge conflicts
- report what was intentionally deferred
- run git diff --check
```

---

# 14. LCD-1 Prompt — Static Liquid Shell Foundation

## Branch

```text
lcd-1-static-liquid-shell
```

## Prompt

```text
Implement LCD-1 only: Static Liquid Shell Foundation.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Do not wrap, reskin, or cosmetically patch the existing Legacy UI. Build a new Liquid Glass Command Deck interface from first principles, using existing non-visual services, workspace/runtime data, and truth boundaries only where they are useful. Legacy pages are reference/fallback, not the design source.

Context:
HelmForge currently has a functional Legacy UI and post-RC refinement work, but the new direction is Liquid Glass Command Deck. The purpose of this phase is to create the new static shell and prove that the app can host the new UI architecture without breaking runtime truth.

Goal:
Create a new static Liquid Command Deck shell with top command/status bar, compact mode dock, main workspace frame, page host region, footer action strip, and placeholder mode pages.

Must not implement:
- page-specific full rebuilds
- old page repainting
- animations
- radial command wheel
- real blur/distortion
- hardware polling changes
- vJoy/output behavior changes
- output verification changes
- Bridge lifecycle management
- recorder capture/encoding
- cloud AI/LLM behavior
- auto-save

Requirements:

1. Add new Liquid UI module structure.

Suggested structure:
- v3_app/liquid/__init__.py
- v3_app/liquid/app_shell.py
- v3_app/liquid/navigation.py
- v3_app/liquid/layout.py
- v3_app/liquid/theme_tokens.py
- v3_app/liquid/glass.py
- v3_app/liquid/pages/__init__.py
- v3_app/liquid/pages/placeholder_pages.py

The exact structure may be adjusted if the repository architecture strongly suggests a better option, but the new Liquid UI must be architecturally separate from Legacy page repainting.

2. Create LiquidCommandShell.

The shell should include:
- top command/status bar
- compact mode dock
- central page host
- footer action strip
- static background/frame styling

The shell must not copy the existing sidebar layout.

3. Create top command/status bar.

It should display, using existing data if available or safe placeholders if not wired yet:
- HelmForge title
- workspace name or workspace state
- saved/unsaved state
- runtime truth chip
- telemetry/source chip if available
- Helm entry/action location

Do not claim live readiness unless existing truth data supports it.

4. Create compact glass mode dock.

Major modes:
- Preflight
- Mapping
- Tuning
- Analysis
- Recorder
- Support

The dock should be compact and visually distinct from a giant sidebar.

In LCD-1, simple buttons are acceptable if styled as dock controls.

5. Create page host region.

The page host should show placeholder Liquid pages for each major mode.

Each placeholder should include:
- page title
- one-sentence purpose
- clear indication that the page is a Liquid Command Deck placeholder
- no fake runtime claims

6. Create footer action strip.

The footer should include:
- concise status message
- Apply/Save/Revert action placeholders if appropriate
- disabled states where actions are not wired

7. Static Liquid Glass theme.

Add theme tokens or helper classes for:
- dark base
- glass panel fill
- border highlight
- muted text
- primary text
- status green/amber/red/cyan
- shadows/glows where possible using safe static styling

No animation yet.
No real blur yet.

8. Integration path.

Add a safe way to launch or select the Liquid shell.

Acceptable options:
- default to Liquid shell if this is the intended new app direction
- add environment/config switch for Legacy fallback
- keep Legacy shell importable while Liquid is developed

Do not delete Legacy UI in LCD-1 unless the project owner explicitly approves later.

9. Tests.

Add focused tests, for example:
- tests/test_lcd_1_static_liquid_shell.py

Coverage should include:
- LiquidCommandShell constructs offscreen
- mode dock contains required modes
- top command/status bar exists
- footer action strip exists
- placeholder pages exist
- shell does not instantiate old page stack as the primary layout
- no runtime authority was introduced
- forbidden readiness/recording/output claims are absent

10. Documentation.

Add:
- docs/HelmForge/lcd-1-static-liquid-shell-report.md

Report must include:
- new module structure
- shell architecture
- how Legacy fallback/reference is preserved
- which backend/data surfaces are reused
- what remains for LCD-2
- runtime truth preservation statement

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_1_static_liquid_shell.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- python -m bridge_app.main --status
- powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
- git diff --check

Deliverables:
- new Liquid shell module
- static top command/status bar
- compact mode dock
- page host with placeholders
- footer action strip
- safe integration path
- tests
- LCD-1 report
- final summary
```

---

# 15. LCD-2 Prompt — Shared Liquid Component Library

## Branch

```text
lcd-2-liquid-component-library
```

## Prompt

```text
Implement LCD-2 only: Shared Liquid Component Library.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Do not wrap, reskin, or cosmetically patch the existing Legacy UI. Build a new Liquid Glass Command Deck interface from first principles, using existing non-visual services, workspace/runtime data, and truth boundaries only where they are useful. Legacy pages are reference/fallback, not the design source.

Context:
LCD-1 created the static Liquid shell. LCD-2 builds reusable components so page rebuilds do not become inconsistent hand-built widget chaos.

Goal:
Create reusable Liquid Glass components for page composition, status truth, flow visualization, form/parameter inspection, and advanced details.

Must not implement:
- full page rebuilds
- animations
- radial menu
- runtime behavior changes
- recorder capture/encoding
- hardware/vJoy/output changes

Requirements:

1. Add component modules.

Suggested files:
- v3_app/liquid/components.py
- v3_app/liquid/status_components.py
- v3_app/liquid/flow_components.py
- v3_app/liquid/parameter_controls.py
- v3_app/liquid/instruments.py

2. Implement layout components.

Create reusable widgets/classes/helpers for:
- LiquidPage
- LiquidPageHeader
- LiquidHeroPanel
- LiquidInstrumentPanel
- LiquidInspectorPanel
- LiquidDetailPanel
- LiquidAdvancedSection
- LiquidSplitPanel
- LiquidStatusRail

3. Implement status components.

Create:
- StatusChip
- TruthBadge
- ReadinessGate
- MetricTile
- DraftStateIndicator
- TelemetryFreshnessRail

Each should support state types:
- ready/verified/saved/safe
- waiting/blocked/attention/unsaved
- error/unsafe/failed
- info/simulation/live-neutral
- disabled/unavailable

4. Implement flow components.

Create:
- RouteFlowRow
- SignalPipelineStage
- ChecklistPanel

These should support concise flow language like:
- Physical Stick X → Roll → Output Intent: vJoy X
- Raw Input → Base Tuning → Filtering → Final Output

5. Implement parameter/inspector components.

Create:
- ParameterRow
- ParameterLabelWithInfo
- NumericParameterControl
- DropdownParameterControl
- AxisSelectorPills
- GuidanceBlock
- LiveSnapshotBlock

If parameter metadata exists, integrate lightly with it. If not, keep interfaces metadata-ready without creating a competing registry.

6. Implement safe styling.

All components should use static Liquid Glass styling:
- dark glass fill
- subtle border
- edge highlight
- readable text
- status color rails
- safe disabled states

No animation yet.
No real blur.

7. Update LCD placeholder pages to demonstrate components.

Use representative components on placeholders, but do not rebuild real pages yet.

8. Tests.

Add:
- tests/test_lcd_2_liquid_component_library.py

Coverage:
- each major component constructs offscreen
- status components display correct state text/color role
- flow rows preserve output intent wording
- readiness gates do not imply output verification
- parameter controls reject unsupported dropdown values where applicable
- no old Legacy page wrapping is introduced

9. Documentation.

Add:
- docs/HelmForge/lcd-2-liquid-component-library-report.md

Report:
- components added
- intended use
- metadata integration status
- deferred animation/effects
- runtime truth preservation

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_2_liquid_component_library.py
- python -m pytest tests/test_lcd_1_static_liquid_shell.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- git diff --check
```

---

# 16. LCD-3 Prompt — Navigation and Mode Architecture

## Branch

```text
lcd-3-navigation-mode-architecture
```

## Prompt

```text
Implement LCD-3 only: Navigation and Mode Architecture.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Do not wrap, reskin, or cosmetically patch the existing Legacy UI. Build a new Liquid Glass Command Deck interface from first principles, using existing non-visual services, workspace/runtime data, and truth boundaries only where they are useful. Legacy pages are reference/fallback, not the design source.

Context:
LCD-1 created the static shell. LCD-2 created reusable Liquid components. LCD-3 turns the shell into a real mode/subpage navigation architecture.

Goal:
Implement major modes, subpage routing, dock selection state, and page host switching for the Liquid Command Deck.

Major modes:
- Preflight
- Mapping
- Tuning
- Analysis
- Recorder
- Support

Subpages:
- Preflight: Command Readiness
- Mapping: HOTAS Map, Route Details, Advanced Route Tables
- Tuning: Base Tuning, Filtering, Combat Profile, Conditional Rules
- Analysis: Effective Response Stack, Live Monitor
- Recorder: Flight Recorder, Clip Library, Capture Backend Truth
- Support: Help / Docs, Perf / Diagnostics, Setup / Runtime Check

Must not implement:
- radial command wheel
- animated transitions
- full page rebuilds
- Legacy sidebar reuse
- runtime behavior changes

Requirements:

1. Add navigation model.

Suggested:
- v3_app/liquid/models/nav_model.py

Each mode should include:
- mode_id
- display_name
- icon/glyph
- short_description
- accent_role
- subpages
- default_subpage

Each subpage should include:
- subpage_id
- display_name
- purpose/question
- route key
- availability state if useful

2. Implement dock selection.

The compact dock should:
- show major modes
- visually highlight selected mode
- update page host
- show hover tooltip/label if practical
- expose accessible names where practical

3. Implement subpage selector.

Use one of:
- top segmented selector
- compact chips near page header
- simple glass flyout without animation

Avoid giant sidebars.

4. Implement page host routing.

The Liquid shell should switch between placeholder/new Liquid pages based on selected route.

5. Preserve session state.

The selected mode/subpage should remain stable during the session.

6. Tests.

Add:
- tests/test_lcd_3_navigation_mode_architecture.py

Coverage:
- required modes exist
- required subpages exist
- default subpage per mode exists
- dock selection changes current mode
- subpage selection changes route
- page host updates without Legacy sidebar
- no radial menu/animation introduced
- no runtime authority changed

7. Documentation.

Add:
- docs/HelmForge/lcd-3-navigation-mode-architecture-report.md

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_3_navigation_mode_architecture.py
- python -m pytest tests/test_lcd_1_static_liquid_shell.py tests/test_lcd_2_liquid_component_library.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- git diff --check
```

---

# 17. LCD-4 Prompt — Preflight Command Page

## Branch

```text
lcd-4-preflight-command-page
```

## Prompt

```text
Implement LCD-4 only: Preflight Command Page.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Do not wrap, reskin, or cosmetically patch the existing Legacy UI. Build a new Liquid Glass Command Deck interface from first principles, using existing non-visual services, workspace/runtime data, and truth boundaries only where they are useful. Legacy pages are reference/fallback, not the design source.

Context:
LCD-1 through LCD-3 created the shell, components, and navigation architecture. LCD-4 replaces the Preflight placeholder with a real Liquid Command Deck page.

Main question:
Can I safely use live output right now?

Goal:
Build a new Preflight page centered on go/no-go truth, readiness gates, next actions, and compact system details.

Must not implement:
- runtime proof logic changes
- Bridge lifecycle changes
- hardware polling changes
- vJoy/output behavior changes
- output verification changes
- fake readiness claims

Requirements:

1. Build new Preflight Liquid page.

Suggested:
- v3_app/liquid/pages/preflight_command_page.py

Do not wrap the old Preflight page.

2. Hero go/no-go panel.

The hero should show:
- overall readiness state
- short explanation
- next recommended action
- primary safe actions if existing commands support them

State examples:
- Ready for live output
- HOTAS not connected
- Telemetry missing
- Telemetry stale
- Output proof missing
- Workspace unsaved
- Simulation mode
- Hard error

Use actual existing truth data where available.

3. Readiness gates.

Create gates for:
- Input
- Telemetry
- Workspace
- vJoy
- Output Proof
- Safety

Each gate should show:
- label
- state
- short reason
- status color role

4. System map/details.

Compact details:
- device/HOTAS state
- driver state if available
- vJoy state
- Bridge telemetry state
- workspace state
- output proof state

5. Next-actions checklist.

Show actionable steps such as:
- Connect HOTAS controller
- Start or check Bridge if applicable
- Run preflight check if existing action exists
- Confirm live input sample if supported
- Save workspace

Use disabled/unavailable states honestly.

6. Advanced diagnostics.

Put raw details in an advanced/collapsible or visually secondary section.

7. Tests.

Add:
- tests/test_lcd_4_preflight_command_page.py

Coverage:
- Preflight page constructs offscreen
- hero exists
- readiness gates exist
- missing HOTAS state does not claim live readiness
- vJoy detected does not claim output verification
- output proof missing is distinct from vJoy detected
- advanced diagnostics are secondary/available
- old Preflight page is not wrapped as the main composition

8. Documentation.

Add:
- docs/HelmForge/lcd-4-preflight-command-page-report.md

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_4_preflight_command_page.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- python -m bridge_app.main --status
- powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
- git diff --check
```

---

# 18. LCD-5 Prompt — Mapping Command Page

## Branch

```text
lcd-5-mapping-command-page
```

## Prompt

```text
Implement LCD-5 only: Mapping Command Page.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Do not wrap, reskin, or cosmetically patch the existing Legacy UI. Build a new Liquid Glass Command Deck interface from first principles, using existing non-visual services, workspace/runtime data, and truth boundaries only where they are useful. Legacy pages are reference/fallback, not the design source.

Main question:
What is each physical control doing?

Goal:
Build a new Mapping page where the HOTAS visual map and route flow are the main experience, not a dense table stack.

Must not implement:
- hardware polling changes
- vJoy/output behavior changes
- output verification changes
- fake live claims
- complex remapping overlay unless already safely supported

Requirements:

1. Build new Mapping Liquid page.

Suggested:
- v3_app/liquid/pages/mapping_command_page.py

Do not wrap the old Mapping page.

2. HOTAS visual map hero.

Use existing HOTAS diagram model/widget if present. If not present, create a stylized static schematic.

The hero should show:
- stick side
- throttle side
- axis markers
- button markers
- hat/POV marker
- selected marker state if practical
- mapping summary labels

3. Selected control inspector.

Show:
- physical control label
- raw channel
- logical function
- output intent target
- current value/state if available
- status/warning if unmapped/unavailable

4. Route flow panel.

Use route flow language:

```text
Physical Stick X → Roll → Output Intent: vJoy X Axis
```

Do not say output write verified unless true.

5. Mapping metrics.

Compact metric tiles:
- axis routes
- button routes
- hat routes
- unmapped controls
- warnings if applicable

6. Advanced route tables.

Move dense tables to advanced/details section.

7. Tests.

Add:
- tests/test_lcd_5_mapping_command_page.py

Coverage:
- Mapping page constructs offscreen
- HOTAS visual hero exists
- required controls appear or are represented
- route flow uses output intent wording
- selected inspector exists
- advanced route details exist
- page does not wrap old Mapping layout as primary composition
- no output verification claim introduced

8. Documentation.

Add:
- docs/HelmForge/lcd-5-mapping-command-page-report.md

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_5_mapping_command_page.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- git diff --check
```

---

# 19. LCD-6 Prompt — Tuning Command Pages

## Branch

```text
lcd-6-tuning-command-pages
```

## Prompt

```text
Implement LCD-6 only: Tuning Command Pages.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Do not wrap, reskin, or cosmetically patch the existing Legacy UI. Build a new Liquid Glass Command Deck interface from first principles, using existing non-visual services, workspace/runtime data, and truth boundaries only where they are useful. Legacy pages are reference/fallback, not the design source.

Main question:
How does this axis respond and feel?

Goal:
Build new Liquid pages for Base Tuning, Filtering, Combat Profile, and Conditional Rules using instrument-style page composition.

Must not implement:
- new tuning math unless explicitly required
- hardware polling changes
- vJoy/output behavior changes
- output verification changes
- unstable graph animation
- fake live claims

Requirements:

1. Build new tuning pages.

Suggested:
- v3_app/liquid/pages/tuning_command_pages.py

Do not wrap old tuning pages as primary composition.

2. Shared page structure.

Each tuning page should use:
- page hero response/instrument area
- selected axis selector
- parameter inspector
- live snapshot block
- structured guidance block
- advanced details section

3. Axis selector.

Selectable axes:
- Roll
- Pitch
- Throttle
- Yaw
- Aux 1
- Aux 2

Selecting an axis should update:
- graph/preview
- parameters
- live snapshot
- guidance

4. Base Tuning page.

Hero:
- response curve preview
- current raw/reference marker if available
- current adjusted/output marker if available

Inspector:
- Curve Mode
- Curve Strength
- Deadzone
- Anti-Deadzone
- Hysteresis
- Output Scale
- Max Output

5. Filtering page.

Hero:
- filtering response preview or signal smoothing instrument

Inspector:
- Center Alpha
- Edge Alpha
- Same Slew Limit
- Reverse Slew Limit

6. Combat Profile page.

Hero:
- combat response preview
- live indicators for relevant lines if safely supported

Inspector:
- Combat Curve
- Combat Scale
- Combat Center Alpha
- Combat Edge Alpha
- Combat Same Slew
- Combat Reverse Slew

7. Conditional Rules page.

Use:
- rule status hero
- enabled/disabled metrics
- condition → action flow rows
- conflict/warning checklist
- advanced rule details

8. Parameter controls.

Use metadata/info icon system if present.

Enum-like parameters should be dropdowns.
Numeric parameters should have validators/caps if metadata exists.

Do not create a competing metadata registry.

9. Guidance blocks.

Each page should show structured guidance:
- Current feel
- What this setting affects
- Suggested range
- Caution/warning
- Selected axis note

10. Tests.

Add:
- tests/test_lcd_6_tuning_command_pages.py

Coverage:
- each tuning page constructs offscreen
- axis selector contains required axes
- selecting axis updates selected-axis state
- enum controls use dropdowns where supported
- numeric controls have validators where metadata exists
- live snapshot block exists
- guidance block contains structured sections
- old tuning pages are not wrapped as primary composition
- no runtime authority changed

11. Documentation.

Add:
- docs/HelmForge/lcd-6-tuning-command-pages-report.md

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_6_tuning_command_pages.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- git diff --check
```

---

# 20. LCD-7 Prompt — Analysis Pages

## Branch

```text
lcd-7-analysis-command-pages
```

## Prompt

```text
Implement LCD-7 only: Analysis Command Pages.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Do not wrap, reskin, or cosmetically patch the existing Legacy UI. Build a new Liquid Glass Command Deck interface from first principles, using existing non-visual services, workspace/runtime data, and truth boundaries only where they are useful. Legacy pages are reference/fallback, not the design source.

Main questions:
- How does raw input become final output?
- What is the HOTAS doing right now?

Goal:
Build new Liquid pages for Effective Response Stack and Live Monitor.

Must not implement:
- hardware polling changes
- vJoy/output behavior changes
- output verification changes
- fake live claims
- hiding stale telemetry

Requirements:

1. Build new Analysis pages.

Suggested:
- v3_app/liquid/pages/analysis_command_pages.py

2. Effective Response Stack page.

Use pipeline layout:

```text
Raw Input → Base Tuning → Filtering → Modes → Rules → Final Output
```

Each stage should show:
- stage name
- current selected axis value/status
- transform summary
- warnings if any
- output intent where relevant

3. Live Monitor page.

Use instrument panel layout:
- axis gauges/meters
- raw vs final paired bars
- button illuminated grid
- hat direction indicator
- telemetry freshness/status rail
- live/simulated/stale truth chip

4. Stale telemetry behavior.

If telemetry is stale:
- panels should clearly show stale state
- values may remain visible but must be marked not live
- no live animation claims

5. Advanced telemetry.

Raw telemetry details may appear in advanced section.

6. Tests.

Add:
- tests/test_lcd_7_analysis_command_pages.py

Coverage:
- Effective Response Stack page constructs
- pipeline stages exist
- Live Monitor page constructs
- axis/button/hat instruments exist
- stale telemetry is marked stale
- simulated state is marked simulation
- no output verification claim is introduced
- old pages are not wrapped as primary composition

7. Documentation.

Add:
- docs/HelmForge/lcd-7-analysis-command-pages-report.md

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_7_analysis_command_pages.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- git diff --check
```

---

# 21. LCD-8 Prompt — Recorder and Helm Command Pages

## Branch

```text
lcd-8-recorder-helm-command-pages
```

## Prompt

```text
Implement LCD-8 only: Recorder and Helm Command Pages.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Do not wrap, reskin, or cosmetically patch the existing Legacy UI. Build a new Liquid Glass Command Deck interface from first principles, using existing non-visual services, workspace/runtime data, and truth boundaries only where they are useful. Legacy pages are reference/fallback, not the design source.

Main questions:
- What can I capture, buffer, and review?
- What is wrong, what would improve it, and what can I safely apply?

Goal:
Build new Liquid pages/surfaces for Flight Recorder and Helm Assistant.

Must not implement:
- fake recorder capture
- fake encoding
- fake playable clips
- cloud AI/LLM behavior
- unsafe auto-apply
- runtime authority changes

Requirements:

1. Flight Recorder Liquid page.

Build:
- recorder status hero
- backend capability rail
- capture/buffer/encoding truth panel
- capture settings inspector
- clip/artifact panel
- advanced backend details

Truth must distinguish:
- simulated metadata artifacts
- real capture unavailable
- backend candidate unavailable
- frame capture available only if actually available
- video encoding unavailable unless implemented
- hindsight video unavailable unless implemented

2. Helm Assistant Liquid deck.

Build:
- assistant status hero/deck
- problem/symptom input area if existing logic supports it
- findings grouped by evidence
- proposed changes as cards
- apply selected/revert actions using existing safe draft semantics
- confidence/evidence notes

Do not turn Helm into a debug text wall.

3. Tests.

Add:
- tests/test_lcd_8_recorder_helm_command_pages.py

Coverage:
- Recorder page constructs
- recorder truth states are explicit
- metadata-only artifacts are not called recordings
- Record Now remains disabled/unavailable unless backend supports real capture
- Helm deck constructs
- Helm proposed changes are staged/draft only
- no cloud AI behavior added
- old pages are not wrapped as primary composition

4. Documentation.

Add:
- docs/HelmForge/lcd-8-recorder-helm-command-pages-report.md

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_8_recorder_helm_command_pages.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- git diff --check
```

---

# 22. LCD-9 Prompt — Support, Help, and Diagnostics

## Branch

```text
lcd-9-support-help-diagnostics
```

## Prompt

```text
Implement LCD-9 only: Support, Help, and Diagnostics.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Do not wrap, reskin, or cosmetically patch the existing Legacy UI. Build a new Liquid Glass Command Deck interface from first principles, using existing non-visual services, workspace/runtime data, and truth boundaries only where they are useful. Legacy pages are reference/fallback, not the design source.

Goal:
Build new Liquid Support pages for Help / Docs, Perf / Diagnostics, and Setup / Runtime Check.

Requirements:

1. Help / Docs page.

Use:
- topic cards
- parameter help modules
- page-specific guidance
- examples
- navigation links to related Liquid pages where supported

If parameter metadata exists, use it as source of truth.

2. Perf / Diagnostics page.

Use:
- diagnostic status banner
- grouped tiles
- Bridge/device/vJoy diagnostics
- environment/runtime info
- raw/internal values in intentional advanced sections
- copy/export actions only if existing support exists

3. Setup / Runtime Check page.

If existing runtime setup check output can be surfaced safely, show:
- driver state
- vJoy state
- device state
- Bridge state
- warnings
- next action checklist

Do not add installer launch behavior unless already supported and safe.

4. Tests.

Add:
- tests/test_lcd_9_support_help_diagnostics.py

Coverage:
- Help page constructs
- diagnostics page constructs
- setup/runtime page constructs
- parameter metadata appears if available
- raw diagnostics are allowed only in diagnostics/advanced context
- no runtime behavior changed
- old pages are not wrapped as primary composition

5. Documentation.

Add:
- docs/HelmForge/lcd-9-support-help-diagnostics-report.md

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_9_support_help_diagnostics.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- git diff --check
```

---

# 23. LCD-10 Prompt — Microinteractions

## Branch

```text
lcd-10-microinteractions
```

## Prompt

```text
Implement LCD-10 only: Microinteractions.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Context:
The static Liquid UI pages should already be stable. LCD-10 adds safe, subtle interaction feedback.

Goal:
Add microinteractions that improve responsiveness without causing layout instability.

Must not implement:
- full page transitions
- radial menu
- real blur
- animated layout geometry
- continuous animation on many widgets
- runtime behavior changes

Requirements:

1. Add motion settings foundation.

Create a simple motion intensity concept if not already present:
- Off
- Reduced
- Standard
- Cinematic placeholder/future

LCD-10 should default to Standard but respect Off/Reduced if implemented.

2. Button interactions.

Add safe hover/pressed/checked/disabled feedback:
- primary actions
- secondary actions
- caution actions

3. Card hover/focus.

Add subtle static or timer-light hover/focus effects:
- border brightening
- status rail emphasis
- selected rim state

4. Status chips/lights.

Add safe status pulse only for small indicators:
- live telemetry
- unsaved draft
- verified state bloom if safe

Do not animate large containers.

5. Save/unsaved state.

Add subtle draft pulse or state emphasis to:
- Save chip
- footer strip
- changed parameter cards if safely identifiable

6. Tests.

Add:
- tests/test_lcd_10_microinteractions.py

Coverage:
- motion settings exist
- Off/Reduced can disable or reduce optional animations
- buttons retain disabled behavior
- status components construct with microinteraction hooks
- no QGraphicsBlurEffect on large containers
- no QPropertyAnimation on complex layout geometry
- no runtime authority changed

7. Documentation.

Add:
- docs/HelmForge/lcd-10-microinteractions-report.md

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_10_microinteractions.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- git diff --check
```

---

# 24. LCD-11 Prompt — Page Transitions and Live Data Motion

## Branch

```text
lcd-11-page-transitions-live-motion
```

## Prompt

```text
Implement LCD-11 only: Page Transitions and Live Data Motion.

You are working on the HelmForge Liquid Command Deck UI redo.

This is a full UI recomposition, not a repaint of the existing app.

Context:
Static layout and microinteractions should already be stable. LCD-11 adds larger motion only where it communicates navigation or live data state.

Goal:
Add page transitions and live data easing without layout instability or truth distortion.

Must not implement:
- radial command wheel
- real blur/distortion
- background drift
- game injection
- hardware polling changes
- delayed/fake telemetry
- graph rebuild loops

Requirements:

1. Page transitions.

Add safe page switching transition:
- old page slight fade/slide out
- new page slight fade/slide in
- optional panel stagger if safe

Timing target:
- 180–260 ms total

Respect motion Off/Reduced.

2. Live data easing.

Where applicable:
- axis bars ease smoothly
- graph dots ease smoothly
- hat indicator updates clearly
- button states illuminate quickly

Live data easing must not hide stale data or create artificial lag.

3. Route trace.

If Mapping/Response Stack supports selected routes, add optional route trace animation.

Only in Standard/Cinematic motion.

4. Stale telemetry behavior.

When telemetry becomes stale:
- stop live motion
- dim/frost affected panels if safe
- show stale state clearly

5. Tests.

Add:
- tests/test_lcd_11_page_transitions_live_motion.py

Coverage:
- motion Off disables page animations
- Reduced minimizes animations
- page transitions do not mutate complex layout geometry unsafely
- live markers update without recreating graph widgets if testable
- stale telemetry stops live-style motion
- no runtime authority changed

6. Documentation.

Add:
- docs/HelmForge/lcd-11-page-transitions-live-motion-report.md

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_11_page_transitions_live_motion.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- git diff --check
```

---

# 25. LCD-12 Prompt — Atmosphere, Radial Menu, Accessibility, QA Freeze

## Branch

```text
lcd-12-atmosphere-radial-qa-freeze
```

## Prompt

```text
Implement LCD-12 only: Atmosphere, Radial Menu, Accessibility, and QA Freeze.

You are working on the HelmForge Liquid Command Deck UI redo.

This is the final polish/freeze phase for the Liquid Command Deck track.

Goal:
Add optional late-stage atmosphere, optional radial command wheel, reduced-motion accessibility, performance QA, and final RC freeze documentation.

Must not implement:
- risky full-app blur
- broad layout mutation
- continuous heavy animation everywhere
- runtime behavior changes
- unsupported recording/output claims

Requirements:

1. Atmosphere effects.

Add only if safe:
- subtle background gradient drift
- soft page accent glow
- static/noise texture if readable
- cursor-following glare only on limited surfaces
- optional shimmer only for small/important panels

Must respect motion Off/Reduced.

2. Radial command wheel.

Implement optional radial quick switch only if static navigation is stable.

Trigger options:
- HelmForge orb click
- keyboard shortcut such as Ctrl+Space if existing shortcut handling supports it

Wheel should include major modes only:
- Preflight
- Mapping
- Tuning
- Analysis
- Recorder
- Support

Second-level subpage selection may be deferred if risky.

3. Accessibility/reduced motion.

Ensure:
- Motion Off works
- Reduced Motion works
- essential status is visible without color alone where practical
- text remains readable
- keyboard focus remains usable where practical

4. Performance QA.

Check:
- app smoke startup
- page switching
- Live Monitor responsiveness
- no major continuous CPU drain from passive effects
- no layout freezes
- no large-container blur regressions

5. Final visual QA checklist.

Create a checklist covering:
- no Legacy repaint pages remain as primary Liquid pages
- top command bar clarity
- dock clarity
- page hero clarity
- readiness truth
- simulation truth
- output proof truth
- recorder truth
- Help/Diagnostics clarity
- reduced motion

6. Tests.

Add:
- tests/test_lcd_12_atmosphere_radial_qa_freeze.py

Coverage:
- atmospheric effects respect Off/Reduced
- radial menu can be disabled
- radial menu lists major modes if enabled
- no risky blur on full app/root container
- no unsupported readiness/recording/output claims
- shell still constructs offscreen

7. Documentation.

Add:
- docs/HelmForge/lcd-12-atmosphere-radial-qa-freeze-report.md
- docs/HelmForge/liquid-command-deck-final-qa-checklist.md

Verification:
- python -m pytest
- python -m pytest tests/test_lcd_12_atmosphere_radial_qa_freeze.py
- python -m pytest tests/test_phase19d_final_acceptance_report.py
- $env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
- python -m bridge_app.main --status
- powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
- powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean
- .\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250
- git diff --check
```

---

# 26. Acceptance Criteria for the Whole LCD Track

The Liquid Command Deck track is accepted only when:

1. The primary app experience is a new Liquid Command Deck UI, not a restyled Legacy shell.
2. The current giant sidebar is replaced by a compact command dock or equivalent mode selector.
3. Each major page has a dominant hero/purpose area.
4. Status truth is clearer than in Legacy.
5. Advanced diagnostics are visually secondary except in Diagnostics.
6. Mapping is visual and flow-based.
7. Tuning pages feel like instruments, not forms.
8. Live Monitor feels like an instrument panel.
9. Flight Recorder truth is explicit and honest.
10. Helm feels like a guided command assistant, not a debug report.
11. Motion can be disabled/reduced.
12. No runtime truth boundaries are weakened.
13. No fake output verification is introduced.
14. No fake recorder capture/encoding is introduced.
15. Full test suite passes.
16. App smoke test passes.
17. Packaged smoke test passes before RC freeze.
18. Documentation explains what was rebuilt and what was preserved.

---

# 27. Final Implementation Guidance

Build the spaceship in this order:

```text
1. Shell
2. Components
3. Navigation
4. Preflight truth
5. Mapping visualization
6. Tuning instruments
7. Analysis instruments
8. Recorder and Helm
9. Support and diagnostics
10. Microinteractions
11. Live motion
12. Atmosphere and freeze
```

Do not start with the disco lights.

Do not let blur drive architecture.

Do not let the current UI layout sneak back in wearing sunglasses and a fake mustache.

The final product should feel calm, premium, dimensional, truthful, and useful:

```text
A Liquid Glass command deck for HOTAS control that can tune a response curve with surgical precision while looking like it came from an expensive spaceship.
```

That is HelmForge’s new UI north star.

---

# 28. One-Line Reminder for Codex

```text
This is a new command-deck UI architecture using proven HelmForge data and truth systems — not a Legacy UI repaint.
```

