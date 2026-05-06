# Product Vision and Visual Design System

**Spec-set role:** forensic reconstruction document generated from the three recovered HOTAS Control Panel chat notes. This document is meant to stand on its own while cross-referencing the rest of the set.

**Evidence taxonomy used throughout:**
- **Confirmed Facts**: directly stated in the recovery notes or visible as exact recovered UI text.
- **Screenshot-Derived Details**: observations recovered from screenshot descriptions in the source notes.
- **Inferences**: explicitly inferred from the notes or reconstructed from adjacent evidence.
- **Desired Improvements**: user preferences, future direction, fixes, or rebuild requirements.
- **Unknowns**: details the notes say are missing, uncertain, or need later verification.

## Confirmed Facts

- The product target is premium HOTAS tuning and diagnostics software, not a rough mapper or toy utility.
- The modern V2 direction uses a dark professional desktop-control workspace with left sidebar, header/status area, assistant launcher, main workspace, scrollable pages, and footer.
- The desired reaction from the user is preserved exactly in the source notes: **“DAMN THIS IS NICE SOFTWARE.”**
- The product should communicate serious engineering/tuning value while remaining understandable.
- Rounded corners, smoothness, spacing discipline, professional copy, and status/action distinction are hard requirements.
- The final sidebar title is `HOTAS V2`; subtitle is `Control workspace`.
- Final header title is `HOTAS Control Panel V2`.
- Final header subtitle is `Professional tuning, live inspection, and assistant-guided diagnostics in one modern control workspace.`
- The flight-recorder chat also preserves a visible tagline: **“Routing, tuning, live inspection, and guided diagnosis in one focused control workspace.”**

## Screenshot-Derived Details

- The final shell uses a left sidebar, top header, top-right `STATUS` cluster, top-right `ASSISTANT` cluster, scrollable main page area, and footer.
- Final top-right status chips include `Workspace Copy`, `Saved`, and `Idle` / `Live`.
- Final top-right assistant entry is `Helm`.
- Status chips must not look like action buttons.
- Action buttons include `Import Profile`, `Revert`, `Save Workspace`, and `Helm`.
- Final icon direction has two variants: a detailed installer/about-page icon and a simplified taskbar/Start Menu icon.

## Inferences

- Exact font family was not recovered, but all sources point toward a modern sans-serif desktop UI with clear heading/body/caption hierarchy.
- Approximate palette uses deep navy/blue-black backgrounds, dark slate-blue cards, muted blue borders, cyan/blue action accents, green live/active states, amber caution states, and red destructive/disabled states.
- The product identity should be closer to engineering workstation / control console / signal lab than generic SaaS or game HUD.

## Desired Improvements

- Avoid pixelated custom canvas-rounded corners.
- Use Qt/QSS/native styling for border radius and visual hierarchy.
- Avoid muddy dark strips behind every text area.
- Avoid debug/prototype wording such as `safe parallel Qt frontend`, `V2 draft`, and overly internal save-flow language in final user-facing copy.
- Keep animations subtle: page fade/slide, sidebar active transition, live/assistant pulse, Helm overlay transition.
- Avoid graph data animation and heavy effects that cause jank.
- Preserve visual seriousness: not bubbly, not toy-like, not generic SaaS.

## Unknowns

- Exact font file.
- Exact finalized color-token values.
- Exact animation implementation.
- Exact final app-icon files and conversion path.
- Whether the simplified taskbar icon was ever converted into a multi-size `.ico`.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 1.2 Design philosophy`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.20 App packaging / installation`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.21 App icon`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 3.1 General V2 window layout`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 3.2 Color palette inferred`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 3.3 Typography`

### 3.3 Typography

No exact font file named. Inferred style:

- Modern sans-serif.
- Bold white headings.
- Smaller pale-blue helper/caption text.
- Monospace used in diagnostics areas and live values.
- Product copy became concise and polished.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 3.4 Rounded corners`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 3.5 Status vs button semantics`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 3.6 Sidebar`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 3.7 Header/top-right cluster`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 3.8 Footer`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 3.9 Animation/motion direction`

### 3.9 Animation/motion direction

Desired and partially implemented:

- Subtle page transition fade/fade+slide.
- Sidebar active-state transition.
- Live/assistant pulse/breathe indicator.
- Helm overlay open/close transition.
- Avoid graph data animation and heavy effects that cause jank.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 25 — Final V2 Mapping page, top overview`

### Screenshot 25 — Final V2 Mapping page, top overview

Sidebar final text `HOTAS V2`, `Control workspace`. Mapping selected. Header final copy: “Professional tuning, live inspection, and assistant-guided diagnostics in one modern control workspace.” Status cluster: STATUS Workspace Copy / Saved / Idle. Assistant cluster with Helm button. Mapping page shows routing overview, live route summary, axis routing table, footer actions.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 38 — Detailed app icon`

### Screenshot 38 — Detailed app icon

Detailed rounded-square dark metallic icon with throttle, joystick, cyan response curve, graph display, and `HOTAS` text. Premium but too detailed for tiny taskbar sizes.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 39 — Simplified taskbar app icon`

### Screenshot 39 — Simplified taskbar app icon

Simpler dark navy rounded-square icon with white joystick silhouette, cyan gauge/curve arc, and cyan bar indicators. Best for taskbar/Start Menu scale. Needs conversion to multi-size `.ico`.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 10.10 V2 early: dark strips behind text looked awful`

### 10.10 V2 early: dark strips behind text looked awful

- Symptom: every text area had darker strip background; muddy/striped.
- Fix: simplify surface hierarchy: app background, card background, control/input background.
- Status: final screenshots much cleaner.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 10.11 V2 copy too debug/prototype-like`

### 10.11 V2 copy too debug/prototype-like

- Symptom: text like “safe parallel Qt frontend,” “V2 draft,” “this page writes only…” sounded dev/test.
- Fix: product-grade copy pass.
- Status: final copy is much more polished, though some status terms like Workspace Copy remain intentionally visible.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 11.1 Things the user liked`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 11.2 Things the user disliked`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 11.3 Performance expectations`

### 11.3 Performance expectations

- Smooth tab switching.
- No obvious redraw jank.
- No visible whole-page repaint on scroll/tab switch.
- Graph updates scoped to graph.
- Hidden pages do not do expensive work.
- Performance instrumentation visible.
- Animations tasteful and not expensive.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 11.4 Packaging preferences`

### 11.4 Packaging preferences

- Real app installation.
- User sees one app/shortcut, not folder full of files.
- Real app icon.
- Start Menu/desktop shortcuts.
- AppData for user configs/profiles/logs.
- Installer/uninstaller.

---




### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Design philosophy inferred from the chat`

### Design philosophy inferred from the chat
The design philosophy was strongly shaped by the following preferences and decisions:

- The app should feel like **serious software**, not a rough hobby utility.
- The UI should be **premium, modern, dark, polished, and intentional**.
- Advanced functionality should exist, but it should **not explode across the main interface**.
- The user repeatedly wanted the current pages to stay **beautiful, clean, and preserved**.
- Main workflows should remain simple, while deeper controls should be hidden behind things like **Configure** dialogs.
- Features should be **useful, not gimmicky**.
- New systems should feel integrated into the product instead of bolted on.
- The app should support both **live monitoring** and **after-the-fact analysis**.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Key goals and UX priorities explicitly visible in the chat`

### Key goals and UX priorities explicitly visible in the chat
- Preserve the existing **Flight Recorder** page and avoid wrecking its layout.
- Add a **real live overlay** without cluttering the recorder page.
- Put advanced overlay controls behind a **Configure** entry point.
- Use **sane defaults** so the user rarely needs to adjust overlay specifics.
- Reuse shared overlay logic across replay/export and live rendering.
- Keep the app looking polished and organized.
- Support a **hindsight / buffered replay** style capture mode.
- Keep visual style consistent between replay overlays and live telemetry overlays.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Overall visual style`

### Overall visual style
The app has a strong, premium dark theme with the following characteristics:

- very dark navy/blue background,
- slightly lighter blue-gray cards,
- bright white headings,
- muted blue-gray descriptive text,
- neon-ish accent chips in cyan/green/orange/yellow tones,
- subtle borders,
- rounded corners throughout,
- layered card-based layout,
- clean spacing,
- a modern desktop-tool feel rather than a game-like HUD aesthetic.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Visual language`

### Visual language
The UI communicates “control workspace” rather than “toy utility.” It uses:

- large rounded cards,
- pill-shaped badges and inputs,
- slim bright progress bars,
- sharp but soft-edged panels,
- consistent margin spacing,
- and a restrained, high-contrast palette.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Typography`

### Typography
Direct font name is not stated.

**Inference:** likely a modern sans-serif desktop UI font. Text styling suggests hierarchy such as:
- large bold page header,
- medium bold section titles,
- lighter gray body/supporting text,
- uppercase small labels for areas like STATUS and ASSISTANT.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Colors observed`

### Colors observed
Approximate visual palette:
- Background: deep navy / blue-black
- Cards: dark slate-blue
- Borders: muted blue lines
- Accent blue: used for buttons, outlines, progress bars, and selection states
- Green: used for active/ready/live states
- Amber/orange: used for unsaved or alert-like status chips
- Axis colors:
  - Roll: light blue (#58B8FF visible)
  - Pitch: mint/green (#6FDB9F visible)
  - Throttle: warm yellow/orange (#F0C46A visible)
  - Yaw: lavender/violet (#CF95FF visible)
  - Aux 1: orange/coral (#FF9B6B visible)
  - Aux 2: aqua/cyan-green (#6ED9D0 visible)



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Component style`

### Component style
- Buttons are often rounded rectangular or pill-like.
- Inputs are dark fill with lighter outline.
- Cards have large radius corners.
- Panels use thin borders rather than strong shadows.
- The overall tone is polished and technical.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Specific UX preferences explicitly stated in the chat`

### Specific UX preferences explicitly stated in the chat
- Do **not** overload Flight Recorder with lots of overlay placement controls.
- Keep current pages intact if they already look good.
- Add advanced settings only behind **Configure**.
- Main controls should remain compact and obvious.
- Sane defaults matter.
- The interface should feel premium and intentional.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Before vs after changes discussed`

### Before vs after changes discussed
#### Before
- Flight Recorder existed with on-demand recording, overlay export, library, preview, and axis overlay options.
- The user worried that adding a live overlay might require a lot of layout changes or too many settings.

#### Design decision phase
- Assistant proposed a separate live overlay path launched from Live Monitor, backed by a shared overlay engine, with advanced settings hidden behind Configure.

#### After
- Live Overlay was successfully implemented.
- Flight Recorder remained intact.
- Live Monitor gained a Live Overlay card.
- A full configuration dialog exists.
- Flight Recorder gained buffered replay / save previous interval mode.

---




### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Design philosophy`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### User experience priorities`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Key constraints and preferences`

### Key constraints and preferences
- Preserve technical feel and “serious tool” identity
- Avoid overly playful or cartoonish UI
- Avoid fluffy, generic consumer-SaaS styling
- Avoid over-reliance on static presets when giving smart recommendations
- Keep control processing responsive even while rich visualization is active
- Rich UI must never compromise low-latency control behavior
- Use modular architecture for advanced features like Helm rather than stuffing logic into a monolithic app file

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### 2.10 Visual Modernization Project`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Colors and style`

### Colors and style
- dark background
- blue accent color family
- user repeatedly praised the dark theme and felt it was clean and technical
- later wanted stronger surface hierarchy, rounded corners, shadows, blur, and premium depth
- wanted the whole app to stay technical and control-console-like



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Borders, corners, shadows`

### Borders, corners, shadows
Originally boxy / square / legacy-framed. Later strong request to modernize with:
- slightly rounded corners everywhere
- stronger but tasteful shadows
- parent/child surface distinction
- more premium selected/active states
- more depth on Helm and graph panels



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Typography`

### Typography
No exact fonts specified. Desired text style:
- technical, clean, premium
- more modern hierarchy
- stronger spacing between headings/subtitles/body
- less flat text rhythm



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Icons`

### Icons
Mentioned/described:
- top-right Helm icon/button
- drawer/docs/help icon later requested for help drawer
- rule/status chips and indicators
- possible helm/nautical identity for assistant



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Tooltips`

### Tooltips
Strongly preferred for explaining advanced fields. The small tooltip icon approach on Conditional Rules was later requested across the app.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Visual hierarchy desires`

### Visual hierarchy desires
- panels should feel like true surfaces
- graph panels should feel like instruments
- stack cards should feel like modules
- Helm should feel like a different operating mode

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Bug/problem: visual modernization too subtle`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Explicit likes`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Explicit dislikes`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Emotional/practical priorities`

### Emotional/practical priorities
- project was almost complete before being lost; reconstruction needs to be dense and forensic
- performance and low latency matter deeply
- user wants humor in normal conversation but app tone itself should remain serious/professional with character
- wants rich explainability and trust in what the app is doing



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Visual style preferences`

### Visual style preferences
- modernized but still sharp
- slightly rounded, not pill-shaped
- shadows and depth, but disciplined
- strong spacing discipline
- polished motion later
- control-room identity preserved

## Second Sweep Addendum: Legacy Shell, Support Surfaces, and Visual Coverage

### Confirmed Facts
The second source comparison found several small visual/support observations that were not lost functionally, but were not preserved as exact wording in the first spec pass. They are retained here because they help rebuild the original-to-V2 visual evolution and the support/diagnostics surfaces.

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.1 Legacy HOTAS Control Panel`

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

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / missing support screenshots

### Screenshot 8 — Legacy Performance popup

Top-right `Perf On`. Popup titled `Performance`, close button. Text: “Lightweight timings for the live UI paths. Keep it off during normal tuning.” Checkbox `Collect live timings`, button Clear. Current live diagnostics show Visible tab Stack, Selected axis Roll, runtime timestamp unavailable, pending refresh counts, next scheduler tick.

### Screenshot 9 — Legacy Help / Tuning Notes popup

Popup on right side titled `Help & Tuning Notes`, close button. Cards explain `Curves` and `Deadzone / Anti-Deadzone / Hysteresis`. Old help panel is narrow and has excessive dead space.

### Screenshot 23 — Initial V2 Help / Docs page

Help content was simple text page with product philosophy and page overview. Later upgraded into searchable topic tree.

### Screenshot 24 — Initial V2 Perf / Diagnostics page

Diagnostics page with dense timing text: active page, runtime live, hidden page skips, page build/switch timings, heartbeat stats, graph timings. Confirms performance instrumentation was built in.

### Screenshot 36 — Final V2 Help / Docs page

Help / Docs selected. Search bar, Sort by Category dropdown, Topics tree, Guide pane. Conditional Rules article selected. Looks like integrated product documentation.

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / shell layout notes

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

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / screenshot 7

#### Screenshot 7 — Phase 2 visual modernization comparison (descriptive placeholder)
- User reaction: only slight visual changes, not strong enough. Still too close to original design.
- Resulting decision: create a bolder Phase 2.5 visual modernization emphasizing stronger radius, shadows, spacing, fit, and hierarchy.

> Note: Actual screenshot embedding was not available in Canvas. Reattach screenshots manually later to these placeholders.
