# Conditional Rules System

**Spec-set role:** forensic reconstruction document generated from the three recovered HOTAS Control Panel chat notes. This document is meant to stand on its own while cross-referencing the rest of the set.

**Evidence taxonomy used throughout:**
- **Confirmed Facts**: directly stated in the recovery notes or visible as exact recovered UI text.
- **Screenshot-Derived Details**: observations recovered from screenshot descriptions in the source notes.
- **Inferences**: explicitly inferred from the notes or reconstructed from adjacent evidence.
- **Desired Improvements**: user preferences, future direction, fixes, or rebuild requirements.
- **Unknowns**: details the notes say are missing, uncertain, or need later verification.

## Confirmed Facts

- The Conditional Rules page creates and inspects modifier rules that inject into the response stack based on conditions.
- Exact final visible title: `Conditional Rules`.
- Exact visible copy: “Build responsive modifier rules, track their live state, and see exactly where they inject into the response stack.”
- Status chips visible: `1 rules`, `0 active`, `0 blocked`, `1 disabled`.
- Action buttons: `Add Rule`, `Edit Selected`, `Duplicate`, `Enable`, `Delete`.
- Prominent example rule: `Yaw 0.75 | Roll > 0.35`.
- Rule target: `Yaw`.
- Parameter: `Output Scale`.
- Operation: `Set`.
- Value: `0.75`.
- Injects at: `Base Output Limits`.
- Mode Gate: `Always`.

## Screenshot-Derived Details

- Legacy Conditional Rules had `Conditional Rule Stack`, `+ Add Conditional Rule`, `DISABLED`, `WARNING`, and `DISABLED` badges.
- The legacy preview sentence said: Set Yaw Output Scale to 0.75 when absolute Roll final output greater than 0.35.
- Initial V2 Rules page was conservative/read-only-looking and later needed to be less placeholder-like.
- Final V2 page uses rule list/detail split, status chips, action row, and product-grade explanatory copy.

## Inferences

- Conditional rules are advanced runtime modifiers rather than static presets.
- The rule engine needs access to reference axis, processing stage, measure type, comparator, threshold, mode gate, button gate, and injection stage.
- Effective Response Stack must display rule injections inline at their actual stage.
- Helm should inspect rule relevance before making tuning recommendations, but v1 Helm should not automatically edit/create/disable rules.

## Desired Improvements

- Group editor fields into `Action`, `When`, and `Condition`.
- Add plain-English preview.
- Make enabled/disabled state prominent.
- Add validation/conflict indicators.
- Add runtime status indicators: `Disabled`, `Inactive`, `Active`, `Blocked`, and possibly `Armed` / `Eligible`.
- Add tooltips for advanced fields: `Stage`, `Measure`, `Operation`, `Button Test`.
- Add live badges/pulses and future simulator support.

## Unknowns

- Exact persisted rule schema.
- Exact rule engine implementation.
- Exact conflict/validation rules.
- Exact execution ordering semantics.
- Whether `Threshold High` supports range/band conditions in final implementation.

## Relevant Implementation Prompt Extract

### Desired Improvements
- Implement Conditional Rules page with status chips: rules, active, blocked, disabled.
- Implement action row: `Add Rule`, `Edit Selected`, `Duplicate`, `Enable`, `Delete`.
- Preserve example rule: `Yaw 0.75 | Roll > 0.35`, disabled, target `Yaw`, parameter `Output Scale`, operation `Set`, value `0.75`, injects at `Base Output Limits`, mode gate `Always`.
- Keep production rule logic safe; full advanced editor can come later if needed.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### 2.13 Conditional Rules page`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 5 — Legacy Conditional Rules tab`

### Screenshot 5 — Legacy Conditional Rules tab

Conditional Rules active. Header card: `Conditional Rule Stack`, text explains conditional rules reshape axes/modes on the fly. Button `+ Add Conditional Rule`. Rule card visible: `Yaw 0.75 | Roll > 0.35`, status `DISABLED`, badges `WARNING`, `DISABLED`, buttons Collapse/Remove. Rule Preview says Set Yaw Output Scale to 0.75 when absolute Roll final output greater than 0.35. Layout has huge empty right space and scroll.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 14 — Repaired legacy Conditional Rules tab`

### Screenshot 14 — Repaired legacy Conditional Rules tab

Conditional Rules layout improved enough to be usable. Still lots of empty right-side space. Rule card readable.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 20 — Initial V2 Conditional Rules page`

### Screenshot 20 — Initial V2 Conditional Rules page

Rules page is read-only/conservative. Rule list on left and rule detail on right. Text explicitly says editing stays conservative in first safe parallel pass. User later wanted this polished and less placeholder-like.



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / `### Screenshot 32 — Final V2 Conditional Rules page`

### Screenshot 32 — Final V2 Conditional Rules page

Conditional Rules selected. Status chips show rules counts. Action buttons Add Rule, Edit Selected, Duplicate, Enable, Delete. Rule list and detail split. Rule detail is much cleaner and product-like.




### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### 2.5 Conditional Rules`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `#### Screenshot 2 — Conditional Rules improved editor (descriptive placeholder)`

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



### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / `### Bug/problem: Conditional Rules page initially too dense`

### Bug/problem: Conditional Rules page initially too dense
#### Symptom
Too many horizontally packed fields; hard to parse.

#### Fixes
- grouped into Action / When / Condition
- added live rule preview sentence
- stronger enabled state and validation visibility

---
