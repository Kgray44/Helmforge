# Post-RC Human Walkthrough Completion Matrix

Source: `HOTAS Control Panel Forensic Spec Set/POST REGULAR PHASES - HUMAN WALKTHR.txt`

Status vocabulary: Fixed, Partial, Not Fixed, Deferred, Cannot Verify Without Visible QA.

Post-RC 4D update: the Mapping, Profiles, Modes, Base Tuning, Filtering, Combat Profile, Conditional Rules, and Effective Response Stack sections were re-audited for control-editing page polish. Rows in those sections use "Fix included in 4D" language where this pass changed or verified code.

## Global / Shell

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Main window should default shorter and resize both ways. | Fixed | `v3_app/theme/tokens.py` sets `Layout.window_height = 840`; `tests/test_post_rc_1a_global_ui_foundation.py` checks resize width and height. | Verified. | None | Offscreen construction validates geometry, not final visual feel. |
| Left page selection bar should look carded/floating with borders and separation. | Partial | `QWidget#appSidebar` has border/radius in `v3_app/theme/qss.py`; 4C strengthened border contrast. | Strengthened sidebar border/separation. | Post-RC 4D | Qt stylesheet cannot provide a true shadow on this widget without a graphics effect pass; visible QA still needed. |
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

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Graphs should read at 30/60 Hz and scroll 7 seconds. | Deferred | Would change telemetry/runtime rendering behavior. | None. | Later runtime/monitor phase | Outside 4C. |
| Axis dropdown should display options. | Fixed | 1A tests verify `liveMonitorAxisSelector`. | Verified. | None | |
| Live State block should be less dense. | Partial | 4B added truth notice; deeper layout deferred. | None. | Post-RC 4D | |
| Buttons in Live State should move to own block. | Deferred | Page-specific layout work. | None. | Post-RC 4D | |
| Buttons/Hats block too large. | Cannot Verify Without Visible QA | Needs visible layout inspection. | None. | Post-RC 4D | |
| Axis Levels should rotate 90 degrees. | Deferred | Page-specific chart visual change. | None. | Post-RC 4D or later | |
| Live Overlay section should be more readable. | Partial | Shared typography and metadata exist. | None. | Post-RC 4D | |
| Configure menu should be themed/resizable and content fit. | Cannot Verify Without Visible QA | Requires opening the configure dialog. | None. | Post-RC 4D | |
| Page should be scrollable. | Fixed | Shell wraps pages in `QScrollArea#pageScrollArea`. | Verified. | None | |
| Add preset dropdown/save custom preset behavior. | Deferred | This is new behavior and persistence-adjacent. | None. | Later explicit feature phase | Outside 4C. |

## Flight Recorder

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Recorder Status block should be displayed better. | Partial | 4B verifies recorder workflow truth cards. | None. | Post-RC 4D | |
| Recorder Library sort dropdown should show options. | Fixed | 1A tests verify `recordingLibrarySortDropdown` has current text/items. | Verified. | None | |
| Recorder Settings should be editable dropdowns/inputs. | Partial | Parameter metadata for recorder settings exists; current runtime capture remains simulated/unavailable. | None. | Later explicit recorder settings phase | Must not imply real capture. |
| Axis Overlay include boxes editable. | Cannot Verify Without Visible QA | Needs page-specific inspection. | None. | Post-RC 4D | |
| Entire backend including hindsight/capture/buffer should be implemented. | Partial | Post-RC 3A-3F reports exist; hard boundaries forbid runtime capture expansion in 4C. | None. | Later recorder runtime phase | 4C preserves truth boundaries. |

## Help / Docs

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| White article backgrounds should match app. | Fixed | QSS includes `QFrame#helpArticleSurface` dark background; 4B tests verify Help page. | Verified. | None | |
| Pages should display detailed, sectioned topic content. | Fixed | Post-RC 1D report and 4B tests verify parameter reference/readability. | Verified. | None | |
| Sort dropdown should show options. | Fixed | 1A tests verify `helpDocsSortDropdown`. | Verified. | None | |
| Categories should be dividers/collapsible folder tree. | Partial | 4B test verifies `helpDocsTopicTree`; deeper category behavior not reworked. | None. | Post-RC 4D | |

## Perf / Diagnostics

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Runtime Truth block should be sorted/displayed better. | Partial | 4B tests verify diagnostics truth legend and Full Live Runtime Ready wording. | None. | Post-RC 4D | |
| Bridge / Telemetry block should not match Runtime Truth height. | Cannot Verify Without Visible QA | Requires rendered layout inspection. | None. | Post-RC 4D | |
| Performance Timings should be expanded/displayed better. | Partial | Existing diagnostics collector/page surface timing data. | None. | Post-RC 4D | |

## Bottom Bar

| Original issue summary | Current status | Evidence from code or tests | Fix included in 4C | Deferred phase | Notes |
|---|---|---|---|---|---|
| Remove Page / Axis / Profile / Source from bottom bar. | Fixed | `Footer` only shows status message and Import/Revert/Save; 1A/4C tests assert forbidden labels are absent. | Verified. | None | |
