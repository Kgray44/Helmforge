# Post-RC 1D Help / Docs Full Overhaul Report

## Summary

Post-RC 1D turns Help / Docs into a richer local in-app manual while preserving all runtime boundaries. The pass adds a dark themed article surface, a collapsible topic tree, structured article sections, working sort modes, parameter metadata reference blocks, and internal page navigation buttons for relevant articles.

## Help / Docs UI changes

- Replaced the visible flat topic list with `helpDocsTopicTree`, a dark themed collapsible `QTreeWidget`.
- Kept a hidden compatibility `helpDocsTopicList` so older local tests and helper paths can still exercise deterministic topic selection.
- Added `helpArticleSurface` as the dark article pane, with section blocks, related topic text, parameter reference blocks, and page-open actions.
- Preserved manual external setup links as user actions only.

## topic tree model

The topic tree groups articles by product-centered categories:

- Getting Started
- Runtime Truth
- Mapping
- Tuning
- Filtering
- Combat Profile
- Modes
- Conditional Rules
- Effective Response Stack
- Live Monitor
- Live Overlay
- Flight Recorder
- Helm Assistant
- Profiles
- Perf / Diagnostics
- Packaging / Setup
- Troubleshooting
- Parameter Reference

Category rows are non-article folder rows. Article rows are selectable and render the article pane.

## article model

`HelpArticle` now supports structured `HelpArticleSection` rows while preserving the older paragraph/body/search API. New and expanded articles use sections such as:

- What this is
- What it does
- When to use it
- Key parameters
- Suggested ranges
- Examples
- Common mistakes
- Runtime truth notes
- Related topics

Legacy article content remains available so earlier phase assertions and long-running runtime truth wording stay intact.

## sort behavior

The Help / Docs sort dropdown now exposes:

- By Category
- By Last Opened
- Alphabetical A-Z
- Alphabetical Z-A
- By Importance

Search remains local and deterministic. Search results preserve category context in the tree.

## metadata integration

The Parameter Reference article is generated from the existing Post-RC parameter metadata registry. Parameter blocks show display name, parameter id, page/category, support scope, value type, min/max or options, default value, examples, warnings, and related help topics where present.

Metadata-backed article links now cover representative Mapping, Base Tuning, Filtering, Modes, Conditional Rules, Live Overlay, and Flight Recorder parameters without duplicating the registry as separate hardcoded lore.

## page navigation buttons

Relevant articles render internal navigation actions such as:

- Open Mapping
- Open Base Tuning
- Open Filtering
- Open Modes
- Open Conditional Rules
- Open Flight Recorder
- Open Perf / Diagnostics

Buttons call the existing app shell page switch callback. They do not open external links, start Bridge, launch services, poll hardware, or activate runtime behavior. Helm articles can route to the existing Helm overlay callback when used.

## articles added/expanded

Added structured coverage for:

- HelmForge overview
- Simulation mode
- Runtime truth model
- Full Live Runtime Ready
- vJoy/output verification
- Bridge telemetry
- HOTAS diagram
- Mapping Route Inspector
- Mapping edit workflow
- Axis routing
- Button routing
- Hat routing
- Curve modes
- Deadzone / anti-deadzone
- Hysteresis
- Output scale / max output
- Slew limits
- Precision mode
- Combat mode
- Stack mode
- Rule stages
- Comparators
- Recorder review/export diagnostics
- One-frame capture proof
- Real capture limitations
- Parameter Reference
- Troubleshooting

Existing Quick Start, Runtime Setup / vJoy Setup, Runtime Indicators, Mapping, Flight Recorder, Live Overlay, Live Monitor, Helm, and Perf / Diagnostics content remains available and searchable.

## known limitations

- This is still an in-app local manual, not generated web documentation.
- Parameter reference blocks are registry-driven but not yet linked from every individual control row.
- The manual intentionally does not claim real hardware readiness without the Phase 16 proof gate.
- The recorder docs describe the current one-frame proof and metadata diagnostics but do not add continuous capture, encoding, preview, or buffering.

## tests run

Planned validation:

- `python -m pytest tests/test_post_rc_1b_parameter_metadata_info_icons.py -q`
- `python -m pytest tests/test_post_rc_1c_parameter_help_coverage.py -q`
- `python -m pytest tests/test_post_rc_1d_help_docs_full_overhaul.py -q`
- `python -m pytest tests/test_post_rc_2c_mapping_diagram_editing.py -q`
- `python -m pytest tests/test_post_rc_3c_one_frame_capture_proof.py -q`
- `python -m pytest tests/test_phase19d_final_acceptance_report.py -q`
- `python -m pytest -q`
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250`
- `python -m bridge_app.main --status`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun`
- `git diff --check`

Actual results are recorded in the final implementation summary.

## runtime truth preservation

No runtime authority was added.
No hardware polling was added.
No Bridge lifecycle behavior was added.
No vJoy writes were added.
No output verification logic was changed.
Full Live Runtime Ready gates were not weakened.
No recorder buffering, encoding, preview, capture loops, game injection, graphics API hooking, cloud/web docs, LLM behavior, or auto-save was added.

The docs preserve the current truth language: telemetry remains the truth surface; output intent is not output write proof; vJoy detected is not output verification; Mapping edits are workspace/config draft only; one-frame capture proof is not recording or runtime readiness; simulation mode remains available.
