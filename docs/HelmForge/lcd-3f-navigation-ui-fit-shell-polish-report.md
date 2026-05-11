# LCD-3F Navigation UI Fit, Dock Tooltip, and Shell Polish Report

## Scope

LCD-3F is a corrective shell/navigation presentation pass for the Liquid Command Deck. It keeps the LCD-3 navigation architecture intact while making the shell more readable and stable before LCD-4 begins real page rebuilds.

No real page behavior was added. Legacy remains the default fallback/reference path.

## why LCD-3F was needed

LCD-3 made the Liquid shell navigable, but the resulting presentation still had several shell-level issues: native-looking tooltip blocks, cryptic dock glyphs, clipped dock selected labels, crowded top status chips, an over-wide Helm action cluster, an awkward page header, a disconnected route selector, default scrollbars, and a large bottom backplate effect behind the floating footer.

LCD-3F corrects those shell/navigation issues without changing runtime authority or page behavior.

## dock hover/tooltip fix

Dock buttons now use short Liquid hover labels such as `Preflight`, `Mapping`, `Tuning`, `Analysis`, `Recorder`, and `Support`. Long mode descriptions moved to status tips and accessible metadata instead of native tooltip blocks.

The Liquid stylesheet now includes a dark `QToolTip` theme, and the dock includes `liquidDockHoverLabel` as a dock-attached glass label bubble. This prevents white native-looking tooltip blocks from becoming the primary hover experience inside the Liquid shell.

## dock glyph/selected-label fit fix

The floating dock remains compact and glyph-first, but its width and controls were slightly increased for readability. Mode glyphs are centered, mode controls use stable dimensions, and `liquidDockActiveLabel` now displays the selected mode name without clipped leading text.

All required modes remain present:

- Preflight
- Mapping
- Tuning
- Analysis
- Recorder
- Support

## top status chip clipping fix

The top status cluster still displays workspace, saved state, runtime truth, and source. The source chip now uses a short visible label such as `Source: Bridge Config` or an ellipsized source filename, while the full source string remains available through tooltip, status tip, and accessible description.

Runtime truth chip text still comes from the existing runtime truth surface.

## Helm action area fix

The Helm action cluster remains in the top bar, but it is now marked and styled as a compact action cluster instead of a wide empty field. The Helm button remains disabled and future-facing.

## page header/subpage selector cleanup

The placeholder route header now separates identity, purpose, and route chips into clearer static regions:

- mode eyebrow, mode title, and subpage title
- purpose/question row
- compact route/status chip row

The subpage selector remains `liquid_subpage_selector`, but it is now styled as a segmented route strip with a mode-aware label such as `Mapping routes` or `Tuning routes`.

## scrollbar styling fix

Liquid scrollbars now have a themed QSS hook with thinner dark tracks and muted cyan handles. This removes the bright default scrollbar look without adding animation.

## oversized footer background slab/scrim fix

The actual floating footer action strip remains `liquid_floating_footer_strip` and stays visually floating. LCD-3F removes the heavy bottom-slab impression by reducing footer clearance height, marking the clearance as transparent, and setting the surface field footer scrim role to `none`.

The oversized backplate behind the footer was reduced without removing the footer strip.

## footer clearance strategy

The page host still reserves bottom clearance so content can scroll above the floating footer. The clearance widget remains `liquid_footer_clearance`, but it is transparent and smaller. Placeholder pages also keep bottom padding so advanced sections are not hidden behind the footer.

## route/demo chip wording cleanup

Primary header chips now use product-facing wording such as:

- Command readiness route
- Route details route
- Page rebuild pending
- Read-only preview

Technical route keys remain available in widget properties, tooltips, accessible descriptions, the route registry, tests, and the advanced placeholder note.

## demo truth consistency

LCD-3F keeps demo/sample states clearly labeled as static, demo, example, placeholder, read-only, or unavailable. Placeholder page chips do not claim current runtime truth. Current runtime truth remains in the top command/status bar.

## runtime truth preservation

LCD-3F changes only Liquid shell/navigation presentation. It does not alter runtime truth data, hardware polling, output proof, live runtime readiness, Bridge ownership, recorder capability, Helm apply/revert semantics, or workspace save/apply semantics.

## what remains for LCD-4

LCD-4 can now rebuild the real Preflight page into the Liquid route host without first untangling shell fit issues. LCD-3F leaves stable route keys, dock state, selector state, header regions, footer clearance, and route placeholder seams in place for LCD-4 through LCD-9.

LCD-10 through LCD-12 still own radial behavior, motion/reduced-motion, atmosphere, blur/distortion, and transition work. LCD-3F preserves those seams but does not implement them.

## package note

LCD-3F changed source UI files and tests only. Packaged output was not rebuilt, and packaged smoke was not rerun, so any existing packaged artifact should not be treated as refreshed by this pass.

## explicit deferred items

- no real page rebuilds were implemented
- no radial menu behavior was added
- no animations were added
- no page transitions were added
- no real blur/distortion was added
- no runtime authority was changed
- no hardware polling was changed
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no recorder capture/encoding was added
- no cloud AI/LLM behavior was added
- no auto-save was added
