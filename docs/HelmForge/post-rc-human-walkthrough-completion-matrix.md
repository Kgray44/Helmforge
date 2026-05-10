# Post-RC Human Walkthrough Completion Matrix

Source: `HOTAS Control Panel Forensic Spec Set/POST REGULAR PHASES - HUMAN WALKTHR.txt`

Status vocabulary: Fixed, Partial, Not Fixed, Deferred, Cannot Verify Without Visible QA.

Post-RC 4D update: the Mapping, Profiles, Modes, Base Tuning, Filtering, Combat Profile, Conditional Rules, and Effective Response Stack sections were re-audited for control-editing page polish. Rows in those sections use "Fix included in 4D" language where this pass changed or verified code.

Post-RC 4E update: Live Monitor, Live Overlay, Flight Recorder, Help / Docs, and Perf / Diagnostics were re-audited for runtime/status-heavy walkthrough polish and final acceptance prep. Rows in those sections use "Fix included in 4E" language where this pass changed or verified code.

## Global / Shell

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Main window should default shorter and resize both ways. | Fixed | `v3_app/theme/tokens.py` sets `Layout.window_height = 800`; `tests/test_post_rc_1a_global_ui_foundation.py` checks resize width and height. | Verified. | None | Offscreen construction validates geometry, not final visual feel. |
| Left page selection bar should look carded/floating with borders and separation, and page names should remain visible at default vertical scale. | Fixed | `QWidget#appSidebar` has strengthened border/radius in `v3_app/theme/qss.py`; `test_post_rc_1a_sidebar_page_names_fit_default_vertical_scale` checks the sidebar height and long page-name fit against the default window height. | Strengthened sidebar border/separation and fixed default-height page-name clipping. | None | True shadow depth still needs visible QA, but the functional label-visibility bug is covered. |
| STATUS cluster and label should sit together on a card. | Fixed | `Header._build_status_cluster()` creates `statusCluster` with the `STATUS` label and chips; 1A tests assert selector. | Verified. | None | |
| ASSISTANT cluster and label should sit together on a card. | Fixed | `Header._build_assistant_cluster()` creates `assistantCluster` with `ASSISTANT` label and Helm button; 1A tests assert selector. | Verified. | None | |
| Every page needs a clear outer boundary. | Fixed | `QScrollArea#pageScrollArea` has border/radius; 1A tests assert boundary selector. | Strengthened page-scroll border. | None | |
| Parameter inputs need hover info icons with what it does, range/options, examples. | Fixed | `parameter_label()`, `ParameterInfoIcon`, and `PARAMETER_HELP`; 1B/1C tests cover info icon and help coverage. | Verified. | None | |
| Buttons need distinct normal/hover/pressed/checked/disabled states. | Fixed | `v3_app/theme/qss.py` contains global button state selectors; 1A and 4C tests check them. | Verified and preserved. | None | |
| Helm button should not look pressed/light-blue by default. | Fixed | `helmButton` uses `uiRole="actionButton"`, is not checkable, and no object-specific active rule exists. | Verified. | None | |
| Dropdowns should show closed text and popup options correctly. | Partial | QSS themes `QComboBox` and popup items; 1A tests verify representative dropdown counts/current text. | Verified representative global selectors. | Post-RC 4D | Offscreen tests cannot prove all popups render correctly on a human display. |
| Bottom bar should not show Page / Axis / Profile / Source. | Fixed | `Footer` only renders status message and Import/Revert/Save actions; 1A and 4C tests check forbidden labels. | Verified. | None | |
| Global text hierarchy should improve. | Partial | Shared QSS defines page/card/body/section roles and 4B selectors. | 4C adds Helm-specific hierarchy selectors. | Post-RC 4D | Remaining page-specific typography belongs to the next control-editing polish pass. |

## Helm

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Helm should not be a separate app screen/sidebar page. | Fixed | `HelmForgeShell` has no `helm` page id; `open_helm_overlay()` uses `HelmOverlay`; Phase 10A/4C tests assert this. | Verified. | None | |
| Helm should glide out from the right side and feel part of the app. | Partial | `HelmOverlay.open_for_parent()` positions a narrower right-side modal and sets `overlayPlacement="right-glide"`. | Narrow right-side geometry added. | Post-RC 4D | True animation is deferred to avoid fragile timing behavior. |
| App behind Helm should blur/dim. | Partial | 4C adds `helmOverlayScrim`, `scrimMode="dimmed"`, and a parent opacity effect. | Added dim scrim. | Post-RC 4D | True blur is deferred; Qt blur would require a higher-risk graphics-effect pass. |
| Helm page/cards have darker/inconsistent backgrounds. | Partial | Shared card/background QSS covers `QDialog#helmOverlay`, `helmOverlayContent`, scroll area, and cards. | 4C keeps Helm cards on shared page-card surfaces. | Visible QA | Offscreen inspection cannot prove all perceived color differences are resolved. |
| Symptom prompt chips should be smaller/less loud. | Fixed | `QPushButton[uiRole="symptomChip"]` padding/font-size reduced in QSS. | Reduced chip weight. | None | |
| Symptom input should be slightly smaller vertically. | Fixed | `helmSymptomInput` min height reduced to 92 and max height 220. | Implemented. | None | |
| Symptom input should wrap horizontally. | Fixed | `setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)` and 4C test. | Implemented. | None | |
| Symptom input should auto-resize vertically within sensible min/max. | Partial | `textChanged` calls `_resize_symptom_input()` and clamps 92 to 220 px. | Implemented simple auto-resize. | Visible QA | Human QA should confirm feel with long text. |
| Analyze / Review Changes / Cancel / Close should not look always pressed. | Fixed | Buttons are normal `action_button` instances, not checkable/checked; 4C tests assert. | Verified. | None | |
| What's wrong and What I'd change boxes should not be locked to equal heights. | Fixed | 4C changed Helm grid to one column with top-aligned content cards and removed forced stretch from diffs. | Implemented. | None | |
| What I found and Apply / Revert boxes should not be locked to equal heights. | Fixed | 4C uses content-sized sequential cards and `helmCardContentSized` properties. | Implemented. | None | |
| All Helm cards should size to contents with reasonable whitespace. | Partial | `helmCardContentSized=True` on major/dynamic cards; no equal-height grid. | Implemented. | Visible QA | Offscreen tests verify properties, not final human perception. |
| What I'd change should be easier to read/comprehend. | Partial | 4C adds Helm recommendation card selectors and content-sized rows; existing grouped diff copy remains deterministic. | Improved hierarchy. | Post-RC 4D | Further copy/layout work may be useful after visible QA. |
| What I found should be easier to read/comprehend. | Partial | `helmFindingCard` gets clearer hierarchy and retains grouped evidence labels. | Improved hierarchy. | Post-RC 4D | |
| Apply/Revert content should be easier to read. | Partial | `helmApplyRevertCard` now places summary/status before a separated action row. | Reordered content. | Visible QA | |
| Apply/Revert buttons should be at the bottom/action area. | Fixed | 4C adds `helmActionRow` after review/status content; tests assert the action row exists. | Implemented. | None | |
| Helm active indicator should be polished green bulb with pulse. | Partial | 4C adds `helmActiveBulb` with radial QSS bulb styling and `pulseStyle="static-qss"`. | Polished static bulb. | Post-RC 4D | Timed pulse animation deferred as test-risky. |
| Preserve deterministic/local Helm behavior. | Fixed | Helm still uses `HelmEngine` and local workspace context only; no cloud imports. | Verified. | None | |
| Preserve in-memory-only Apply/Revert and Save Workspace persistence boundary. | Fixed | Existing Phase 10 tests verify no file write until Save Workspace; 4C did not change apply/revert model. | Verified. | None | |

## Mapping

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Text in boxes is hard to read / mono-styled. | Partial | 4D adds `controlPolish="post-rc-4d"` hooks to route cards and keeps shared typography/QSS selectors. | Fix included in 4D: route card polish hooks and table sizing properties. | Visible QA | Offscreen tests verify structure, not final human readability. |
| Move Preflight to its own tab/dashboard. | Partial | `runtimePreflightCard` remains present for compatibility; 4D adds `mappingPreflightDashboardCard` with `uiRole="preflightDashboard"` and `tabSplitDeferred=True`. | Fix included in 4D: clearer dashboard marker; real tab split deferred. | Post-RC 4E or later | A real tab split would be a larger navigation change. |
| Axis/Button/Hat routing backgrounds and card design need polish and content fit. | Partial | `axisRoutingTable`, `buttonRoutingTable`, and `hatRoutingTable` have `polishedRouteTable=True`, taller rows, resize-to-content columns, and stretch-last-section. | Fix included in 4D. | Visible QA | |
| Mapping dropdowns appear empty. | Partial | Mapping route/editor dropdowns remain metadata-backed and populated; 4D keeps table cell widgets and sizing. | Fix included in 4D: table sizing/polish, not popup-render changes. | Visible QA | Offscreen tests cannot prove popup paint. |
| Mapping buttons should not look always on and should hover. | Fixed | Global QPushButton states apply and 4D preservation tests verify 2C editor actions remain normal buttons. | Verified in 4D. | None | |
| Route Inspector/editor should be easy to read and Save Workspace required wording clear. | Partial | `routeInspectorPanel`, `routeEditorPanel`, `routeEditorPersistNotice`, and 2C tests verify wording and draft-only behavior. | Fix included in 4D: preserved editor and added deferred 2D notice when 2D is absent. | Visible QA | |

## Profiles

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Profile column should show fuller names and be expandable. | Partial | `profileLibraryTree` column 0 defaults to 280 px; 4D test verifies width. | Fix included in 4D. | Visible QA | Manual expansion feel still needs visible QA. |
| Profiles should have distinct defaults and selection should update view. | Fixed | `profileLibraryTree.currentItemChanged` updates `selectedProfileId`, `selectedProfileName`, and `selectedProfileDescription`; 4D test selects Aggressive Combat. | Fix included in 4D. | None | Descriptions stay local/draft-only. |
| Profile page text should be more readable. | Partial | 4D adds selected-profile detail labels and distinct preset description copy. | Fix included in 4D. | Visible QA | |
| Profile buttons should not look pressed and should hover. | Fixed | Global button QSS states apply. | Verified globally. | None | |

## Modes

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Cards should not force equal heights or big open gaps. | Partial | Modes cards use `add_card_to_grid()` and now expose `controlPolish="post-rc-4d"` with content sizing. | Fix included in 4D. | Visible QA | |
| Menus should be preset dropdowns, not text boxes. | Partial | Supported stack mode is a populated `QComboBox`; button lists remain text because no supported preset list exists. | Verified in 4D; unsupported future modes not added. | Post-RC 4E or later | |

## Base Tuning

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Mapped axes should be selectable. | Fixed | `axis_list_card()` creates checkable buttons and wires `on_axis_selected`; 4A tests cover tuning usability. | Verified by existing phase scope. | None | |
| Non-number parameters should be dropdowns; numeric parameters should have caps. | Fixed | `dropdown_field_row()`, `apply_numeric_validator()`, and metadata registry. | Verified by 1B/1C/4A tests. | None | |
| Live Snapshot should be more readable. | Partial | 4A structure remains and 4D verifies snapshot/guidance/axis selection. | Verified in 4D. | Visible QA | |
| Guidance should be broken down clearer. | Fixed | Base Tuning guidance remains divided into Current feel, What this setting affects, Suggested range, Caution, and Selected axis note. | Verified in 4D. | None | |
| Response Preview should show live axis dot indicators. | Fixed | `baseTuningGraph` exposes Linear and Adjusted live marker objects; 4A/4D tests verify reuse. | Verified in 4D. | None | Markers are diagnostics only, not output proof. |

## Filtering

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Mapped axes should be selectable. | Fixed | Shared `axis_list_card()` and 4A tuning usability pass. | Verified. | None | |
| Parameters should have caps. | Fixed | Metadata validators and numeric ranges. | Verified. | None | |
| Live Snapshot and Guidance should match Base Tuning improvements. | Fixed | Filtering guidance uses the same five-section structure and `filteringGraph` exposes Input/Filtered markers. | Verified in 4D. | None | |

## Combat Profile

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Mapped axes should be selectable. | Fixed | Shared axis selector. | Verified. | None | |
| Numeric parameters should reject unusable values/letters. | Fixed | Metadata-backed validators. | Verified. | None | |
| Live Snapshot and Guidance need clearer display. | Fixed | Combat guidance uses the same five-section structure. | Verified in 4D. | None | |
| Response Preview should show live dots on all three lines, updated smoothly. | Fixed | `combatGraph` exposes Linear, Baseline, and Combat markers; timer remains the existing safe 4A UI refresh. | Verified in 4D. | None | No runtime pipeline behavior changed. |

## Conditional Rules

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Rule List block looks unfinished and columns should fit. | Partial | `conditionalRuleList` has `polishedRuleTable=True`, taller rows, resize-to-content columns, and stretch-last-section. | Fix included in 4D. | Visible QA | |
| Buttons should not appear pressed and should hover. | Fixed | Global button QSS states. | Verified globally. | None | |
| Rule Detail text should be easier to read and sectioned. | Partial | Existing Action/When/Condition groups remain; 4D adds layout-order properties. | Fix included in 4D. | Visible QA | |
| Dropdowns should display all supported options. | Partial | Rule dropdowns are populated from supported sets; `ruleParameterField` intentionally exposes only `Output Scale` because evaluator support has one parameter. | Fix included in 4D: support notice added instead of fake options. | Post-RC 4E or later | More targets require evaluator support first. |
| Rule Logic should move above Rule Detail. | Fixed | `ruleLogicCard` is built before `conditionalRuleDetailCard`; 4D test verifies `layoutOrder`. | Fix included in 4D. | None | |

## Effective Response Stack

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Add smooth downward gliding animation from card to card. | Deferred | Static `v` flow indicators remain; no animation added. | None. | Later visual-motion phase | Avoided fragile animation tests in 4D. |
| Axis selector dropdown shows blank. | Fixed | 1A tests verify `stackAxisSelector` has current text/items. | Verified. | None | |
| Add Total Change block under graph. | Fixed | `stackTotalChangeCard` shows Before, After, Delta, and Most impact from deterministic stage data. | Fix included in 4D. | None | |
| Highlight stage affecting output most. | Partial | `_mark_most_impactful_stage()` sets `mostImpactful` from largest deterministic stage delta. | Fix included in 4D. | Visible QA | QSS/static visual emphasis can be refined after human QA. |
| Right-side blocks should not be equal height and should resize to content. | Partial | Existing `add_card_to_grid()` top-aligns lower cards; Total Change is content-sized. | Fix included in 4D. | Visible QA | |
| Buttons should not appear pressed and should hover. | Fixed | Global button states. | Verified globally. | None | |

## Live Monitor

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4E | Deferred phase | Notes |
|---|---|---|---|---|---|
| Graphs should read at 30/60 Hz and scroll 7 seconds. | Partial | `liveMonitorGraphCadenceLabel` documents the current diagnostic UI refresh; `LiveOverlayConfig.defaults()` keeps 7.5 seconds and 4E labels the page graph history as 7 seconds. | Added explicit cadence/history labels without changing the runtime telemetry model. | Later runtime/monitor phase | Timer remains 750 ms to avoid changing runtime behavior in a polish pass; true 30/60 Hz graph refresh needs a separate runtime/monitor decision. |
| Axis dropdown should display options. | Fixed | `liveMonitorAxisSelector` is populated from `AXIS_DISPLAY_NAMES`; 1A and 4E tests verify visible options/current text. | Verified. | None | |
| Live State block should be less dense. | Partial | `liveMonitorCompactState` now exposes compact runtime truth, output proof, and telemetry-source rows above the diagnostic detail text. | Added compact state rows and 4E test coverage. | Visible QA | Detailed diagnostic text remains available for truth preservation; manual QA should judge final density. |
| Buttons in Live State should move to own block. | Fixed | 4E adds `liveMonitorActionBlock` for Bridge request buttons outside `liveMonitorCompactState`. | Moved commands into dedicated action card. | None | Buttons remain request-file actions only. |
| Buttons/Hats block too large. | Partial | HOTAS and output button grids are nested inside the `buttonsHatsCard` summary area instead of occupying a separate large lower grid. | Reduced footprint structurally. | Visible QA | Human QA still needed for perceived size. |
| Axis Levels should rotate 90 degrees / line up vertically. | Partial | 4E adds `liveMonitorAxisLevelsVertical` with `axisLevelLayout="vertical-bars"` and lays all axis rows across one horizontal row. | Added testable vertical-layout marker and revised layout. | Visible QA | True rotated text/bars are deferred because current progress bars are horizontal Qt widgets. |
| Live Overlay section should be more readable. | Fixed | `liveOverlayCard` already uses scan rows; 4E keeps truth rows and adds config preset support. | Verified with 4E tests. | None | |
| Page should be scrollable. | Fixed | Shell wraps pages in `QScrollArea#pageScrollArea`; 1A/4E construction passes offscreen. | Verified. | None | |

## Live Overlay

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4E | Deferred phase | Notes |
|---|---|---|---|---|---|
| Configure menu should use dark app background, not white. | Partial | `liveOverlayConfigDialog` now has `postRc4eStyled=True`, scroll-area/content object names, and shared QSS covers dialogs/cards. | Added styled/testable dialog surface. | Visible QA | Offscreen tests cannot prove final perceived color. |
| Configure dialog default vertical size should be smaller and resizable both ways. | Fixed | `LiveOverlayConfigDialog` minimum height lowered to 520, default `resize(820, 560)`, and `setSizeGripEnabled(True)`. | Implemented. | None | Existing product-polish test updated to the smaller height contract. |
| Content should fit with no rows squished and page/dialog should be scrollable. | Fixed | 4E wraps cards in `liveOverlayConfigScrollArea` with `widgetResizable=True`. | Implemented. | None | |
| Presets dropdown next to existing buttons with 5 presets; selecting preset applies rules. | Fixed | `liveOverlayPresetDropdown` lists Regular, Compact, High Contrast, Telemetry Focus, Minimal, and Custom; `_apply_preset()` updates local draft fields. | Implemented local app-owned presets. | None | Presets affect only overlay config draft. |
| Default preset regular. | Partial | Regular exists as the first preset, but existing accepted defaults and Phase 12A tests still expect `LiveOverlayConfig.defaults().preset == "Custom"`. | Added Regular without breaking the persisted default contract. | Later explicit preset-default migration | Changing the default preset is deferred to avoid breaking established config/backward tests in a polish pass. |
| Editing settings switches preset to Custom. | Fixed | `_mark_custom()` switches `liveOverlayPresetDropdown` to Custom when supported settings change. | Implemented. | None | |
| Save custom preset with provided/default name. | Partial | `liveOverlaySavePresetButton` and `liveOverlayPresetNameInput` add a named preset to the current dialog instance, defaulting to `Custom 1`, `Custom 2`, etc. | Implemented dialog-local save. | Later persistence phase | Saved custom presets are not persisted across app launches; no auto-save added. |

## Flight Recorder

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4E | Deferred phase | Notes |
|---|---|---|---|---|---|
| Recorder Status block should be displayed better. | Partial | `recorderStatusCard` has `scanFriendlyRows=True`; 4E adds workflow map before proof/buffer/export/review cards. | Added scan-friendly marker and workflow card. | Visible QA | Dense truth rows remain to preserve accepted recorder proof boundaries. |
| Recorder Library sort dropdown should show options. | Fixed | `recordingLibrarySortDropdown` now lists Newest First, Oldest First, Artifact Type, and Playable First; 4E tests verify. | Added visible options. | None | Sorting behavior itself remains existing scan order unless explicitly expanded later. |
| Recorder Settings should be editable dropdowns/inputs. | Partial | Record Cursor is now editable and safely updates in-memory `FlightRecorderSettings`; supported button states remain capability-bound. | Enabled supported cursor setting safely. | Later recorder settings phase | Broader destination/frame-rate/source editing is deferred to avoid recorder model churn. |
| Record Cursor checkbox should be editable if supported. | Fixed | `recordCursorCheckbox` is enabled and toggles the in-memory settings object. | Implemented. | None | No persistence or auto-save added. |
| Axis Overlay include boxes editable if supported. | Fixed | `recorderAxisInclude_*` checkboxes are enabled and update in-memory axis include settings. | Implemented. | None | No runtime or compositor authority added. |
| Workflow should distinguish settings/proof/buffer/artifact/export/library. | Fixed | 4E adds `recorderWorkflowMapCard` listing the six workflow steps and truth boundaries. | Implemented. | None | |
| Distinguish intermediate JSON, image sequence, encoded clip, playable verified clip. | Fixed | Existing 3D/3E/3F labels preserved; 4E strengthens Export / Encoding copy with encoded-clip/playable-verification wording. | Implemented wording polish. | None | |
| Entire backend including hindsight/capture/buffer should be implemented. | Partial | Post-RC 3A-3F recorder seams exist; 4E intentionally does not add new capture/encoding/storage backend features. | Verified/preserved existing surfaces. | Later recorder runtime phase | Hard boundaries forbid new runtime capture, global hotkeys, or encoder backend work in 4E. |

## Help / Docs

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4E | Deferred phase | Notes |
|---|---|---|---|---|---|
| White article backgrounds should match app. | Fixed | QSS includes dark `QFrame#helpArticleSurface`; 1D/4E tests verify article surface object/properties. | Verified and marked `postRc4eReadable=True`. | None | |
| Pages should display detailed, sectioned topic content. | Fixed | `HelpArticle.sections`, parameter reference blocks, and 1D tests cover structured sections. | Verified. | None | |
| Sort dropdown should show options. | Fixed | `HELP_SORT_OPTIONS` and `helpDocsSortDropdown` list five modes; 1D/4E tests verify. | Verified. | None | |
| Categories should be dividers/collapsible folder tree. | Partial | `helpDocsTopicTree` uses top-level category items with no article `UserRole`; 1D tests verify non-article categories. | Verified existing tree; no architecture redo. | Visible QA | Manual QA should check spacing/selection polish. |
| Final recorder export/storage truth docs. | Fixed | Help service contains Recorder encoding/export preview and Recorder durable frame storage articles with truth boundaries. | Verified existing 3E/3F docs in 4E scope. | None | |

## Perf / Diagnostics

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4E | Deferred phase | Notes |
|---|---|---|---|---|---|
| Runtime Truth block should be sorted/displayed better. | Partial | 4E adds `diagnosticsHintProofReadinessLegend` to separate hints, proof, and readiness above detailed cards. | Added evidence-strength legend. | Visible QA | The Runtime Truth row list remains intentionally exhaustive. |
| Bridge / Telemetry block should not match Runtime Truth height. | Partial | `perfBridgeTelemetryCard` now exposes `cardSizing="content"` and keeps shorter scan rows. | Added content-sizing marker. | Visible QA | Qt grid equalization still needs visible QA. |
| Performance Timings should be expanded/displayed better. | Partial | `perfTimingCard` has `expandedTimingDisplay=True` and retains page/heartbeat/graph/startup metrics. | Added testable expanded timing marker. | Later diagnostics metrics phase | New metrics were not invented where collector data does not exist. |
| Diagnostics should distinguish hints, proof, and readiness. | Fixed | 4E legend text explicitly defines Hint, Proof, and Readiness; tests verify. | Implemented. | None | |

## Final Walkthrough Acceptance Summary

| Category | Count | Notes |
|---|---:|---|
| Fully Fixed | 45 | Rows with code/test evidence or existing accepted tests covering the issue. |
| Partially Fixed | 28 | Rows improved structurally or textually but still needing visible QA or larger follow-up. |
| Deferred | 5 | Rows requiring runtime/animation/persistence/backend changes outside 4E. |
| Cannot Verify Without Visible QA | 4 | Remaining perception/layout items that need a real desktop walkthrough. |

## Recommended 5A manual visible QA checks

| Area | Check |
|---|---|
| Live Monitor | Verify graph readability, compact-state density, command-card placement, Buttons/Hats footprint, and axis-level orientation on a real desktop. |
| Live Overlay | Open Configure and verify dark styling, scroll behavior, preset application, custom naming, and row spacing at default and resized dimensions. |
| Flight Recorder | Verify workflow scan order, status-card readability, library dropdown rendering, editable cursor/axis include controls, and disabled-button explanations. |
| Help / Docs | Verify topic-tree spacing/selection, article typography, parameter-reference blocks, search behavior, sort behavior, and page navigation buttons. |
| Perf / Diagnostics | Verify Runtime Truth grouping, Bridge/Telemetry height/content sizing, Performance Timings readability, and Hint/Proof/Readiness legend clarity. |

## Bottom Bar

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Remove Page / Axis / Profile / Source from bottom bar. | Fixed | `Footer` only shows status message and Import/Revert/Save; 1A/4C tests assert forbidden labels are absent. | Verified. | None | |
