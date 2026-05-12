# LCD-7S Command Button Wiring Audit

LCD-7S was needed because Liquid pages had gained many command buttons, but the product contract was stricter than "buttons exist." HelmForge is tuning/control software: every enabled command must navigate, copy, stage, validate, revert, toggle UI-only state, or otherwise produce visible safe feedback. Silent enabled no-op buttons are not acceptable.

## Button/action audit summary

The audit covers real Liquid pages and shell-level Liquid controls: Preflight, Mapping / HOTAS Map, Mapping / Route Details, Mapping / Advanced Route Tables, Base Tuning, Filtering, Combat Profile, Conditional Rules, Effective Response Stack, Live Monitor, and the current Recorder pages present in the checkout. Shell mode dock buttons, subpage selector buttons, Helm launcher, and disabled footer buttons are also marked with explicit command metadata.

LCD-7S adds shared command action metadata through Liquid button helpers. Buttons now expose an `actionKind` such as `navigation`, `copy`, `stage_draft`, `validate`, `revert`, `toggle_ui`, `select_state`, `open_panel`, or `disabled_deferred`. Disabled controls expose a `disabledReason`, tooltip, status tip, or accessible description.

## Enabled actions by page

Preflight: Open Setup / Runtime Check, Open Help / Docs, Open Mapping / HOTAS Map, Copy preflight status, and Copy setup checklist.

Mapping / HOTAS Map: marker selection, Edit selected route, Open Route Details, Open Advanced Route Tables, Copy selected route, and Copy mapping summary.

Mapping / Route Details: Stage route change, Validate route, Validate all routes, Copy route details, Copy route table summary, Open Advanced Route Tables, Back to HOTAS Map, and Revert staged route edits when the shell owns the draft.

Mapping / Advanced Route Tables: Select route, inline Stage route changes, Validate all routes, Copy route table summary, navigation back to HOTAS Map / Route Details, and Revert staged route edits when available.

Base Tuning / Filtering / Combat Profile: Stage tuning change, Copy tuning parameters, Copy preview values, Revert staged tuning edits when draft ownership is available, and navigation to related tuning pages.

Conditional Rules: Copy rule summary and Validate rules.

Effective Response Stack: Copy selected stage, Copy full response stack summary, and navigation to Base Tuning, Filtering, Combat Profile, Conditional Rules, and Live Monitor.

Live Monitor: Toggle raw/final overlay, Pause/resume visual monitor, Clear local graph history, Copy current sample, Copy telemetry summary, and Open Effective Response Stack.

Recorder pages present in the checkout: Copy recorder status and navigate between Flight Recorder, Clip Library, and Capture Backend Truth. Recorder action rows remain disabled unless a safe navigation-only metadata action exists.

Shell controls: mode dock and subpage selector buttons navigate; Helm opens the Liquid Helm panel; footer Apply / Save / Revert remain disabled pending safe global workspace wiring.

## Disabled/deferred actions by page

Preflight disables Simulation Mode control because no safe Liquid runtime-mode toggle is implemented in this phase.

Mapping / HOTAS Map disables Reset selected route because route-level defaults are not represented as a safe workspace operation.

Mapping edit pages disable Add route because route creation is not represented in the current workspace mapping schema. Revert buttons are disabled when a page is constructed without shell draft ownership.

Tuning disables Reset selected axis because LCD-7S does not add a route-level default restore operation. Read-only tuning parameters expose disabled staging with their read-only reason.

Conditional Rules disables Add rule, Edit selected rule, and Enable / disable rule because no safe Liquid workspace rule-edit seam exists yet.

Recorder disables Record Now and Save Last Clip without starting capture or saving video. If a backend ever reports support without a safe Liquid controller callback, the button remains disabled and explains that capture/video action is not wired from the Liquid page.

Footer Apply / Save / Revert remain disabled with explicit reasons because LCD-7S does not add global workspace command authority.

## Navigation actions wired

Navigation buttons now carry `actionKind="navigation"` and `routeTarget` metadata. Preflight can open setup/help/mapping routes. Mapping buttons navigate between HOTAS Map, Route Details, and Advanced Route Tables. Tuning and Analysis route buttons navigate to the relevant Liquid route. Recorder pages can navigate among existing Recorder routes when the shell route callback is available.

## Copy actions wired

Copy buttons now carry `actionKind="copy"` and copy non-empty page-specific text to the Qt clipboard. Copy actions also set a `lastActionStatus` feedback property/status tip so clicks are not silent.

## Draft/stage/validate/revert actions wired

Mapping stage buttons keep using the existing mapping edit model and shell draft workspace path. Tuning stage buttons keep using the existing tuning edit model and shell draft path. Validate buttons now produce visible feedback without mutating runtime state. Revert buttons are marked as `revert` and remain disabled when draft ownership is unavailable.

## Unsafe actions disabled

LCD-7S does not add enabled controls for Write to vJoy, Verify Output, Start Bridge, Stop Bridge, Restart Bridge, Apply live, Record Now without safe capture support, or Save Last Clip without a real hindsight/video buffer and safe controller seam.

## No-op buttons removed/fixed

The audit test now fails if a real Liquid page exposes an enabled button without a safe `actionKind`, or if a disabled button lacks a reason. Previously quiet copy/validate/toggle buttons now copy data, set visible feedback metadata, navigate, stage drafts, or toggle UI-only state.

## Runtime truth preservation statement

No new runtime authority was added. No hardware polling was added. No vJoy/output behavior was changed. No output verification behavior was changed. No Bridge lifecycle management was added. No recorder capture/encoding was added. No cloud AI/LLM behavior was added. No auto-save was added. No animations/page transitions/radial menu/real blur were added.
