# LCD-1F Floating Command Surface Report

## Why This Correction Was Needed

This section explains why this correction was needed. LCD-1 created a separate Liquid shell and LCD-1R corrected the first sidebar-like composition, but the middle and bottom of the interface still felt too sectioned/sidebar-like. The mode dock, page area, and footer read as separate zones instead of floating glass controls layered over one command surface.

LCD-1F keeps the work inside LCD-1 shell scope and corrects the static geometry before LCD-2 starts.

## What Was Still Too Sectioned/Sidebar-Like

This section documents what was still too sectioned/sidebar-like.

The previous shell still had a left lane, a central page island, and a bottom footer strip. Even though the pieces were narrower and more dimensional, they still implied hard partitions. The dock was visually attached to the left edge, the page host sat inside nested glass boundaries, and the footer behaved like a bottom section instead of a floating command HUD.

## Floating Dock And Floating Footer Correction

The shell now has one main `liquid_command_surface`. A subtle `liquid_surface_glass_field` spans that surface, while the dock and footer are layered into the same surface instead of occupying separate layout rows or columns.

The floating dock is now `liquid_floating_mode_dock`. It uses compact glyph-first controls, keeps full mode names through accessible names and tooltips, and shows the selected mode in a small label bubble. The floating footer is now `liquid_floating_footer_strip`; it remains disabled and truthful, but reads as a HUD control layer over the deck rather than a separate bottom page section.

## Future Radial Navigation Prepared But Not Implemented

This section documents how future radial navigation is prepared but not implemented.

LCD-1F adds `liquid_radial_anchor_orb` as a future quick-switch anchor only. It has tooltip and accessible text indicating future use. It does not open a menu, register interactions, add transitions, or implement radial behavior.

## No Pages/Features Were Removed

This section confirms no pages/features were removed.

No pages/features were removed. All major modes remain represented:

- Preflight
- Mapping
- Tuning
- Analysis
- Recorder
- Support

The placeholder pages still expose hero, context/inspector, detail/action, and advanced/deferred regions. The future page/subpage intent remains available for LCD-2 and LCD-3.

## LCD-2 And LCD-3 Build Path

LCD-2 can turn the raw floating glass regions into shared Liquid components: surface slabs, floating HUD strips, glyph controls, hero instruments, context inspectors, status rails, and action groups.

LCD-3 can add real mode/subpage routing on top of the existing `LiquidModeDefinition`, `LiquidModeDock`, and `liquid_page_host` seams without reworking the static command surface.

## Runtime Truth Preservation

This section documents runtime truth preservation. LCD-1F does not change runtime behavior, hardware polling, vJoy/output behavior, output verification, Bridge lifecycle management, recorder capture/encoding, cloud AI/LLM behavior, or auto-save.

The shell continues to display existing `AppState` labels and disabled placeholders only. No live readiness, output verification, recording availability, hardware health, or Bridge ownership is claimed beyond existing truth data.

## Deferred Scope

- No LCD-2 component library was implemented.
- No LCD-3 mode/subpage routing was implemented.
- No real page rebuilds were implemented.
- No radial menu behavior was implemented.
- No animations or page transitions were added.
- No real blur/distortion was added.
- No runtime authority was changed.
