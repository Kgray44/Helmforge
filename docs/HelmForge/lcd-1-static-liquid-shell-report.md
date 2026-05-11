# LCD-1 Static Liquid Shell Report

## Scope

LCD-1 adds the static Liquid Command Deck shell as a separate UI architecture. It does not repaint, wrap, or restyle the Legacy shell. Legacy pages remain available as reference and fallback while the Liquid interface grows through later LCD phases.

## New Module Structure

This section documents the new module structure:

- `v3_app/liquid/__init__.py`
- `v3_app/liquid/app_shell.py`
- `v3_app/liquid/navigation.py`
- `v3_app/liquid/layout.py`
- `v3_app/liquid/theme_tokens.py`
- `v3_app/liquid/glass.py`
- `v3_app/liquid/pages/__init__.py`
- `v3_app/liquid/pages/placeholder_pages.py`

The focused regression coverage lives in `tests/test_lcd_1_static_liquid_shell.py`.

## Shell Architecture

This section documents shell architecture. `LiquidCommandShell` is a new `QWidget` host with these static regions:

- top command/status bar: product title, Liquid shell subtitle, workspace/profile chip, saved state chip, runtime truth chip, source chip, and disabled Helm entry location.
- compact mode dock: Preflight, Mapping, Tuning, Analysis, Recorder, and Support as compact dock buttons.
- workspace frame: a glass-styled central frame that holds the dock and page host.
- page host: a `QStackedWidget` containing one Liquid placeholder page per major mode.
- footer action strip: status message plus disabled Apply, Save, and Revert placeholders.

The shell does not instantiate the Legacy sidebar, Legacy header, Legacy footer, or old page stack as its primary layout.

## Legacy Fallback

Legacy fallback is preserved. `build_window(..., ui_shell="legacy")` still constructs `HelmForgeShell`, and `legacy` remains the LCD-1 default. The Liquid shell can be selected with `build_window(..., ui_shell="liquid")`, `python -m v3_app.main --ui-shell liquid`, or `HELMFORGE_UI_SHELL=liquid`.

This keeps the existing acceptance suite and operational UI path stable while making the new Liquid shell hostable.

## Backend/Data Surfaces Reused

This section documents backend/data surfaces reused. LCD-1 reuses existing non-visual state only:

- `v3_app.services.app_state.AppState`
- `RuntimeUiState` labels and tones for runtime truth chips
- saved/unsaved state from `AppState.saved`
- workspace/profile state from `AppState.active_profile`
- source/config state from `AppState.source_config`
- bridge telemetry snapshot shape for passive chip updates when the existing app runtime supplies telemetry

LCD-1 does not introduce new runtime authority.

## Runtime Truth Preservation

This section documents runtime truth preservation. The Liquid shell displays current runtime truth labels from existing state. It does not claim full readiness, live output, output verification, recording availability, hardware health, Bridge ownership, or write proof beyond what existing truth state supports.

The footer actions are disabled placeholders. The Helm entry is a disabled location marker. No workspace write, apply, revert, lifecycle, recorder, or cloud behavior is wired in LCD-1.

## What Remains For LCD-2

LCD-2 should build the shared Liquid component library before replacing real pages. Expected next work:

- reusable glass panels and command chips
- shared status/readiness components
- reusable page hero/instrument primitives
- consistent mode/subpage composition helpers
- accessibility and sizing rules for the new component set
- placeholder demonstrations using the shared components

## Explicit Non-Goals Confirmed

- No animations, real blur, distortion, radial menu, or motion system was added.
- No hardware polling changes were added.
- No vJoy/output behavior changes were added.
- No output verification changes were added.
- No Bridge lifecycle management was added.
- No recorder capture or encoding was added.
- No cloud AI/LLM behavior was added.
- No auto-save was added.
