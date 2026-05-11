# LCD-1R Static Shell Recomposition Report

## Why LCD-1R Was Needed

This section explains why LCD-1R was needed.

LCD-1 proved that HelmForge can host a separate Liquid shell without changing runtime authority. The first shell was intentionally safe, but it was too Legacy-like: a vertical text dock, one large bordered content rectangle, and placeholders that did not yet demonstrate the Liquid Command Deck information architecture.

This corrective pass keeps LCD-1 scope but recomposes the static shell so the next phase starts from a command-deck foundation instead of a conservative sidebar-and-card shape.

## What Was Too Legacy-Like

The original LCD-1 shell still read as too Legacy-like because it used large stacked text navigation controls, a single bordered page host, repeated same-weight panels, and placeholder pages that were mostly empty rectangles. It looked closer to an admin dashboard with darker styling than to a cockpit command deck.

## How The Dock Was Corrected

The dock was corrected into a compact glyph-first command rail. Each major mode still exists, but the visible controls are short mode codes with accessible names and tooltips carrying the full labels. The dock now uses a narrow floating-glass footprint and an active label bubble, so text no longer dominates the navigation surface.

The required modes remain:

- Preflight
- Mapping
- Tuning
- Analysis
- Recorder
- Support

## How The Workspace Composition Was Corrected

This section explains how the workspace composition was corrected.

The workspace composition was corrected from one large empty box into a layered static command surface:

- `liquidCommandWorkspace` provides the shell-level command workspace.
- `liquidDeckBackplane` provides the cockpit-style static backplane.
- `liquidWorkspaceGlow` provides a non-animated static glow layer.
- `liquidPageHost` remains the page host, but it now sits inside the layered deck instead of acting as the whole visual idea.

The top command/status bar now has a compact command orb, grouped status capsule, command cluster, and static status rail. The footer remains a disabled action strip and still does not write, save, apply, revert, or manage runtime behavior.

## Placeholder Pages Now Prepare For LCD-2/LCD-3/LCD-4+

This section explains how placeholder pages now prepare for the later Liquid phases.

Each placeholder now demonstrates the future page architecture rather than merely occupying a blank panel:

- a mode status rail
- a page title and purpose
- a dominant hero / primary instrument region
- context inspector region
- detail/action region
- advanced/details region

The hero titles prepare the later page rebuilds:

- Preflight: Go / No-Go Readiness
- Mapping: HOTAS Visual Map
- Tuning: Response Instrument
- Analysis: Signal / Live Monitor Instrument
- Recorder: Capture Capability Deck
- Support: Diagnostics / Help Console

LCD-2 can replace these raw regions with shared Liquid components. LCD-3 can extend the mode rail and page host into real mode/subpage routing. LCD-4 and later page phases can replace placeholders one at a time without reworking the shell.

## Runtime Truth Preservation

This section documents runtime truth preservation.

Runtime truth preservation remains unchanged. The Liquid shell displays existing `AppState` runtime labels, saved state, workspace/profile state, and source/config state. It does not claim live readiness, verified output, hardware health, capture readiness, or Bridge ownership unless existing truth data supports that wording.

No runtime authority was changed. LCD-1R adds static composition only.

## Deferred Scope

- no full page rebuilds were implemented
- no animations were added
- no radial menu was added
- no real blur/distortion was added
- no runtime authority was changed
- no hardware polling was changed
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no recorder capture/encoding was added
- no cloud AI/LLM behavior was added
- no auto-save was added
