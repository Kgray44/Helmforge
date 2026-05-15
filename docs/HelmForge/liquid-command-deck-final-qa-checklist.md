# Liquid Command Deck Final QA Checklist

LCD-12 freeze checklist for the Liquid Command Deck primary experience.

## Launch And Shell

- [ ] app launches into Liquid Command Deck primary experience
- [ ] Legacy pages are not the primary Liquid page compositions
- [ ] compact dock / mode selector clarity
- [ ] top command bar clarity
- [ ] footer action strip clarity
- [ ] shell remains usable at the minimum supported window size

## Routes

- [ ] each major mode opens
- [ ] each subpage opens
- [ ] each page has a dominant hero/purpose area
- [ ] compact dock navigation still works when the optional quick switch wheel is disabled

## Truth Surfaces

- [ ] Preflight readiness truth is clear and does not claim readiness without existing proof
- [ ] Mapping output intent truth stays labeled as intent, not output proof
- [ ] Tuning parameter/control clarity is preserved while editing
- [ ] Analysis / Live Monitor live/stale truth remains visible
- [ ] Recorder capture truth / metadata-only truth remains explicit
- [ ] Helm draft/apply/revert truth stays workspace-draft only
- [ ] Help / Diagnostics clarity is preserved
- [ ] simulation fallback truth remains readable
- [ ] vJoy detected vs output proof distinction remains explicit
- [ ] output proof missing distinction remains explicit

## Motion And Accessibility

- [ ] motion OFF leaves navigation, focus, status text, and controls usable
- [ ] reduced motion leaves navigation, focus, status text, and controls usable
- [ ] standard motion remains polished without layout movement
- [ ] Cinematic shows visible passive background/atmosphere motion within 10 seconds
- [ ] Cinematic shows visible status breathing within 5 seconds
- [ ] Cinematic shows visible page transition when switching modes/subpages
- [ ] Cinematic shows visible route/signal sweep somewhere in the app
- [ ] Motion Proof panel visibly animates in Cinematic
- [ ] Off fully disables optional motion
- [ ] Reduced is calmer than Standard
- [ ] Standard is visibly animated but less dramatic than Cinematic
- [ ] no mode looks identical to every other mode
- [ ] active button motion is smooth on hover, press, release, and selected states
- [ ] active card motion is smooth on hover, focus, selection, and deselection
- [ ] page transition motion is visible when switching major modes
- [ ] subpage transition motion is visible when switching route chips/tabs
- [ ] axis selection motion is visible on Tuning/Analysis axis pills
- [ ] route/signal sweep motion is visible on Mapping or Effective Response Stack route surfaces
- [ ] status state-change animation is visible without changing status truth text
- [ ] save/apply/revert animation shows draft/saved/apply-intent feedback without runtime proof claims
- [ ] Live Monitor smooth visual motion is visible in real/simulation/fallback truth states
- [ ] passive atmosphere quality is smooth, low-contrast, and not skippy
- [ ] Cinematic not being just background animation is confirmed through active controls and page motion
- [ ] no obnoxious full-screen movement or screensaver-like passive animation
- [ ] radial menu enabled/disabled behavior is verified if the optional quick switch wheel is enabled
- [ ] optional quick switch wheel closes with Escape and does not trap focus
- [ ] atmosphere readability is acceptable on every major mode
- [ ] status chips remain readable over atmosphere accents
- [ ] disabled buttons remain visibly disabled
- [ ] focus indicators remain visible

## Performance And Safety

- [ ] no large-container blur
- [ ] no broad layout mutation
- [ ] no high-frequency full-page repaint loop
- [ ] no obvious flicker/freeze
- [ ] Live Monitor frames advance without increasing full render count
- [ ] diagnostics pages do not animate raw panels aggressively
- [ ] hidden pages do not run heavy atmosphere/live effects
- [ ] build_analysis_command_model is not called per visual tick
- [ ] packaged smoke result is recorded
- [ ] physical HOTAS validation status is recorded

## Final Status

- [x] packaged smoke result: passed with `.\packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250`
- [x] LCD-12A normal-display motion visibility QA: passed with Cinematic atmosphere, status breathing, page transition, quick switch wheel, Motion Proof rail, and Live Monitor fallback motion visible/testable
- [x] LCD-12B normal-display motion quality QA: passed with Off/Reduced/Standard/Cinematic mode sweep, active Helm button interpolation, quick switch wheel animation, route sweep/page motion, and Live Monitor fallback motion with zero sample/full-render delta
- [x] LCD-12B page switch correction QA: passed for Mapping, Tuning, Analysis, and Support route pairs with snapshot crossfade/glide, previous/current snapshots present, changing enter/exit alpha, and glide offset settling to zero
- [x] LCD-12B packaged smoke result: passed after `powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_release.ps1 -Clean`
- [ ] physical HOTAS validation status: physical/manual continuous HOTAS-axis movement was not performed
