# Core Tuning Engine, Mapping, and Modes

**Spec-set role:** forensic reconstruction document generated from the three recovered HOTAS Control Panel chat notes. This document is meant to stand on its own while cross-referencing the rest of the set.

**Evidence taxonomy used throughout:**
- **Confirmed Facts**: directly stated in the recovery notes or visible as exact recovered UI text.
- **Screenshot-Derived Details**: observations recovered from screenshot descriptions in the source notes.
- **Inferences**: explicitly inferred from the notes or reconstructed from adjacent evidence.
- **Desired Improvements**: user preferences, future direction, fixes, or rebuild requirements.
- **Unknowns**: details the notes say are missing, uncertain, or need later verification.

## Confirmed Facts

- The app maps physical HOTAS axes/buttons/hats to logical and runtime vJoy outputs.
- Explicit hardware in the Helm/recovery chat: **Thrustmaster T.Flight HOTAS One**.
- Explicit hardware in the rebuild/productization chat: **Thrustmaster Flight HOTAS One**.
- Final recovered axis set: `Roll`, `Pitch`, `Throttle`, `Yaw`, `Aux 1`, `Aux 2`.
- Raw axis channels visible/inferred: `Axis 1`, `Axis 2`, `Axis 3`, `Axis 6`, `Axis 7`, `Axis 8`.
- Logical outputs: `Roll / X`, `Pitch / Y`, `Throttle / Z`, `Yaw / RZ`, `Slider 0 / SL0`, `Aux Output / RX`.
- Mapping page examples preserve the runtime remap:
  - Roll: Raw axis 1 -> X -> X (axis 1)
  - Pitch: Raw axis 2 -> Y -> Y (axis 2)
  - Throttle: Raw axis 3 -> Z -> Z (axis 3)
  - Yaw: Raw axis 6 -> RZ -> RX (axis 4)
  - Aux 1: Raw axis 7 -> SL0 -> RY (axis 5)
  - Aux 2: Raw axis 8 -> RX -> RZ (axis 6)
- Final pages in this scope: `Mapping`, `Modes`, `Base Tuning`, `Filtering`, `Combat Profile`, `Profiles`.

## Screenshot-Derived Details

- Mapping page status chips: `Current Workspace`, `Runtime Idle`, `Mapping Ready`.
- Mapping page footer actions: `Import Profile`, `Revert`, `Save Workspace`.
- Modes page includes `Precision Mode`, `Combat Mode`, `Live Mode State`, and `Mode Notes`.
- Base Tuning page includes `Mapped Axes`, `Parameters`, `Response Preview`, `Live Snapshot`, and `Guidance`.
- Filtering page includes a step preview graph and filtering parameters.
- Combat Profile page includes combat-specific curve/filtering parameters and guidance states such as `Caution`.
- Profiles page includes built-in presets `Balanced Flight`, `Precision Tracking`, `Aggressive Combat`, `Smooth Cinematic`, and personal profile `Current Workspace`.

## Inferences

- Battlefield-style aircraft control constraints strongly shaped tuning defaults and mode behavior.
- Precision Mode steadies aim/tracking by scaling authority.
- Combat Mode/Zoom gating applies calmer response behavior when aiming/zooming/combat input is active.
- Per-axis tuning is intended to let roll, pitch, throttle, yaw, and auxiliary controls each feel distinct and controllable.
- Yaw twist can introduce dirty micro-inputs; one recommendation was to consider moving yaw from stick twist to throttle rocker.

## Desired Improvements

- Base/Filtering/Combat pages should avoid table-only presentation and use grouped columns, tooltips, graph panels, feel summaries, and tuning guidance.
- Linear graph reference must remain a true `y=x` line.
- Profiles should eventually support save/load/export/import, game-specific profiles, and recommendation-strength ties.
- **Quick Tune** was planned for later and should help with axis calibration, deadzone/invert suggestions, and first-pass recommended tuning.

## Unknowns

- Exact profile JSON schema.
- Exact config file schema for `hotas_bridge_config_v2.json`.
- Exact runtime bridge and vJoy API implementation.
- Exact final curve/filtering implementation as shipped.
- Exact controller enumeration and mapping backend.

## Relevant Implementation Prompt Extract

### Desired Improvements
- Implement Mapping page with Axis Routes 6, Button Routes 15, Hat Routes 1.
- Implement Modes page with `Precision Mode`, `Combat Mode`, `Live Mode State`, and `Mode Notes`.
- Implement Base Tuning page with `Curve Mode`, `Curve Strength`, `Deadzone`, `Anti-Deadzone`, `Hysteresis`, `Output Scale`, `Max Output`.
- Implement Filtering page with `Center Alpha`, `Edge Alpha`, `Same Slew Limit`, `Reverse Slew Limit`.
- Implement Combat Profile page with `Combat Curve`, `Combat Scale`, `Combat Center Alpha`, `Combat Edge Alpha`, `Combat Same Slew`, `Combat Reverse Slew`.
- Implement Profiles page with built-in presets and personal profiles.
- Changes update the current workspace immediately and write permanently only when saved.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 1.1 What the software is`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 1.3 Hardware/controllers discussed`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 1.4 High-level product goals`

### 1.4 High-level product goals

- Make HOTAS tuning approachable without hiding advanced control.
- Give the user live feedback on raw and processed input.
- Let the user tune separate response layers: base tuning, filtering, combat modifiers, conditional rules, final stack.
- Support profiles/presets for different flight/control needs.
- Make the app feel professional enough to distribute.
- Preserve old app during V2 migration.
- Make V2 safer through draft/workspace behavior rather than destructive direct writes.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.7 Mapping page`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.8 Modes page`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.9 Base Tuning page`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.10 Filtering page`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.11 Combat Profile page`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.12 Profiles page`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 1 — Legacy Modes tab, broken/old Phase 2 style`

### Screenshot 1 — Legacy Modes tab, broken/old Phase 2 style

Visible legacy app title: `HOTAS Control Panel`. Top dark header with cyan line. Top-right buttons: `Saved`, `Helm`, `Perf Off`, `Help / Docs`. Main tab row includes `Modes`, `Base Tuning`, `Filtering`, `Combat Profile`, `Conditional Rules`, `Effective Response Stack`. Modes tab active. Page brief card: “Choose which buttons activate precision and combat behavior, and how those modes combine.” Trigger Sources card with inputs for Precision Hold Buttons (`0`), Combat Trigger Buttons, Combat Zoom/Aim Buttons (`5`), Combat Extra Buttons. Bottom workspace actions bar: Reload, Reset Defaults, Open Live Monitor, Save, Save + Restart Bridge, Close. UI has cyan glowing borders, jagged rounded corners, and large chrome.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 2 — Legacy Base Tuning tab with preview graph`

### Screenshot 2 — Legacy Base Tuning tab with preview graph

Base Tuning active. Page brief: “Tune each axis’s baseline feel, including curve shape, center behavior, and output limits.” Left table shows axes Roll, Pitch, Throttle, Yaw, Aux 1/Aux 2 with columns Axis, Mapping, Curve, k, Deadzone, Anti-DZ, etc. Right Instrument View card: `Axis Response Preview`, controls Axis, Preview Mode, Compare Against, checkboxes `Show linear reference`, `Linear reference follows deadzone`. Graph titled `LIVE RESPONSE PLOT`. Bottom footer overlays large action bar. Some content clipped.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 3 — Legacy Filtering tab`

### Screenshot 3 — Legacy Filtering tab

Filtering active. Page brief: “Control smoothing and slew limiting so each axis responds cleanly near center and during fast changes.” Left table columns Axis, Mapping, Center Alpha, Edge Alpha, Same Slew, Reverse Slew. Right Instrument View: `Filtering Preview`, controls Axis and Test, graph shows input vs filtered line. Heavy nested cards and scrollbars.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 4 — Legacy Combat Profile tab`

### Screenshot 4 — Legacy Combat Profile tab

Combat Profile active. Page brief: combat mode curve strength, damping, and rate limiting. Left table includes Combat k, Combat Scale, Center Alpha, Edge Alpha. Right `Combat Response Preview` graph. Still crowded and overlapping in old style.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 10 — Repaired legacy Modes tab`

### Screenshot 10 — Repaired legacy Modes tab

After repair pass: UI flatter/crisper, fewer heavy rounded fake borders, proper scrollbars. Sidebar not yet V2. Modes page now scrollable. Header still legacy layout but less bloated. Footer action row slimmed.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 11 — Repaired legacy Base Tuning tab`

### Screenshot 11 — Repaired legacy Base Tuning tab

Shows the old notebook tab system but with better scroll handling and less jagged chrome. Base table and graph visible. Page scroll bar on right; footer no longer covers content as severely.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 12 — Repaired legacy Filtering tab`

### Screenshot 12 — Repaired legacy Filtering tab

Filtering page readable with scrollbars, left table and right preview graph. Still legacy style but much more stable.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 13 — Repaired legacy Combat Profile tab`

### Screenshot 13 — Repaired legacy Combat Profile tab

Combat Profile page stabilized. Left table and right graph visible; scrolling improved.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 16 — Initial PySide6 V2 Modes page`

### Screenshot 16 — Initial PySide6 V2 Modes page

First V2 shell. Left sidebar titled `HOTAS V2`, subtitle `Safe parallel Qt frontend`. Nav items include Modes, Base Tuning, Filtering, Combat Profile, Conditional Rules, Effective Response Stack, Helm, Help / Docs, Perf / Diagnostics. Header says `HOTAS Control Panel V2`, subtitle “A ground-up Qt / pyqtgraph frontend running beside the stable legacy app.” Top-right chips `V2 draft`, `Clean`, `Runtime live`, buttons `Import Legacy`, `Save V2 Draft`. Modes page uses rounded cards for Precision Mode, Combat Mode, Live Mode State, Mode Notes.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 17 — Initial V2 Base Tuning page`

### Screenshot 17 — Initial V2 Base Tuning page

Base Tuning active. Left Mapped Axes and Parameters panels. Main graph `Response Preview` using pyqtgraph. Linear line initially wrong/curved issue noticed. Bottom cards: Live Snapshot and Guidance. UI already much smoother and modern.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 18 — Initial V2 Filtering page`

### Screenshot 18 — Initial V2 Filtering page

Filtering active. Similar layout to Base. Graph shows step response. Parameter fields for Center Alpha, Edge Alpha, Same Slew, Reverse Slew. Guidance and live snapshot cards.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 19 — Initial V2 Combat Profile page`

### Screenshot 19 — Initial V2 Combat Profile page

Combat Profile active. Graph shows combat curve. Guidance card can show `Extreme` status in red. Parameter panel lists combat curve/scale/alpha/slew values.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 26 — Final V2 Mapping page, lower routing`

### Screenshot 26 — Final V2 Mapping page, lower routing

Scrolled Mapping page shows Axis Routing table, Button Routing and Hat Routing cards. Button routing table contains HOTAS Button/vJoy Button/Raw/Output. Hat routing has HOTAS Hat, vJoy POV, Up/Right/Down/Left/Live. Footer has Import Profile, Revert, Save Workspace.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 27 — Final V2 Modes page`

### Screenshot 27 — Final V2 Modes page

Modes selected in sidebar. Page has clean cards with Precision Mode, Combat Mode, Live Mode State, Mode Notes. Dark background is calmer; no ugly dark text strips. Active sidebar highlight works correctly.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 28 — Final V2 Base Tuning page`

### Screenshot 28 — Final V2 Base Tuning page

Base Tuning selected. Graph shows linear gray reference and curved blue/green response lines. Mapped Axes list, parameters, live snapshot, guidance. Linear reference now appears straight. `Center` control visible near graph.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 29 — Final V2 Filtering page`

### Screenshot 29 — Final V2 Filtering page

Filtering selected. Graph shows raw step/reference and filtered response. Left parameter panel. Live Snapshot and Guidance cards. Clean final copy and no developer wording.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 30 — Final V2 Combat Profile page`

### Screenshot 30 — Final V2 Combat Profile page

Combat Profile selected. Graph shows multiple lines; guidance card has `Caution` badge. Text reads more product-like. Parameter fields listed on left.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 31 — Final V2 Profiles page`

### Screenshot 31 — Final V2 Profiles page

Profiles selected. Profile Library left with Built-In Presets and Personal Profiles. Detail panel right. Setup Summary, Profile Feel, Profile Actions. Buttons include Save Current As New, Import JSON, Duplicate, Export JSON, Use This Profile, Rename, Delete.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 5.1 Axis mappings`

### 5.1 Axis mappings

Final Mapping page examples:

- Roll: Raw axis 1 -> X -> X (axis 1)
- Pitch: Raw axis 2 -> Y -> Y (axis 2)
- Throttle: Raw axis 3 -> Z -> Z (axis 3)
- Yaw: Raw axis 6 -> RZ -> RX (axis 4)
- Aux 1: Raw axis 7 -> SL0 -> RY (axis 5)
- Aux 2: Raw axis 8 -> RX -> RZ (axis 6)

**Battlefield-safe routing note:** runtime routing may remap RX / RY / RZ / SL0 behind the scenes when needed.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 5.2 Button mappings`

### 5.2 Button mappings

- HOTAS buttons mapped to vJoy buttons.
- Button routing table supports add/remove/reset 1:1.
- Visible mapped buttons: 6–15 in one screenshot.
- Live Monitor shows HOTAS Buttons B1–B15 and mapped output buttons Out 1–Out 20.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 5.3 Hat mappings`

### 5.3 Hat mappings

- HOTAS Hat 1 mapped to vJoy POV 1.
- Optional directional buttons for Up/Right/Down/Left.
- Visible values: Up 7, Right 18, Down 19, Left 0.
- Live state: Centered.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 5.4 Response tuning parameters`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 5.5 Flight/Battlefield control logic`

### 5.5 Flight/Battlefield control logic

The app was intended for HOTAS tuning in flight/vehicle games, especially Battlefield-style control constraints.

Important inference from UI:

- Precision Mode helps steady aim/tracking by scaling authority.
- Combat Mode/Zoom gating applies different curve/smoothing behavior when zooming/aiming/combat input is active.
- Battlefield-safe runtime routing remaps logical axes to runtime vJoy outputs to satisfy game expectations.
- Per-axis response tuning helps roll, pitch, throttle, yaw, and auxiliary controls feel controllable.

---




### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Hardware / controller context`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### 2.1 Base Tuning`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### 2.2 Filtering`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### 2.3 Combat Profile`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### 2.4 Modes`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `#### Screenshot 3 — Modes page with behavior summary (descriptive placeholder)`

#### Screenshot 3 — Modes page with behavior summary (descriptive placeholder)
- Visible content: fields for Precision Hold Buttons, Combat Trigger Buttons, Combat Zoom/Aim Buttons, Combat Extra Buttons, Stack Mode.
- A Current Behavior Summary box was present or desired.
- Side help text was explicitly removed in favor of tooltip icons.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `#### Screenshot 4 — Base Tuning / Filtering / Combat pages with graphs (descriptive placeholder)`

#### Screenshot 4 — Base Tuning / Filtering / Combat pages with graphs (descriptive placeholder)
- Visible content: per-axis rows, grouped column families, graph on right, Feel Summary and Tuning Guidance boxes below.
- Design inference: graphs likely include line plot on dark background with accent color line, optional overlay line, and controls above.
- User reaction: very positive about graphs; they made the app feel much more serious and explainable.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `## 5. Control Mapping and HOTAS Logic`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Profiles/presets`

### Profiles/presets
A full preset architecture was planned for later, not yet implemented at the time of many discussions.

Planned ideas included:
- save/load/export/import presets
- game-specific profiles later
- profile system tied into future recommendation strength ideas



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Calibration / Quick Tune`

### Calibration / Quick Tune
A **Quick Tune** feature was planned for later. It would likely help with:
- axis calibration
- deadzone/invert suggestions
- first-pass recommended tuning

## Second Sweep Addendum: Core Purpose, Hardware Intent, and Tuning-Tab Polish

### Confirmed Facts
The second comparison found several short but important source statements about the app's purpose, controller intent, and why Base/Filtering/Combat needed graph-led polish. They are preserved here because they help a scratch rebuild maintain the original problem framing.

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / core purpose and hardware intent

### Core purpose of the software
The software is a desktop application called **HOTAS Control Panel V2**. In this chat, it is consistently presented as a polished, dark-themed control workspace for:

- routing controller inputs,
- tuning HOTAS behavior,
- live inspection / telemetry,
- guided diagnosis,
- replay analysis,
- overlay-based debugging,
- and an embedded assistant called **Helm**.

Visible tagline text from the application header in multiple screenshots:

- **“Routing, tuning, live inspection, and guided diagnosis in one focused control workspace.”**

This suggests the app was not just a mapper. It was intended to be a **central cockpit-like control and analysis environment** for a HOTAS setup.

### Hardware / controller intent
Direct hardware support is not fully enumerated in this chat, but the project clearly targets a **HOTAS (Hands On Throttle And Stick)** setup and includes named axes such as:

- Roll
n- Pitch
- Throttle
- Yaw
- Aux 1
- Aux 2

**Inference:** The software likely supported a joystick + throttle combination and exposed controller data streams for tuning, monitoring, and export. The specific controller model is not named in this chat.

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / purpose

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

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / tuning-tab polish bug

### Bug/problem: other tabs felt less polished than Conditional Rules
#### Symptom
Base/Filtering/Combat looked too table-first and lacked hierarchy.

#### Fixes discussed
- grouped columns into logical families
- short purpose statement on each tab
- graph panels on right
- tooltip help instead of side notes

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / workflow preferences

### Workflow preferences
- direct tuning tabs remain for parameter work
- Helm handles problem-driven diagnosis
- Helm should not auto-save
- rule editing by Helm deferred for later

---
