# HOTAS Control Panel — Master Recovery Index

**Spec-set role:** forensic reconstruction document generated from the three recovered HOTAS Control Panel chat notes. This document is meant to stand on its own while cross-referencing the rest of the set.

**Evidence taxonomy used throughout:**
- **Confirmed Facts**: directly stated in the recovery notes or visible as exact recovered UI text.
- **Screenshot-Derived Details**: observations recovered from screenshot descriptions in the source notes.
- **Inferences**: explicitly inferred from the notes or reconstructed from adjacent evidence.
- **Desired Improvements**: user preferences, future direction, fixes, or rebuild requirements.
- **Unknowns**: details the notes say are missing, uncertain, or need later verification.

## Source Inventory

### Confirmed Facts
- Source 1: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md`
- Source 2: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md`
- Source 3: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md`
- The source notes describe a lost/recovered desktop application called **HOTAS Control Panel** / **HOTAS Control Panel V2**.
- The application is a HOTAS/vJoy mapping, tuning, inspection, recording, overlay, and assistant-guided diagnostics workspace.
- The primary modern rebuild direction is **PySide6 / Qt Widgets** with **pyqtgraph** for graphs, while preserving backend/config/tuning/rule/bridge logic where possible.
- The recovered source material is split here into eight topic documents instead of one giant document.

## Document Set

### Confirmed Facts
| # | Document | Primary Scope |
|---|---|---|
| 1 | `01-hotas-control-panel-master-recovery-index.md` | Provenance, dedupe rules, cross-reference map, global evidence model. |
| 2 | `02-product-vision-and-visual-design-system.md` | Product identity, design philosophy, visual system, layout, copy tone, icon direction. |
| 3 | `03-core-tuning-engine-mapping-and-modes.md` | Hardware context, mapping, profiles, modes, base tuning, filtering, combat profile, tuning math. |
| 4 | `04-conditional-rules-system.md` | Conditional rule model, UI, status, runtime behavior, example rule, rule-editor requirements. |
| 5 | `05-graphs-and-effective-response-stack.md` | Graph philosophy, curve previews, filtering graphs, Effective Response Stack, live markers, bugs. |
| 6 | `06-helm-assistant-specification.md` | Helm identity, UI, behavior, diagnosis model, tone, safety, icon. |
| 7 | `07-flight-recorder-live-monitor-and-live-overlay.md` | Flight Recorder, Recording Library, Clip Preview, hindsight buffer, Live Monitor, Live Overlay. |
| 8 | `08-architecture-performance-rebuild-roadmap-and-unknowns.md` | Architecture, state model, performance, packaging, rebuild order, prompts, unknowns. |

## Dedupe Rules Applied

### Confirmed Facts
- Repeated source facts were merged into the document where the fact is primary.
- Exact labels, settings, field names, hotkeys, paths, UI text, file/module names, feature names, and prompt wording were preserved in source-preserved blocks.
- When two chats repeat the same feature at different levels of detail, the more specific chat owns the detailed block and the other document cross-references it.
- Implementation prompts are preserved in the relevant topic document when topic-specific, and summarized in the architecture/roadmap document.

### Screenshot-Derived Details
- Page-specific screenshot observations are placed in the page's most relevant document.
- General shell, design-system, and app-icon screenshots are placed in the Product Vision and Visual Design System document.
- Recorder/overlay screenshots are placed in the Flight Recorder, Live Monitor, and Live Overlay document.
- Helm overlay and icon observations are placed in the Helm Assistant Specification.

### Inferences
- Hardware/control intent that is explicit in one source and inferred in another is treated as confirmed only where directly named.
- PySide6/Qt is confirmed by the broad rebuild/productization notes; in the flight-recorder-only source it remains an inference because that source says framework was not explicitly confirmed there.

### Desired Improvements
- Desired improvements are retained as rebuild requirements unless the source explicitly labels them as later/nice-to-have.
- User dislikes are preserved because they are important negative requirements.

### Unknowns
- Unknowns are not collapsed away. They are gathered globally in Document 8 and repeated narrowly in topic documents where they affect implementation.

## Cross-Reference Map

### Confirmed Facts
- Mapping and tuning values: see Document 3.
- Conditional rule schema and example rule: see Document 4.
- Graph and stack behavior: see Document 5.
- Helm assistant behavior and tone: see Document 6.
- Flight Recorder and Live Overlay exact defaults: see Document 7.
- Safe parallel V2 strategy, architecture, performance, packaging, unknowns: see Document 8.

### Screenshot-Derived Details
- Final V2 Mapping/Modes/Base/Filtering/Combat/Profiles screenshots: Document 3.
- Conditional Rules screenshots: Document 4.
- Effective Response Stack screenshots: Document 5.
- Helm screenshots and icon screenshot: Document 6.
- Flight Recorder, Live Overlay, Live Monitor screenshots: Document 7.
- Shell/header/sidebar/icon visual screenshots: Document 2.

### Inferences
- Battlefield and flight-control tuning strategy is concentrated in Document 3.
- Live overlay implementation method is concentrated in Document 7.
- Runtime and persistence architecture are concentrated in Document 8.

### Desired Improvements
- Visual modernization and copy tone: Document 2.
- Quick Tune and tuning workflow expansion: Document 3.
- Rule simulator/runtime status expansion: Document 4.
- Stack pinning, flow arrows, and live modifier visibility: Document 5.
- Smarter Helm diagnosis: Document 6.
- Overlay defaults/configuration/persistence: Document 7.
- Packaging/productization/testing: Document 8.

### Unknowns
- Global unknowns: Document 8.
- Topic-local unknowns are also included in each topic document.

## Source Preservation Note

### Confirmed Facts
This set intentionally includes two layers:
- a normalized forensic spec layer for implementation use;
- source-preserved blocks that retain the original recovered wording under the relevant topic.

### Desired Improvements
Future reconstruction work should treat the source-preserved blocks as governing evidence if a normalized summary and exact source wording ever appear to disagree.

## Second Sweep Coverage Addendum

### Confirmed Facts
This addendum was added after a second comparison of all three source files against this spec set. The first pass preserved the functional material, but several source-level framing notes and a handful of small rebuild-useful observations were only represented in normalized form. The following source wording is retained here so the spec set can replace the recovery chats as a reconstruction source without losing provenance.

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_rebuild_and_productization.md` / purpose

# HOTAS Control Panel Recovery Notes — Chat V2 Rebuild and Productization

> **Purpose of this document:** forensic reconstruction notes for the HOTAS Control Panel project after the original software was erased. This document preserves every meaningful design, architecture, feature, bug, fix, UI direction, and rebuild instruction from this chat. It is intentionally dense. It is not a marketing summary. It is a rebuild blueprint pulled from the wreckage of the engineering goblin explosion.

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / scope

# HOTAS Control Panel Recovery Notes — Chat: Flight Recorder, Live Overlay, and Helm

## Scope and Intent
This document is a forensic reconstruction of **this specific chat thread only**. It is meant to preserve recoverable details from the conversation so the HOTAS Control Panel software can be rebuilt after the original files were lost. This is not a broad project history for the entire HOTAS application; it is a dense recovery record for the features, UI states, design decisions, prompts, screenshots, and implementation direction discussed here.

Where something is not directly stated in the chat, it is labeled as **Inference**.

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_flight_recorder_live_overlay_and_helm.md` / appendix

## Appendix — Recovery Notes Summary
This chat establishes that the app was already highly polished before the live overlay feature. The most important recovered decisions are:

- **Do not wreck the current page.**
- **Put live overlay in Live Monitor.**
- **Hide advanced controls behind Configure.**
- **Use a shared overlay engine.**
- **Support both forward capture and hindsight/buffer capture.**
- **Keep overlay colors and behavior consistent between live and exported replay.**
- **Preserve Helm as a branded internal assistant with nautical theming.**

That is the core blueprint recovered from this thread.

### Source-Preserved Block: `hotas_control_panel_recovery_notes_chat_v_2_hotas_control_panel_helm_recovery.md` / end note

# HOTAS Control Panel Recovery Notes — Chat HOTAS Control Panel / Helm + Recovery

## End note
This document is intended as a forensic reconstruction blueprint, not a loose summary. Use it as the reference skeleton for rebuilding the lost HOTAS Control Panel project.

### Screenshot Attachment Note

> Screenshots are not embedded in this Canvas document. Each screenshot below is a placeholder/description so it can be manually reattached later.

### Structural Source Headings Preserved For Exact Coverage

```text
## 1. Project Overview
## 2. Major Features Discussed
## 3. UI / UX Reconstruction
## 3A. Screenshot Reconstruction
### Screenshot reconstruction sections
## 3.10 Screenshot Reconstruction
## 10. Bugs, Problems, and Fixes
## 11. Design Decisions and Preferences
## 12. Rebuild Checklist
```
