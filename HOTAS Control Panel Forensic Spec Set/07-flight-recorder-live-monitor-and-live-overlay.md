# Flight Recorder, Live Monitor, and Live Overlay

**Spec-set role:** forensic reconstruction document generated from the three recovered HOTAS Control Panel chat notes. This document is meant to stand on its own while cross-referencing the rest of the set.

**Evidence taxonomy used throughout:**
- **Confirmed Facts**: directly stated in the recovery notes or visible as exact recovered UI text.
- **Screenshot-Derived Details**: observations recovered from screenshot descriptions in the source notes.
- **Inferences**: explicitly inferred from the notes or reconstructed from adjacent evidence.
- **Desired Improvements**: user preferences, future direction, fixes, or rebuild requirements.
- **Unknowns**: details the notes say are missing, uncertain, or need later verification.

## Confirmed Facts

- Flight Recorder captures the desktop and composites time-matched HOTAS axis traces into the finished clip.
- Live Overlay is a detached real-time telemetry strip rendered over gameplay or the desktop.
- Live Overlay belongs in `Live Monitor`, not in `Flight Recorder`.
- Advanced Live Overlay settings belong behind `Configure`.
- Replay/export overlay and live overlay should share a common overlay engine.
- Forward capture mode records from trigger time for configured duration.
- Buffered/hindsight mode continuously buffers the last configured duration and saves that interval when triggered.
- Exact recorder hotkey example: `Ctrl+Shift+F10`.
- Exact live overlay toggle hotkey example: `Ctrl+Shift+F9`.
- Exact display example: `NE160QDM-NYJ (2048x1280)`.
- Exact recorder values include `Length: 20 s`, `Frame Rate: 30 fps`, `History: 6.00 s`, `Overlay Source: Final output`, `Capture Source: Current display`.
- Exact live overlay config values include `Position: Bottom strip`, `Margin: 18 px`, `Width: Standard`, `Height: 0.60`, `Opacity: 0.66`, `Background: 0.82`, `Line thickness: 2.80`, `FPS cap: 60 fps`, `Source: Final output`, `History: 7.50 s`.

## Screenshot-Derived Details

- Flight Recorder status chips include `Ready`, `Hotkey armed`, `Final output`, `Buffering`, `Clip hotkey armed`, and `Recording`.
- Flight Recorder buttons include `Record Now` and later `Save Last Clip`.
- Live Overlay card includes `Hide Overlay`, `Configure`, `Preset Custom`, status `Active`, attached display text, toggle hint, and summary text `Custom | Bottom strip | 66% opacity | Final output`.
- Live Overlay Configuration sections: `Placement`, `Appearance`, `Behavior`, `Data`, `Axes`.
- Recording Library table columns: `Clip`, `Recorded`, `Duration`, `Opened`.
- Clip Preview includes Play button, timeline/scrubber, `Reveal File`, and metadata line.
- Exported clips have the overlay baked into video, not only shown in the app.

## Inferences

- The live overlay likely requires a desktop UI toolkit that supports transparent, always-on-top, click-through windows on Windows.
- `Final output` is visibly confirmed; future `Raw` and `Both` overlay source modes were suggested but not confirmed in the screenshots.
- The recorder/overlay system turns the app into a post-action debugging and tuning evidence tool.
- Axis colors are shared so live telemetry and exported replay overlays stay visually consistent.

## Desired Improvements

- Keep Flight Recorder layout intact.
- Do not dump “50 different settings” into recorder UI.
- Sane defaults should make Configure rarely necessary.
- Avoid graphics API hooking, game injection, and anti-cheat-risky techniques.
- Support click-through, always-on-top, borderless/frameless, transparent live overlay behavior.
- Persist overlay placement/opacity/source/history/config.
- Verify hotkeys, library refresh/sort, clip preview, display attach, and overlay color consistency.

## Unknowns

- Exact capture/encoding pipeline.
- Exact overlay compositor implementation.
- Exact graph renderer implementation.
- Exact clip indexing/library storage.
- Whether overlay could attach to a target window beyond display attachment.
- Whether raw/final/both source modes were implemented beyond `Final output`.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Feature: Flight Recorder`

### Feature: Flight Recorder
#### What it does
A dedicated feature/page for desktop capture plus HOTAS telemetry overlay compositing. It captures the desktop, then overlays time-matched HOTAS axis traces into the finished clip.

#### Why it exists
It allows clean replay of what happened on-screen along with the HOTAS signal history, making it useful for:

- tuning,
- debugging,
- reviewing maneuvers,
- comparing presets,
- and preserving interesting gameplay/control events.

#### How it should behave
Two recorder behaviors are discussed and later shown in screenshots:

1. **Forward capture mode**: start recording from the moment a keybind is pressed and save the next configured duration.
2. **Buffered / hindsight mode**: continuously buffer the last configured duration, then save that already-buffered time window when the hotkey is pressed.

This second behavior is explicitly compared to **Hindsight**.

#### Visible UI elements
From screenshots and discussion:

- Page title: **Flight Recorder**
- Description text:
  - **“Capture the desktop on demand, then composite a time-matched axis trace overlay into the finished video.”**
  - **“Use the hotkey when you want a clean replay of what happened on-screen with the matched HOTAS signal history baked into the clip.”**
- Status chips / badges such as:
  - Ready
  - Hotkey armed
  - Final output
  - Buffering
  - Clip hotkey armed
  - Recording
- Primary action buttons such as:
  - Record Now
  - Save Last Clip
- Recorder progress bar / fill bar
- Recorder Settings card
- Axis Overlay card
- Recording Library card
- Clip Preview card
- Bottom status/footer bar with recording messages and workspace context

#### Settings / options / parameters visible in the chat
- Destination
- Length
- Frame Rate
- History
- Overlay Source
- Capture Source
- Display
- Hotkey
- Record the cursor
- Trigger Mode (later screenshot)

Specific visible values from screenshots include:
- Length: **20 s**
- Frame Rate: **30 fps**
- History: **6.00 s** in earlier screenshots; later **7.50 s** appears in Live Overlay Configuration for live overlay data
- Overlay Source: **Final output**
- Capture Source: **Current display**
- Hotkey examples:
  - **Ctrl+Shift+F10** for recorder/hindsight trigger
  - **Ctrl+Shift+F9** for live overlay toggle
- Display example:
  - **NE160QDM-NYJ (2048x1280)**
- Trigger Mode example from later screenshot:
  - **Press to save previous interval**

#### Interactions with other parts of the program
- Shares axis colors/settings with the live overlay.
- Produces clips that can be reopened in **Clip Preview** and **Recording Library**.
- Uses HOTAS telemetry as overlay source.
- Uses the app’s workspace save/revert flow.
- Fits into the broader live monitoring / analysis workflow.

#### Improvements / evolution discussed
- Originally shown as an on-demand recorder with overlay export.
- Later expanded to include **hindsight / buffered replay** behavior.
- Later gained trigger-mode language that suggests a more formalized mode system.
- Later screenshot suggests the workflow became “save the last clip” rather than only “record now.”

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Feature: Live Overlay`

### Feature: Live Overlay
#### What it does
A detached, real-time telemetry strip rendered over gameplay or the desktop. It shows rolling HOTAS axis traces live.

#### Why it exists
It provides immediate feedback during gameplay/testing without requiring post-export review. It is useful for:

- verifying what the controls are doing right now,
- correlating feel to actual output,
- tuning response behavior while flying/driving,
- and creating a more advanced instrumentation feel for the app.

#### How it should behave
The architecture and UX were explicitly refined in the chat:

- The overlay should **not** wreck the current Flight Recorder page.
- It should be a **separate top-level window**.
- It should be:
  - borderless / frameless,
  - transparent background,
  - always-on-top,
  - click-through,
  - and best suited for windowed or borderless fullscreen use.
- It should be toggleable by a **keybind**.
- It should have sane defaults.
- Advanced controls should be hidden behind **Configure**.
- It should be launched from **Live Monitor**, not shoved into Flight Recorder.

#### Visible UI elements
From the later screenshots:
- Live Monitor page includes a dedicated **Live Overlay** card.
- Buttons:
  - **Hide Overlay** (meaning overlay is currently visible/active)
  - **Configure**
- Preset label/control:
  - **Preset** with visible value **Custom**
- Status chip:
  - **Active**
- Attached display status:
  - **Attached to NE160QDM-NYJ (2048x1280)**
- Toggle hint:
  - **Toggle: Ctrl+Shift+F9**
- Summary text on the right:
  - **Custom | Bottom strip | 66% opacity | Final output**

#### Advanced configuration settings shown in dialog
The **Live Overlay Configuration** dialog contains these grouped sections:

1. **Placement**
   - Position
   - Margin
   - Attach
   - Width
   - Height
   - Display

2. **Appearance**
   - Opacity
   - Background
   - Line thickness
   - Show legend
   - Show live values

3. **Behavior**
   - Auto-hide when target loses focus
   - Always on top
   - Click-through
   - FPS cap
   - Toggle hotkey

4. **Data**
   - Source
   - History

5. **Axes**
   - Axis list with Include toggles and Color values

Buttons at bottom:
- Restore Defaults
- OK
- Cancel

#### Specific values visible in screenshot
- Position: **Bottom strip**
- Width: **Standard**
- Margin: **18 px**
- Height: **0.60**
- Attach: **Attach to display**
- Display: **NE160QDM-NYJ (2048x1280)**
- Opacity: **0.66**
- Background: **0.82**
- Line thickness: **2.80**
- FPS cap: **60 fps**
- Toggle hotkey: **Ctrl+Shift+F9**
- Source: **Final output**
- History: **7.50 s**

#### Preset / configuration philosophy
The user explicitly wanted:
- a small **Configure** button,
- defaults that are sane enough that most people will not need to open it,
- and to avoid dumping fifty settings directly into the main page.

The assistant suggested a model where the live overlay remains simple on the main page, while advanced settings live in a dialog/drawer. The resulting screenshots show exactly that approach.

#### Architectural direction discussed
The live overlay was supposed to share a **common overlay engine** with the replay/export overlay rather than duplicating logic. The intended shared pieces were:

- telemetry buffer / history ring buffer,
- overlay style/config model,
- trace builder / layout logic,
- renderer core,
- replay/export compositor adapter,
- live overlay window adapter.

#### Constraints / non-goals discussed
- Avoid game injection.
- Avoid graphics API hooking.
- Avoid anti-cheat-risky methods.
- Keep it external, window-based, and best-effort for borderless/windowed mode.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Feature: Live Monitor`

### Feature: Live Monitor
#### What it does
A page dedicated to live HOTAS inspection.

#### Visible purpose text
From screenshot:
- **“Watch raw HOTAS input, final vJoy output, buttons, hats, and axis levels in one dedicated live workspace.”**

This strongly implies the page can display both raw input and final output and likely expose broader controller state than just a single graph.

#### Visible controls
- Monitor Controls section
- Axis selector (visible value: **Roll**)
- Checkbox: **Show raw and output together**
- A “Live” status chip/button on the right side of the Monitor Controls card
- Live Overlay card beneath it
- Raw Input Trace graph for selected axis

#### Visible graph title
- **Raw Input Trace · Roll**

#### Visible graph description
- **“Recent raw HOTAS input for the selected axis.”**

#### Relationship to Live Overlay
The Live Overlay controls were placed here rather than in Flight Recorder. This was an explicit design decision to preserve Flight Recorder’s page cleanliness.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Feature: Recording Library`

### Feature: Recording Library
#### What it does
A table/list of recorded clips that can be sorted, refreshed, and reopened.

#### Visible UI elements
- Title: **Recording Library**
- Description line along the lines of reviewing captures from the selected destination and reopening them without leaving V2
- Sort control with example value: **Newest First**
- Refresh button
- Table columns:
  - Clip
  - Recorded
  - Duration
  - Opened

#### Example recorded row visible
- Clip name truncated as something like **flight ...**
- Recorded date/time example: **Apr 04, 2026 09:11 PM**
- Duration: **0:20**
- Opened: **Apr 04, 2026 09:12**

#### Why it exists
It keeps the replay/export workflow inside the app and avoids leaving the workspace.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Feature: Clip Preview`

### Feature: Clip Preview
#### What it does
An in-app video playback area for reviewing captured clips.

#### Visible UI elements
- Title: **Clip Preview**
- Description text indicating clips can be played back directly inside the workspace
- Video frame area
- Playback control bar (seen more fully in later screenshot)
- Play button
- Timeline/scrubber
- Reveal File button
- Metadata line under player

#### Visible metadata examples
- Recorded filename: **flight_recorder_2026-04-04_21-11-42**
- Overlay: **Final output**
- Resolution: **2048x1280**
- Length: **20s**

#### Why it exists
To immediately verify capture results and keep the workflow integrated.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Feature: Hindsight / Buffered Replay / Save Previous Interval`

### Feature: Hindsight / Buffered Replay / Save Previous Interval
#### What it does
Continuously buffers the last configured duration and saves that buffered clip when the trigger hotkey is pressed.

#### Why it exists
Important events often happen before the user decides to capture them. This mode lets the app save the previous interval after the fact.

#### Evidence in chat
The user explicitly described:
- an option in Flight Recorder to record from the point the other keybind is pressed for the configured duration,
- or instead buffer the duration and, when the keybind is pressed, save the current buffer,
- described as **“its like hindsight”**.

The later screenshot shows this realized in UI form with:
- status chips including **Buffering** and **Clip hotkey armed**,
- button **Save Last Clip**,
- Trigger Mode value **Press to save previous interval**,
- status text indicating the app is recording or buffering and instructing the hotkey use.

#### Why this is significant
It elevates Flight Recorder from a standard recorder into a retroactive capture/debugging tool.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Feature: Workspace Save / Revert`

### Feature: Workspace Save / Revert
#### Visible UI elements
In lower right of app window across multiple screenshots:
- **Revert**
- **Save Workspace**

#### Related status text
Top status region in later screenshots shows:
- **Workspace Copy**
- **Unsaved**
- **Live**

Bottom status/footer references things like:
- **Workspace copy: hotas_bridge_config_v2.json**
- **Preset profile: Balanced Flight** (earlier screenshot)

This implies the application supported workspace persistence, working copies, and unsaved-change indicators.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Screenshot 1 — Flight Recorder main page with “Record Now”`

### Screenshot 1 — Flight Recorder main page with “Record Now”
**File placeholder:** `d1171511-6312-49e5-b7f8-839b3690f5ee.png`

#### What is visible
A full-window screenshot of **HOTAS Control Panel V2** on the **Flight Recorder** page.

#### Left sidebar
Top branding panel:
- app icon thumbnail on left
- large label **HOTAS V2**
- subtext **Control workspace**

Sections visible in sidebar:
- **SETUP**
  - Mapping
  - Profiles
  - Modes
- **TUNING**
  - Base Tuning
  - Filtering
  - Combat Profile
  - Conditional Rules
- **ANALYSIS**
  - Effective Response Stack
  - Live Monitor
  - Flight Recorder (selected)
- **SUPPORT**
  - Help / Docs
  - Perf / Diagnostics

Bottom sidebar card:
- circular green live indicator
- label **Runtime**
- larger text **Live telemetry**

#### Main header area
- Large title: **HOTAS Control Panel V2**
- Description: **Routing, tuning, live inspection, and guided diagnosis in one focused control workspace.**
- Right status area:
  - STATUS label
  - badges: Preset, Saved, Live
- Right assistant area:
  - ASSISTANT label
  - Helm button

#### Flight Recorder section
- Title: **Flight Recorder**
- Description text about capturing the desktop and compositing time-matched axis trace overlay
- Additional instruction text about using the hotkey to create a clean replay with matched HOTAS signal history baked into the clip
- Status badges:
  - Ready
  - Hotkey armed
  - Final output
- Button on right: **Record Now**

#### Recorder Settings card
Visible fields and buttons:
- Destination with path ending in `hotas_recordings_v2`
- Browse
- Open Folder
- Length: 20 s
- Frame Rate: 30 fps
- History: 6.00 s
- Overlay Source: Final output
- Capture Source: Current display
- Display: NE160QDM-NYJ (2048x1280)
- Hotkey: Ctrl+Shift+F10
- Checkbox / toggle: Record the cursor
- Green badge/button: Game ready
- Label or button: Settings
- Blue progress bar at 100%
- Status text below: **Saved recording to flight_recorder_2026-04-04_21-11-42.mp4.**

#### Axis Overlay card
- Title: **Axis Overlay**
- Description about choosing which axes appear in the rendered overlay and assigning colors
- Table with columns: Axis / Include / Color
- Rows: Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2
- Roll, Pitch, Throttle, Yaw appear included; Aux 1 / Aux 2 may also be present with toggles

#### Lower cards partially visible
- Recording Library
- Clip Preview

#### Bottom footer/status bar
- Left message repeats saved recording filename
- Center breadcrumb/status line includes:
  - Flight Recorder
  - Roll
  - Balanced Flight
  - Preset profile: Balanced Flight
- Right buttons: Revert / Save Workspace

#### Design inferences
This is a mature, organized page. The recorder workflow was already polished before the live overlay discussion began.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Screenshot 2 — Flight Recorder with library table and loaded clip preview`

### Screenshot 2 — Flight Recorder with library table and loaded clip preview
**File placeholder:** `429cf5b5-58fd-4b47-b16f-c124a853d86d.png`

#### What is visible
The same overall app on Flight Recorder, but further scrolled/lower content is visible.

#### Differences from screenshot 1
- The top of the page is partially cropped away.
- The progress/status area remains visible.
- **Recording Library** and **Clip Preview** are now prominently shown.

#### Recording Library details
- Sort control visible with **Newest First**
- Refresh button
- Table visible with one recording row
- Columns: Clip, Recorded, Duration, Opened
- Example row:
  - clip name truncated as `flight ...`
  - recorded `Apr 04, 2026 09:11 PM`
  - duration `0:20`
  - opened `Apr 04, 2026 09:12`

#### Clip Preview details
- Description about opening captures directly inside the workspace
- Text indicating loaded file: `flight_recorder_2026-04-04_21-11-42.mp4`
- Preview image shows a recording of the app itself
- Overlay traces are visible along the bottom of the previewed clip

#### Design significance
This confirms the recorder was not just an exporter. It had a review workflow built in.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Screenshot 3 — Flight Recorder preview with playback controls and metadata`

### Screenshot 3 — Flight Recorder preview with playback controls and metadata
**File placeholder:** `97116bd9-2de4-419c-8912-dd856d285902.png`

#### What is visible
The Flight Recorder page with a more complete Clip Preview area.

#### Clip Preview details
- Larger previewed video frame
- Play button below preview
- Scrubber/timeline bar
- Time indicator showing something like **0:07 / 0:20**
- **Reveal File** button
- Metadata line below:
  - `Recorded: flight_recorder_2026-04-04_21-11-42`
  - `Overlay: Final output`
  - `Resolution: 2048x1280`
  - `Length: 20s`

#### Recording Library details
Still visible on left, with same row.

#### Design significance
This shows the in-app player became much more than a placeholder. It had interactive transport controls and file reveal integration.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Screenshot 4 — Exported clip open in external media player`

### Screenshot 4 — Exported clip open in external media player
**File placeholder:** `08ff6aa9-81a6-4beb-8310-a0f060901295.png`

#### What is visible
Windows Media Player or a similar media app is open with the exported recorder video playing.

#### Inside the video frame
- The HOTAS Control Panel app is visible being recorded on-screen
- A large bottom telemetry overlay strip is composited over the video
- Overlay contains:
  - axis traces in multiple colors
  - legend/value list on the right side of strip
  - line graph spanning left-to-right
- The overlay is semi-transparent and wide, covering the bottom band of the video

#### Design significance
This confirms the exported file itself had the overlay baked into it, not just in-app preview.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Screenshot 5 — Live overlay working over desktop / browser / PDF`

### Screenshot 5 — Live overlay working over desktop / browser / PDF
**File placeholder:** `08e9b077-6a3d-4918-a574-322eb77b5605.png`

#### What is visible
A desktop screenshot with multiple windows open:
- browser displaying a Canvas PDF / Exam page,
- another chat or app window on the right,
- and a detached telemetry overlay strip sitting across the bottom of the screen.

#### Overlay appearance
- Semi-transparent dark strip
- Label on left: **HOTAS live telemetry**
- Real-time axis traces in multiple colors
- Legend/value list on the right side of strip
- The overlay floats above the desktop content
- It looks click-through / detached rather than embedded into the main app

#### Design significance
This is the first visual proof that the **real live overlay** exists and works outside the main application window.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Screenshot 6 — Updated Flight Recorder with buffering / save last clip`

### Screenshot 6 — Updated Flight Recorder with buffering / save last clip
**File placeholder:** `2e5ad759-c907-44f3-9a40-9ccd7c1dfbab.png`

#### What is visible
Flight Recorder page in a newer state.

#### Top status area changes
- STATUS badges now show:
  - Workspace Copy
  - Unsaved
  - Live

#### Flight Recorder section changes
- Status badges now show:
  - Buffering
  - Clip hotkey armed
  - Final output
- Right action button changed to: **Save Last Clip**

#### Recorder Settings changes
- Trigger Mode field is visible with value:
  - **Press to save previous interval**
- Hotkey and other settings remain present
- Green state chip still says **Game ready**
- Progress/status region says something like the app is recording/buffering the current display and the hotkey saves the last N seconds
- Bottom status line says:
  - **Saved recording to flight_recorder_2026-04-05_12-06-00.mp4.**

#### Design significance
This confirms the hindsight/buffer concept made it into the UI and became a formal recorder mode.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Screenshot 7 — Live Monitor page with Live Overlay controls`

### Screenshot 7 — Live Monitor page with Live Overlay controls
**File placeholder:** `df6c82a7-ce99-4530-88a7-a01d3d0b8b29.png`

#### What is visible
The **Live Monitor** page of the app.

#### Page title and description
- Title: **Live Monitor**
- Description: **Watch raw HOTAS input, final vJoy output, buttons, hats, and axis levels in one dedicated live workspace.**

#### Monitor Controls card
- Axis selector set to **Roll**
- Checkbox: **Show raw and output together**
- Live chip on the right

#### Live Overlay card
- Title: **Live Overlay**
- Description: **Launch the detached telemetry strip, choose a preset, and adjust advanced behavior only when needed.**
- Buttons: **Hide Overlay**, **Configure**
- Preset field/value: **Custom**
- Status chip: **Active**
- Display attachment text: **Attached to NE160QDM-NYJ (2048x1280)**
- Toggle hint: **Toggle: Ctrl+Shift+F9**
- Summary text: **Custom | Bottom strip | 66% opacity | Final output**

#### Graph below
- Title: **Raw Input Trace · Roll**
- Description: **Recent raw HOTAS input for the selected axis.**
- Large graph with blue trace spikes

#### Design significance
This is the clearest confirmation of the final architectural/UI decision: the overlay feature belongs in **Live Monitor**, not Flight Recorder.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Screenshot 8 — Live Overlay Configuration dialog`

### Screenshot 8 — Live Overlay Configuration dialog
**File placeholder:** `f0aa307f-bdb5-4f03-8db6-daaaa01e6881.png`

#### What is visible
A detached modal window titled:
- **Live Overlay Configuration - HOTAS Control Panel V2**

#### Intro text
- **“Fine-tune placement, appearance, and data behavior for the detached live telemetry overlay. Axis colors are shared with Flight Recorder so replays and live telemetry stay consistent.”**

#### Sections and fields
##### Placement
- Position: Bottom strip
- Margin: 18 px
- Attach: Attach to display
- Width: Standard
- Height: 0.60
- Display: NE160QDM-NYJ (2048x1280)

##### Appearance
- Opacity: 0.66
- Background: 0.82
- Line thickness: 2.80
- Show legend checkbox
- Show live values checkbox

##### Behavior
- Auto-hide when target loses focus
- Always on top
- Click-through
- FPS cap: 60 fps
- Toggle hotkey: Ctrl+Shift+F9

##### Data
- Source: Final output
- History: 7.50 s

##### Axes
- Table showing Axis / Include / Color
- Roll, Pitch, Throttle, Yaw, Aux rows visible
- Shared axis colors with recorder

#### Bottom buttons
- Restore Defaults
- OK
- Cancel

#### Design significance
This dialog is the exact embodiment of the user’s UX preference: **advanced settings are available, but hidden until needed**.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Confirmed architecture decisions from the chat`

### Confirmed architecture decisions from the chat
The live overlay should be implemented without destroying the existing Flight Recorder page. The assistant proposed, and the later screenshots strongly imply, the following architecture path:

#### Shared overlay engine
A shared overlay core should handle:
- telemetry history buffering,
- axis inclusion,
- axis colors,
- time window / history duration,
- graph scaling / layout,
- legend rendering,
- live value rendering,
- line/trace generation.

#### Two rendering/output paths
1. **Replay / export overlay rendering**
   - Used when compositing overlay into captured recordings.
2. **Live transparent overlay window rendering**
   - Used for detached, real-time on-screen overlay.

#### Suggested shared modules/components discussed
- telemetry buffer / history ring buffer
- overlay style/config model
- overlay trace builder / graph layout logic
- overlay renderer core
- replay/export compositor adapter
- live overlay window adapter

#### Window behavior for live overlay
The live overlay should be:
- separate top-level window,
- frameless / borderless,
- transparent background,
- always-on-top,
- click-through,
- able to show/hide independently of main app.

#### Main UI entry point decision
- Launch/control entry point should live in **Live Monitor**.
- Flight Recorder should remain focused on capture/replay/export.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### State / workflow behavior inferred from screenshots`

### State / workflow behavior inferred from screenshots
#### Recorder states
Visible examples:
- Ready
- Hotkey armed
- Buffering
- Clip hotkey armed
- Recording
- Saved
- Live
- Unsaved
- Workspace Copy

This implies the app had a structured state model around:
- workspace dirty/saved state,
- recorder armed/running/buffering state,
- overlay active state,
- and live telemetry/runtime status.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Configuration persistence inferred`

### Configuration persistence inferred
Visible strings suggest saved/working files and preset/workspace relationships:
- **Preset profile: Balanced Flight**
- **Workspace copy: hotas_bridge_config_v2.json**

**Inference:** The app likely stored JSON-based workspace/config files and supported working copies or modifiable clones of presets.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Framework / language`

### Framework / language
No framework or programming language is explicitly confirmed in this chat.

**Inference:** Because of the custom desktop UI, detached overlay window, cards, dialogs, and Windows-native appearance, the app may have been implemented in something like Qt / PySide / PyQt or another desktop UI framework. However, this is not confirmed and should not be treated as recovered fact.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Input handling / controller data model`

### Input handling / controller data model
Direct implementation code is not shown, but the UI and descriptions imply the app had at least two distinct streams:
- **raw HOTAS input**
- **final vJoy output**

This is explicitly visible in Live Monitor description text.

**Inference:** The app likely read physical controller input, applied mapping/tuning/transforms, then exposed/emitted a processed output stream through vJoy or equivalent virtual joystick layer.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Profiles / presets / workspaces`

### Profiles / presets / workspaces
Visible concepts:
- Preset
- Saved / Unsaved
- Workspace Copy
- Save Workspace
- Revert
- Preset profile: Balanced Flight
- Custom live overlay preset

This strongly suggests:
- reusable profiles/presets,
- mutable workspace copies,
- saved vs unsaved state management,
- and per-feature settings persistence.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Directly recoverable axis set`

### Directly recoverable axis set
Visible axes in overlay tables and legends:
- Roll
- Pitch
- Throttle
- Yaw
- Aux 1
- Aux 2



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Raw vs final output`

### Raw vs final output
The app supported both:
- raw HOTAS input,
- and final processed output.

This is explicit in the Live Monitor text and in the discussion of overlay source.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Overlay source options`

### Overlay source options
At minimum, the following source is visible:
- **Final output**

The design discussion also left room for future options like:
- Raw
- Both

The earlier assistant’s architecture advice explicitly suggested supporting raw/final/both later, but only **Final output** is visibly confirmed in the implemented screenshots.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Profiles / tuning implications`

### Profiles / tuning implications
The footer text mentions:
- **Balanced Flight**
- **Preset profile: Balanced Flight**

This indicates the app supported named tuning or mapping profiles for flight behavior.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Intended tuning behavior (partial, inferred)`

### Intended tuning behavior (partial, inferred)
This specific chat did not include explicit curve mathematics, deadzone formulas, or detailed axis transformation logic. However, the UI and page names strongly imply support for:
- per-axis tuning,
- filtering,
- combat profile behavior,
- conditional rules,
- effective response stack analysis.

The control logic was likely broad enough to support scenarios where the user wanted to inspect roll, pitch, throttle, yaw behavior live and in exported replays.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Specific vehicle/game tuning discussions`

### Specific vehicle/game tuning discussions
This chat did **not** contain detailed Battlefield-specific tuning values or helicopter/jet mapping logic. Those items may exist in other chats, but they are **not recoverable from this thread** beyond the general fact that this is HOTAS control software and the app uses flight-themed language.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Purpose of the overlay recorder system`

### Purpose of the overlay recorder system
To capture what happened on-screen and time-match it with controller behavior so the resulting clip is useful for analysis and debugging rather than just being plain video.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### What it recorded`

### What it recorded
- Desktop / current display video
- HOTAS telemetry traces composited into the final clip



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### How hindsight / buffer capture worked`

### How hindsight / buffer capture worked
Recovered design/behavior:
- The app can continuously buffer the last configured interval.
- Pressing the trigger keybind saves that buffered segment.
- This is represented in UI as **Trigger Mode: Press to save previous interval**.
- The user explicitly compared it to **Hindsight**.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### UI support for recorder`

### UI support for recorder
Recovered UI pieces:
- status chips,
- keybind armed indicators,
- progress bar,
- current display selector,
- record cursor toggle,
- overlay source selector,
- history duration setting,
- recording library,
- in-app preview,
- reveal file control,
- save last clip button.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### How it helped tune controls`

### How it helped tune controls
By matching controller traces to what happened in gameplay or on-screen behavior, it allowed the user to review:
- control timing,
- axis movement,
- behavior under current profile/preset,
- and likely whether tuning changes improved controllability.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Export / replay / debug significance`

### Export / replay / debug significance
This system effectively turned the app into:
- a tuning tool,
- a debugging recorder,
- and a post-action analysis tool.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Closest implementation artifacts that should still be preserved`

### Closest implementation artifacts that should still be preserved
The conversation produced detailed **implementation prompts** intended for Codex / coding agents. Those prompts were important design artifacts because they captured constraints and architecture plans. The main ideas contained in those prompts included:

- preserve current Flight Recorder page,
- build live overlay as a separate real-time always-on-top window,
- put launch/control in Live Monitor,
- hide advanced settings behind Configure,
- reuse shared overlay logic rather than duplicating replay/live code,
- use a shared telemetry buffer, overlay config, trace builder, renderer core, and adapters.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Recovered implementation direction from those prompts`

### Recovered implementation direction from those prompts
#### Shared overlay engine pieces
- telemetry buffer / history ring buffer
- overlay style/config model
- trace builder / graph layout logic
- renderer core
- replay/export compositor adapter
- live overlay window adapter

#### UI deliverables
- Open Live Overlay / Hide Overlay control
- Configure dialog
- compact status summary
- live overlay detach/toggle support
- buffered replay trigger mode in Flight Recorder



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Dependencies or setup steps`

### Dependencies or setup steps
No direct dependency list is present.

**Inference:** live overlay functionality would require a desktop UI toolkit capable of transparent always-on-top windows and click-through behavior on Windows.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Problem: Risk of wrecking the current Flight Recorder page`

### Problem: Risk of wrecking the current Flight Recorder page
#### Symptom / concern
The user explicitly did **not** want to change or damage the current page layout while adding live overlay functionality.

#### Cause
Adding many overlay settings directly into Flight Recorder would clutter it and compromise its design.

#### Fix / design solution
- Keep Flight Recorder visually stable.
- Put live overlay entry point in Live Monitor.
- Hide advanced overlay settings behind Configure.
- Reuse shared overlay logic behind the scenes.

#### Status
Resolved at the design level and apparently implemented successfully based on later screenshots.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Problem: Live overlay settings could become excessive`

### Problem: Live overlay settings could become excessive
#### Symptom / concern
The user explicitly said they did not want **“50 different settings”** for location and exact sizing on replay/saved footage.

#### Fix / design solution
- Replay/export should keep settings minimal.
- Live overlay can justify more settings, but they should be hidden behind Configure.
- Defaults should be sane and not require touching.

#### Status
Resolved in implementation screenshots through the dedicated configuration dialog.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Problem: Need real live overlay without invasive techniques`

### Problem: Need real live overlay without invasive techniques
#### Symptom / concern
A live overlay sounded desirable, but there was concern about difficulty and implementation approach.

#### Fix / design solution discussed
Use a separate transparent overlay window rather than injected in-game rendering or graphics API hooking.

#### Status
Appears implemented successfully based on screenshot showing detached desktop overlay.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Explicit preferences from the user`

### Explicit preferences from the user
- The current UI/page setup was considered **beautiful** and should be preserved.
- Advanced controls should not clutter the main page.
- A small **Configure** button is ideal.
- Defaults should be so sane that extra settings rarely need touching.
- For replay/saved past footage, there should **not** be a huge number of overlay positioning/sizing settings.
- A real live overlay was highly desirable.
- If live overlay exists, then more appearance/placement settings become useful.
- The user was very enthusiastic about a separate live overlay and the configure-dialog pattern.
- The user wanted Helm to have a small ship’s wheel icon with a modern-but-1780 feel.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Things the user wanted preserved`

### Things the user wanted preserved
- The overall Flight Recorder page layout
- The polished look of the app
- A clean main workflow
- The app’s premium feeling



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Things the user disliked or wanted to avoid`

### Things the user disliked or wanted to avoid
- Wrecking the existing page
- Dumping too many settings directly into the main recorder UI
- Overcomplicating replay overlay configuration



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Strong workflow preferences`

### Strong workflow preferences
- Keep simple controls visible; hide advanced configuration until needed.
- Support a one-key trigger workflow for overlay visibility.
- Support a one-key capture workflow for both forward and buffered recording modes.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Performance / behavior expectations implied`

### Performance / behavior expectations implied
- Efficient overlay update rate (FPS cap available)
- Smooth enough to be useful live
- External, detached overlay that stays out of the way
- Click-through so it does not interfere with the game or desktop interaction

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Must-have features from this chat`

### Must-have features from this chat
- Recreate the **Flight Recorder** page with:
  - header/title/description,
  - recorder status chips,
  - recorder settings card,
  - axis overlay card,
  - recording library,
  - clip preview,
  - bottom status/footer,
  - save/revert workspace controls.
- Recreate **Live Monitor** page with:
  - Monitor Controls,
  - Raw Input Trace graph,
  - Live Overlay control card.
- Implement **Live Overlay** as a detached transparent window.
- Implement **Configure** dialog for overlay settings.
- Implement **toggle hotkey** for live overlay.
- Implement **forward capture** mode.
- Implement **buffered/hindsight** mode.
- Share axis color configuration between live overlay and recorder overlay.
- Preserve **Helm** assistant UI presence in top header.
- Preserve or recreate Helm icon asset slot next to title on Helm page.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Nice-to-have / polish features from this chat`

### Nice-to-have / polish features from this chat
- Working in-app video preview transport controls
- Reveal File integration
- Library sorting and refresh
- Workspace Copy / Unsaved / Live state chips
- Preset profile display (e.g. Balanced Flight)
- Restore Defaults button in overlay configuration
- Status summaries like `Custom | Bottom strip | 66% opacity | Final output`



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### UI pieces to recreate`

### UI pieces to recreate
- Left sidebar with section headers and selected-state highlight
- Brand tile (`HOTAS V2`, `Control workspace`)
- Top status block and assistant block
- Large rounded cards
- Rounded pill controls and badges
- Semi-transparent overlay strip
- Graph panels
- Footer status/breadcrumb bar



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Files/modules likely needed`

### Files/modules likely needed
Recovered from architecture discussion:
- telemetry buffer / history ring buffer module
- overlay config/style model
- trace builder / layout module
- renderer core
- replay/export compositor
- live overlay window module
- Flight Recorder page/module
- Live Monitor page/module
- overlay configuration dialog/module
- workspace/profile persistence module
- recording library management module
- clip preview/player module



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Recommended implementation order`

### Recommended implementation order
1. Recreate the main desktop shell and sidebar/header/footer layout.
2. Rebuild Flight Recorder page structure and static fields.
3. Rebuild Live Monitor page structure and graph placeholders.
4. Implement shared telemetry/overlay core.
5. Recreate export/replay overlay path for Flight Recorder.
6. Implement detached live overlay window using shared core.
7. Add Configure dialog and persistence.
8. Add forward capture and buffered capture trigger modes.
9. Recreate recording library and clip preview playback flow.
10. Add Helm icon/title treatment.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Testing / debugging checklist`

### Testing / debugging checklist
- Verify overlay colors match between live overlay and exported clips.
- Verify live overlay toggle hotkey works reliably.
- Verify recorder hotkey works for both forward and buffered modes.
- Verify Flight Recorder page remains visually intact after feature additions.
- Verify clip preview loads saved files correctly.
- Verify library refresh/sort behavior.
- Verify workspace save/revert and unsaved indicators.
- Verify overlay placement/opacity config persists.
- Verify click-through + always-on-top behavior on Windows.
- Verify attached display logic for overlay placement.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Details not recoverable from this chat`

### Details not recoverable from this chat
- Exact programming language/framework
- Exact project file structure and filenames
- Exact controller hardware model(s)
- Exact vJoy integration code or libraries
- Exact capture/encoding pipeline implementation
- Exact graph rendering implementation
- Exact workspace/preset JSON schema
- Exact overlay compositing code
- Any math for response curves or filtering
- Any button/hat mapping logic details



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Screenshots needing manual review if higher precision is required`

### Screenshots needing manual review if higher precision is required
All screenshots should be manually reattached and zoomed if exact field text, spacing, or tiny labels are needed. This document preserves what is legible at chat resolution, but finer UI details may require direct image inspection in the original files.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Features referenced but not fully explained`

### Features referenced but not fully explained
- Mapping page
- Profiles page
- Modes page
- Base Tuning
- Filtering
- Combat Profile
- Conditional Rules
- Effective Response Stack
- Help / Docs
- Perf / Diagnostics
- Helm assistant capabilities beyond branding/presence



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Questions future-you should answer later`

### Questions future-you should answer later
- What exact desktop framework was used?
- What capture library or renderer was used for Flight Recorder?
- How were raw input and final output represented internally?
- What exact preset/workspace file formats existed?
- Was the live overlay always display-attached, or could it target a specific window?
- Were raw/final/both overlay source modes implemented beyond Final output?
- How were clips indexed in Recording Library?

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `## 14. Codex / AI Rebuild Prompt`

## 14. Codex / AI Rebuild Prompt

Use the following as a rebuild prompt for this specific chat’s recovered scope:

### Rebuild Prompt
I need you to rebuild the HOTAS Control Panel V2 features described below from a recovery document. Treat this as a forensic reconstruction of a lost desktop application UI and feature set. Preserve the overall premium dark-theme style and do not redesign the product into something generic.

Scope to rebuild:
1. Main desktop shell with left sidebar, top header/status area, assistant area, and bottom footer/status bar.
2. Flight Recorder page with:
   - title and descriptive text,
   - status chips,
   - Recorder Settings card,
   - Axis Overlay card,
   - Recording Library card,
   - Clip Preview card,
   - Save Workspace / Revert controls,
   - workspace/preset/status context in footer.
3. Live Monitor page with:
   - Monitor Controls section,
   - axis selector,
   - raw input trace graph,
   - Live Overlay control card.
4. Detached live telemetry overlay window that is:
   - transparent,
   - click-through,
   - always-on-top,
   - toggleable by hotkey,
   - bottom-strip by default,
   - driven by shared telemetry data.
5. Live Overlay Configuration dialog with grouped sections:
   - Placement,
   - Appearance,
   - Behavior,
   - Data,
   - Axes.
6. Flight Recorder trigger modes:
   - forward capture from trigger time for configured duration,
   - buffered/hindsight capture that saves the last configured interval when the trigger is pressed.
7. Shared axis color configuration between exported replay overlays and live overlay.
8. Helm assistant presence in header and support for a small ship’s wheel icon next to Helm title on its page.

Hard constraints:
- Preserve the clean Flight Recorder layout; do not clutter it with advanced live overlay placement settings.
- Put live overlay controls in Live Monitor.
- Keep advanced live overlay settings hidden behind a Configure dialog.
- Use sane defaults so the overlay works immediately without opening Configure.
- Reuse a shared overlay engine between replay/export overlay rendering and the live overlay window.
- Avoid invasive graphics API hooking or game injection; prefer an external top-level overlay window.

Recovered design details:
- App title: HOTAS Control Panel V2
- Main tagline: “Routing, tuning, live inspection, and guided diagnosis in one focused control workspace.”
- Live Monitor subtitle: “Watch raw HOTAS input, final vJoy output, buttons, hats, and axis levels in one dedicated live workspace.”
- Flight Recorder subtitle should mention capturing the desktop on demand and compositing a time-matched axis trace overlay into the finished video.
- Axis set: Roll, Pitch, Throttle, Yaw, Aux 1, Aux 2
- Example axis colors:
  - Roll #58B8FF
  - Pitch #6FDB9F
  - Throttle #F0C46A
  - Yaw #CF95FF
  - Aux 1 #FF9B6B
  - Aux 2 #6ED9D0
- Example overlay defaults:
  - position Bottom strip
  - width Standard
  - opacity 0.66
  - background 0.82
  - line thickness 2.80
  - source Final output
  - history 7.50 s
  - attach to display
  - click-through on
  - always-on-top on
- Recorder example settings:
  - length 20 s
  - frame rate 30 fps
  - history 6.00 s
  - hotkey Ctrl+Shift+F10
  - display NE160QDM-NYJ (2048x1280)
- Live overlay toggle hotkey example: Ctrl+Shift+F9

Architecture expectations:
Create a shared overlay engine with:
- telemetry history ring buffer,
- overlay style/config model,
- trace builder / graph layout logic,
- renderer core,
- replay/export overlay compositor,
- live overlay window adapter.

Make the UI feel premium:
- deep navy background,
- lighter dark-blue cards,
- rounded corners,
- pill-style badges and controls,
- high-contrast white headings,
- muted descriptive text,
- subtle borders,
- polished spacing.

Implementation notes:
- Support status chips such as Ready, Hotkey armed, Buffering, Clip hotkey armed, Final output, Active, Live, Workspace Copy, Unsaved.
- Support Recording Library with sort and refresh.
- Support Clip Preview with play button, scrubber, and Reveal File button.
- Support Workspace save/revert flow.
- Keep everything modular and maintainable.

Deliverables:
- Recreated UI shell and pages
- Shared overlay engine
- Recorder modes
- Live overlay window
- Configure dialog
- basic persistence for workspace/overlay settings
- placeholder Helm page/title area with icon support

If any implementation details are uncertain, keep the visible product behavior and UI structure faithful to the recovered design rather than inventing a radically different system.

---




### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.15 Live Monitor page`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.19 Overlay / Recorder / Flight Recorder`

### 2.19 Overlay / Recorder / Flight Recorder

**Feature mentioned from project memory in this chat:** The app had an overlay and a flight recorder concept.

**Known details preserved from conversation context:**

- Overlay could be turned on/off with a keybind.
- Flight recorder could record from the point a keybind is pressed for a specified duration.
- Alternative mode: maintain a buffer for a specified duration and, when keybind is pressed, save the current buffer — described by user as “hindsight.”
- Intended purpose: capture control behavior around flight moments so tuning problems could be reviewed after they occur.
- Mentioned as already existing in earlier HOTAS project work.

**Needed rebuild note:** This chat did not provide screenshots of the overlay/recorder UI in the later V2, but the behavior should be preserved as a planned/known feature.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `## 7. Overlay / Recorder / Flight Recorder Features`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 34 — Final V2 Live Monitor page, graph view`

### Screenshot 34 — Final V2 Live Monitor page, graph view

Live Monitor selected. Runtime Live in sidebar and top status. Monitor Controls card with Axis dropdown and checkbox. Raw Input Trace graph and Raw vs Final Overlay graph. Shows live-looking plotted data.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 35 — Final V2 Live Monitor page, axis/buttons view`

### Screenshot 35 — Final V2 Live Monitor page, axis/buttons view

Scrolled Live Monitor shows Axis Levels bar chart: Roll/Pitch/Throttle/Yaw/Aux1/Aux2 raw and final bars. HOTAS Buttons B1–B15 and Mapped Output Buttons Out 1–Out 20 visible. Strong professional live telemetry feel.




### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `## 7. Overlay / Recorder / “Flight Recorder” Features`

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
