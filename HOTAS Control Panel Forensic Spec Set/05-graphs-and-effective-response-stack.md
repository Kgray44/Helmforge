# Graphs and Effective Response Stack

**Spec-set role:** forensic reconstruction document generated from the three recovered HOTAS Control Panel chat notes. This document is meant to stand on its own while cross-referencing the rest of the set.

**Evidence taxonomy used throughout:**
- **Confirmed Facts**: directly stated in the recovery notes or visible as exact recovered UI text.
- **Screenshot-Derived Details**: observations recovered from screenshot descriptions in the source notes.
- **Inferences**: explicitly inferred from the notes or reconstructed from adjacent evidence.
- **Desired Improvements**: user preferences, future direction, fixes, or rebuild requirements.
- **Unknowns**: details the notes say are missing, uncertain, or need later verification.

## Confirmed Facts

- Graphs are a trust-building tuning instrument, not decoration.
- The graph stack includes base response graph, filtering graph, combat graph, Effective Response Stack graph, Live Monitor graphs, and overlay telemetry traces.
- The Effective Response Stack page inspects one selected axis at a time from raw HOTAS input through shaping, filtering, mode modifiers, rule injections, and final output.
- Exact final visible title: `Effective Response Stack`.
- Exact graph title: `Raw vs Final`.
- Exact graph copy: “The live marker rides on the effective response line for the selected axis.”
- Stage cards show `IN`, `OUT`, `DELTA`, input/output bars, status badges, and explanation.
- Stages discussed include `Raw Input`, `Center Conditioning`, `Curve / Shape`, `Base Output Limits`, `Filtering`, `Mode Modifiers`, inline `Rule Injections`, and `Final Output`.

## Screenshot-Derived Details

- Legacy Effective Response Stack had controls `Axis Roll`, `Graph Mode Raw vs Final`, `Stack View Show All Stages`, `LIVE`, `Freeze`, and `Copy Snapshot`.
- Initial V2 stack had Signal Chain left, graph right, Mode State, Current Stack Summary, Selected Stage, and Rule Driver Values.
- Initial stack had a visible twitching/micro-seizure every few seconds.
- Final V2 screenshot showed stage cards with clean live/active badges and bars, with no old twitch visible.

## Inferences

- The stack must reuse widgets and update values in place to avoid layout churn.
- Freeze must capture actual processing state, not only pause repaint.
- Rule Driver Values should show external axis data used by rules without rendering full extra axis stacks.
- Filtering preview is dynamic time/step-response, while stack graph is raw-vs-final response, not a scrolling timeline.

## Desired Improvements

- Stronger arrows/connectors and subtle green flow.
- More distinct rule cards vs normal stages.
- More terminal emphasis on `Final Output`.
- Bigger live modifier detection.
- Mini magnitude bars inside stage cards.
- Stage pinning.
- Show all vs show only active/changed stages.
- Rule execution-order labels where meaningful.
- Stronger spacing/panel hierarchy.

## Unknowns

- Exact graph rendering library in the older legacy app.
- Exact final graph style/token values.
- Exact curve formulas as implemented in the final app.
- Exact stage-detail payload schema.
- Exact signal timing and sampling mechanics.

## Relevant Implementation Prompt Extract

### Desired Improvements
- Implement pyqtgraph response previews and live graphs.
- Base Tuning linear reference must be true `y=x`.
- Effective Response Stack must reuse widgets and update values in place.
- Stage cards should show `IN`, `OUT`, `DELTA`, live/active badges, input/output bars, and descriptions.
- Include `Mode State`, `Current Stack Summary`, `Selected Stage`, and `Rule Driver Values`.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.14 Effective Response Stack page`

### 2.14 Effective Response Stack page

**Purpose:** inspect the full processing pipeline for one selected axis from raw input through shaping, filtering, modes, rules, and final output.

**Visible title:** `Effective Response Stack`

**Visible copy:**

- “Inspect one selected axis at a time from raw HOTAS input through shaping, filtering, mode modifiers, rule injections, and final output.”

**Controls:**

- Axis dropdown: Roll, Yaw, etc.
- `Live` status button/pill.

**Main layout:**

- Left: Signal Chain panel.
- Right: Raw vs Final graph.
- Lower right: cards for Mode State, Current Stack Summary, Selected Stage, Rule Driver Values.

**Signal Chain stages visible:**

- Raw Input — Live
- Center Conditioning — Active
- Curve / Shape — Active
- More stages below visible in scroll.

Each stage card shows:

- IN
- OUT
- DELTA
- Progress bars/line indicators labeled Input and Output.
- Stage description.

**Graph:**

- Title: `Raw vs Final`.
- Copy: “The live marker rides on the effective response line for the selected axis.”
- Shows raw/reference and final/processed curve.
- Marker at current position.
- Caption: “Raw input on X, effective output on Y.”
- `Center` control appears near graph.

**Known bug:** Signal Chain previously had a periodic glitch/micro-seizure. This was likely from heartbeat refresh, widget rebuilds, layout invalidation, or graph/container sync loops. Fix required updating values in place and reusing widgets.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 6 — Legacy Effective Response Stack tab`

### Screenshot 6 — Legacy Effective Response Stack tab

Effective Response Stack active. Page brief: inspect full live processing chain. Controls Axis Roll, Graph Mode Raw vs Final, Stack View Show All Stages, `LIVE`, `Freeze`, `Copy Snapshot`. Left stage card `Raw Input`, right Instrument View `Effective Response Graph`. Large bottom footer bar.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 15 — Repaired legacy Effective Response Stack tab`

### Screenshot 15 — Repaired legacy Effective Response Stack tab

Stack page with filter row and two-pane layout. Still legacy but stable. Content reachable with scroll.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 21 — Initial V2 Effective Response Stack page`

### Screenshot 21 — Initial V2 Effective Response Stack page

Signal Chain left, graph right, Mode State, Current Stack Summary, Selected Stage, Rule Driver Values. Signal chain had twitching glitch every few seconds. This page looked like crown jewel but needed stability.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 33 — Final V2 Effective Response Stack page`

### Screenshot 33 — Final V2 Effective Response Stack page

Effective Response Stack selected. Signal Chain card left with Raw Input, Center Conditioning, Curve/Shape stage cards. Graph right. Stage cards use colored live/active badges and clean signal bars. No old twitch visible in screenshot.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 6.1 Base response graph`

### 6.1 Base response graph

- Shows raw input on X axis and processed output on Y axis.
- Contains true linear reference line.
- Contains adjusted curve line(s).
- Center marker.
- Used to preview S-curve/deadzone/output scale effects.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 6.2 Filtering graph`

### 6.2 Filtering graph

- Step preview.
- Shows input vs filtered output over time.
- Demonstrates smoothing and slew limits.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 6.3 Combat graph`

### 6.3 Combat graph

- Shows combat-mode response curve.
- Can compare baseline/reference vs combat output.
- Guidance warns when values feel extreme/cautious.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 6.4 Effective Response Stack graph`

### 6.4 Effective Response Stack graph

- Raw vs Final graph for selected axis.
- Marker rides on effective response line.
- Shows relationship between raw HOTAS input and final output after stack.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 6.5 Live Monitor graphs`

### 6.5 Live Monitor graphs

- Raw Input Trace: recent raw samples over time.
- Raw vs Final Overlay: raw and final output overlaid.
- Axis Levels: bar visualization for each axis, raw blue/final green.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 6.6 Graph technical stack`

### 6.6 Graph technical stack

- pyqtgraph selected for fast interactive engineering graphs.
- Graph updates should be scoped locally.
- Avoid full page redraw on graph changes.
- Avoid constant graph animation.
- Graphs should resize smoothly and look integrated.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 10.6 V2 early: Base Tuning Linear line was curved`

### 10.6 V2 early: Base Tuning Linear line was curved

- Symptom: “Linear” reference line looked like transformed/adjusted curve.
- Cause: reference line likely reused transformed dataset.
- Fix: plot true `y=x` line independently.
- Status: final screenshots show straight reference line.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 10.7 V2 early: Effective Response Stack micro-seizure`

### 10.7 V2 early: Effective Response Stack micro-seizure

- Symptom: Signal Chain visually glitched every few seconds.
- Likely cause: timer/heartbeat rebuilding cards, layout invalidation, live refresh thrash, widget recreation.
- Fix: update values in place, reuse stage widgets, avoid layout churn.
- Status: final screenshots look stable; verify live runtime.




### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### 2.6 Graph / Curve Preview System`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### 2.7 Effective Response Stack Inspector`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `#### Screenshot 1 — Effective Response Stack early polished version (descriptive placeholder)`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `## 6. Visual Tools / Graphs / Curve Editor`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Bug/problem: Effective Response Stack initially lacked enough hierarchy / flow polish`

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




### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Graphs directly shown in this chat`

### Graphs directly shown in this chat
#### Overlay graph / telemetry strip
Visible both in exports and as live overlay:
- scrolling time-series traces,
- multiple colored lines for axes,
- legend/value list on right,
- dark semi-transparent background,
- compact strip layout anchored to bottom.

#### Live Monitor graph
Visible as **Raw Input Trace · Roll**:
- large panel graph,
- dark background grid,
- blue line/spike trace,
- focused on selected axis.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### What these graphs represented`

### What these graphs represented
- Live rolling controller values over time.
- For overlay: a compact multi-axis view intended for gameplay instrumentation.
- For Live Monitor: a more detailed single-axis trace view.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### How the user interacted with them`

### How the user interacted with them
From this thread:
- Choose axis in Live Monitor.
- Option to show raw and output together.
- Choose included axes and colors for overlay.
- Configure overlay position, opacity, history, thickness, legend, etc.
- Use hotkeys to toggle overlay or trigger capture.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Visual behavior`

### Visual behavior
The overlay appears designed to be readable but not dominant:
- bottom strip placement,
- moderate opacity,
- compact height,
- consistent axis color legend,
- optional legend/value visibility.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Math / transformation logic`

### Math / transformation logic
This chat does **not** provide exact math formulas for curve shaping or scaling. The only explicit logic direction is that a shared trace builder/layout system should translate buffered telemetry into renderable traces.

---
