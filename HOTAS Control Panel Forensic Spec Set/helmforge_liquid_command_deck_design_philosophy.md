# HelmForge Liquid Command Deck — UI Design Philosophy

## Purpose

This document defines the design philosophy for the next HelmForge UI direction. It is not an implementation prompt yet, and it intentionally does not cover animations, transitions, final visual effects, or motion polish. Those belong in a separate document.

The goal is to stop repeatedly patching the existing Legacy UI and instead define a new product identity: a smooth, modern, beautiful, highly functional flight-controller software interface.

HelmForge should feel like a premium glass-cockpit command deck for configuring and validating a HOTAS control pipeline, not like a Qt settings app with dark cards.

## Core Design Direction

The new UI direction is called:

# Liquid Glass Command Deck

This design should feel inspired by:

- modern aircraft glass cockpits
- high-end HOTAS and flight sim control software
- premium dark workstation interfaces
- subtle futuristic command decks
- smooth Liquid Glass-style layered surfaces
- practical engineering dashboards

The visual language should be modern, glossy, dimensional, and useful. It should not become cluttered, gimmicky, or purely decorative.

The app should look like it belongs next to a HOTAS, an OLED monitor, a flight sim setup, and a concerning but productive amount of coffee.

## What Is Wrong With the Current Direction

The current Legacy UI is functional, but visually it still feels like:

- sidebar plus scroll cards
- many repeated label/value rows
- developer dashboard language
- too many bordered boxes
- too many equally important cards
- pages that feel like forms instead of operating modes
- status information scattered across the interface
- advanced/debug data too visible
- layout patches instead of a designed product system

The recent Cockpit attempt improved some things, especially status visibility, but it still reused too much of the old layout structure. It looked like the Legacy UI wearing cockpit-themed armor, not a new app design.

The core issue is not just color or card styling. The issue is information architecture.

The app needs fewer containers, stronger layout, bigger primary workspaces, and clearer hierarchy.

## Primary Philosophy

# Data is not layout.

The Legacy UI layout should not be reused just because the data already exists there.

The new UI should reuse the same backend, services, workspace data, runtime truth, mapping models, Helm logic, and Bridge telemetry, but it should not reuse the old page structure as the design source.

Bad approach:

```text
Legacy page + new QSS + glass borders
```

Good approach:

```text
New Liquid Glass page layout using existing data/services
```

The data can stay. The visual composition should be new.

## Main Product Identity

HelmForge should feel like a control deck, not a settings menu.

Each page should feel like an operating mode with a clear job:

- Preflight answers: Can I safely use live output right now?
- Mapping answers: What does each physical control do?
- Tuning answers: How does this axis respond and feel?
- Live Monitor answers: What is the HOTAS doing right now?
- Flight Recorder answers: What can I capture, buffer, or review?
- Helm answers: What is wrong, what would improve it, and what can be safely applied?

Every page should have a purpose-specific hero area, not just a vertical list of cards.

## Global Layout Concept

The current giant sidebar should be replaced or heavily reduced. A full-height text sidebar feels too much like an enterprise dashboard and consumes too much visual space.

A better layout direction:

```text
┌───────────────────────────────────────────────────────────────┐
│ HelmForge Command Deck       Workspace   Saved   HOTAS Status │
│                                                               │
│  compact glass nav                                           │
│     Preflight                                                 │
│     Mapping       ┌─────────────────────────────────────┐     │
│     Tuning        │  Page Hero / Primary Instrument      │     │
│     Analysis      │                                     │     │
│     Recorder      └─────────────────────────────────────┘     │
│     Support                                                 │
│                                                               │
│                    ┌───────────────┐ ┌───────────────────┐   │
│                    │ Context Panel │ │ Actions / Details │   │
│                    └───────────────┘ └───────────────────┘   │
│                                                               │
│          Workspace ready.                 Apply  Save  Helm   │
└───────────────────────────────────────────────────────────────┘
```

The app should have:

1. a compact navigation system
2. a unified top command/status bar
3. a primary instrument area per page
4. supporting context/detail panels
5. a slim action/footer strip
6. advanced diagnostics tucked away or visually secondary

## Navigation Philosophy

The current giant sidebar should not remain the main design. It is practical but visually heavy.

The new UI should use a more modern navigation system that feels like part of a flight control interface.

## Recommended Navigation: Glass Command Dock + Optional Radial Switcher

### Main Navigation: Compact Glass Dock

Use a compact floating glass icon dock instead of a giant text sidebar.

Major modes:

1. Preflight
2. Mapping
3. Tuning
4. Analysis
5. Recorder
6. Support

The dock could be vertical or horizontal, but it should be compact, modern, and always available.

When hovering or selecting a mode, a small glass label or flyout can show page names.

Example:

```text
[ ◉ ]  Preflight
[ ⬡ ]  Mapping
[ ◌ ]  Tuning
[ ✦ ]  Analysis
[ ● ]  Recorder
[ ? ]  Support
```

The important point: navigation should feel like a mode selector, not a website sidebar.

### Secondary Navigation: Subpage Flyouts or Mode Panels

Each major mode can contain subpages.

Example:

```text
Tuning
 ├ Base Tuning
 ├ Filtering
 ├ Combat Profile
 └ Conditional Rules
```

These can appear as:

- glass flyout panels
- top segmented subnav
- contextual mode selector
- compact page chips near the header

The subpage selector should be discoverable but not huge.

### Optional Quick Navigation: Radial Command Wheel

A radial menu could be extremely cool, but it should not be the only navigation system.

Radial menus are excellent for quick mode switching, but not ideal for long page lists.

Best use:

- optional quick-switch overlay
- opened by clicking the HelmForge logo/orb
- opened by keyboard shortcut such as Ctrl+Space
- used for major modes, not every single page

Example:

```text
                  Preflight
                     ▲
       Support ◀  HELMFORGE  ▶ Mapping
                     ▼
                  Tuning
        Recorder        Analysis
```

Hovering or selecting a mode could reveal sub-options.

The radial menu should be a later enhancement after the static layout is stable.

## Visual Style: Liquid Glass

The whole app should have a glass design, almost like a Liquid Glass interface.

The design should use:

- dark navy/black base surfaces
- translucent glass-like panels
- layered depth
- subtle gradients
- soft edge highlights
- thin glowing borders
- status-colored reflections
- rounded geometry
- premium spacing
- smooth, calm visual hierarchy

Glass should not mean clutter.

Bad:

```text
[card][card][card][card][card][card][card][card]
```

Better:

```text
One large glass command surface
  with a few floating instruments
  with status embedded into the layout
```

The UI should feel dimensional and smooth, but still readable and practical.

## Color and Status Language

Color must mean something.

Use a consistent state language:

- Green: ready, verified, safe, saved
- Amber: attention, waiting, setup blocked, missing device
- Red: hard error, failure, unsafe condition
- Cyan/Blue: information, live data, simulation, neutral active state
- White/bright text: primary information
- Muted blue-gray: secondary information

Avoid random glow colors that do not communicate state.

The UI should not become RGB gamer soup. It should be sleek and intentional.

## Component Philosophy

The UI should stop relying on endless label/value cards.

Instead, use fewer, stronger components.

## 1. Page Hero / Primary Instrument

Every page needs one dominant hero element.

Examples:

- Preflight: go/no-go command status
- Mapping: HOTAS visual map
- Base Tuning: response curve instrument
- Filtering: smoothing/filter response instrument
- Combat Profile: combat response instrument
- Live Monitor: live axis/button instrument panel
- Flight Recorder: capture timeline/status display
- Helm: recommendation/change review deck

This hero element should answer the page’s main question immediately.

## 2. Context / Inspector Panel

Details should orbit the hero.

The context panel should show:

- selected axis/control/profile/mode
- current state
- editable parameters
- route/action summary
- relevant warnings

This should not become a giant database table.

## 3. Metric Tiles

Use metric tiles for important counts and values.

Examples:

```text
AXIS ROUTES
6
input channels
```

```text
BUTTON ROUTES
15
switch bindings
```

```text
HAT ROUTES
1
POV route
```

Metric tiles should be compact, readable, and visually distinct from normal data rows.

## 4. Readiness Gates

Use readiness gates for go/no-go states.

Examples:

- Input
- Telemetry
- Workspace
- vJoy
- Output Proof
- Safety

Each gate should have:

- label
- state
- status color
- short explanation

This is better than burying readiness across many rows.

## 5. Route / Flow Rows

Mapping and pipeline pages should show flows, not raw strings.

Example:

```text
Raw Axis 1 → Roll → vJoy X Axis
```

or

```text
Physical Stick X → Roll Function → Output Intent: X Axis
```

Flow rows should be used for:

- Mapping
- Effective Response Stack
- Conditional Rules
- Helm proposed changes
- Bridge/data pipeline summaries

## 6. Checklist Panels

Warnings and actions should use checklist-style panels.

Example:

```text
● Connect HOTAS controller
○ Run Preflight Check
○ Confirm live input sample
✓ Workspace saved
✓ vJoy detected
```

This is more actionable than paragraphs of warning text.

## 7. Advanced Details Panels

Advanced data should be available but visually secondary.

Advanced areas can include:

- raw runtime states
- telemetry keys
- config filenames
- raw booleans
- internal diagnostic messages
- debug-only wording

Advanced details should not dominate the normal page.

## Avoided Patterns

The new UI should avoid:

- giant permanent sidebar
- page-long card stacks
- repeated label/value rows everywhere
- raw internal strings in normal UI
- too many bordered boxes
- nested scroll areas
- every page using the same grid
- huge empty cards
- random status colors
- debug/prototype text
- bolted-on footer/header elements
- clutter where everything appears equally important

If everything is important, nothing is important.

## Page Design Concepts

## Preflight

Main question:

> Can I safely use live output right now?

Preflight should not be a long scroll list. It should be mostly visible at once.

Suggested structure:

```text
┌───────────────────────────────────────────────────────────────┐
│ PREFLIGHT                                                     │
│ Verify controller, telemetry, workspace, output, and safety.   │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│ ┌─────────────── GO / NO-GO STATUS ─────────────────────────┐ │
│ │ ⚠ HOTAS NOT CONNECTED                                    │ │
│ │ Workspace and vJoy are ready. Live input proof is missing.│ │
│ │ Next: connect controller, then run Preflight Check.       │ │
│ │ [Run Check] [Simulation Mode] [Setup Guide]               │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                               │
│ ┌──── Input ────┐ ┌── Telemetry ─┐ ┌── Workspace ─┐           │
│ │ Missing       │ │ Waiting      │ │ Loaded       │           │
│ └───────────────┘ └──────────────┘ └──────────────┘           │
│ ┌──── vJoy ─────┐ ┌── Output ────┐ ┌── Safety ────┐           │
│ │ Detected      │ │ Not verified │ │ Gated        │           │
│ └───────────────┘ └──────────────┘ └──────────────┘           │
│                                                               │
│ ┌ System Map / Details ─────────────┐ ┌ Next Actions ───────┐ │
│ │ Device: HOTAS missing             │ │ ● Connect HOTAS     │ │
│ │ Driver: Ready                     │ │ ○ Run Check         │ │
│ │ vJoy: Detected                    │ │ ○ Confirm input     │ │
│ │ Workspace: Saved                  │ │ ✓ Workspace saved   │ │
│ └───────────────────────────────────┘ └─────────────────────┘ │
│                                                               │
│ Advanced Diagnostics: visually secondary                      │
└───────────────────────────────────────────────────────────────┘
```

Preflight should show status hierarchy:

1. overall go/no-go
2. readiness gates
3. core supporting details
4. action checklist
5. advanced diagnostics

Not 20 cards all yelling at the user.

## Mapping

Main question:

> What is each physical control doing?

Mapping should become one of the most visually impressive pages.

Suggested structure:

```text
┌───────────────────────────────────────────────────────────────┐
│ MAPPING                                                       │
│ Physical controls → logical functions → virtual output intent │
├───────────────────────────────────────────────────────────────┤
│ ┌──────────────────── HOTAS VISUAL MAP ────────────────────┐ │
│ │                                                           │ │
│ │             big beautiful HOTAS schematic                 │ │
│ │                                                           │ │
│ │ clickable controls, route glow, selected channel highlight│ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                               │
│ ┌ Selected Control ─────────────┐ ┌ Route Flow ─────────────┐ │
│ │ Stick X                       │ │ Raw Axis 1 → Roll → X   │ │
│ │ Currently maps to Roll        │ │ Intent: vJoy X Axis     │ │
│ │ [Change Mapping]              │ │ Status: Draft saved     │ │
│ └───────────────────────────────┘ └─────────────────────────┘ │
│                                                               │
│ Advanced Route Tables                                         │
└───────────────────────────────────────────────────────────────┘
```

The HOTAS diagram should be the hero.

Tables should become advanced/detail editors lower on the page, not the main event.

Mapping should use route flows instead of raw debug text.

## Profiles

Main question:

> Which profile is active, and what profiles can I load or manage?

Profiles should use:

- active profile hero card
- profile tiles
- import/export/apply actions
- saved/unsaved state
- compact details

It should not feel like a file list pasted into a form.

## Modes

Main question:

> Which operating modes are active, and how do they affect the control stack?

Modes should use:

- mode tiles
- active mode chips
- mode relationship flow rows
- binding summaries
- quick enable/disable controls
- advanced mode details lower on the page

## Base Tuning / Filtering / Combat Profile

Main question:

> How does this axis respond and feel?

Tuning pages should feel like instruments, not forms.

Suggested structure:

```text
┌───────────────────────────────────────────────────────────────┐
│ BASE TUNING                                      Axis: Roll   │
├───────────────────────────────────────────────────────────────┤
│ ┌──────────────── Response Instrument ─────────────────────┐ │
│ │                                                           │ │
│ │                  curve graph + live marker                │ │
│ │                                                           │ │
│ └───────────────────────────────────────────────────────────┘ │
│ ┌ Axis Selector ───────┐ ┌ Tuning Controls ─────────────────┐ │
│ │ Roll  Pitch  Yaw     │ │ Curve Mode: Expo                 │ │
│ │ Throttle Aux1 Aux2   │ │ Strength: 0.34                   │ │
│ └──────────────────────┘ │ Deadzone: 0.03                   │ │
│                          └──────────────────────────────────┘ │
│ ┌ Advisory ─────────────────────────────────────────────────┐ │
│ │ More curve strength softens center, but may reduce snap.  │ │
│ └───────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

The graph/response preview should be the hero.

Controls should feel like an inspector panel for the selected axis.

Guidance should be advisory, not a tiny sentence in a huge empty card.

## Conditional Rules

Main question:

> What rules can change the response stack, and when do they trigger?

Conditional Rules should use:

- rule system status banner
- enabled/disabled metrics
- condition → action flow rows
- rule cards or modern table
- conflict/warning checklist
- advanced rule details lower on the page

## Effective Response Stack

Main question:

> How does raw input become final output?

Use a pipeline/flow layout:

```text
Raw Input → Base Tuning → Filtering → Modes → Rules → Final Output
```

Each stage should be a flow card, with selected axis status and preview instruments.

Avoid dense debug blocks unless inside Advanced.

## Live Monitor

Main question:

> What is the HOTAS doing right now?

Live Monitor should look like a real instrument panel.

Use:

- axis gauges/meters
- raw vs final paired bars
- button illuminated grid
- hat direction indicator
- telemetry freshness/status rail
- live/simulated state clearly shown

Avoid tables where gauges would communicate better.

## Flight Recorder

Main question:

> What can I capture, buffer, and review?

Flight Recorder should use:

- recorder status hero
- backend capability rail
- capture settings as instrument controls
- timeline or clip strip
- clip library as modern cards/table
- clear simulated/metadata-only truth when real capture is unavailable

Do not claim real capture if it is not implemented.

## Helm Assistant

Main question:

> What is wrong, what would improve it, and what can I safely apply?

Helm should feel like a command assistant panel, not a separate window or scroll-clipping monster.

Suggested structure:

```text
┌──────────────────── HELM ASSISTANT ────────────────────┐
│ Status: Analyzing workspace                             │
│ Confidence: Medium                                      │
├─────────────────────────────────────────────────────────┤
│ Problem                                                 │
│ “Can’t hold aim steady”                                 │
├─────────────────────────────────────────────────────────┤
│ Findings                                                │
│ ✓ Roll curve may be too sharp                           │
│ ⚠ Yaw filtering may be too low                          │
│ ✓ No unsafe output changes                              │
├─────────────────────────────────────────────────────────┤
│ Proposed Changes                                        │
│ [Yaw Center Alpha 0.25 → 0.36]                          │
│ [Roll Curve Strength 0.34 → 0.50]                       │
├─────────────────────────────────────────────────────────┤
│ [Apply Selected] [Revert]                               │
└─────────────────────────────────────────────────────────┘
```

Helm should be readable, structured, and focused.

## Help / Docs

Main question:

> How do I understand and use this page or parameter?

Help should use:

- topic cards
- parameter help modules
- examples
- page links
- structured explanations
- no raw debug/prototype notes

## Perf / Diagnostics

Main question:

> What is the system actually reporting?

This is one of the few places where raw details are acceptable.

It should still look intentional:

- diagnostic status banner
- grouped tiles
- Bridge/device/vJoy diagnostics
- environment/runtime info
- raw/internal values allowed
- copy/export actions if available

## Static-First Rule

Liquid Glass visual design should begin as a static layout.

Do not start with:

- blur effects
- animations
- opacity effects
- drawers
- dynamic layout mutation
- heavy QGraphics effects
- hover animation systems

Those final touches belong in a separate phase/document.

The first implementation should be beautiful and stable without motion.

The rule:

# Build the glass cockpit first. Add the afterburners later.

## Implementation Philosophy for Codex

Future implementation prompts should clearly say:

- do not wrap or reskin Legacy pages
- do not reuse old page layouts as the design source
- create new Liquid Glass Command Deck layouts
- use existing data/services only
- preserve backend/runtime behavior
- keep Legacy as fallback/reference
- use static layouts first
- no animations/effects until stable

Magic sentence:

> Do not wrap or reskin the Legacy pages. Recompose the application into a new Liquid Glass Command Deck layout using existing data/services only. Legacy pages are reference/fallback, not the layout source.

## Summary

The new HelmForge UI should be:

- smooth
- modern
- glassy
- functional
- premium
- cockpit-inspired
- visually cohesive
- less cluttered
- more hierarchical
- less form-like
- more instrument-like

The goal is not to make the current UI prettier.

The goal is to create a new product experience for HelmForge: a Liquid Glass Command Deck for HOTAS mapping, tuning, monitoring, validation, recording, and assistant-guided configuration.

Legacy UI stays as a safe fallback.

The new UI should be designed like a modern control deck from the ground up, using the same proven backend.
