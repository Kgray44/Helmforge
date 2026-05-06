# Helm Assistant Specification

**Spec-set role:** forensic reconstruction document generated from the three recovered HOTAS Control Panel chat notes. This document is meant to stand on its own while cross-referencing the rest of the set.

**Evidence taxonomy used throughout:**
- **Confirmed Facts**: directly stated in the recovery notes or visible as exact recovered UI text.
- **Screenshot-Derived Details**: observations recovered from screenshot descriptions in the source notes.
- **Inferences**: explicitly inferred from the notes or reconstructed from adjacent evidence.
- **Desired Improvements**: user preferences, future direction, fixes, or rebuild requirements.
- **Unknowns**: details the notes say are missing, uncertain, or need later verification.

## Confirmed Facts

- Assistant name: **Helm**.
- Helm is a built-in tuning/diagnostic assistant.
- Final direction: Helm is not a normal sidebar tab; it launches from the top-right assistant cluster.
- Final overlay uses dimmed/de-emphasized background app.
- Visible top-right section label: `ASSISTANT`.
- Visible launcher/button text: `Helm`.
- Helm changes apply only to current workspace/in-memory draft until saved.
- Helm supports applying selected changes and reverting last Helm changes.
- Example user symptom: “Combat mode feels sluggish.”
- Example generated changes include:
  - Yaw Combat Center Alpha 0.52 -> 0.68
  - Pitch Combat Center Alpha 0.56 -> 0.68
  - Yaw Combat Reverse Slew 0.06 -> 0.09
  - Yaw Combat Same Slew 0.06 -> 0.09
  - Yaw Combat Scale 0.68 -> 0.79

## Screenshot-Derived Details

- Final Helm overlay top-left title: `Helm`.
- Subtitle: “Diagnosis-first tuning guidance for the current workspace.”
- Status card includes green pulse indicator, `Helm is active`, `Context-linked assistant`.
- Safety pill: `In-memory only`.
- Cards: `What’s wrong?`, `What I’d change`, `What I found`, `Apply / Revert`.
- Text box placeholder: `Example: Can't hold aim steady on target.`
- Symptom chips:
  - Can’t hold aim steady
  - Too twitchy near center
  - Overshoots target
  - Combat mode feels sluggish
  - Reversals feel sticky
  - Hard to track smoothly
- Actions:
  - Analyze
  - Review Changes
  - Cancel
  - Apply Selected Changes
  - Revert Last Helm Changes

## Inferences

- Helm should inspect current tuning stack, modes, rules, feel summary, and runtime state.
- Helm v1 can adjust Base Tuning, Filtering, Combat Profile, and mode-related settings.
- Helm v1 should not automatically edit/create/disable conditional rules.
- The assistant needs a structured symptom engine underneath the natural-language input.
- The name Helm reinforces nautical/piloting/command identity.

## Desired Improvements

- Use first-person voice.
- Avoid cold third-person phrases such as “Helm will now...”.
- Avoid raw machine diff dumps.
- Make diagnosis smarter, more contextual, and less preset/timid.
- Add adaptive recommendation magnitudes.
- Analyze rules in real time and say if they are relevant.
- Ask follow-up questions only when needed.
- Preserve premium, calm, concise, slightly characterful tone.
- Support future symptom library, fingerprint/vector matching, and deeper rule analysis.

## Unknowns

- Exact Helm diagnostic algorithm.
- Exact symptom library.
- Exact fix/recommendation library.
- Exact confidence-scoring method.
- Exact icon asset file path after recovery.
- Whether Helm final UI is modal overlay or right-side slide-out in the rebuilt V2; source notes include both final overlay and earlier large slide-out direction.

## Relevant Implementation Prompt Extract

### Desired Improvements
- Helm must be launched from top-right, not in main tab strip/sidebar.
- Helm opens as overlay/modal or large right-side diagnostic workspace depending final UI pass.
- Background dims/blurs/de-emphasizes.
- Include green pulse: `Helm is active` / `Context-linked assistant`.
- Sections: `What’s wrong?`, `What I’d change`, `What I found`, `Apply/Revert`.
- Apply selected changes to in-memory state only; no auto-save.
- Revert last Helm changes.
- Use first-person, polished, product-grade text.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.18 Helm assistant`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 7 — Legacy Helm workspace/tab`

### Screenshot 7 — Legacy Helm workspace/tab

Helm was a page/tab-like diagnostic workspace. Left small status `Helm is active`. Main title `Helm`, copy about describing problem in plain language and inspecting stack/modes/live rule context. Sections: `What's wrong?`, `What I'd change`, `Apply / Revert`. Buttons include Revert Last Helm Changes, Cancel, Apply Selected Changes. At this point Helm was not yet overlay.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 22 — Initial V2 Helm page/tab`

### Screenshot 22 — Initial V2 Helm page/tab

Helm was still a sidebar page. It showed What’s wrong, What I’d change, What I found, Apply/Revert. User wanted Helm moved out of sidebar into a floating assistant overlay.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 37 — Final V2 Helm overlay`

### Screenshot 37 — Final V2 Helm overlay

Helm overlay open over dimmed app. Background app visible/dimmed. Overlay rounded and large. Top status card with green pulsing circle, `Helm is active`, `Context-linked assistant`, Close button. Main content sections as described under Helm. This confirms Helm is no longer a sidebar page.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 8.1 Name and purpose`

### 8.1 Name and purpose

Assistant name: **Helm**.

Purpose:

- Diagnose control-feel problems from plain language.
- Inspect current stack/modes/rules/runtime context.
- Recommend tuning changes.
- Apply selected changes safely to in-memory/current workspace draft.
- Let user review before saving.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 8.2 UI evolution`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 8.3 Helm interaction model`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 8.4 Helm tone goals`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 10.9 V2 early: Helm symptom chips looked like action buttons`

### 10.9 V2 early: Helm symptom chips looked like action buttons

- Symptom: What’s Wrong suggestions confused with Analyze/Review/Cancel buttons.
- Fix: make chips lighter/smaller and action buttons distinct.
- Status: final overlay improved.




### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Feature: Helm Assistant`

### Feature: Helm Assistant
#### What it is
A built-in assistant within the HOTAS Control Panel app. It is consistently shown in the top-right header area as an assistant panel/section.

#### Visible UI details
- Label: **ASSISTANT**
- Button/entry labeled **Helm**
- Located near the top-right header, underneath or beside the status area

#### Purpose inferred from the app and chat
The assistant was referred to as a built-in assistant concept. In this chat it was not functionally expanded, but it appears conceptually tied to:

- explanation,
- guided diagnostics,
- adjustments,
- and potentially helping interpret tuning, profiles, or issues.

#### Icon request discussed
The user wanted to add a small icon next to the title **Helm** at the top of its page. Desired visual style:
- a really basic icon of a ship’s wheel,
- modern,
- but with a **1780 design** influence,
- clear/transparent background.

A generated icon asset was produced for this request.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Screenshot 9 — Helm icon asset`

### Screenshot 9 — Helm icon asset
**File placeholder:** `a_2d_vector_illustration_of_a_ship_s_wheel_icon_is.png`

#### Requested design
- Basic icon of a ship’s wheel
- Modern
- 1780 design influence
- Clear / transparent background
- Intended to sit next to the title **Helm** at the top of its page

#### Generated visual
- Centered ship’s wheel icon
- Thin outlined, modern, clean construction
- Eight-spoke / classic nautical wheel feel
- Blue-gray / slate color palette
- Transparent-capable PNG asset (RGBA file)

#### Recovery note
The file should be preserved as a candidate icon asset for Helm page branding.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `## 8. “Helm” Assistant / Built-in Assistant Concept`

## 8. “Helm” Assistant / Built-in Assistant Concept

### Name
**Helm**

### Placement in the UI
- Top-right header region
- Under or adjacent to the status cluster
- Inside a rounded assistant card with label **ASSISTANT** and a button/entry labeled **Helm**

### Purpose recoverable from this chat
The main app tagline includes **guided diagnosis**, and Helm is visually placed as the built-in assistant. Although this thread did not define its full capability set, the name and placement suggest it was intended to assist with:
- interpreting settings,
- diagnosing control/tuning issues,
- guiding the user through the app,
- or generally acting as an internal helper.

### Personality / theming
The name **Helm** strongly reinforces the nautical / command / piloting metaphor. The later icon request confirms the user wanted this theme visually reinforced with a ship’s wheel icon.

### Icon design requirements
The requested icon next to the Helm title should be:
- basic/simple,
- modern,
- ship’s wheel,
- influenced by an 18th-century / 1780 design,
- on a clear/transparent background.

### Asset note
A generated PNG exists and should be preserved as a starting point for Helm branding.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / `### Potential asset issue: Helm icon background`

### Potential asset issue: Helm icon background
#### Symptom / concern
The user requested a clear/transparent background.

#### Recovery note
A PNG was generated and should be preserved. The file itself supports transparency. Manual review is still recommended to ensure the icon works cleanly at the small title size intended for the Helm page.

---




### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### 2.8 Helm (built-in smart helper)`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `#### Screenshot 5 — Helm early fold-out overlay (descriptive placeholder)`

#### Screenshot 5 — Helm early fold-out overlay (descriptive placeholder)
- Visible content: small compact overlay with text input, quick chips, what I found, confidence, recommended changes, apply/review/cancel.
- User feeling: too cramped, too small, too much content packed into pop-out.
- This directly led to Helm being promoted to a dedicated right-side slide-out workspace.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `#### Screenshot 6 — Helm large workspace mode (descriptive placeholder)`

#### Screenshot 6 — Helm large workspace mode (descriptive placeholder)
- Visible content: large right-side overlay covering most of the app, background dim/blur, “Helm is active” header/indicator, diagnosis sections, diff list, apply/revert.
- Important design decision: Helm should feel different from tabs, more like a diagnostic bridge/command workspace.
- User reaction: loved the concept but wanted richer wording and smarter diagnosis.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `## 8. “Helm” Assistant / Built-in Assistant Concept`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Bug/problem: Helm too small / cramped`

### Bug/problem: Helm too small / cramped
#### Symptom
Tiny overlay could not comfortably display everything.

#### Fix
Promoted to large dedicated right-side slide-out workspace.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Bug/problem: Helm wording too cold / third-person`

### Bug/problem: Helm wording too cold / third-person
#### Symptom
User disliked repeated “Helm thinks… Helm checked…” style.

#### Fix requested
Switch to first-person voice; more human and natural.

---



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Bug/problem: Helm suggestions felt too preset / too weak`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Implementation architecture explicitly requested for Helm`

### Implementation architecture explicitly requested for Helm
Helm should become its own subsystem/library rather than live as a huge block in the main app file:
- Helm engine/service
- symptom library
- recommendation/fix library
- structured types/models
- context analysis helpers

## Second Sweep Addendum: Whole-Concept Anchor

### Confirmed Facts
The first pass preserved Helm's sub-sections, but the source's whole-section heading is also retained here so the assistant concept remains discoverable as a single rebuild unit.

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `## 8. Helm Assistant / Built-in Assistant Concept`

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
