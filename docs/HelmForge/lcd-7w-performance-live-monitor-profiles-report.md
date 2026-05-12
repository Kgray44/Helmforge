# LCD-7W Performance, Live Monitor, and Profiles Library Report

## Why LCD-7W Was Needed

LCD-7T through LCD-7V made the Liquid Analysis and Tuning pages real command surfaces, but three core usability faults remained:

- Effective Response Stack still felt too heavy, could rebuild too much during stage selection, and needed stronger guarantees that stage cards/details never became empty.
- Live Monitor advanced only when telemetry values changed. Stationary HOTAS input therefore stopped drawing instead of producing a flat time trace.
- Tuning / Profiles Library existed, but it was only a profile summary and did not behave like a preset/profile browser.

## Effective Response Stack Performance Root Cause

The page already avoided a full rebuild for telemetry bursts, but stage selection still forced a page render and axis changes did not refresh every visible selector/snapshot surface in place. The stack also lacked an explicit lightweight chain contract for regression tests and future maintenance.

## Effective Response Stack Lightweight Chain Fix

- Kept the vertical stage chain as a fixed, cached set of stage widgets.
- Added the `chainImplementation=cached_lightweight_stage_widgets` contract on the response stack chain.
- Updated selected-axis controls, live snapshot, stage widgets, detail panel, and advanced details in place for telemetry/axis updates where possible.
- Changed stage selection so it refreshes the detail panel only rather than rebuilding the full page.
- Ensured every stage continues to show stage name, selected axis/value text, summary, and source/truth context even when values are unavailable.

## Effective Response Stack Axis Selection Fix

Axis selectors remain single-selection controls. Roll -> Yaw -> Throttle changes now update:

- selected-axis property/chip context
- top and inspector axis selectors
- stage chain values
- selected stage details
- advanced details
- copy context used by stage/stack actions

## Live Monitor Stationary-Input Behavior Fix

Live Monitor now has an active-page-only display sampler. The sampler repeats the latest cached passive telemetry sample while the Live Monitor route is visible, so stationary inputs continue drawing flat right-to-left traces over time.

The sampler:

- samples only the latest cached `BridgeTelemetrySnapshot`/Analysis model
- does not poll HOTAS hardware
- does not send Bridge commands
- does not write vJoy
- stops when Live Monitor is hidden
- does not append fake samples when telemetry is missing
- keeps graph history bounded
- updates the graph in place instead of rebuilding the page

## Live Monitor Idle Glitch Fix

Missing telemetry renders once as missing/unavailable state and does not grow history. Identical incoming telemetry is still coalesced at the telemetry-update path, while the active display sampler is responsible for flat-line history. Hidden Live Monitor pages do not continue growing history.

## Buttons / Hats Display Fix

The existing passive Buttons / Hat panel remains populated from telemetry when data exists. When unavailable, the model still labels button and hat state as unavailable rather than leaving a silent empty panel.

## Profiles Library Tree / Preset Implementation

Tuning / Profiles Library now includes a folder-style preset selector:

- Active Workspace
  - Current Workspace
- Built-in Presets
  - Balanced Default
  - Precision Aim
  - Smooth Flight
  - Combat Response
- Imported Profiles
  - Empty / import pending

Selecting a preset updates the preview only. It does not apply, save, mutate runtime state, write output, or prove output. Four built-in presets are represented as deterministic preview descriptions:

- Balanced Default: conservative general-purpose tuning
- Precision Aim: softer center / finer small movement control
- Smooth Flight: stronger smoothing / gentle response
- Combat Response: faster combat-oriented response preview

`Apply preset to draft` is disabled because safe workspace preset-apply semantics are not currently represented. Copy and navigation actions remain enabled and truthful.

## Blank Page Protections

LCD-7W preserves the existing route-host protections:

- same-route navigation does not clear the page
- route factory failures show visible error fallback panels
- telemetry sync exceptions are trapped as non-destructive shell properties
- route cycling tests assert non-empty widgets for every Liquid route
- hidden high-frequency Analysis/Tuning pages are not rebuilt on telemetry bursts

## Visual QA Artifacts

Regenerated artifact target:

- screenshots: `artifacts/liquid-ui/lcd-7w/`
- PDF report: `artifacts/liquid-ui/lcd-7w/liquid-ui-lcd-7w-visual-report.pdf`

The screenshot/report scripts now support `lcd-7w` directly.

## Deferred

- Broad visual simplification remains deferred.
- Recorder and Helm were not rebuilt.
- Support and Diagnostics were not rebuilt.
- Profile import/export/duplicate/rename/delete/apply semantics remain disabled until safe workspace profile mutation exists.
- Live Monitor display sampling is UI-only cached-data sampling, not a runtime polling system.

## Runtime Truth Preservation Statement

LCD-7W preserves runtime truth boundaries. The pages are passive visualizations and workspace draft/profile preview surfaces only. No runtime authority was changed, no hardware polling was added, no vJoy/output behavior was changed, no output verification behavior was changed, no Bridge lifecycle management was added, no cloud AI/LLM behavior was added, and no auto-save was added.

Explicitly:

- no Recorder/Helm page was rebuilt
- no Support/Diagnostics page was rebuilt
- no radial menu behavior was added
- no page transition animations were added
- no hardware polling was added
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no cloud AI/LLM behavior was added
- no auto-save was added
