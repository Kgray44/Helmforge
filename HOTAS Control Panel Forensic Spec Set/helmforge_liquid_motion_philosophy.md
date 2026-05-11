# HelmForge Motion Philosophy

## Purpose

This document defines the animation, lighting, shading, and material-motion philosophy for the future HelmForge Liquid Glass Command Deck UI.

The goal is not to make the interface flashy for the sake of being flashy. Motion should communicate state, depth, readiness, interaction, and system activity. HelmForge should feel alive, premium, smooth, and technically serious — like a precision flight-control command deck, not a generic dashboard with neon duct tape.

The guiding principle:

> Everything should feel suspended in glass, magnetically guided, and purpose-driven.

The interface should feel calm by default, responsive when touched, and expressive when system state changes. It should never become distracting, unstable, or visually chaotic.

---

# 1. Motion Philosophy

HelmForge’s motion language should feel like a modern aircraft glass cockpit blended with premium control software. The UI should feel:

- smooth
- quiet
- confident
- precise
- layered
- glassy
- functional
- alive, but not hyperactive

Motion should always answer one of these questions:

1. **What changed?**
2. **What is active?**
3. **What needs attention?**
4. **Where did this panel/control come from?**
5. **What system path is being affected?**
6. **Is this live, waiting, staged, saved, blocked, or verified?**

If an animation does not help answer one of those questions, it should probably be removed or made extremely subtle.

HelmForge should not feel like a cartoon app. No excessive bounce, no rubbery panels, no random RGB glow storms, and no motion that makes controls feel imprecise. The app should feel like expensive engineering software that also happens to look gorgeous.

---

# 2. Active vs Passive Animation

Animations fall into two broad categories.

## Active Animations

Active animations happen because the user does something or because a clear state change occurs.

Examples:

- page switches
- opening navigation
- selecting a control
- applying a workspace
- saving a workspace
- running preflight
- changing axis selection
- opening Helm
- selecting a route
- moving a HOTAS axis
- starting/stopping recorder state

Active animations should be crisp, purposeful, and quick. They should help the user understand what changed.

## Passive Animations

Passive animations are always-on or gently recurring background motion.

Examples:

- subtle background drift
- status light breathing
- faint glass shimmer
- soft telemetry pulse
- ambient reflections
- very slow glow movement

Passive animations should be barely noticeable. They should make the app feel premium and alive without pulling attention away from tuning, mapping, or monitoring.

A good passive animation should be something the user feels more than consciously notices.

---

# 3. Passive / Always-On Animation Ideas

## 3.1 Subtle Background Drift

The app background should not be flat. It can have a deep dark layered gradient with extremely slow movement, as if light is passing through tinted cockpit glass.

Possible elements:

- very slow blue/cyan gradient drift
- faint dark-violet or teal haze
- subtle radial glow behind the current page
- low-contrast layered glass shapes
- nearly invisible noise/grain
- soft diagonal light movement
- faint parallax glow fields
- gentle movement over 20–60 seconds

This should feel like a cockpit canopy reflection, not a music visualizer.

### Design Notes

Good:

- slow
- subtle
- low contrast
- atmospheric
- premium

Avoid:

- obvious repeating loops
- fast waves
- distracting patterns
- bright moving blobs
- anything that competes with data

## 3.2 Floating Glass Panel Idle Motion

Some background glass layers or hero surfaces may have extremely subtle floating motion.

Recommended limits:

- 1–2 px movement maximum
- very slow cycle
- only decorative panels or hero background layers
- not every card
- not input controls
- not data tables
- not sliders

The main working controls must remain visually stable. Floating should create depth, not seasickness.

Best candidates:

- decorative background glass layers
- large page hero slab
- Helm assistant orb
- inactive atmospheric panels

Avoid floating:

- sliders
- tables
- text-heavy cards
- tuning controls
- diagnostics
- graphs while the user is interacting

## 3.3 Live Status Pulse

Status indicators should breathe subtly based on their state.

Suggested behavior:

- **Green / verified:** calm slow pulse every 3–4 seconds
- **Amber / waiting:** soft attention pulse
- **Red / hard error:** sharper pulse, only for true faults
- **Blue / simulation/info:** calm shimmer or slow glow

The pulse can affect:

- small LED lights
- status chip borders
- page readiness gates
- top command status
- Helm active indicator
- recorder armed indicator
- telemetry live indicator
- unsaved draft indicator

The pulse should be tasteful and should not make the whole screen flash.

## 3.4 Telemetry Shimmer

When live data is flowing, certain UI elements should feel active.

Examples:

- live telemetry chip has a soft pulse
- axis bars ease smoothly
- route path glows briefly when input changes
- small data dots travel along an input → processing → output route
- Live Monitor gauges have a subtle active shimmer

This should be especially useful on:

- Mapping
- Live Monitor
- Effective Response Stack
- Base Tuning
- Filtering
- Combat Profile

The animation should communicate signal flow, not decorative chaos.

## 3.5 Ambient Reflection Glints

Liquid Glass panels need subtle highlights.

Possible effects:

- a thin diagonal highlight near top edges
- faint specular glint on glass corners
- slow sheen across hero panels
- cursor-reactive highlight on hover
- tiny reflection dot on LED/status bulbs

The goal is to make panels feel like layered material instead of flat rectangles.

Avoid huge white streaks, over-bright glares, or anything that makes text harder to read.

---

# 4. Active Interaction Animations

## 4.1 Page Transitions

Page switches should feel like changing aircraft MFD modes.

Preferred transition:

- old page fades/slides slightly away
- new page fades/slides in
- hero area appears first
- supporting panels follow with a slight stagger

Suggested timing:

- old page fade out: 100–140 ms
- new page slide/fade in: 180–240 ms
- panel stagger: 30–60 ms between major groups

The transition should be quick. The app should not feel slow or theatrical.

### Recommended Page Transition Feel

- smooth
- fast
- directional
- depth-based
- no giant sweeping movement
- no bounce
- no long wait

## 4.2 Navigation Opening

If the app uses a compact glass dock, navigation should feel magnetic and smooth.

### Dock Hover

When hovering a nav icon:

- icon lifts slightly
- scale increases subtly, around 1.00 → 1.04 or 1.06
- label bubble fades/slides out
- selected mode gets a stronger glow rail
- nearby items may separate by 2–4 px if safe

### Mode Flyout

When opening a mode with subpages:

- glass flyout expands from the dock
- subpage options fade in
- selected item is highlighted
- background may dim slightly behind flyout
- flyout should close cleanly when focus leaves

This should feel like a floating navigation lens, not a giant sidebar.

## 4.3 Radial Command Wheel

The radial command wheel should be an optional quick navigation feature, not the only navigation method.

Possible trigger methods:

- click HelmForge logo/orb
- hold navigation dock center button
- keyboard shortcut such as Ctrl + Space

### Opening Animation

- central HelmForge orb expands
- radial segments unfold outward
- labels fade in after segment expansion
- active category gets a glow ring
- background dims slightly

### Closing Animation

- selected segment compresses back toward the orb
- selected page emits a small glow trail toward the page header
- radial menu fades away
- page transition begins

### Radial Menu Structure

Best used for major categories:

- Preflight
- Mapping
- Tuning
- Analysis
- Recorder
- Support

Second-level options can appear when hovering a category, such as:

- Tuning → Base Tuning, Filtering, Combat Profile, Conditional Rules
- Analysis → Effective Response Stack, Live Monitor
- Support → Help / Docs, Perf / Diagnostics

The radial menu should feel like a command selector, not a cluttered page list.

## 4.4 Button Interactions

Buttons should feel tactile and glassy.

### Primary Actions

For important actions like Apply Workspace and Save Workspace:

- hover: glow expands softly
- press: button depresses by about 1 px
- release: quick rebound
- success: green edge sweep or small ripple
- warning/failure: amber pulse or subtle shake

### Secondary Actions

For actions like Import Profile or Open Setup Guide:

- hover brightens border
- background tint shifts slightly
- press gives a small tactile response

### Caution Actions

For actions like Revert or Reset:

- amber outline or warning tint
- hover increases caution glow
- click may show confirmation later if needed

No cartoon bounce. The interaction should feel like a magnetic glass control.

## 4.5 Status Chip Transitions

When status changes, chips should transition visibly.

Example:

`HOTAS Not Connected` → `Live Verified`

Suggested animation:

- old text fades out
- chip border sweeps from amber to green
- new text fades in
- status light blooms once
- then returns to calm state

This makes live state changes feel real and understandable.

## 4.6 Save / Unsaved State Animation

Unsaved state should be obvious but elegant.

When workspace becomes unsaved:

- Save chip changes to amber
- small draft dot appears
- footer/action strip gains a subtle amber edge
- Save Workspace button pulses once

When workspace becomes saved:

- green success sweep across save chip
- footer returns to calm state
- saved chip blooms once

This should make the workspace state impossible to miss without annoying the user.

## 4.7 Card Hover and Focus

Cards and panels should respond subtly to hover and focus.

Suggested effects:

- border brightens
- glass highlight shifts
- shadow deepens
- panel raises 1–2 px visually
- status rail becomes more luminous

For selected cards:

- stronger rim light
- active glow
- related panels lightly illuminate

For clickable control cards:

- hover communicates clickability
- selected state remains visually distinct

---

# 5. Page-Specific Motion Concepts

## 5.1 Preflight

Preflight should feel like a startup checklist.

### Page Load

Suggested sequence:

1. Hero go/no-go banner appears.
2. Readiness gates light in sequence:
   - Input
   - Telemetry
   - Workspace
   - vJoy
   - Output Proof
   - Safety
3. The blocked or waiting gate receives amber emphasis.
4. Next action checklist fades in.

### Running Preflight Check

When the user presses Run Preflight Check:

- gates enter checking state
- each gate shows a small scan animation
- results settle into green/amber/red
- hero status updates
- next recommended action updates

### Status States

Preflight should visually distinguish:

- ready for live use
- simulation/setup mode
- HOTAS missing
- telemetry stale
- output proof missing
- workspace unsaved
- hard error

## 5.2 Mapping

Mapping should use motion to show relationships between physical controls, logical mapping, and output intent.

### Route Glow

When selecting a HOTAS control:

- selected physical control glows
- route line appears from physical input to logical function
- output intent target highlights
- related table row or inspector softly illuminates

Example route:

`Physical Stick X → Roll → vJoy X Axis`

### Live Input Pulse

When input changes:

- corresponding control marker pulses
- axis meter moves smoothly
- route path briefly brightens
- output intent chip updates

### Remap Flow

When changing a mapping:

- old route fades down
- new route draws in
- Apply to Draft button receives amber staged glow
- footer unsaved indicator pulses

This should make mapping feel understandable and physical.

## 5.3 Base Tuning / Filtering / Combat Profile

Tuning pages should feel like instruments.

### Graph Marker Easing

Live graph dots should ease smoothly rather than jump.

Examples:

- raw input marker eases to new position
- processed output marker follows
- current curve area glows faintly around active point

### Parameter Changes

When changing a parameter:

- graph updates smoothly
- affected curve segment highlights briefly
- guidance/advisory panel crossfades to updated advice
- changed parameter gets brief amber draft pulse

### Axis Switching

When switching from Roll to Pitch, etc.:

- selected axis pill glows
- graph content crossfades/slides
- controls update cleanly
- live snapshot updates with a subtle transition

## 5.4 Live Monitor

Live Monitor should be the most alive page.

Suggested animations:

- axis bars ease smoothly
- button states illuminate instantly
- hat direction indicator rotates/highlights direction
- raw vs final meters update with smooth easing
- telemetry live indicator pulses
- stale data dims/frosts affected panels

### Stale Data Behavior

If telemetry becomes stale:

- gauges desaturate
- motion stops
- amber stale overlay or chip appears
- values remain readable but clearly not live

## 5.5 Flight Recorder

Flight Recorder should use timeline and capture-state motion.

Possible animations:

- standby state: calm blue pulse
- armed state: slow blue/amber breathing
- recording state: active red/amber indicator
- hindsight buffer: moving timeline strip
- save clip: selected segment locks and slides into clip library
- exported clip: success sweep

Even before real recording exists, the page should show disabled/standby state clearly and beautifully.

## 5.6 Helm Assistant

Helm should feel like a right-side assistant docking panel.

### Opening

- right-side glass panel slides in
- background dims slightly
- current page remains visible behind
- Helm status orb pulses once

### Analysis

- input/problem card locks into place
- evidence chips appear
- findings cards populate in sequence
- proposed changes stage in order

### Applying Changes

- selected change cards pulse
- Apply Selected triggers staged glow
- workspace draft state turns amber
- footer Save Workspace chip lights up

Helm should feel calm, smart, and guided — not like a debug report in a scroll box.

---

# 6. Lighting and Shading System

Liquid Glass requires more than blur and opacity. The illusion comes from layered material, edge lighting, shadows, glares, and depth.

## 6.1 Glass Material Layers

Each glass panel can be visually composed from several layers:

1. **Base tint** — dark translucent navy/black.
2. **Border highlight** — thin cyan/blue edge.
3. **Inner shadow** — creates depth inside panel.
4. **Top highlight** — suggests reflected light.
5. **Status rail** — green/amber/red/cyan when relevant.
6. **Glow field** — faint aura behind important panels.

Even without true real-time blur, these layers can make panels feel like glass.

## 6.2 Edge Lighting

Cards should have subtle edge highlights:

- top-left edge slightly brighter
- bottom-right edge slightly darker
- active/selected panel receives stronger rim light
- warning panels receive amber side rail
- verified panels receive green side rail

This makes panels feel thick and dimensional.

## 6.3 Light Glares

Light glares can enhance the glass feel if used carefully.

Possible glare elements:

- thin diagonal reflection streaks
- small specular highlight in panel corners
- soft top-edge shine
- tiny reflection on status bulbs
- cursor-following hover highlight

Rules:

- never reduce readability
- never dominate the panel
- avoid large white smears
- avoid excessive glare on text-heavy panels

## 6.4 Shadows

Dark UIs need subtle shadows to create depth.

Use:

- soft drop shadows behind floating docks
- deeper shadows behind overlays
- inner shadows in glass panels
- small colored glows around active system states
- larger ambient glow behind hero sections

Panels should feel suspended above the background, not painted flat.

## 6.5 Distortion Behind Glass

True distortion/blur can be expensive and risky in PySide6 if applied broadly. It should be delayed until the static layout is stable.

### First Approach: Fake Distortion

Use:

- tinted translucent backgrounds
- gradient overlays
- subtle noise texture
- softened borders
- layered highlights
- darker/lighter patches behind glass

This creates the impression of liquid glass without expensive real-time blur.

### Later Approach: Optional Real Blur/Distortion

Only consider real blur/distortion later for:

- static backgrounds
- small overlays
- navigation flyouts
- Helm panel background

Avoid applying real blur to the full app or large scrolling page content until thoroughly tested.

Guiding rule:

> Fake it beautifully before rendering it expensively.

## 6.6 Ambient Lighting by Page

Each page can have a subtle accent color while keeping the same overall design system.

Suggested accents:

- **Preflight:** amber/cyan
- **Mapping:** cyan/blue
- **Base Tuning:** blue/violet
- **Filtering:** teal/cyan
- **Combat Profile:** amber/red
- **Conditional Rules:** purple/amber
- **Effective Response Stack:** cyan/green
- **Live Monitor:** green/cyan
- **Flight Recorder:** red/amber
- **Helm:** teal/green
- **Diagnostics:** blue/gray

The page accent can affect:

- background glow
- hero border
- selected nav state
- key status rail
- subtle light bloom

This gives each page identity without breaking cohesion.

---

# 7. Visual Texture Ideas

## 7.1 Noise / Grain

A very subtle grain texture can prevent large glass surfaces from looking flat.

Rules:

- extremely low contrast
- should not affect text readability
- should not look dirty or pixelated
- should be consistent across panels

## 7.2 Fine Grid / Coordinate Lines

A faint cockpit grid can help technical pages feel more instrument-like.

Best places:

- Mapping diagram background
- Live Monitor meters
- Tuning graphs
- Effective Response Stack
- Flight Recorder timeline

The grid should be barely visible and should not make the UI look busy.

## 7.3 Scanline Shimmer

A subtle scanline shimmer can create an MFD-style feel.

Use carefully. Too much scanline makes the app feel like an old CRT instead of modern glass.

Best use:

- live telemetry panels
- recorder timeline
- diagnostics waveform/meter panels

## 7.4 Edge Refraction Illusion

Create the feeling of thick glass by combining:

- bright top/left edge
- darker bottom/right edge
- subtle inner border
- tinted background
- slight corner highlights

This can be done without real distortion.

## 7.5 Layered Depth

The UI should have a clear visual depth stack:

1. atmospheric background
2. floating navigation dock
3. main workspace glass slab
4. page hero instrument
5. supporting context panels
6. active overlays/flyouts
7. top command/status layer

Each layer should have slightly different opacity, border strength, shadow, and glow.

## 7.6 Specular Corner Highlights

Small highlights in the upper corners of glass cards can create an iOS Liquid Glass-like material feel.

Use:

- tiny curved highlight
- soft opacity
- consistent directionality
- no obstruction of content

---

# 8. Motion Intensity Modes

HelmForge should eventually support motion intensity settings.

Suggested setting:

```text
Motion: Off / Reduced / Standard / Cinematic
```

## Off

- no animation
- immediate state changes
- no passive motion
- safest mode for performance/accessibility

## Reduced

- essential transitions only
- minimal fades
- no background drift
- no route particles
- no large motion

## Standard

- default polished experience
- page transitions
- hover feedback
- status pulses
- graph/meter easing
- subtle background atmosphere

## Cinematic

- full experience
- radial menu animation
- background drift
- route traces
- liquid glass glints
- richer status blooms
- page panel staggering

Motion settings help with:

- performance
- accessibility
- motion sensitivity
- debugging
- user preference

---

# 9. Implementation Safety Notes

## 9.1 Safe Early Effects

These are relatively safe to use early:

- QSS gradients
- static border highlights
- static glass panel styling
- hover/pressed QSS states
- small status light timers
- graph marker easing
- meter value easing
- simple color transitions via controlled state updates

## 9.2 Riskier Effects

These should be delayed and tested carefully:

- QGraphicsBlurEffect on large widgets
- QGraphicsOpacityEffect on large containers
- QPropertyAnimation on page layouts
- animated resizing of complex pages
- live background blur
- nested translucent overlays
- custom paint caching based on widget geometry
- continuous animation on many widgets
- dynamic reparenting during interactions
- repeated updateGeometry loops

## 9.3 Sacred Stability Rule

> Motion must never create layout instability. Static layout comes first; animation decorates stable geometry only.

This rule is non-negotiable.

Do not animate layout geometry until the static layout is proven stable. Prefer animating small visual properties, small indicators, and data markers over entire page structures.

---

# 10. Animation Timing Rules

The entire app should share a timing language.

## Recommended Timing Ranges

| Interaction | Timing |
|---|---:|
| Tiny hover feedback | 80–120 ms |
| Button press/release | 60–100 ms |
| Status chip update | 120–180 ms |
| Page transition | 180–260 ms |
| Panel/flyout open | 180–240 ms |
| Radial menu open | 220–320 ms |
| Passive status pulse | 2.5–4 seconds |
| Background drift | 20–60 seconds |

## Easing Style

Preferred easing:

- ease-out cubic for entering
- ease-in cubic for leaving
- ease-in-out for steady movement
- no excessive bounce
- no elastic effects on technical controls

Motion should feel premium and precise, not playful or rubbery.

---

# 11. Specific Animation Concepts

## 11.1 Glass Settle

When a page opens, panels appear to settle into place.

Behavior:

- small vertical motion
- fade in
- subtle depth shift
- no large sweeping entrance

Best for:

- page hero area
- major support panels
- top status banner

## 11.2 Signal Sweep

A thin glow travels across a readiness rail or route line.

Best for:

- Run Preflight Check
- Apply Workspace
- Save Workspace
- route validation
- output verification state changes

## 11.3 Status Bloom

When a system becomes verified, the status light blooms once then returns to calm.

Best for:

- HOTAS connected
- vJoy verified
- workspace saved
- telemetry live
- output proof verified

## 11.4 Magnetic Hover

A card or button feels magnetically responsive to hover.

Behavior:

- slight lift
- edge glow
- highlight follows cursor
- selected state remains stable

Best for:

- navigation dock
- route cards
- system tiles
- major action buttons

## 11.5 Route Trace

A glowing trace moves from source to target.

Best for Mapping:

- physical control → logical function → output intent
- selected route preview
- remap confirmation
- live input path visualization

## 11.6 Live Breath

Live telemetry panels breathe softly while active.

If telemetry stops:

- breath stops
- panel dims
- stale state appears

Best for:

- Live Monitor
- Mapping selected input
- Effective Response Stack

## 11.7 Draft Pulse

Unsaved changes create a soft amber pulse.

Affected areas:

- footer action strip
- Save Workspace button
- workspace chip
- changed parameter cards
- staged mapping route

## 11.8 Apply Ripple

Applying a workspace sends a ripple from the Apply button through the page status rail.

This communicates that the draft was sent into the runtime/config pipeline.

## 11.9 Helm Thinking

Helm should not use a basic spinner. It should have a classy assistant-state animation.

Possible behavior:

- animated orb highlight
- slow rotating reflection
- evidence chips appearing in sequence
- recommendation cards staging in
- apply candidates lighting softly

## 11.10 Recorder Timeline Sweep

Flight Recorder should use a timeline sweep.

Behavior:

- timeline moves while recording/buffering
- saved clip segment locks in place
- export success sends a sweep into the clip library

---

# 12. What Not To Animate

Do not animate:

- text size
- table row layout
- large scroll areas continuously
- every card constantly
- raw diagnostics panels
- form fields while typing
- layout width/height on complex pages
- graph full rebuilds
- page content while user is dragging sliders
- anything that makes controls feel imprecise

Especially avoid motion on tuning controls while the user is actively dragging or typing. Precision controls must feel stable.

---

# 13. Desired Final Feel

The final HelmForge motion/material system should feel like this:

- The app is mostly calm.
- Important systems breathe.
- Pages transition smoothly.
- Status changes feel physical.
- Glass panels reflect light subtly.
- Live data moves with eased precision.
- Nothing screams unless something is actually wrong.
- The interface has depth without hiding functionality.
- The UI feels premium but engineering-serious.

The final vibe:

> A premium Liquid Glass flight-control command deck that can tune a HOTAS axis curve with surgical precision and still look like it came from an expensive spaceship.

---

# 14. Motion and Lighting Implementation Phases

The full vision should be implemented in safe phases.

## Motion Phase 0: Static Liquid Glass

Goal:

- establish visual material and layout
- no active animation yet

Includes:

- new app layout
- glass panels
- gradients
- shadows
- edge lighting
- status colors
- static glares
- stable page geometry

## Motion Phase 1: Microinteractions

Goal:

- make controls feel responsive

Includes:

- button hover/press
- card hover
- chip state transitions
- status light pulses
- saved/unsaved pulse
- subtle focus states

## Motion Phase 2: Page Transitions

Goal:

- make navigation feel smooth and premium

Includes:

- page fade/slide
- panel stagger
- command dock flyout
- mode switch highlight
- top status transition

## Motion Phase 3: Live Data Motion

Goal:

- make live systems feel alive and readable

Includes:

- axis meter easing
- graph dot easing
- route trace animation
- telemetry pulse
- recorder timeline sweep
- stale-data dim/freeze behavior

## Motion Phase 4: Liquid Glass Atmosphere

Goal:

- add subtle ambient material motion

Includes:

- background drift
- cursor-following glare
- soft parallax
- glass shimmer
- ambient page glow
- optional reduced-motion setting

## Motion Phase 5: Advanced Navigation and Overlays

Goal:

- add high-end interaction surfaces

Includes:

- radial command wheel
- animated page selector
- Helm slide-in assistant
- Mapping remap overlay
- advanced flyouts
- richer interaction choreography

---

# 15. Forbidden Early Effects

During early redesign implementation, avoid the following until static layout and page stability are proven:

- QGraphicsBlurEffect on large containers
- QGraphicsOpacityEffect on page/root containers
- QPropertyAnimation on layout geometry
- animated drawers
- live blur behind scrolling pages
- dynamic widget reparenting during clicks
- repeated layout mutation inside resize/show events
- continuous animation on many widgets at once
- nested translucent scroll overlays
- custom paint caching that depends on zero-size geometry

These can create freezes, clipping, broken layout, or performance problems.

---

# 16. Final Guiding Laws

## Law 1: Static First

The static UI must be beautiful, stable, and fully usable before animation is added.

## Law 2: Motion Serves Meaning

Every animation must communicate state, relationship, or action.

## Law 3: Controls Stay Precise

No animation should make tuning, mapping, or monitoring feel less accurate.

## Law 4: Live Data Moves Smoothly

Live values should ease and flow, but never lag in a way that hides truth.

## Law 5: Status Is Sacred

Green, amber, red, and cyan must mean something consistent.

## Law 6: Advanced Effects Are Optional

The app must remain usable with motion off or reduced.

## Law 7: No Layout Instability

Animations must never mutate complex layouts in ways that can freeze, clip, or hide content.

## Law 8: Glass Is More Than Blur

Liquid Glass is built from layering, tint, highlights, edge lighting, shadows, texture, and depth — not just blur and opacity.

## Law 9: Calm by Default, Expressive on Change

The interface should be calm until the user interacts or a system state changes.

## Law 10: No Raccoon Engineering

If an effect looks cool but risks stability, readability, or control precision, it waits for a later phase. The spaceship gets wings before the disco lights.

