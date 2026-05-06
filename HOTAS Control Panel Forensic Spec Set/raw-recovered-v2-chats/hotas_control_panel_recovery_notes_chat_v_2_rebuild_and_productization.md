# HOTAS Control Panel Recovery Notes — Chat V2 Rebuild and Productization

> **Purpose of this document:** forensic reconstruction notes for the HOTAS Control Panel project after the original software was erased. This document preserves every meaningful design, architecture, feature, bug, fix, UI direction, and rebuild instruction from this chat. It is intentionally dense. It is not a marketing summary. It is a rebuild blueprint pulled from the wreckage of the engineering goblin explosion.

---

## 1. Project Overview

### 1.1 What the software is

**HOTAS Control Panel** is a desktop control-mapping and tuning application for configuring a HOTAS / joystick-style input device and routing it into virtual joystick outputs, especially for flight/vehicle control workflows. The project evolved from a legacy custom-styled desktop control panel into a modern **HOTAS Control Panel V2** built as a safe parallel app using **PySide6 / Qt Widgets** and **pyqtgraph**.

The software’s core purpose is to let the user tune, inspect, and route HOTAS controls in one workspace:

- Map physical HOTAS axes/buttons/hats to logical vJoy outputs.
- Tune each axis with curves, deadzones, smoothing, slew limiting, output scale, and max output.
- Configure modes such as **Precision Mode** and **Combat Mode**.
- Define conditional rules that modify an axis or parameter based on another axis/mode condition.
- Inspect the full processing pipeline through an **Effective Response Stack**.
- View live input/output telemetry in a **Live Monitor**.
- Manage reusable **Profiles**.
- Use **Helm**, an integrated diagnostic assistant, to describe flight-control symptoms and receive suggested tuning changes.
- Package the app like real Windows software, with a proper installer, app icon, Start Menu shortcut, and hidden support files.

### 1.2 Design philosophy

The project’s visual and UX target changed dramatically during the chat. The desired direction became:

- **Premium engineering / tuning software**.
- Modern dark theme.
- Crisp, smooth, rounded, professional desktop feel.
- Real product identity, not a themed widget experiment.
- Users should open it and think: **“DAMN THIS IS NICE SOFTWARE.”**

The user strongly preferred:

- Rounded corners throughout.
- Smooth animations and micro-interactions.
- High polish without jank.
- Clear visual hierarchy.
- Clear distinction between status indicators and action buttons.
- Polished product copy rather than debug/prototype wording.
- Real installer/app behavior rather than a desktop shortcut pointing into a messy support folder.

### 1.3 Hardware/controllers discussed

Known hardware/control context:

- The user owns/uses a **Thrustmaster Flight HOTAS One**.
- The app maps physical HOTAS input to **vJoy** virtual outputs.
- Physical controls visible/inferred from the UI:
  - Axes: Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2.
  - Raw axis channels: Axis 1, Axis 2, Axis 3, Axis 6, Axis 7, Axis 8.
  - Logical outputs: Roll / X, Pitch / Y, Throttle / Z, Yaw / RZ, Slider 0 / SL0, Aux Output / RX.
  - Buttons: HOTAS buttons 1–15 visible in mapping/live monitor pages.
  - Hats: HOTAS Hat 1 mapped to vJoy POV 1, with Up/Right/Down/Left directional button mappings such as 7, 18, 19, 0.

### 1.4 High-level product goals

- Make HOTAS tuning approachable without hiding advanced control.
- Give the user live feedback on raw and processed input.
- Let the user tune separate response layers: base tuning, filtering, combat modifiers, conditional rules, final stack.
- Support profiles/presets for different flight/control needs.
- Make the app feel professional enough to distribute.
- Preserve old app during V2 migration.
- Make V2 safer through draft/workspace behavior rather than destructive direct writes.

---

## 2. Major Features Discussed

### 2.1 Legacy HOTAS Control Panel

**What it was:** the original/legacy UI before V2. It used a dark sci-fi control-console style with cyan borders, tabbed sections, and many nested custom frames. It contained the core tuning features and was nearly complete before the user’s original files were erased.

**Primary tabs/features visible in legacy screenshots:**

- Modes
- Base Tuning
- Filtering
- Combat Profile
- Conditional Rules
- Effective Response Stack
- Helm
- Help / Docs
- Performance popup

**Known files changed during legacy refactors:**

- `hotas_control_panel_app.py`
- `app_performance.py`
- `hotas_ui_theme.py`
- `Open-HOTAS-Control-Panel.cmd`
- `Edit-HOTAS-Curves.cmd`
- Packaged output: `HOTASControlPanel.exe`

### 2.2 Phase 1 performance/refactor work

**What changed:** a major under-the-hood refactor before the later UI work.

Preserved details from Codex report:

- UI/dirty/runtime updates moved through a coordinated heartbeat instead of competing refresh timers.
- Runtime polling became adaptive.
- Hidden and non-live areas were no longer polled at the same cost as live stack/rules views.
- Dirty-state tracking was reduced from whole-app snapshot churn to targeted per-tab refresh work.
- Preview math caching was introduced for linear references, static curves, dynamic previews, and feel/guidance output.
- Packaged app rebuilt to `HOTASControlPanel.exe`.
- Both launchers updated to prefer the packaged build:
  - `Open-HOTAS-Control-Panel.cmd`
  - `Edit-HOTAS-Curves.cmd`

**Purpose:** reduce app refresh cost, reduce UI churn, and improve responsiveness before UI polish.

### 2.3 Phase 2 / advanced legacy visual pass

**What it attempted:** make the legacy UI bolder, more modern, and more visually polished.

**What went wrong:**

- UI looked only slightly more modern.
- Rounded corners were pixelated/jagged.
- Opening tabs became slower.
- Scrollbars/page scrolling broke on many pages.
- Content became unreachable.
- Sections continued overlapping.
- Bottom action bar consumed too much space and visually covered content.
- Too much decorative chrome stole room from actual controls.

**User reaction:** frustration; the pass looked like a partial facelift but introduced major usability regressions.

### 2.4 Legacy repair/stabilization pass

Codex later repaired many legacy issues.

**Root causes found:**

- Global mousewheel handling used `bind_all()` once per `ScrollableFrame`, so every wheel event fanned out through multiple scroll containers.
- Modes, Base Tuning, Filtering, and Combat Profile lacked reliable page-level vertical scrolling.
- Footer/action bar was oversized and reduced usable viewport height.
- Too many major surfaces used a custom canvas-backed rounded renderer, adding redraw cost and jagged Windows scaling.
- Extra wrapper chrome consumed usable space.
- Hidden refresh work was already reduced, but there was not enough instrumentation for tab reuse/skips/scrollregion churn.

**Fixes implemented:**

- Simplified main shell layout.
- Workspace owned expanding middle row.
- Footer placed in its own reserved row.
- Removed “Tabs stay focused…” strip.
- Reduced header/workspace padding.
- Slimmed bottom action bar.
- Added page-level scroll containers for Modes, Base Tuning, Filtering, Combat Profile.
- Kept internal scroll where appropriate: rules list, stack columns, Helm/help workspace bodies, table horizontals.
- Replaced per-instance global wheel bindings with a single routed wheel system.
- Added cached scrollregion and width syncing.
- Preserved tab reuse.
- Added hidden-tab skip accounting.
- Moved major surfaces off canvas-rounded renderer.
- Simplified border/surface system.

**Measured performance from repair report:**

- Reused tab switches: about **1.49 ms average**, **4.53 ms max** after first-load reuse.
- Steady-state graph drawing: about **0.68 ms average**.
- Biggest first-load hotspot: shared tuning bundle build, about **548.7 ms** the first time a tuning tab was entered.

**Scroll geometry verification:**

- Modes: content height 683 vs viewport 386.
- Base: 897 vs 390.
- Filtering: 897 vs 390.
- Combat: 912 vs 390.
- Conditional Rules: 1057 vs 219.
- Effective Response Stack left: 1990 vs 137.
- Effective Response Stack right: 1084 vs 151.
- Help / Docs: 1055 vs 619.
- Helm: 757 vs 370.

**Output:** repaired build pointed to `dist_repair1`.

### 2.5 V2 frontend rebuild

**Decision:** The current UI stack had reached diminishing returns. The user wanted a complete UI redo, not another skin pass.

**Chosen stack:**

- **PySide6 / Qt Widgets** for the frontend.
- **pyqtgraph** for live/interactive graphs.
- Preserve existing backend/config/tuning/rule/bridge logic where possible.

**Reasoning:**

- Qt Widgets gives mature desktop layouts, splitters, scroll areas, tables, native UI patterns, cleaner rendering, and better professional polish.
- pyqtgraph is suitable for fast engineering/scientific plotting.
- Rebuilding the frontend allowed better looks and smoother performance while keeping the backend brain.

### 2.6 Safe parallel V2 strategy

V2 was intentionally designed as a **parallel app**, not a destructive rewrite.

**Rules established:**

- Current/legacy app remains intact and launchable.
- V2 has its own entry point, launcher, packaging target, and dist folder.
- Existing launchers should keep opening stable legacy until explicitly switched.
- V2 initially uses safe workspace/draft behavior.
- V2 should not silently overwrite original configs.
- V2 should read/import legacy but save separately until compatibility is proven.

**Suggested structure:**

```text
/shared_core
    backend logic
    config parsing
    tuning math
    rule engine
    runtime bridge adapters
    common models / DTOs

/legacy_app
    current existing frontend
    untouched except safe shared-core import adjustments if required

/v2_app
    new PySide6 frontend
    new page classes
    new widgets
    new theme system
    new graph components
    new launcher / entry point
```

### 2.7 Mapping page

**Purpose:** map raw HOTAS axes/buttons/hats to vJoy outputs.

**Visible V2 page title:** `Mapping`

**Visible copy:**

- “Map raw HOTAS axes, buttons, and hats to the bridge outputs that drive vJoy.”
- “This workspace controls the raw routing layer. The selected profile still owns the mappings, so any changes here follow the same safe draft flow as the rest of V2.”

**Status chips visible:**

- `Current Workspace`
- `Runtime Idle`
- `Mapping Ready`

**Sections:**

1. Routing Overview
   - Axis Routes: 6
   - Button Routes: 15
   - Hat Routes: 1
   - Note: “Axis, button, and hat routes are unique. Battlefield-safe runtime routing still remaps RX / RY / RZ / SL0 behind the scenes when needed.”

2. Live Route Summary
   - Shows how active workspace lands on runtime vJoy outputs.
   - Example mappings:
     - Roll: Raw axis 1 -> X -> X (axis 1)
     - Pitch: Raw axis 2 -> Y -> Y (axis 2)
     - Throttle: Raw axis 3 -> Z -> Z (axis 3)
     - Yaw: Raw axis 6 -> RZ -> RX (axis 4)
     - Aux 1: Raw axis 7 -> SL0 -> RY (axis 5)
     - Aux 2: Raw axis 8 -> RX -> RZ (axis 6)
   - Runtime idle note: “Runtime is idle. You can still edit the mapping workspace, and the bridge will pick it up the next time it is live.”

3. Axis Routing
   - Table columns:
     - Function
     - Raw Axis
     - Logical Output
     - Runtime vJoy
     - Invert
     - Live Raw
     - Live Output
   - Rows:
     - Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2.
   - Invert checkboxes.
   - Live raw/output values, e.g. `+0.00`.

4. Button Routing
   - Copy: “Map each HOTAS button to the vJoy button that should fire on output.”
   - Buttons: `Add Route`, `Remove Selected`, `Reset 1:1`.
   - Table columns:
     - HOTAS Button
     - vJoy Button
     - Raw
     - Output
   - Visible routes: buttons 6–15, values mostly `Idle`.

5. Hat Routing
   - Copy: “Drive a vJoy POV and optional directional buttons from each HOTAS hat switch.”
   - Buttons: `Add Hat`, `Remove Selected`.
   - Table columns:
     - HOTAS Hat
     - vJoy POV
     - Up
     - Right
     - Down
     - Left
     - Live
   - Visible row: HOTAS Hat 1, vJoy POV 1, direction values 7 / 18 / 19 / 0, live `Centered`.

**Footer actions visible on page:**

- `Import Profile`
- `Revert`
- `Save Workspace`

### 2.8 Modes page

**Purpose:** configure precision and combat activation modes without raw tuning details.

**Visible title:** `Modes`

**Visible copy:**

- “Configure precision and combat activation without diving into raw tuning values.”
- “Keep trigger lists, zoom gating, and the current live mode state in one clear workspace.”

**Sections:**

1. Precision Mode
   - Copy: “Buttons that enable precision scaling.”
   - Field: `Buttons`, value `0`.
   - Summary text: “Precision uses button hold detection. Configured.”

2. Combat Mode
   - Copy: “Buttons that drive combat/zoom behavior.”
   - Fields:
     - Trigger Buttons
     - Zoom Buttons, value `5`
     - Extra Buttons
     - Stack Mode, value `multiply`
   - Text: “Zoom buttons currently do activate combat behavior in the runtime layer.”

3. Live Mode State
   - Copy: “Current runtime mode evaluation from bridge telemetry.”
   - Status: `Live`.
   - State: `Normal`.
   - Values:
     - Precision off
     - Combat off
     - Trigger off
     - Zoom off
     - Extra off
     - Stack multiply

4. Mode Notes
   - Copy: “Quick reading for the current configuration.”
   - Example final product copy: “Precision engages with button 0. Combat can open from no trigger buttons, while zoom uses button 5. Extra combat gating is driven by no extra buttons. When Precision and Combat overlap, their scaling currently multiply together.”

### 2.9 Base Tuning page

**Purpose:** tune baseline response behavior before mode-specific modifiers.

**Visible title:** `Base Tuning`

**Visible copy:**

- “Shape the underlying axis response before mode-specific modifiers get involved.”
- “Changes update the current workspace immediately and are only written out when you save.”

**Layout:**

- Left column: Mapped Axes card + Parameters card.
- Right/main: Response Preview graph.
- Bottom: Live Snapshot and Guidance cards.

**Mapped Axes list:**

- Roll
- Pitch
- Throttle
- Yaw
- Aux 1
- Aux 2

**Parameters visible:**

- Curve Mode: `s`
- Curve Strength: examples `0.34`, `0.58` depending selected axis.
- Deadzone: `0.03` or `0.04`.
- Anti-Deadzone: `0.00`.
- Hysteresis: `0.00`.
- Output Scale: `1.00`.
- Max Output: `1.00`.

**Graph:**

- Title: `Response Preview`.
- Copy: “Live response preview for the selected axis.”
- X-axis raw input, Y-axis processed output.
- Linear reference line must be true `y=x`.
- Adjusted curve line shows processed response.
- Marker at center.
- `Center` control shown near graph.

**Known bug fixed:** Linear line was originally curved like the adjusted curve. It must be mathematically linear.

### 2.10 Filtering page

**Purpose:** control damping and slew behavior without rebuilding the curve.

**Visible title:** `Filtering`

**Visible copy:**

- “Control damping and slew behavior without rebuilding the whole response curve.”
- “Changes update the current workspace immediately and are only written out when you save.”

**Parameters visible:**

- Center Alpha
- Edge Alpha
- Same Slew Limit
- Reverse Slew Limit

Example values:

- Center Alpha: `0.92`, `0.88`.
- Edge Alpha: `0.92`, `0.88`.
- Same Slew Limit: `0.18`, `0.12`.
- Reverse Slew Limit: `0.18`, `0.12`.

**Graph:**

- Step preview: input vs filtered output.
- Shows raw input square-ish steps and filtered output with slew-limited response.
- Used pyqtgraph.

### 2.11 Combat Profile page

**Purpose:** tune a more constrained combat/zoom layer without disturbing baseline response.

**Visible title:** `Combat Profile`

**Visible copy:**

- “Tune the more constrained combat/zoom layer without disturbing the baseline response.”
- “Changes update the current workspace immediately and are only written out when you save.”

**Parameters visible:**

- Combat Curve
- Combat Scale
- Combat Center Alpha
- Combat Edge Alpha
- Combat Same Slew
- Combat Reverse Slew

Example values:

- Combat Curve: `0.50`, `0.72`
- Combat Scale: `0.80`, `0.68`
- Combat Center Alpha: `0.60`, `0.52`
- Combat Edge Alpha: `0.60`, `0.52`
- Combat Same Slew: `0.09`
- Combat Reverse Slew: `0.09`

**Guidance examples:**

- `Caution`
- “Feels: Stable center response, Trimmed overall authority, Heavy damping, Controlled same-direction response, Freer reversals — Smoothing is heavy and may feel sluggish, especially near small corrections.”

### 2.12 Profiles page

**Purpose:** manage built-in presets and personal profiles.

**Visible title:** `Profiles`

**Visible copy:**

- “Keep built-in presets and personal profiles in one library. The selected profile becomes the live workspace for the rest of V2.”
- Status chip: `Active Profile`.
- Text: “Current Workspace is currently live across Modes, Base Tuning, Filtering, Combat Profile, Rules, and Stack.”

**Buttons:**

- `Save Current As New`
- `Import JSON`
- `Duplicate`
- `Export JSON`
- `Use This Profile`
- `Rename`
- `Delete`

**Profile Library visible:**

- Built-In Presets:
  - Balanced Flight — Preset — Ready
  - Precision Tracking — Preset — Ready
  - Aggressive Combat — Preset — Ready
  - Smooth Cinematic — Preset — Ready
- Personal Profiles:
  - Current Workspace — Personal — Active

**Profile Detail:**

- Current Workspace.
- Loaded from current V2 workspace copy.
- Pills/chips:
  - `Personal`
  - `Active`
  - `hotas_bridge_config_v2.json`
- Copy: selecting a profile makes it active immediately. Edits elsewhere in V2 update the personal profile directly until switching to another one.

**Setup Summary fields:**

- Mapped Axes: 6
- Precision: button 0
- Combat Trigger: Not configured
- Zoom Gate: button 5
- Extra Gate: Not configured
- Stack Mode: multiply
- Enabled Rules: 0

**Profile Feel:**

Summaries per axis:

- Roll: stable center response, fast same-direction response.
- Combat: stable center response, trimmed overall authority.
- Pitch: stable center response, fast same-direction response.
- Yaw: soft near center, stable center response, strong edge ramp, etc.

### 2.13 Conditional Rules page

**Purpose:** create and inspect modifier rules that inject into the response stack based on conditions.

**Visible title:** `Conditional Rules`

**Visible copy:**

- “Build responsive modifier rules, track their live state, and see exactly where they inject into the response stack.”

**Status chips:**

- `1 rules`
- `0 active`
- `0 blocked`
- `1 disabled`

**Action buttons:**

- `Add Rule`
- `Edit Selected`
- `Duplicate`
- `Enable`
- `Delete`

**Layout:**

- Rule List on left.
- Rule Detail on right.
- Rule Logic card below/right.

**Rule visible:**

- `Yaw 0.75 | Roll > 0.35`
- Targets: `Yaw`
- Parameter: `Output Scale`
- Status: `Disabled`

**Rule details:**

- Disabled badge.
- Title: `Yaw 0.75 | Roll > 0.35`.
- Text: `Targets Yaw. Watches Roll Final Output > 0.35. Set Output Scale.`
- Disabled: rule is turned off.
- Fields:
  - Targets: Yaw
  - Parameter: Output Scale
  - Operation: Set
  - Value: 0.75
  - Injects At: Base Output Limits
  - Mode Gate: Always

**Rule Logic copy:**

- “Conditional rules are injected inline at the stage they affect. Use them for hover bands, roll-linked trims, or mode-specific filtering shifts.”
- “Select a rule to review its target axis, gating, reference signal, and injection stage in one place.”

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

### 2.15 Live Monitor page

**Purpose:** watch raw HOTAS input, final vJoy output, buttons, hats, axis levels, and live traces.

**Visible title:** `Live Monitor`

**Visible copy:**

- “Watch raw HOTAS input, final vJoy output, buttons, hats, and axis levels in one dedicated live workspace.”

**Monitor Controls:**

- Axis dropdown: Roll.
- Checkbox: `Show raw and output together`.
- `Live` status pill.

**Graphs:**

1. `Raw Input Trace · Roll`
   - Copy: “Recent raw HOTAS input for the selected axis.”
   - Line graph showing samples over time.
   - “Newest samples are on the right edge.”

2. `Raw vs Final Overlay · Roll`
   - Copy: “Recent processed output leaving the bridge for the selected axis.”
   - Shows raw and final output overlaid for direct comparison.
   - Caption: “Raw and final output are overlaid for direct comparison.”

**Cards:**

- Live State:
  - “Current mode state and bridge activity.”
  - “Precision Off | Combat Off | Trigger Off | Zoom Off”
  - “Active rules: none right now.”
- Buttons / Hats:
  - HOTAS Hat: `(0, 0)`
  - Output Hat: `(0, 0)`
  - Copy: HOTAS buttons and hats are sampled directly from source device while mapped outputs reflect current bridge state. No hat movement is active right now.
- Axis Levels:
  - Bar visualization for Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2.
  - Raw shown blue, final shown green.
  - Scale labels +1.0 to -1.0.
- HOTAS Buttons:
  - Button pills B1 through B15.
- Mapped Output Buttons:
  - Output pills Out 1 through Out 20 visible.

### 2.16 Help / Docs page

**Purpose:** built-in app guide/documentation.

**Visible title:** `Help / Docs`

**Visible copy:**

- “Search the built-in guide, browse by category, and keep the details you use most close at hand.”

**Controls:**

- Search field placeholder: `Search features, pages, or tuning terms`.
- Sort dropdown: `By Category`.

**Layout:**

- Topics tree on left.
- Guide pane on right.

**Topics tree categories visible:**

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
- Reference
  - Tuning Glossary
- Workflow
  - Saving and Importing

**Guide content example:** Conditional Rules guide explains rules answer three questions:

1. What changes? Choose target axis, parameter, operation, value.
2. When does it run? Add mode gates or button gating if needed.
3. What signal condition does it watch? Pick reference axis, processing stage, measure type, comparator, and threshold.

### 2.17 Performance / Diagnostics page

**Purpose:** show timing and instrumentation so performance claims are verifiable.

**Legacy/V2 diagnostics fields included:**

- active page
- runtime state
- selected axis
- source file
- hidden page skips
- runtime path checks
- page build/switch times
- heartbeat timing
- graph draw timings
- startup total/config/widget timing

Example metrics visible in V2 screenshot:

- `v2.active_page: perf`
- `v2.runtime: live`
- `v2.selected_axis: Yaw`
- `v2.source: V2 draft: hotas_bridge_config_v2.json`
- `v2.hidden_page_skips: 41689`
- page build timings for base, combat, stack, filtering, modes, rules, help, perf.
- page switch timings.
- heartbeat average/max.
- graph draw average/max.

### 2.18 Helm assistant

**Purpose:** built-in tuning/diagnostic assistant.

**Evolution:** Initially a normal tab in the legacy and early V2 sidebar. Later moved into a floating assistant/overlay launched from the top-right assistant cluster.

**Desired behavior:**

- Helm appears as a special assistant, not just another page.
- A small launcher/button exists in the top-right `ASSISTANT` row.
- Clicking `Helm` opens a large overlay/modal.
- Background app is dimmed/blurred/de-emphasized beneath the overlay.
- Helm has a pulsing green indicator when active/ready.
- Helm works against the current workspace and applies changes only safely/in-memory/draft until saved.

**Visible Helm overlay structure:**

- Top-left: `Helm`.
- Subtitle: “Diagnosis-first tuning guidance for the current workspace.”
- Top-right status card:
  - Green pulse indicator.
  - `Helm is active`.
  - `Context-linked assistant`.
- Close button.
- Helm intro section:
  - “Describe the control problem in plain language, let Helm inspect the current tuning context, and review the proposed workspace changes before you apply them.”
- Safety pill: `In-memory only`.
- Left card: `What’s wrong?`
  - Copy: “Describe the symptom first, then review what Helm recommends.”
  - Text box placeholder: `Example: Can't hold aim steady on target.`
  - Symptom chips:
    - Can’t hold aim steady
    - Too twitchy near center
    - Overshoots target
    - Combat mode feels sluggish
    - Reversals feel sticky
    - Hard to track smoothly
  - Action buttons:
    - Analyze
    - Review Changes
    - Cancel
- Right card: `What I’d change`
  - Copy: “Exact before-and-after diffs that can be applied to the current workspace.”
- Bottom-left card: `What I found`
  - Copy: “Diagnosis, confidence, and context from the current stack and runtime state.”
  - Status: `Idle`
  - Message: “I’m ready when you are.”
  - Copy: “Describe the symptom in plain language, then press Analyze.”
- Bottom-right card: `Apply / Revert`
  - Copy: “Helm updates the current workspace only. Save when you want to keep the result.”
  - Buttons:
    - Apply Selected Changes
    - Revert Last Helm Changes
  - Status: “Helm is standing by.”

**Earlier Helm examples:**

- User typed: “Combat mode feels sluggish.”
- Helm generated changes:
  - Yaw Combat Center Alpha 0.52 -> 0.68
  - Pitch Combat Center Alpha 0.56 -> 0.68
  - Yaw Combat Reverse Slew 0.06 -> 0.09
  - Yaw Combat Same Slew 0.06 -> 0.09
  - Yaw Combat Scale 0.68 -> 0.79
- Helm status: “5 changes ready.”
- Copy needed polish to sound natural, not machine-dumped.

### 2.19 Overlay / Recorder / Flight Recorder

**Feature mentioned from project memory in this chat:** The app had an overlay and a flight recorder concept.

**Known details preserved from conversation context:**

- Overlay could be turned on/off with a keybind.
- Flight recorder could record from the point a keybind is pressed for a specified duration.
- Alternative mode: maintain a buffer for a specified duration and, when keybind is pressed, save the current buffer — described by user as “hindsight.”
- Intended purpose: capture control behavior around flight moments so tuning problems could be reviewed after they occur.
- Mentioned as already existing in earlier HOTAS project work.

**Needed rebuild note:** This chat did not provide screenshots of the overlay/recorder UI in the later V2, but the behavior should be preserved as a planned/known feature.

### 2.20 App packaging / installation

**User goal:** make the app feel like a real Windows app, not a desktop shortcut into a folder full of support files.

**Recommended final deployment model:**

- PySide6 app build.
- One-folder release build, not necessarily one-file.
- Inno Setup installer.
- Real `.ico` icon embedded in EXE/installer/shortcuts.
- Start Menu shortcut.
- Optional Desktop shortcut.
- Uninstaller entry.
- App files installed to a normal install directory:
  - `%ProgramFiles%\HOTAS Control Panel V2`
  - or `%LocalAppData%\Programs\HOTAS Control Panel V2`
- User data stored separately:
  - `%AppData%\HOTASControlPanelV2`
  - or `%LocalAppData%\HOTASControlPanelV2`

**Important principle:** app binaries/support files live in install folder; editable user data lives in AppData.

### 2.21 App icon

Two icon directions were generated/discussed:

1. Detailed icon
   - Dark rounded-square frame.
   - HOTAS throttle and joystick hardware.
   - Cyan/teal graph lines and tuning display.
   - Word `HOTAS` at bottom.
   - Premium, glossy, detailed.
   - Best for large installer/about-page/icon preview sizes.
   - Possible downside: too detailed at 16x16 or taskbar size.

2. Simplified/bolder taskbar icon
   - Dark navy rounded-square background.
   - Minimal white joystick silhouette.
   - Cyan gauge arc / response curve behind it.
   - Cyan bar/level indicators to the side.
   - No small detailed text.
   - Designed to read better at small taskbar/start-menu sizes.
   - Better for Windows taskbar and Start Menu.

**Important note:** Need convert simplified PNG into multi-size `.ico` with embedded sizes such as 16, 24, 32, 48, 64, 128, 256.

---

## 3. UI / UX Reconstruction

### 3.1 General V2 window layout

The final V2 UI uses a dark modern layout with:

- Left vertical sidebar.
- Main content workspace to the right.
- Top header across main content.
- Top-right status cluster and assistant launcher.
- Scrollable central page area.
- Bottom footer/action/status bar.
- Rounded cards/panels everywhere.
- Blue/cyan accent colors.
- Green live/active status colors.
- Red/destructive/caution states where needed.

### 3.2 Color palette inferred

Approximate colors/inferred roles:

- App background: very dark navy/blue-black.
- Sidebar/card surfaces: slightly lighter navy.
- Card border: muted blue/cyan stroke.
- Active nav background: richer blue.
- Active nav left accent: bright cyan vertical bar.
- Primary button: blue/cyan filled or bordered.
- Status live/active: green/teal glow.
- Warning/caution: amber/yellow/orange.
- Disabled/destructive: red/dark red.
- Text: white for headings, pale blue-gray for secondary text.
- Graph grid: subtle dark blue grid lines.
- Graph curves: cyan/blue, green, gray linear/reference.

### 3.3 Typography

No exact font file named. Inferred style:

- Modern sans-serif.
- Bold white headings.
- Smaller pale-blue helper/caption text.
- Monospace used in diagnostics areas and live values.
- Product copy became concise and polished.

### 3.4 Rounded corners

Rounded corners became a hard preference:

- Buttons rounded.
- Cards rounded.
- Sidebar rounded.
- Header/status panels rounded.
- Inputs/dropdowns rounded.
- Overlay rounded.
- App icon rounded-square.

Important implementation rule: use Qt/QSS/native styling, not heavy custom canvas corner renderers. Avoid jagged/pixelated corners and expensive custom painting.

### 3.5 Status vs button semantics

Problem noticed in early V2: status chips and action buttons looked too similar.

Final direction:

- Status chips should be small, quiet, non-button-like:
  - Workspace Copy
  - Saved
  - Idle/Live
- Action buttons should look clickable:
  - Import Profile
  - Revert
  - Save Workspace
  - Helm
- Primary actions should have stronger emphasis.

### 3.6 Sidebar

Final sidebar contents:

- Title: `HOTAS V2`
- Subtitle: `Control workspace`
- Navigation items:
  - Mapping
  - Modes
  - Base Tuning
  - Filtering
  - Combat Profile
  - Profiles
  - Conditional Rules
  - Effective Response Stack
  - Live Monitor
  - Help / Docs
  - Perf / Diagnostics
- Active page highlight:
  - Rounded blue item background.
  - Cyan border/outline.
  - Bright cyan vertical accent at left.
- Bottom live status card:
  - Dot/pulse indicator.
  - Label `Runtime`.
  - State `Idle` or `Live`.

### 3.7 Header/top-right cluster

Final header:

- Main title: `HOTAS Control Panel V2`
- Subtitle: `Professional tuning, live inspection, and assistant-guided diagnostics in one modern control workspace.`
- Top-right `STATUS` cluster:
  - `Workspace Copy`
  - `Saved`
  - `Idle` or `Live`
- Top-right `ASSISTANT` cluster:
  - `Helm` button.

### 3.8 Footer

Final footer includes:

- Left status message, e.g. “Reverted the workspace to the last saved or imported state.”
- Center details:
  - Page: mapping/base/filtering/combat/profiles/rules/stack/monitor/help.
  - Axis: Roll.
  - Profile: Current Workspace.
  - Source: Workspace copy: `hotas_bridge_config_v2.json`.
- Right action buttons:
  - `Import Profile`
  - `Revert`
  - `Save Workspace`

### 3.9 Animation/motion direction

Desired and partially implemented:

- Subtle page transition fade/fade+slide.
- Sidebar active-state transition.
- Live/assistant pulse/breathe indicator.
- Helm overlay open/close transition.
- Avoid graph data animation and heavy effects that cause jank.

---

## 3.10 Screenshot Reconstruction

> Screenshots are not embedded in this Canvas document. Each screenshot below is a placeholder/description so it can be manually reattached later.

### Screenshot 1 — Legacy Modes tab, broken/old Phase 2 style

Visible legacy app title: `HOTAS Control Panel`. Top dark header with cyan line. Top-right buttons: `Saved`, `Helm`, `Perf Off`, `Help / Docs`. Main tab row includes `Modes`, `Base Tuning`, `Filtering`, `Combat Profile`, `Conditional Rules`, `Effective Response Stack`. Modes tab active. Page brief card: “Choose which buttons activate precision and combat behavior, and how those modes combine.” Trigger Sources card with inputs for Precision Hold Buttons (`0`), Combat Trigger Buttons, Combat Zoom/Aim Buttons (`5`), Combat Extra Buttons. Bottom workspace actions bar: Reload, Reset Defaults, Open Live Monitor, Save, Save + Restart Bridge, Close. UI has cyan glowing borders, jagged rounded corners, and large chrome.

### Screenshot 2 — Legacy Base Tuning tab with preview graph

Base Tuning active. Page brief: “Tune each axis’s baseline feel, including curve shape, center behavior, and output limits.” Left table shows axes Roll, Pitch, Throttle, Yaw, Aux 1/Aux 2 with columns Axis, Mapping, Curve, k, Deadzone, Anti-DZ, etc. Right Instrument View card: `Axis Response Preview`, controls Axis, Preview Mode, Compare Against, checkboxes `Show linear reference`, `Linear reference follows deadzone`. Graph titled `LIVE RESPONSE PLOT`. Bottom footer overlays large action bar. Some content clipped.

### Screenshot 3 — Legacy Filtering tab

Filtering active. Page brief: “Control smoothing and slew limiting so each axis responds cleanly near center and during fast changes.” Left table columns Axis, Mapping, Center Alpha, Edge Alpha, Same Slew, Reverse Slew. Right Instrument View: `Filtering Preview`, controls Axis and Test, graph shows input vs filtered line. Heavy nested cards and scrollbars.

### Screenshot 4 — Legacy Combat Profile tab

Combat Profile active. Page brief: combat mode curve strength, damping, and rate limiting. Left table includes Combat k, Combat Scale, Center Alpha, Edge Alpha. Right `Combat Response Preview` graph. Still crowded and overlapping in old style.

### Screenshot 5 — Legacy Conditional Rules tab

Conditional Rules active. Header card: `Conditional Rule Stack`, text explains conditional rules reshape axes/modes on the fly. Button `+ Add Conditional Rule`. Rule card visible: `Yaw 0.75 | Roll > 0.35`, status `DISABLED`, badges `WARNING`, `DISABLED`, buttons Collapse/Remove. Rule Preview says Set Yaw Output Scale to 0.75 when absolute Roll final output greater than 0.35. Layout has huge empty right space and scroll.

### Screenshot 6 — Legacy Effective Response Stack tab

Effective Response Stack active. Page brief: inspect full live processing chain. Controls Axis Roll, Graph Mode Raw vs Final, Stack View Show All Stages, `LIVE`, `Freeze`, `Copy Snapshot`. Left stage card `Raw Input`, right Instrument View `Effective Response Graph`. Large bottom footer bar.

### Screenshot 7 — Legacy Helm workspace/tab

Helm was a page/tab-like diagnostic workspace. Left small status `Helm is active`. Main title `Helm`, copy about describing problem in plain language and inspecting stack/modes/live rule context. Sections: `What's wrong?`, `What I'd change`, `Apply / Revert`. Buttons include Revert Last Helm Changes, Cancel, Apply Selected Changes. At this point Helm was not yet overlay.

### Screenshot 8 — Legacy Performance popup

Top-right `Perf On`. Popup titled `Performance`, close button. Text: “Lightweight timings for the live UI paths. Keep it off during normal tuning.” Checkbox `Collect live timings`, button Clear. Current live diagnostics show Visible tab Stack, Selected axis Roll, runtime timestamp unavailable, pending refresh counts, next scheduler tick.

### Screenshot 9 — Legacy Help / Tuning Notes popup

Popup on right side titled `Help & Tuning Notes`, close button. Cards explain `Curves` and `Deadzone / Anti-Deadzone / Hysteresis`. Old help panel is narrow and has excessive dead space.

### Screenshot 10 — Repaired legacy Modes tab

After repair pass: UI flatter/crisper, fewer heavy rounded fake borders, proper scrollbars. Sidebar not yet V2. Modes page now scrollable. Header still legacy layout but less bloated. Footer action row slimmed.

### Screenshot 11 — Repaired legacy Base Tuning tab

Shows the old notebook tab system but with better scroll handling and less jagged chrome. Base table and graph visible. Page scroll bar on right; footer no longer covers content as severely.

### Screenshot 12 — Repaired legacy Filtering tab

Filtering page readable with scrollbars, left table and right preview graph. Still legacy style but much more stable.

### Screenshot 13 — Repaired legacy Combat Profile tab

Combat Profile page stabilized. Left table and right graph visible; scrolling improved.

### Screenshot 14 — Repaired legacy Conditional Rules tab

Conditional Rules layout improved enough to be usable. Still lots of empty right-side space. Rule card readable.

### Screenshot 15 — Repaired legacy Effective Response Stack tab

Stack page with filter row and two-pane layout. Still legacy but stable. Content reachable with scroll.

### Screenshot 16 — Initial PySide6 V2 Modes page

First V2 shell. Left sidebar titled `HOTAS V2`, subtitle `Safe parallel Qt frontend`. Nav items include Modes, Base Tuning, Filtering, Combat Profile, Conditional Rules, Effective Response Stack, Helm, Help / Docs, Perf / Diagnostics. Header says `HOTAS Control Panel V2`, subtitle “A ground-up Qt / pyqtgraph frontend running beside the stable legacy app.” Top-right chips `V2 draft`, `Clean`, `Runtime live`, buttons `Import Legacy`, `Save V2 Draft`. Modes page uses rounded cards for Precision Mode, Combat Mode, Live Mode State, Mode Notes.

### Screenshot 17 — Initial V2 Base Tuning page

Base Tuning active. Left Mapped Axes and Parameters panels. Main graph `Response Preview` using pyqtgraph. Linear line initially wrong/curved issue noticed. Bottom cards: Live Snapshot and Guidance. UI already much smoother and modern.

### Screenshot 18 — Initial V2 Filtering page

Filtering active. Similar layout to Base. Graph shows step response. Parameter fields for Center Alpha, Edge Alpha, Same Slew, Reverse Slew. Guidance and live snapshot cards.

### Screenshot 19 — Initial V2 Combat Profile page

Combat Profile active. Graph shows combat curve. Guidance card can show `Extreme` status in red. Parameter panel lists combat curve/scale/alpha/slew values.

### Screenshot 20 — Initial V2 Conditional Rules page

Rules page is read-only/conservative. Rule list on left and rule detail on right. Text explicitly says editing stays conservative in first safe parallel pass. User later wanted this polished and less placeholder-like.

### Screenshot 21 — Initial V2 Effective Response Stack page

Signal Chain left, graph right, Mode State, Current Stack Summary, Selected Stage, Rule Driver Values. Signal chain had twitching glitch every few seconds. This page looked like crown jewel but needed stability.

### Screenshot 22 — Initial V2 Helm page/tab

Helm was still a sidebar page. It showed What’s wrong, What I’d change, What I found, Apply/Revert. User wanted Helm moved out of sidebar into a floating assistant overlay.

### Screenshot 23 — Initial V2 Help / Docs page

Help content was simple text page with product philosophy and page overview. Later upgraded into searchable topic tree.

### Screenshot 24 — Initial V2 Perf / Diagnostics page

Diagnostics page with dense timing text: active page, runtime live, hidden page skips, page build/switch timings, heartbeat stats, graph timings. Confirms performance instrumentation was built in.

### Screenshot 25 — Final V2 Mapping page, top overview

Sidebar final text `HOTAS V2`, `Control workspace`. Mapping selected. Header final copy: “Professional tuning, live inspection, and assistant-guided diagnostics in one modern control workspace.” Status cluster: STATUS Workspace Copy / Saved / Idle. Assistant cluster with Helm button. Mapping page shows routing overview, live route summary, axis routing table, footer actions.

### Screenshot 26 — Final V2 Mapping page, lower routing

Scrolled Mapping page shows Axis Routing table, Button Routing and Hat Routing cards. Button routing table contains HOTAS Button/vJoy Button/Raw/Output. Hat routing has HOTAS Hat, vJoy POV, Up/Right/Down/Left/Live. Footer has Import Profile, Revert, Save Workspace.

### Screenshot 27 — Final V2 Modes page

Modes selected in sidebar. Page has clean cards with Precision Mode, Combat Mode, Live Mode State, Mode Notes. Dark background is calmer; no ugly dark text strips. Active sidebar highlight works correctly.

### Screenshot 28 — Final V2 Base Tuning page

Base Tuning selected. Graph shows linear gray reference and curved blue/green response lines. Mapped Axes list, parameters, live snapshot, guidance. Linear reference now appears straight. `Center` control visible near graph.

### Screenshot 29 — Final V2 Filtering page

Filtering selected. Graph shows raw step/reference and filtered response. Left parameter panel. Live Snapshot and Guidance cards. Clean final copy and no developer wording.

### Screenshot 30 — Final V2 Combat Profile page

Combat Profile selected. Graph shows multiple lines; guidance card has `Caution` badge. Text reads more product-like. Parameter fields listed on left.

### Screenshot 31 — Final V2 Profiles page

Profiles selected. Profile Library left with Built-In Presets and Personal Profiles. Detail panel right. Setup Summary, Profile Feel, Profile Actions. Buttons include Save Current As New, Import JSON, Duplicate, Export JSON, Use This Profile, Rename, Delete.

### Screenshot 32 — Final V2 Conditional Rules page

Conditional Rules selected. Status chips show rules counts. Action buttons Add Rule, Edit Selected, Duplicate, Enable, Delete. Rule list and detail split. Rule detail is much cleaner and product-like.

### Screenshot 33 — Final V2 Effective Response Stack page

Effective Response Stack selected. Signal Chain card left with Raw Input, Center Conditioning, Curve/Shape stage cards. Graph right. Stage cards use colored live/active badges and clean signal bars. No old twitch visible in screenshot.

### Screenshot 34 — Final V2 Live Monitor page, graph view

Live Monitor selected. Runtime Live in sidebar and top status. Monitor Controls card with Axis dropdown and checkbox. Raw Input Trace graph and Raw vs Final Overlay graph. Shows live-looking plotted data.

### Screenshot 35 — Final V2 Live Monitor page, axis/buttons view

Scrolled Live Monitor shows Axis Levels bar chart: Roll/Pitch/Throttle/Yaw/Aux1/Aux2 raw and final bars. HOTAS Buttons B1–B15 and Mapped Output Buttons Out 1–Out 20 visible. Strong professional live telemetry feel.

### Screenshot 36 — Final V2 Help / Docs page

Help / Docs selected. Search bar, Sort by Category dropdown, Topics tree, Guide pane. Conditional Rules article selected. Looks like integrated product documentation.

### Screenshot 37 — Final V2 Helm overlay

Helm overlay open over dimmed app. Background app visible/dimmed. Overlay rounded and large. Top status card with green pulsing circle, `Helm is active`, `Context-linked assistant`, Close button. Main content sections as described under Helm. This confirms Helm is no longer a sidebar page.

### Screenshot 38 — Detailed app icon

Detailed rounded-square dark metallic icon with throttle, joystick, cyan response curve, graph display, and `HOTAS` text. Premium but too detailed for tiny taskbar sizes.

### Screenshot 39 — Simplified taskbar app icon

Simpler dark navy rounded-square icon with white joystick silhouette, cyan gauge/curve arc, and cyan bar indicators. Best for taskbar/Start Menu scale. Needs conversion to multi-size `.ico`.

---

## 4. Software Architecture / Technical Design

### 4.1 Legacy architecture details

Known/mentioned files:

- `hotas_control_panel_app.py`
  - Main legacy UI/app logic.
  - Received layout repair, page scrolling, centralized wheel routing, tab/perf instrumentation, compact footer, scroll tracking.
- `app_performance.py`
  - Performance coordination/refactor work.
- `hotas_ui_theme.py`
  - Surface rendering strategy, visual tokens, chrome/border behavior.
- `Open-HOTAS-Control-Panel.cmd`
  - Launcher.
- `Edit-HOTAS-Curves.cmd`
  - Launcher/editor helper.

### 4.2 Legacy performance architecture

- Coordinated heartbeat instead of competing refresh timers.
- Adaptive runtime polling.
- Hidden/non-live areas polled less.
- Targeted dirty tracking per tab instead of whole-app snapshots.
- Preview math caching.
- Hidden-tab skip counters.
- Graph render timing.
- Scroll region instrumentation.

### 4.3 V2 architecture target

Frontend:

- Python + PySide6 / Qt Widgets.
- pyqtgraph for live plots and response previews.

Architecture concepts:

- `QMainWindow` shell.
- Left sidebar navigation.
- Header/status/assistant area.
- Central stacked page container.
- Footer action/status bar.
- `QScrollArea` for tall pages.
- `QSplitter`/resizable layouts where useful.
- Lazy page construction.
- Reused page instances.
- Hidden pages skip expensive work.
- Scoped graph updates.
- Signals/slots for cross-component updates.
- Theme/QSS design system.

Recommended folder layout:

```text
v2_app/
  main.py / app entry point
  ui/
  pages/
  widgets/
  adapters/
  services/
  models/
  theme/
shared_core/
  config models/parsing
  tuning math
  rule engine
  runtime bridge adapters
  common domain models
legacy_app/
  preserved original frontend
packaging/
  build scripts
  installer scripts
  icon assets
```

### 4.4 State management

V2 uses a safe workspace/draft model:

- Source file visible: `hotas_bridge_config_v2.json`.
- Status chip: `Workspace Copy`.
- Saved state: `Saved` / `Clean` earlier.
- Runtime state: `Idle` / `Live`.
- Footer says `Profile: Current Workspace`.
- Changes update current workspace immediately and write out only when saved.
- Import Profile, Revert, Save Workspace available globally.
- Helm changes apply only to current workspace/draft until saved.

### 4.5 Data flow inferred

1. Physical HOTAS input is read by runtime bridge.
2. Mapping page routes raw axes/buttons/hats to logical outputs and runtime vJoy outputs.
3. Base Tuning shapes underlying axis response.
4. Filtering applies smoothing and slew limits.
5. Modes determine Precision/Combat/Trigger/Zoom/Extra states.
6. Combat Profile applies combat/zoom-specific response modifiers.
7. Conditional Rules inject changes inline at stages.
8. Effective Response Stack shows full pipeline.
9. Live Monitor samples raw/final runtime values.
10. Profiles store selectable config sets.
11. Helm reads current tuning context and proposes workspace diffs.

---

## 5. Control Mapping and HOTAS Logic

### 5.1 Axis mappings

Final Mapping page examples:

- Roll: Raw axis 1 -> X -> X (axis 1)
- Pitch: Raw axis 2 -> Y -> Y (axis 2)
- Throttle: Raw axis 3 -> Z -> Z (axis 3)
- Yaw: Raw axis 6 -> RZ -> RX (axis 4)
- Aux 1: Raw axis 7 -> SL0 -> RY (axis 5)
- Aux 2: Raw axis 8 -> RX -> RZ (axis 6)

**Battlefield-safe routing note:** runtime routing may remap RX / RY / RZ / SL0 behind the scenes when needed.

### 5.2 Button mappings

- HOTAS buttons mapped to vJoy buttons.
- Button routing table supports add/remove/reset 1:1.
- Visible mapped buttons: 6–15 in one screenshot.
- Live Monitor shows HOTAS Buttons B1–B15 and mapped output buttons Out 1–Out 20.

### 5.3 Hat mappings

- HOTAS Hat 1 mapped to vJoy POV 1.
- Optional directional buttons for Up/Right/Down/Left.
- Visible values: Up 7, Right 18, Down 19, Left 0.
- Live state: Centered.

### 5.4 Response tuning parameters

Base tuning:

- Curve Mode (`s` / S-Curve)
- Curve Strength / k
- Deadzone
- Anti-Deadzone
- Hysteresis
- Output Scale
- Max Output

Filtering:

- Center Alpha
- Edge Alpha
- Same Slew Limit
- Reverse Slew Limit

Combat profile:

- Combat Curve
- Combat Scale
- Combat Center Alpha
- Combat Edge Alpha
- Combat Same Slew
- Combat Reverse Slew

Modes:

- Precision Hold Buttons: button 0.
- Combat Trigger Buttons: optional/blank.
- Combat Zoom/Aim Buttons: button 5.
- Combat Extra Buttons: optional/blank.
- Precision + Combat Stack Mode: multiply.

### 5.5 Flight/Battlefield control logic

The app was intended for HOTAS tuning in flight/vehicle games, especially Battlefield-style control constraints.

Important inference from UI:

- Precision Mode helps steady aim/tracking by scaling authority.
- Combat Mode/Zoom gating applies different curve/smoothing behavior when zooming/aiming/combat input is active.
- Battlefield-safe runtime routing remaps logical axes to runtime vJoy outputs to satisfy game expectations.
- Per-axis response tuning helps roll, pitch, throttle, yaw, and auxiliary controls feel controllable.

---

## 6. Visual Tools / Graphs / Curve Editor

### 6.1 Base response graph

- Shows raw input on X axis and processed output on Y axis.
- Contains true linear reference line.
- Contains adjusted curve line(s).
- Center marker.
- Used to preview S-curve/deadzone/output scale effects.

### 6.2 Filtering graph

- Step preview.
- Shows input vs filtered output over time.
- Demonstrates smoothing and slew limits.

### 6.3 Combat graph

- Shows combat-mode response curve.
- Can compare baseline/reference vs combat output.
- Guidance warns when values feel extreme/cautious.

### 6.4 Effective Response Stack graph

- Raw vs Final graph for selected axis.
- Marker rides on effective response line.
- Shows relationship between raw HOTAS input and final output after stack.

### 6.5 Live Monitor graphs

- Raw Input Trace: recent raw samples over time.
- Raw vs Final Overlay: raw and final output overlaid.
- Axis Levels: bar visualization for each axis, raw blue/final green.

### 6.6 Graph technical stack

- pyqtgraph selected for fast interactive engineering graphs.
- Graph updates should be scoped locally.
- Avoid full page redraw on graph changes.
- Avoid constant graph animation.
- Graphs should resize smoothly and look integrated.

---

## 7. Overlay / Recorder / Flight Recorder Features

The chat references an already-existing overlay/recorder system from the HOTAS app project:

- Overlay can be toggled with a keybind.
- Flight Recorder can start recording when keybind is pressed for a specified duration.
- Alternative “hindsight” mode buffers the last N seconds and saves the buffer when keybind is pressed.
- Intended for reviewing control behavior after a maneuver or bad-feeling moment.
- Helps tune controls using captured evidence.

Missing details:

- No screenshots of the overlay recorder in this chat.
- No exact file names/code shown.
- No specific export format shown.

Rebuild note:

- Include overlay/recorder as a known later feature after V2 core UI stabilizes.
- Should integrate with Live Monitor/Perf/diagnostics if rebuilt.

---

## 8. Helm Assistant / Built-in Assistant Concept

### 8.1 Name and purpose

Assistant name: **Helm**.

Purpose:

- Diagnose control-feel problems from plain language.
- Inspect current stack/modes/rules/runtime context.
- Recommend tuning changes.
- Apply selected changes safely to in-memory/current workspace draft.
- Let user review before saving.

### 8.2 UI evolution

Legacy:

- Helm button in top-right header.
- Opened a full Helm page/workspace.

Early V2:

- Helm existed as a left sidebar tab.

Final V2:

- Helm removed from normal sidebar.
- Top-right assistant cluster with `Helm` button.
- Opens modal overlay with dimmed/blurred app beneath.
- Green pulsing status indicator.

### 8.3 Helm interaction model

User enters a symptom or clicks a symptom chip.

Example symptom chips:

- Can’t hold aim steady
- Too twitchy near center
- Overshoots target
- Combat mode feels sluggish
- Reversals feel sticky
- Hard to track smoothly

Helm then:

1. Analyzes current workspace.
2. Produces confidence/readout.
3. Recommends exact before/after diffs.
4. Allows applying selected changes.
5. Allows reverting last Helm changes.
6. Does not auto-save permanently; user must save workspace.

### 8.4 Helm tone goals

- Confident.
- Concise.
- Calm.
- Premium.
- Helpful.
- Intelligent.
- Not robotic.
- Not repetitive.
- Not a raw machine diff dump.

Preferred `What I Found` structure:

- Concise top-level diagnosis.
- Why Helm believes it.
- Recommended first changes.
- What is deprioritized.
- Confidence/priority framing.

---

## 9. Code Snippets / Implementation Details

No full production source code snippets were provided in this chat. The chat contains implementation briefs, architecture prompts, Codex result reports, file names, and UI screenshots.

### 9.1 Key implementation briefs from this chat

Important prompts were created for Codex:

1. Legacy Phase 3 layout/performance/render repair.
2. PySide6/Qt frontend rebuild using pyqtgraph.
3. Safe parallel V2 migration.
4. Ground-up V2 frontend overhaul with rounded corners and premium polish.
5. V2 correctness/semantics/premium polish update.
6. Final premium polish/productization pass.
7. Windows packaging/installer/icon setup.

### 9.2 Important file/component names preserved

Legacy:

- `hotas_control_panel_app.py`
- `app_performance.py`
- `hotas_ui_theme.py`
- `Open-HOTAS-Control-Panel.cmd`
- `Edit-HOTAS-Curves.cmd`
- `HOTASControlPanel.exe`

V2/packaging expected:

- `v2_app/`
- `shared_core/`
- `legacy_app/`
- `packaging/`
- `packaging/inno/`
- `packaging/build_release.ps1` or similar.
- `dist_v2_release/`
- `installer_output/`
- `assets/app_icon.ico`

### 9.3 Dependencies mentioned

- PySide6 / Qt Widgets.
- pyqtgraph.
- Possible packaging tools:
  - `pyside6-deploy`
  - PyInstaller one-folder build
  - Inno Setup installer

---

## 10. Bugs, Problems, and Fixes

### 10.1 Legacy Phase 2: pixelated rounded corners

- Symptom: rounded corners looked jagged/pixelated.
- Likely cause: custom canvas-backed rounded renderer, aliased custom drawing, scaled assets, too many outline/shadow layers, DPI scaling mismatch.
- Fix: move major surfaces off canvas-rounded renderer, use cleaner frame-backed shells, reduce border/shadow spread, later switch to Qt/QSS border-radius in V2.
- Status: legacy repaired; V2 solved more cleanly.

### 10.2 Legacy Phase 2: missing/broken scrollbars

- Symptom: user could not view full page on tabs.
- Cause: bad scroll container structure and `bind_all()` wheel routing per instance.
- Fix: page-level scroll containers, centralized wheel routing, cached scrollregion/width sync.
- Status: repaired.

### 10.3 Legacy Phase 2: slow tab switching

- Symptom: tab switching became slower.
- Likely cause: rebuilding tab contents, canvas redraws, graph redraws, layout thrash.
- Fix: tab reuse instrumentation, reduced custom rendering, hidden-tab skip accounting.
- Status: improved; V2 later addressed fundamentally.

### 10.4 Legacy Phase 2: bottom action bar clipping content

- Symptom: bottom workspace actions covered/reduced usable content.
- Fix: footer made compact and explicitly reserved in layout.
- Status: repaired.

### 10.5 V2 early: active sidebar page indicator wrong

- Symptom: Modes stayed highlighted even when on other pages.
- Fix: active page selection state must update correctly; final screenshots show correct active states.
- Status: fixed.

### 10.6 V2 early: Base Tuning Linear line was curved

- Symptom: “Linear” reference line looked like transformed/adjusted curve.
- Cause: reference line likely reused transformed dataset.
- Fix: plot true `y=x` line independently.
- Status: final screenshots show straight reference line.

### 10.7 V2 early: Effective Response Stack micro-seizure

- Symptom: Signal Chain visually glitched every few seconds.
- Likely cause: timer/heartbeat rebuilding cards, layout invalidation, live refresh thrash, widget recreation.
- Fix: update values in place, reuse stage widgets, avoid layout churn.
- Status: final screenshots look stable; verify live runtime.

### 10.8 V2 early: top-right statuses looked like buttons

- Symptom: V2 Draft/Clean/Runtime Live looked like Import/Save buttons.
- Fix: split status chips and action buttons visually.
- Status: final top-right cluster uses `STATUS` chips and `ASSISTANT` row.

### 10.9 V2 early: Helm symptom chips looked like action buttons

- Symptom: What’s Wrong suggestions confused with Analyze/Review/Cancel buttons.
- Fix: make chips lighter/smaller and action buttons distinct.
- Status: final overlay improved.

### 10.10 V2 early: dark strips behind text looked awful

- Symptom: every text area had darker strip background; muddy/striped.
- Fix: simplify surface hierarchy: app background, card background, control/input background.
- Status: final screenshots much cleaner.

### 10.11 V2 copy too debug/prototype-like

- Symptom: text like “safe parallel Qt frontend,” “V2 draft,” “this page writes only…” sounded dev/test.
- Fix: product-grade copy pass.
- Status: final copy is much more polished, though some status terms like Workspace Copy remain intentionally visible.

### 10.12 Icon generation workflow failure

- Symptom: user asked for a second simplified icon variant and eventually got frustrated because output handling did not match request.
- Correct expected output: generate simpler bold icon and convert/export actual `.ico` file, not merely PNG/image preview.
- Remaining task: ensure simplified variant is converted to multi-size `.ico` and linked/placed at `assets/app_icon.ico`.

---

## 11. Design Decisions and Preferences

### 11.1 Things the user liked

- PySide6/Qt V2 direction.
- Modern dark premium UI.
- Rounded corners everywhere.
- New Mapping page.
- New Profiles page.
- Live Monitor page.
- Help/Docs page after improvement.
- Effective Response Stack as a premium/crown-jewel page.
- Helm as overlay assistant rather than sidebar tab.
- Pulsing green live/Helm indicator.
- Graph integration with pyqtgraph.
- Clear active sidebar highlight.
- Status/footer live indicators.

### 11.2 Things the user disliked

- Legacy UI looking like “hardcoded decent html at best.”
- Pixelated/jagged rounded corners.
- Slow tab switching.
- Redraw skipping/loading effect.
- Missing scrollbars/unreachable content.
- Overlap/clipping.
- Bottom action bar taking too much room.
- Darker strips behind all text.
- Status chips looking like buttons.
- Helm suggestions looking like action buttons.
- Machine/copy-paste Helm output.
- Debug/test/internal wording.

### 11.3 Performance expectations

- Smooth tab switching.
- No obvious redraw jank.
- No visible whole-page repaint on scroll/tab switch.
- Graph updates scoped to graph.
- Hidden pages do not do expensive work.
- Performance instrumentation visible.
- Animations tasteful and not expensive.

### 11.4 Packaging preferences

- Real app installation.
- User sees one app/shortcut, not folder full of files.
- Real app icon.
- Start Menu/desktop shortcuts.
- AppData for user configs/profiles/logs.
- Installer/uninstaller.

---

## 12. Rebuild Checklist

### 12.1 Must-have features

- [ ] Safe parallel V2 frontend in PySide6.
- [ ] pyqtgraph graphs.
- [ ] Left sidebar navigation.
- [ ] Header with status cluster and Helm launcher.
- [ ] Footer with status and save/import/revert actions.
- [ ] Mapping page.
- [ ] Modes page.
- [ ] Base Tuning page.
- [ ] Filtering page.
- [ ] Combat Profile page.
- [ ] Profiles page.
- [ ] Conditional Rules page.
- [ ] Effective Response Stack page.
- [ ] Live Monitor page.
- [ ] Help / Docs page.
- [ ] Perf / Diagnostics page.
- [ ] Helm overlay assistant.
- [ ] Runtime status indicators.
- [ ] Save/import/revert workspace model.
- [ ] App packaging/installer.
- [ ] App icon.

### 12.2 Nice-to-have / later features

- [ ] Flight Recorder / hindsight buffer.
- [ ] Overlay toggle with keybind.
- [ ] Richer Helm analysis text.
- [ ] More detailed profile editing.
- [ ] Full native rule editor.
- [ ] Export/import profile library.
- [ ] More animation polish.
- [ ] About/update/check-for-updates panel.

### 12.3 Implementation order

1. Preserve legacy app.
2. Extract/define shared core interfaces.
3. Build V2 Qt shell.
4. Build design system/QSS.
5. Implement mapping/workspace/profile state.
6. Implement tuning pages and graphs.
7. Implement rules/stack/live monitor.
8. Implement Helm overlay.
9. Implement Help/Docs/Perf.
10. Add polish/copy/animations.
11. Package with installer and icon.
12. Test end-to-end.

### 12.4 Testing/debug checklist

- [ ] Legacy app still launches.
- [ ] V2 launches separately.
- [ ] Active nav state correct for every page.
- [ ] All pages scroll if needed.
- [ ] No overlap/clipping at common window sizes.
- [ ] Base linear reference is truly linear.
- [ ] Graphs update without whole-page jank.
- [ ] Effective Response Stack does not twitch.
- [ ] Hidden pages skip work.
- [ ] Runtime live/idle indicators accurate.
- [ ] Save workspace writes correct file.
- [ ] Revert restores last saved/imported state.
- [ ] Import Profile works safely.
- [ ] Helm apply/revert only affects workspace/draft until saved.
- [ ] Installer installs/uninstalls cleanly.
- [ ] App icon appears on EXE, installer, Start Menu, taskbar.

---

## 13. Unknowns / Gaps

- Exact original source code is missing.
- Exact internal data schema for `hotas_bridge_config_v2.json` not shown.
- Exact runtime bridge implementation not shown.
- Exact vJoy library/API calls not shown.
- Exact controller polling method not shown.
- Flight Recorder/overlay details mentioned but not fully shown in screenshots.
- No complete packaging scripts shown yet.
- Simplified app icon PNG exists conceptually, but final `.ico` conversion path must be completed.
- Exact animation implementation not shown.
- Exact Helm diagnostic algorithm not provided; only UI behavior and example output.
- Exact profile JSON schema unknown.
- Exact rule engine schema unknown beyond visible fields.

Questions to answer later:

1. What is the full config schema?
2. What Python modules handle vJoy and physical HOTAS input?
3. What runtime bridge process/API exists?
4. What exact package/version requirements are needed?
5. Should installer be per-user or per-machine?
6. Should V2 eventually become default launcher?
7. Should legacy be kept installed side-by-side forever?

---

## 14. Codex / AI Rebuild Prompt

```text
You are rebuilding HOTAS Control Panel V2 from recovery notes.

The original app was erased. Use these notes as the blueprint. The goal is to rebuild a polished PySide6 / Qt Widgets desktop app for HOTAS/vJoy mapping, tuning, live monitoring, profiles, conditional rules, effective response stack inspection, and Helm assistant diagnostics.

Do not rebuild the old legacy custom-painted UI. Build the V2 architecture.

Core stack:
- Python
- PySide6 / Qt Widgets
- pyqtgraph for all live/interactive graphs
- Shared backend/core modules for config, tuning math, rule engine, runtime bridge adapters, profiles, and workspace state

Preserve these major pages:
- Mapping
- Modes
- Base Tuning
- Filtering
- Combat Profile
- Profiles
- Conditional Rules
- Effective Response Stack
- Live Monitor
- Help / Docs
- Perf / Diagnostics
- Helm overlay assistant

Global UI requirements:
- Dark premium engineering-software theme
- Rounded corners throughout using Qt/QSS/native styling
- Left sidebar with active page highlight and runtime status at bottom
- Header with title, polished subtitle, STATUS chips, and ASSISTANT/Helm launcher
- Footer with status, page/axis/profile/source details, Import Profile, Revert, Save Workspace
- No ugly dark text strips everywhere
- No debug/prototype wording
- Product-grade copy
- Smooth page switching and no visible redraw jank
- Hidden pages must skip expensive work
- Graph updates must be scoped locally
- Performance diagnostics must remain available

Implement safe workspace model:
- Use a workspace copy/draft file, e.g. hotas_bridge_config_v2.json
- Changes update the workspace immediately but only write permanently when user saves
- Import Profile, Revert, Save Workspace actions must be safe
- Helm changes apply only to current workspace until saved

Implement Mapping page:
- Routing Overview: Axis Routes 6, Button Routes 15, Hat Routes 1
- Live Route Summary with mappings such as Roll Raw axis 1 -> X -> X(axis1), Pitch Raw axis 2 -> Y -> Y(axis2), Throttle Raw axis 3 -> Z -> Z(axis3), Yaw Raw axis 6 -> RZ -> RX(axis4), Aux1 Raw axis 7 -> SL0 -> RY(axis5), Aux2 Raw axis 8 -> RX -> RZ(axis6)
- Axis Routing table with Function, Raw Axis, Logical Output, Runtime vJoy, Invert, Live Raw, Live Output
- Button Routing table with Add Route, Remove Selected, Reset 1:1
- Hat Routing table with Add Hat, Remove Selected

Implement Modes page:
- Precision Mode with Buttons field, default 0
- Combat Mode with Trigger Buttons, Zoom Buttons default 5, Extra Buttons, Stack Mode multiply
- Live Mode State showing Precision/Combat/Trigger/Zoom/Extra/Stack states
- Mode Notes with polished product copy

Implement Base Tuning page:
- Mapped axes list Roll, Pitch, Throttle, Yaw, Aux1, Aux2
- Parameters: Curve Mode, Curve Strength, Deadzone, Anti-Deadzone, Hysteresis, Output Scale, Max Output
- pyqtgraph response preview
- Linear reference line must be true y=x and never transformed by the curve math
- Live Snapshot and Guidance cards

Implement Filtering page:
- Parameters: Center Alpha, Edge Alpha, Same Slew Limit, Reverse Slew Limit
- Step preview graph showing input vs filtered output
- Live Snapshot and Guidance

Implement Combat Profile page:
- Parameters: Combat Curve, Combat Scale, Combat Center Alpha, Combat Edge Alpha, Combat Same Slew, Combat Reverse Slew
- Combat response graph
- Guidance card with warning/caution/extreme states where needed

Implement Profiles page:
- Profile Library with Built-In Presets: Balanced Flight, Precision Tracking, Aggressive Combat, Smooth Cinematic
- Personal Profiles with Current Workspace active
- Profile Detail, Setup Summary, Profile Feel, Profile Actions
- Buttons: Save Current As New, Import JSON, Duplicate, Export JSON, Use This Profile, Rename, Delete

Implement Conditional Rules page:
- Status chips: rules, active, blocked, disabled
- Action row: Add Rule, Edit Selected, Duplicate, Enable, Delete
- Rule List and Rule Detail split
- Example rule: Yaw 0.75 | Roll > 0.35, disabled, target Yaw, parameter Output Scale, operation Set, value 0.75, injects at Base Output Limits, mode gate Always
- Rule Logic explanatory card
- Keep production rule logic safe; full advanced editor can come later if needed

Implement Effective Response Stack page:
- Axis selector
- Live status
- Signal Chain with stage cards Raw Input, Center Conditioning, Curve / Shape, etc.
- Stage cards show IN/OUT/DELTA, live/active badges, input/output bars, description
- Raw vs Final graph with live marker
- Mode State, Current Stack Summary, Selected Stage, Rule Driver Values cards
- Fix/avoid periodic twitch: reuse widgets and update values in place; do not rebuild cards on heartbeat

Implement Live Monitor page:
- Monitor Controls with axis selector and Show raw and output together checkbox
- Raw Input Trace graph
- Raw vs Final Overlay graph
- Live State and Buttons/Hats cards
- Axis Levels visualization with raw blue and final green bars for Roll/Pitch/Throttle/Yaw/Aux1/Aux2
- HOTAS Buttons B1-B15
- Mapped Output Buttons Out1-Out20

Implement Help / Docs:
- Search field
- Sort dropdown By Category
- Topics tree with Advanced Pages, Analysis, Core Pages, Diagnostics, Getting Started, Reference, Workflow
- Guide pane with product documentation articles

Implement Helm overlay:
- Not a sidebar page
- Top-right assistant launcher opens overlay/modal
- Background app dimmed/blurred/de-emphasized
- Green pulsing indicator: Helm is active / Context-linked assistant
- Sections: What’s wrong?, What I’d change, What I found, Apply/Revert
- Symptom chips: Can’t hold aim steady, Too twitchy near center, Overshoots target, Combat mode feels sluggish, Reversals feel sticky, Hard to track smoothly
- Actions: Analyze, Review Changes, Cancel, Apply Selected Changes, Revert Last Helm Changes
- Text tone must be polished and product-grade

Implement Perf / Diagnostics:
- Show active page, runtime state, selected axis, source file, hidden page skips, runtime path checks, page build/switch timings, heartbeat timing, graph draw timings, startup timings

Packaging:
- Build release executable/folder
- Create proper Windows installer using Inno Setup or equivalent
- Create Start Menu shortcut, optional Desktop shortcut, uninstall entry
- Install app files to Program Files or LocalAppData Programs
- Store user data/config/profiles/logs in AppData/LocalAppData, not beside executable
- Use app icon assets/app_icon.ico
- Create both detailed icon for large sizes and simplified bold icon for taskbar/start-menu

Testing requirements:
- No overlap or clipping
- Every page scrolls correctly
- Graphs smooth
- Hidden pages skip work
- Effective Response Stack stable
- Active sidebar state correct
- Linear reference line truly linear
- Runtime live/idle indicators accurate
- Save/import/revert safe
- Helm overlay safe and performant
- Installer app icon appears correctly

Build this as polished, premium, shippable desktop software. The target reaction is: “DAMN THIS IS NICE SOFTWARE.”
```

---

## 15. Immediate Recovery Notes From This Chat’s Last Turn

The user became frustrated because a requested instruction was not followed. The important correction is:

- If asked to create a Canvas recovery document, create the Canvas document immediately and do not continue prior icon-generation work.
- If asked for an `.ico`, produce an actual `.ico` file, not only a generated image.
- For the simplified icon, create a multi-size ICO from the simple PNG and save it under a clear filename such as `HOTAS_Control_Panel_V2_Taskbar_Icon.ico`.

This document was created to satisfy the recovery-document instruction and preserve the HOTAS V2 rebuild details from the chat.

