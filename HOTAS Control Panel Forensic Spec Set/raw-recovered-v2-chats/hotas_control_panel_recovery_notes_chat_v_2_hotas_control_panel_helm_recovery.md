# HOTAS Control Panel Recovery Notes — Chat HOTAS Control Panel / Helm + Recovery

## 1. Project Overview

### What the software is
A desktop HOTAS tuning and control-mapping application for joystick/throttle setups, built to let the user inspect, modify, diagnose, and optimize input behavior at a far deeper level than ordinary game control menus. The app is not just a mapper. It is a **control laboratory** for tuning how raw controller input becomes final output.

### Core purpose
The software exists to solve a real user problem: games, especially aircraft in Battlefield-style titles, often do not provide enough tuning depth for HOTAS use. The app is meant to bridge that gap by letting the user:
- map axes and buttons cleanly,
- reshape axis response with curves and conditioning,
- build mode-specific behaviors,
- visualize the effects live,
- inspect the full response chain,
- and eventually get guided tuning advice through an embedded helper called **Helm**.

### Design philosophy
The app’s design philosophy evolved into something very specific:
- **technical, enthusiast-grade, control-room aesthetic**
- dark UI with blue-accent styling
- highly visual and inspectable
- powerful, but still understandable
- not toy-like, not generic SaaS, not childish
- problem-solving oriented, not just parameter-editing oriented
- built for people who care about feel, latency, and control precision

The project intentionally became more than “a settings page.” It was discussed as a serious diagnostic/tuning workstation. Several times the design target was described as a **premium control console**, **signal lab**, **avionics/control-room tool**, or **engineering workstation** rather than a generic utility.

### Hardware / controller context
Explicit hardware discussed:
- **Thrustmaster T.Flight HOTAS One**

Known user mapping described in chat:
- Right joystick:
  - Left/right = roll
  - Forward/back = pitch
  - Twist/pivot = yaw
  - Trigger = weapon fire
  - Top buttons used for weapon switching, exit aircraft, repair, etc.
- Left throttle:
  - Forward/back = throttle
  - Buttons used for zoom/view switch, flares, and other aircraft functions

The software is clearly intended to support at least this HOTAS and likely similar joystick/throttle devices through a customizable mapping/tuning layer.

### User experience priorities
Explicit priorities repeatedly mentioned:
- input tuning must help with difficult real-game problems like:
  - “can’t hold aim steady”
  - “too twitchy near center”
  - “combat feels sluggish”
  - “overshoots target”
- UI must look and feel premium
- UI must move **smoothly** and not look like pages are manually redrawn
- CPU and GPU usage should be kept very low
- system latency should be minimized aggressively
- visuals should be modernized without turning the app into a bubbly dashboard
- components should be highly inspectable and richly visualized
- there should be a clear distinction between:
  - parameter-driven tuning tabs
  - problem-driven smart diagnosis (Helm)

### Key constraints and preferences
- Preserve technical feel and “serious tool” identity
- Avoid overly playful or cartoonish UI
- Avoid fluffy, generic consumer-SaaS styling
- Avoid over-reliance on static presets when giving smart recommendations
- Keep control processing responsive even while rich visualization is active
- Rich UI must never compromise low-latency control behavior
- Use modular architecture for advanced features like Helm rather than stuffing logic into a monolithic app file

---

## 2. Major Features Discussed

### 2.1 Base Tuning
#### What it does
Provides per-axis baseline tuning for the core axes and auxiliary axes. This is where the user shapes raw axis behavior before other modifiers like combat mode or rules are applied.

#### Why it exists
To compensate for poor or shallow in-game controller tuning, especially for aircraft aiming and tracking.

#### Settings discussed
For each axis, the table eventually included fields like:
- Curve
- k (curve strength)
- Deadzone
- Anti-DZ
- Hysteresis
- Scale
- Max
- Precision
- Invert

#### Why these matter
- **Curve / k** soften center control and strengthen outer-edge authority
- **Deadzone** suppresses drift/noise near center
- **Anti-deadzone** helps response start more clearly after deadzone
- **Hysteresis** adds slight stickiness around zero to reduce jitter/sign-flipping
- **Scale / Max** control overall output authority
- **Precision** applies an additional scale during precision mode
- **Invert** flips axis direction

#### UI behavior
This lived on a tab with row-per-axis editing and graph previews on the right. Later the graph updated when rows were selected and while values were edited.

#### Related improvements discussed
- grouped columns into conceptual families
- add tooltips
- add a graph for current input/output response
- add overlays comparing Normal/Precision/Combat and linear reference
- add a checkbox to let the linear reference follow deadzone or not
- add selected-row highlighting
- add feel summary and tuning guidance below graphs

---

### 2.2 Filtering
#### What it does
Provides per-axis smoothing and slew-rate limiting, especially near center and during reversals.

#### Why it exists
To remove twitchiness and improve the feeling of steady tracking without destroying responsiveness.

#### Fields discussed
- Center Alpha
- Edge Alpha
- Same Slew
- Reverse Slew

#### Behavior
- Center Alpha / Edge Alpha determine how directly output follows input depending on input magnitude
- Same Slew limits change while continuing in the same direction
- Reverse Slew limits change more aggressively during rapid reversals

#### UI details
- tab with per-axis table
- grouped columns into:
  - Smoothing
  - Rate Limiting
- graph or dynamic preview panel on right showing response-over-time / step response behavior
- feel summary and caution guidance below

---

### 2.3 Combat Profile
#### What it does
Provides a mode-specific override layer for tuning while combat mode is active.

#### Why it exists
To let the aircraft remain maneuverable in general flight but become calmer and more precise during aiming/combat.

#### Fields discussed
- Combat k
- Combat Scale
- Center Alpha
- Edge Alpha
- Same Slew
- Reverse Slew

#### UI details
- grouped into:
  - Combat Curve
  - Combat Smoothing
  - Combat Slew
- graph on right comparing combat behavior to normal behavior
- overlays eventually discussed
- graph mode selector already existed

---

### 2.4 Modes
#### What it does
Controls which buttons activate precision and combat behaviors and how those modes combine.

#### Fields described
- Precision Hold Buttons
- Combat Trigger Buttons
- Combat Zoom/Aim Buttons
- Combat Extra Buttons
- Precision + Combat Stack Mode

#### Why it exists
The user needed control behavior to react differently depending on gameplay context such as firing, zooming, or entering a more precise aim state.

#### Key logic example
- Trigger held could activate precision
- Zoom button could activate combat
- Precision + Combat could stack via Multiply

#### UI evolution
Originally the page had separate side help notes. Later these were replaced by the same tiny tooltip-style help used on Conditional Rules. The page also gained a **Current Behavior Summary** that described what button sets triggered what behavior.

---

### 2.5 Conditional Rules
#### What it does
Allows one axis/mode/button condition to modify parameters of another axis on the fly.

#### Why it exists
This is the advanced logic layer. It allows dynamic behavior like reducing yaw authority while roll exceeds a threshold, or applying axis behavior only in certain mode/button contexts.

#### Examples discussed
One prominent example shown repeatedly:
- Reduce Yaw Output Scale to **0.75** when absolute Roll final output is greater than **0.35**

#### Core rule structure
The rule editor evolved into grouped sections:
- **Action**
  - Parameter
  - Operation
  - Target Axis
  - Value
- **When**
  - Mode Gate
  - Buttons
  - Button Test
- **Condition**
  - Reference Axis
  - Stage
  - Measure
  - Comparator
  - Threshold
  - Threshold High

#### Important UI/UX changes discussed
- group fields visually into sections
- add plain-English live rule preview sentence
- make Enabled/Disabled visually prominent
- improve “Add Conditional Rule” affordance
- add validation / conflict indicators
- status chips / validation state in header
- tooltips for advanced fields like Stage, Measure, Operation, Button Test
- runtime status indicators for rules:
  - Disabled
  - Inactive
  - Active
  - Blocked
  - maybe Armed/Eligible etc.
- rule header should include summary and state
- later desire for active pulse/badge states

#### Runtime-awareness ideas
- live badge/pulse showing whether a rule is active/blocked/inactive
- future simulator with slider for exploring what actions/rules would trigger

#### Relationship to other systems
- Effective Response Stack needed to show rule injections inline at their actual injection point in the chain
- Helm later needed to inspect rules in real time, not merely mention them vaguely

---

### 2.6 Graph / Curve Preview System
#### What it does
Shows visually what the current tuning will do to axis input/output behavior.

#### Why it exists
Critical trust feature. Users should tune behavior, not numbers in a vacuum.

#### Graph capabilities discussed
- baseline linear reference (45° line)
- deadzone-aware linear reference option
- current response curve
- mode selectors such as Normal, Precision, Combat
- overlay selector for comparisons
- live marker/dot showing current input/output location
- stage-specific graphing in Effective Response Stack
- dynamic response preview for filtering

#### Future enhancements discussed
- compare Normal vs Precision vs Combat vs Precision+Combat overlays
- rule impact view
- raw vs final graph in Effective Response Stack
- mini feel summary box under graphs
- caution/recommendation box under graphs

---

### 2.7 Effective Response Stack Inspector
#### What it does
A new dedicated tab/workspace to show the full live processing chain for **one selected axis at a time**, from raw input to final output.

#### Why it exists
This became one of the crown-jewel features. It explains *why* the axis feels the way it does by showing the actual live pipeline.

#### Final conceptual structure
Top controls:
- selected-axis dropdown
- graph mode
- freeze/resume
- optional copy snapshot
- maybe show-all vs changed-only

Left side:
- vertical stack of stage cards
- downward flow arrows/connectors between them
- subtle green animated pulse traveling down the arrows

Stages discussed:
1. Raw Input
2. Center Conditioning
   - Deadzone
   - Anti-deadzone
   - Hysteresis
3. Curve / Shape
4. Base Output Limits
5. Filtering
6. Mode Modifiers
7. Inline Rule Injections at actual point in flow
8. Final Output

Each stage card shows:
- title
- live status chip
- input value
- output value
- delta
- explanation line
- selectable for more detail

Right side:
- Raw vs Final graph (generic response graph, not scrolling timeline)
- live marker/dot on curve
- selected stage detail panel
- mode summary
- current stack summary
- rule driver values panel (small supporting live values for other axes used in rules)

#### Important design decisions
- **one selected axis only**
- do not show other full axis stacks at the same time
- rules must appear inline at their true injection point, not in one static rule block
- external axis data used by rules should appear only in a small secondary panel, not as full extra stacks
- Freeze must freeze actual state, not just pause repaint

#### Later requested enhancements
- stronger arrow styling / flow
- more distinct rule cards vs normal stages
- more terminal emphasis on Final Output
- bigger live modifier detection
- mini magnitude bars inside stage cards
- stage pinning
- show all vs show only active/changed stages
- rule execution order labels where meaningful
- stronger spacing/panel hierarchy

---

### 2.8 Helm (built-in smart helper)
#### What it is
A smart in-app tuning diagnostician originally planned as a tiny corner helper, later redesigned into a full workspace.

#### Final chosen name
**Helm**

#### Why it exists
To allow users to describe a control problem in human language, such as:
- “Can’t hold aim steady”
- “Too twitchy near center”
- “Combat mode feels sluggish”
- “Overshoots target”

Helm would then inspect the current app state and suggest exact tuning changes.

#### Key behavior
- natural language input front-end
- structured symptom engine underneath
- follow-up questions only when needed
- confidence indicator
- diagnosis summary
- context note(s)
- exact before/after diffs
- checkboxes to selectively apply changes
- apply to **in-memory only**, not auto-save
- revert last Helm changes

#### Tone/personality decisions
- must speak in **first person**
- light professional tone
- tiny bit of character
- not goofy, not corporate, not third-person report style

#### Huge UX evolution
Originally a small fold-out overlay from top-right. Eventually that was judged too cramped. User strongly preferred Helm to be **different from a tab** because it is not just another parameter page.

Final direction:
- top-right Helm button
- opens a large **slide-out workspace** from the right
- covers about **70% of app width**
- background dims and blurs simultaneously
- “Helm is active” bar fades in with subtle pulsing green glow
- Helm acts like a different **workspace mode**, not a normal tab

#### Internal diagnosis model discussed
Desired pipeline:
1. interpret symptom
2. detect scope (global/mode-specific/etc.)
3. prioritize relevant axes dynamically
4. diagnose which layer is responsible
5. inspect stack / modes / feel summary / rules
6. size changes adaptively
7. explain reasoning and expected effect

#### Important future direction
Helm should become much smarter over time:
- larger symptom library
- more detailed diagnosis
- possibly vector/fingerprint-based matching later
- stronger context awareness
- deeper rule analysis

---

### 2.9 Performance / Latency Refactor
#### Why it was needed
The app became sluggish after rich live visualization features were added. User explicitly wanted:
- CPU and GPU use minimized
- system latency cut down to an absolute minimum
- whole app to feel smooth and immediate

#### Major Phase 1 performance changes recorded in chat
- coordinated heartbeat instead of competing timers
- adaptive runtime polling
- hidden/non-live areas no longer polled at the same cost as live views
- dirty-state tracking reduced from whole-app snapshot churn to targeted refresh work
- preview math cached for references/curves/response previews/feel/guidance output
- graphs accept signature hints so marker/live updates do not pay full geometry-signature cost
- Effective Response Stack freeze actually freezes the view
- stack cards and rule cards keep persistent structure and skip reconfiguring unchanged widgets
- perf panel improved with diagnostics for visible tab, runtime mode, pending work, scheduler timing, cache behavior

#### Measured notes reported
- steady stack refresh ~1.7 ms after layout in smoke run
- stack.build_state ~0.10 ms
- rules.render_cards ~0.22 ms
- graph.draw_plot ~0.45 ms average in mixed smoke
- remaining hotspots: per-tab preview recomputation and dirty-state capture during edits ~9–11 ms in source-mode smoke tests

---

### 2.10 Visual Modernization Project
#### Why it exists
Even after features and performance improved, the app still felt visually like “2005 manually drawn and redrawn graphics.” User wanted:
- more modern visuals
- smoother movement
- subtle curve on sharp edges
- soft shadows
- less flat boxy legacy feeling
- more premium control-console identity

#### Core modernization goals discussed
- slight but visible rounded corners
- soft shadows
- strong surface hierarchy
- better spacing and fit
- stronger panel/card language
- modernized tabs, buttons, inputs, headers
- not bubbly, not SaaS, not toy-like

#### Additional explicit requirement
Spacing and layout discipline were called out later as first-class needs:
- no overlap
- consistent spacing rhythm
- no cramped fit
- no clipping
- cards/graphs/Helm sections must breathe properly

---

## 3. UI / UX Reconstruction

### Overall window layout
The app is a dark desktop application with a strong top shell/header and multiple main tabs. The bottom has an action bar with things like save/reload/close/perf/help depending on state. The central area changes depending on tab/workspace.

### Core top-level areas observed/discussed
- top shell/header with app title and status/info area
- main tab strip for tuning/inspection tabs
- content body
- right-side graph/diagnostic panels on many pages
- bottom action bar
- top-right special controls including Helm, perf, maybe help/docs

### Known major tabs/pages
- Modes
- Base Tuning
- Filtering
- Combat Profile
- Conditional Rules
- Effective Response Stack
- Helm is *not* a normal tab; later it becomes a special overlay workspace

### Colors and style
- dark background
- blue accent color family
- user repeatedly praised the dark theme and felt it was clean and technical
- later wanted stronger surface hierarchy, rounded corners, shadows, blur, and premium depth
- wanted the whole app to stay technical and control-console-like

### Borders, corners, shadows
Originally boxy / square / legacy-framed. Later strong request to modernize with:
- slightly rounded corners everywhere
- stronger but tasteful shadows
- parent/child surface distinction
- more premium selected/active states
- more depth on Helm and graph panels

### Typography
No exact fonts specified. Desired text style:
- technical, clean, premium
- more modern hierarchy
- stronger spacing between headings/subtitles/body
- less flat text rhythm

### Icons
Mentioned/described:
- top-right Helm icon/button
- drawer/docs/help icon later requested for help drawer
- rule/status chips and indicators
- possible helm/nautical identity for assistant

### Tooltips
Strongly preferred for explaining advanced fields. The small tooltip icon approach on Conditional Rules was later requested across the app.

### Visual hierarchy desires
- panels should feel like true surfaces
- graph panels should feel like instruments
- stack cards should feel like modules
- Helm should feel like a different operating mode

---

### Screenshot reconstruction sections

#### Screenshot 1 — Effective Response Stack early polished version (descriptive placeholder)
- Visible content: vertical stack of stage cards on left, graph panel on right, summaries beneath/right.
- UI elements likely visible: Raw Input, Center Conditioning, Curve / Shape, Base Output Limits, Filtering, Mode Modifiers, inline rule card(s), Final Output.
- Design details: dark theme, blue accents, compact cards, status chips, graph with live point marker.
- Inferred state: selected axis shown; stack live; one stage selected.
- Problems/improvements discussed:
  - stronger arrows/connectors
  - distinguish rule cards more from normal stages
  - improve graph breathing room
  - smarter Rule Driver Values panel

#### Screenshot 2 — Conditional Rules improved editor (descriptive placeholder)
- Visible content: grouped sections Action / When / Condition, rule preview sentence, status badge.
- Exact visible types of text discussed elsewhere:
  - “Set Yaw Output Scale to 0.75 when absolute Roll final output is greater than 0.35.”
  - ACTIVE / DISABLED / VALID / WARNING style labels.
- Improvements noted:
  - grouped fields were a big UX win
  - plain-English preview was “excellent”
  - status/validation in header worked well
- Remaining issue discussed:
  - header density
  - Enabled/Disabled could still become a stronger toggle

#### Screenshot 3 — Modes page with behavior summary (descriptive placeholder)
- Visible content: fields for Precision Hold Buttons, Combat Trigger Buttons, Combat Zoom/Aim Buttons, Combat Extra Buttons, Stack Mode.
- A Current Behavior Summary box was present or desired.
- Side help text was explicitly removed in favor of tooltip icons.

#### Screenshot 4 — Base Tuning / Filtering / Combat pages with graphs (descriptive placeholder)
- Visible content: per-axis rows, grouped column families, graph on right, Feel Summary and Tuning Guidance boxes below.
- Design inference: graphs likely include line plot on dark background with accent color line, optional overlay line, and controls above.
- User reaction: very positive about graphs; they made the app feel much more serious and explainable.

#### Screenshot 5 — Helm early fold-out overlay (descriptive placeholder)
- Visible content: small compact overlay with text input, quick chips, what I found, confidence, recommended changes, apply/review/cancel.
- User feeling: too cramped, too small, too much content packed into pop-out.
- This directly led to Helm being promoted to a dedicated right-side slide-out workspace.

#### Screenshot 6 — Helm large workspace mode (descriptive placeholder)
- Visible content: large right-side overlay covering most of the app, background dim/blur, “Helm is active” header/indicator, diagnosis sections, diff list, apply/revert.
- Important design decision: Helm should feel different from tabs, more like a diagnostic bridge/command workspace.
- User reaction: loved the concept but wanted richer wording and smarter diagnosis.

#### Screenshot 7 — Phase 2 visual modernization comparison (descriptive placeholder)
- User reaction: only slight visual changes, not strong enough. Still too close to original design.
- Resulting decision: create a bolder Phase 2.5 visual modernization emphasizing stronger radius, shadows, spacing, fit, and hierarchy.

> Note: Actual screenshot embedding was not available in Canvas. Reattach screenshots manually later to these placeholders.

---

## 4. Software Architecture / Technical Design

### Known files/modules mentioned explicitly
- `hotas_control_panel_app.py`
- `app_performance.py`
- `HOTASControlPanel.exe`
- `Open-HOTAS-Control-Panel.cmd`
- `Edit-HOTAS-Curves.cmd`

### Architecture direction inferred
Python desktop app with a central application file plus supporting modules. The later refactor strongly suggests the app uses:
- a main UI shell
- per-tab views/components
- shared state / runtime control logic
- performance helper / scheduler module
- persistent graph preview components
- structured subsystems for advanced features like Helm

### Important architectural principles explicitly discussed
- do not cram advanced logic into one main app file
- Helm should be modular:
  - engine/service
  - symptom library
  - fix/recommendation library
  - types/models
  - context-analysis helpers
- app should use a retained/component-like architecture rather than visibly redrawing pages in chunks
- UI should use persistent containers/surfaces where possible
- heavy live work should be decoupled from core control path

### Data flow / state ideas
Likely flow for axis tuning:
1. raw controller input
2. center conditioning
3. curve shaping
4. output limits
5. filtering
6. mode modifiers
7. rule injections
8. final output / vJoy / downstream control output

This was made explicit in Effective Response Stack discussions.

### Saving/loading configuration
Not fully detailed, but clearly present. Important note from Helm:
- Helm applies changes to **in-memory current state only**
- user must still save manually

### State management desires
- persistent structures for stack cards and rule cards
- avoid full-page rebuilds
- central update heartbeat
- hidden tabs/workspaces should suspend or throttle heavy live work
- graph geometry caching
- only selected axis stack recomputed/rendered

### Planned architecture improvements
- design tokens / visual system
- motion tokens / motion system later
- centralized scheduler/heartbeat
- performance debug layer
- improved modularization for Helm

---

## 5. Control Mapping and HOTAS Logic

### Actual HOTAS mapping described by user
Hardware: Thrustmaster T.Flight HOTAS One

#### Right joystick
- left/right = roll
- forward/back = pitch
- twist/pivot = yaw
- trigger = weapon firing
- top button = changing weapons
- top button = exiting aircraft
- top front button = activate equipment slot 1 / emergency repair

#### Left throttle
- forward/back = throttle
- one inside-right button unknown / not remembered
- A button = aim zoom / changes POV from outside to inside heli
- B button = flares
- Y button unknown / not remembered

### Battlefield tuning logic discussed
A lot of the app’s tuning design came from Battlefield helicopter aiming problems.

#### Main gameplay problems described
- hard to hold crosshairs steady on targets
- yaw too twitchy / dirty
- using twist yaw likely introduces unwanted roll/pitch
- need soft center response but strong edge response
- combat mode should calm aiming without making general flight mushy

#### Important tuning strategy discussed
- Roll = get onto attack lane
- Yaw = micro-corrections
- Pitch = commit/track vertically
- Throttle = steady altitude / overall control

#### Recommended hardware mapping idea
Strong recommendation was made to consider moving yaw from stick twist to throttle rocker because twist introduces dirty micro-inputs. Whether the app itself implemented hardware mapping changes is not stated, but the tuning logic was built around these realities.

### Per-axis tuning targets discussed
Base default suggestions at one point:
- Roll: S-curve with mild soft center
- Pitch: slightly stronger soft center than roll
- Yaw: strongest soft center / strongest damping
- Throttle: mostly linear or very mild curve

Combat defaults discussed separately:
- stronger damping / lower output especially on yaw and pitch
- throttle mostly unchanged

### Precision mode logic
Per-axis precision scales used when precision mode active. Precision often stacked with combat mode through Multiply.

### Profiles/presets
A full preset architecture was planned for later, not yet implemented at the time of many discussions.

Planned ideas included:
- save/load/export/import presets
- game-specific profiles later
- profile system tied into future recommendation strength ideas

### Calibration / Quick Tune
A **Quick Tune** feature was planned for later. It would likely help with:
- axis calibration
- deadzone/invert suggestions
- first-pass recommended tuning

---

## 6. Visual Tools / Graphs / Curve Editor

### Graph philosophy
Graphs are central, not decorative. They act as trust-building tuning instruments.

### Base curve graph
Shows input vs output mapping.
- linear reference line
- deadzone-aware linear reference option
- transformed curve based on deadzone, curve, scale, max, precision, etc.
- live dot showing current position

### Combat graph
Shows combat response and possibly comparison to normal.

### Filtering preview
Unlike static curve graph, this needs to represent dynamic response-over-time / step response / reversal response.

### Effective Response Stack graph
Generic response graph showing Raw vs Final, with current live point. Not a scrolling timeline.

### Controls affecting graphs
- row selection in tables updates graph automatically
- editing values updates graph live
- graph mode selector can show Normal, Precision, Combat, etc.
- overlay selector to compare modes later
- linear reference deadzone checkbox later

### Math / transformation logic discussed
Curves were described with formulas earlier in the conversation, including cubic-blend S-curves and deadzone remapping logic.

Representative math discussed:
- odd-symmetric cubic blend like `y = (1-k)x + kx^3` for centered axes
- deadzone remap to preserve full-range output after deadzone
- one-sided/J-curve style for throttle suggested
- adaptive filtering based on center/edge alpha and same/reverse slew

### Visual feedback behavior
- graph updates live but later optimized with caching
- curves should not rebuild fully every tick if only live marker changes
- preview graphs should feel like instruments, not generic charts

---

## 7. Overlay / Recorder / “Flight Recorder” Features

This chat referenced earlier project work that included an overlay and flight recorder system.

### Overlay
- overlay could be turned on/off with a keybind
- there was also a “Configure” idea for advanced overlay placement/styling, but sane defaults should mean most users do not need to touch it often

### Flight Recorder / hindsight buffer
A very notable feature discussed earlier in project context:
- option in Flight Recorder to record from the moment a keybind is pressed for a specified duration
- or instead keep a rolling buffer of the duration
- when the keybind is pressed, save the current buffer
- explicitly described as “like hindsight”

### Why it matters
This recorder likely supports retrospective tuning/debugging by letting the user capture what happened leading up to an event rather than only after starting a recording.

### UI relation
Precise UI layout for recorder not fully detailed in this chat, but it is definitely part of the project’s major feature set and should be remembered in rebuild planning.

---

## 8. “Helm” Assistant / Built-in Assistant Concept

### Name choice
Final selected name: **Helm**
- preferred over “Trim” because Trim felt too much like an action
- user wanted something with identity, not a boring “assistant” label

### What Helm does
- user describes control problem in natural language
- Helm analyzes it using structured symptom engine
- inspects context, stack, modes, feel summary, rule state
- proposes exact changes to any relevant axes/settings
- can apply selected changes to in-memory current state
- can revert last applied Helm changes

### Where it appears
Final direction:
- launched from top-right button/icon
- opens a large slide-out workspace from the right
- about 70% width
- background dims and blurs
- “Helm is active” bar fades in with subtle green pulse

### What it can explain/adjust
For v1:
- Base Tuning
- Filtering
- Combat Profile
- Mode-related settings

Not for v1:
- editing/creating/disabling conditional rules automatically

### Personality/style
- first-person voice
- concise
- professional
- slightly human / characterful
- should say things like:
  - “I think…”
  - “I checked the stack…”
  - “I’d start here…”
- user strongly disliked cold third-person phrasings like “Helm will now…”

### Relationships to other systems
Helm must be able to reference:
- Feel Summary
- Caution engine (lightly, not as authority)
- Effective Response Stack
- live rule analysis
- current mode state

### Important user complaints / improvements about Helm
- initial version felt too cramped
- “What I found” repeated the same text too much
- suggestions felt too preset / too conservative
- context note about rules was too vague
- Helm should actually analyze rules in real time and say if they are relevant

---

## 9. Code Snippets / Implementation Details

No large raw code snippet blocks from the user were included directly in this chat for the HOTAS app itself.

### Concrete implementation artifacts mentioned
- `hotas_control_panel_app.py`
- `app_performance.py`
- launchers:
  - `Open-HOTAS-Control-Panel.cmd`
  - `Edit-HOTAS-Curves.cmd`
- packaged executable:
  - `HOTASControlPanel.exe`

### Concrete implementation details described from Codex update
- coordinated heartbeat for UI/dirty/runtime updates
- adaptive runtime polling
- targeted per-tab dirty-state tracking instead of whole-app snapshot churn
- caching for:
  - linear references
  - static curves
  - dynamic response previews
  - feel/guidance output
- graph signature hints so marker/live updates avoid full geometry cost
- Effective Response Stack freeze now freezes the view
- persistent stack card and rule card structures
- perf diagnostics expanded

### Implementation architecture explicitly requested for Helm
Helm should become its own subsystem/library rather than live as a huge block in the main app file:
- Helm engine/service
- symptom library
- recommendation/fix library
- structured types/models
- context analysis helpers

### Dependencies/setup
No package list explicitly stated in this chat. This is a gap for later recovery.

---

## 10. Bugs, Problems, and Fixes

### Bug/problem: app became sluggish / delayed
#### Symptom
Controls felt sluggish/delayed after adding richer visualizations.

#### Likely causes discussed
- Effective Response Stack doing too much live work
- graphs rebuilding too much
- animations too expensive
- summaries/rule status recalculating too often
- hidden tabs possibly still updating
- control path too coupled to UI work

#### Fixes
- coordinated heartbeat
- adaptive polling
- hidden area work reduction
- graph/path caching
- persistent structures
- freeze mode improvements
- diagnostics

#### Result
Significant Phase 1 performance improvement.

---

### Bug/problem: Conditional Rules page initially too dense
#### Symptom
Too many horizontally packed fields; hard to parse.

#### Fixes
- grouped into Action / When / Condition
- added live rule preview sentence
- stronger enabled state and validation visibility

---

### Bug/problem: other tabs felt less polished than Conditional Rules
#### Symptom
Base/Filtering/Combat looked too table-first and lacked hierarchy.

#### Fixes discussed
- grouped columns into logical families
- short purpose statement on each tab
- graph panels on right
- tooltip help instead of side notes

---

### Bug/problem: Effective Response Stack initially lacked enough hierarchy / flow polish
#### Symptom
Needed stronger arrows, distinction between rule cards and stage cards, better graph presence.

#### Fixes/planned fixes
- stronger arrows/connectors
- green animated flow
- rule cards visually distinct
- more terminal final output card
- stage pinning, biggest modifier highlight, mini magnitude bars, etc.

---

### Bug/problem: Helm too small / cramped
#### Symptom
Tiny overlay could not comfortably display everything.

#### Fix
Promoted to large dedicated right-side slide-out workspace.

---

### Bug/problem: Helm wording too cold / third-person
#### Symptom
User disliked repeated “Helm thinks… Helm checked…” style.

#### Fix requested
Switch to first-person voice; more human and natural.

---

### Bug/problem: Helm suggestions felt too preset / too weak
#### Symptom
Recommendations did not feel bold or contextual enough.

#### Fixes requested
- adaptive recommendation magnitudes
- deeper context use
- actual rule inspection
- better layer diagnosis
- stronger explanation of why change sizes were chosen

---

### Bug/problem: visual modernization too subtle
#### Symptom
After Phase 2, app did not look different enough.

#### Fix requested
A much bolder Phase 2.5:
- stronger radius
- stronger shadows
- stronger panel hierarchy
- better spacing and fit
- more premium shell/header
- better graph/stack/Helm surface treatment

---

## 11. Design Decisions and Preferences

### Explicit likes
- dark technical UI
- blue accents
- graph previews and live visualizations
- grouped sections and plain-English previews
- Effective Response Stack as flagship feature
- Helm as a named character/workspace, not generic assistant
- top-right Helm entry point
- large slide-out workspace mode for Helm
- control-console / premium workstation feel

### Explicit dislikes
- overly boxy / legacy 2005 appearance
- cold third-person wording in Helm
- suggestions that feel too preset or timid
- vague context notes
- tiny cramped helper overlays
- side help text instead of small tooltips
- visual chunking / page redraw feeling
- overlapping / cramped / barely-fitting layout
- generic SaaS or bubbly styling

### Emotional/practical priorities
- project was almost complete before being lost; reconstruction needs to be dense and forensic
- performance and low latency matter deeply
- user wants humor in normal conversation but app tone itself should remain serious/professional with character
- wants rich explainability and trust in what the app is doing

### Visual style preferences
- modernized but still sharp
- slightly rounded, not pill-shaped
- shadows and depth, but disciplined
- strong spacing discipline
- polished motion later
- control-room identity preserved

### Workflow preferences
- direct tuning tabs remain for parameter work
- Helm handles problem-driven diagnosis
- Helm should not auto-save
- rule editing by Helm deferred for later

---

## 12. Rebuild Checklist

### Must-have features
- Main shell with dark technical UI
- Tabs:
  - Modes
  - Base Tuning
  - Filtering
  - Combat Profile
  - Conditional Rules
  - Effective Response Stack
- per-axis tuning tables
- graph preview panels on right
- grouped columns/sections with tooltips
- mode system (precision/combat stack)
- Conditional Rules editor with grouped sections and plain-English preview
- Effective Response Stack with one-axis live chain and inline rule injection
- Helm workspace launched from top-right
- save/load current state
- performance-optimized update architecture

### Nice-to-have / later features
- preset architecture
- Quick Tune / onboarding setup
- stronger Helm intelligence / fingerprint matching
- rule simulator
- export/screenshot/reporting
- richer docs drawer
- motion system overhaul

### UI pieces to recreate
- shell/header
- top tab strip
- right-side graph panels
- action bar
- rule editor card system
- stack cards and arrows
- Helm workspace overlay mode
- perf/help/status controls top-right

### Likely files/modules needed
- main app shell/app file
- performance/scheduler module
- graph/preview module(s)
- rule engine/editor module
- response stack inspector module
- Helm engine/module set
- design token / styling layer
- persistence/config module

### Suggested rebuild order
1. Core app shell and performance-friendly state/update architecture
2. Base Tuning / Filtering / Combat / Modes pages with graph panels
3. Conditional Rules editor and rule logic
4. Effective Response Stack
5. Helm workspace v1
6. performance polish
7. visual modernization / motion modernization
8. preset architecture / Quick Tune / docs / smarter Helm

### Testing/debugging checklist
- verify axis mapping and updates
- verify graph updates without lag
- verify hidden tabs do not keep full live work
- verify stack only renders selected axis
- verify freeze truly freezes stack state
- verify rule states (active/blocked/etc.) display correctly
- verify Helm apply/revert only touches in-memory state
- verify no overlap/clipping/layout crowding
- verify performance metrics stay low

---

## 13. Unknowns / Gaps

### Missing/unclear details
- exact dependency list / packages
- exact project folder structure besides files mentioned
- exact persistence file format
- exact graph rendering library / toolkit
- exact UI toolkit/framework details
- exact launcher packaging workflow
- exact styles/colors/tokens after later visual phases
- exact code for curves and transformations as implemented in final app

### Screenshots needing manual review later
All screenshots should be manually reattached and used to refine:
- exact spacing
- exact labels
- exact colors
- exact panel widths
- exact chips/button text
- exact graph styling

### Feature references not fully explained
- full overlay/flight recorder UI
- preset architecture details
- Quick Tune specifics
- help/docs drawer content layout
- export/reporting format
- eventual rule simulator behavior

### Questions to answer later
- what UI framework was used exactly?
- what config file format was used?
- how were controller devices enumerated and mapped?
- what graph library/path rendering system was used?
- what exact design tokens/colors should be used in final rebuild?

---

## 14. Codex / AI Rebuild Prompt

Use this as a rebuild-oriented prompt for Codex or another coding agent:

---

Rebuild the HOTAS Control Panel desktop app described in these recovery notes.

This is a premium enthusiast-grade HOTAS tuning and diagnostics tool, not a generic settings page. The app must support deep per-axis response tuning, mode-specific behaviors, conditional rules, live graph previews, a full one-axis Effective Response Stack inspector, and a diagnostic workspace called Helm.

### Core architecture requirements
- Build a persistent desktop app shell with a dark technical control-console aesthetic.
- Optimize for low CPU/GPU use and minimal control latency.
- Use retained/persistent UI surfaces instead of visibly redrawing page chunks.
- Hidden tabs/workspaces must suspend or heavily throttle expensive live work.
- Graphs must cache geometry where possible and update live markers independently.
- The control-processing path must stay responsive even when rich diagnostics are open.

### Main tabs/features
1. **Modes**
   - Precision Hold Buttons
   - Combat Trigger Buttons
   - Combat Zoom/Aim Buttons
   - Combat Extra Buttons
   - Precision + Combat Stack Mode
   - Current Behavior Summary
   - tooltip-style help

2. **Base Tuning**
   - per-axis fields for Curve, k, Deadzone, Anti-DZ, Hysteresis, Scale, Max, Precision, Invert
   - grouped column families
   - graph preview on right
   - feel summary / tuning guidance

3. **Filtering**
   - per-axis Center Alpha, Edge Alpha, Same Slew, Reverse Slew
   - grouped columns
   - dynamic response preview graph
   - feel summary / caution guidance

4. **Combat Profile**
   - per-axis combat-specific curve/filtering values
   - graph preview and overlays

5. **Conditional Rules**
   - grouped editor with Action / When / Condition sections
   - live plain-English rule preview sentence
   - strong enabled/disabled state
   - validation/conflict indicators
   - runtime status chips
   - tooltip help for advanced fields

6. **Effective Response Stack**
   - one selected axis at a time
   - vertical live stage cards with arrows/connectors
   - subtle green animated flow down arrows
   - stages: Raw Input → Center Conditioning → Curve → Base Output Limits → Filtering → Mode Modifiers → inline Rule Injections → Final Output
   - graph on right showing Raw vs Final with live marker
   - selected stage detail panel
   - Current Stack Summary
   - Rule Driver Values panel
   - Freeze/Resume that freezes actual state
   - strong distinction between main stages and injected rule cards

7. **Helm**
   - launched from top-right, not in main tab strip
   - opens a right-side slide-out workspace covering about 70% width
   - background dims and blurs while open
   - “Helm is active” bar fades in with subtle green pulse
   - first-person voice
   - natural language symptom input
   - prompt chips
   - 0–2 follow-up questions when needed
   - structured diagnosis engine underneath
   - confidence indicator
   - context notes using stack/rules/modes/feel summary
   - exact before/after diffs with checkboxes
   - apply selected changes to in-memory state only
   - revert last Helm changes
   - no auto-save
   - do not let Helm edit/create rules in v1

### Visual design requirements
- dark premium control-console aesthetic
- visible but disciplined rounded corners
- soft shadows and strong surface hierarchy
- precise spacing, zero overlap, clean alignment
- modernized buttons, inputs, tabs, cards, graph panels
- not bubbly, not generic SaaS, not toy-like

### Motion / rendering requirements
- use transform/opacity-style transitions later where possible
- persistent surfaces, not page-like redraws
- no visible chunk-by-chunk panel loading
- smooth, retained-feeling UI behavior

### Performance requirements
- minimum practical CPU/GPU use
- minimal end-to-end control latency
- central update heartbeat / scheduler
- hidden/inactive content suspension
- graph/path caching
- diagnostics/perf mode for future regression detection

### Build order suggestion
1. shell + performance foundation
2. base/filter/combat/modes pages with graph previews
3. conditional rules
4. effective response stack
5. Helm workspace
6. visual modernization pass
7. motion modernization pass
8. presets / Quick Tune / smarter Helm / docs drawer / simulator later

### Tone/UX requirements
- serious, instrument-like, enthusiast-grade
- highly inspectable and explainable
- trust-building visuals
- rich diagnostics but still understandable

Rebuild from these notes as faithfully as possible, preserving feature names, labels, relationships, and the app’s overall identity.

---

## End note
This document is intended as a forensic reconstruction blueprint, not a loose summary. Use it as the reference skeleton for rebuilding the lost HOTAS Control Panel project.

