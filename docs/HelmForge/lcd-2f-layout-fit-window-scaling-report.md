# LCD-2F Layout Fit, Default Window Scale, and Overlap Cleanup Report

## Scope

LCD-2F is a corrective layout-stability pass for the Liquid Command Deck shell and LCD-2 component demonstrations. It keeps the floating command surface direction from LCD-1F and the shared component platform from LCD-2, while making the current placeholder pages fit more safely at the default and documented minimum Liquid sizes.

## previous layout issue

The LCD-2 placeholder demonstrations could crowd vertically and visually collide with the floating footer at the old app default scale. The page header also placed title, subtitle, and sample status chips into a crowded horizontal region, and sample status chips could read like current runtime truth when the top command/status bar was reporting a different live state.

## default window size

Legacy keeps the existing shared default size of `1152 x 800`.

Liquid now has its own preferred default window size of `1840 x 1040`, clamped to the available screen size where practical. On smaller or offscreen displays, the applied size is reduced so the window does not request more space than the current display can provide.

## minimum size

Liquid now has a documented preferred minimum size of `1360 x 800`, also clamped to the available display in small/offscreen contexts. This avoids requiring a full 1920 x 1080 display while giving the floating command surface enough room for the dock, hero region, inspector/detail panels, advanced section, and footer clearance.

## Liquid and Legacy

Liquid and Legacy differ intentionally. Legacy continues using `v3_app.theme.tokens.Layout` for its existing default/minimum geometry so the established Legacy shell tests and usability contract are not disturbed. Liquid uses `v3_app.liquid.theme_tokens.LiquidLayout` for the larger preferred default and minimum.

## overlap fixes

LCD-2F adds scroll-safe Liquid page hosting and lowers over-wide size hints from Liquid status chips so the shell can remain usable at the documented minimum size. Placeholder page regions retain the same major areas:

- page header
- hero/primary instrument
- inspector/context
- detail/action
- advanced/deferred
- floating footer

No major placeholder region was removed.

## footer clearance

The floating footer remains `liquid_floating_footer_strip`. The command surface now includes a layout-aware `liquid_footer_clearance` spacer below the page host, with `footerClearance=True`, so page content ends above the floating HUD strip instead of painting underneath it.

## header/chip wrapping

The Liquid placeholder header now separates title, subtitle, and chip content into explicit regions:

- `liquidPlaceholderHeaderTitleRegion_*`
- `liquidPlaceholderHeaderSubtitleRegion_*`
- `liquidPlaceholderHeaderChipRegion_*`

Subtitle text wraps, and demo chips sit in a secondary row so they do not merge into the title line.

## Demo Truth Consistency

LCD-2F labels placeholder status chips and contradictory examples as static demonstrations. Sample states now use wording such as `Static component sample`, `Demo gate: Runtime blocked`, and `Example state: Output proof missing`. If the top command/status bar reports current runtime truth such as `Live Verified`, the placeholder page does not present blocked/missing proof examples as current truth.

## runtime truth preservation

This pass does not alter runtime truth data. Top command/status bar truth still comes from the existing `AppState` runtime surface. Static placeholder chips are labeled as demo/example/static component samples when they differ from current truth.

## What remains for LCD-3

LCD-3 can build navigation and mode/subpage architecture on top of the now more stable Liquid shell. The current pass only prepares layout fit and does not add routing behavior.

## Explicit deferred items

- no LCD-3 navigation was implemented
- no real page rebuilds were implemented
- no animations were added
- no radial menu behavior was added
- no real blur/distortion was added
- no runtime authority was changed
- no hardware polling was changed
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no recorder capture/encoding was added
- no cloud AI/LLM behavior was added
- no auto-save was added
