# Phase 12C - Live Overlay Polish and Boundary Freeze

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Final Phase 12 Live Overlay polish and boundary freeze only

## Summary

Phase 12C finalizes the Live Overlay Foundation work. It tightens Live Monitor card behavior, refreshes final hotkey/click-through support wording, hardens overlay close-state handling, updates Help / Docs and architecture documentation, and adds final boundary tests before Phase 13.

Phase 12C does not add runtime authority.

## Phase 12A Summary

Phase 12A added the shared Live Overlay core:

- recovered axis colors;
- serializable overlay configuration with validation/clamping;
- telemetry history buffer;
- trace builder;
- Live Monitor Live Overlay card;
- Live Overlay Configuration dialog shell.

## Phase 12B Summary

Phase 12B added detached rendering:

- app-owned top-level frameless overlay window;
- Qt renderer for trace lines, legend, live values, and idle runtime truth text;
- Live Monitor Show Overlay / Hide Overlay behavior;
- Active only while the detached overlay window is visible;
- config dialog OK/Cancel integration with the visible overlay.

## Phase 12C Polish

Phase 12C adds final polish:

- direct overlay-window close events notify Live Monitor, so Status returns to `Inactive`;
- the configuration dialog removes stale Phase 12A wording;
- click-through support wording is now `Not verified`;
- Help / Docs states that Live Overlay is app-owned and detached, does not inject into games, does not use graphics API hooking, and does not capture the screen;
- final Phase 12 boundary tests protect the no-runtime-authority line.

## Final Live Overlay Behavior

Live Monitor Live Overlay card:

- Title: Live Overlay
- Description: Launch the detached telemetry strip, choose a preset, and adjust advanced behavior only when needed.
- Buttons: Show Overlay / Hide Overlay and Configure
- Preset: Custom
- Status: Active only when the detached overlay window is visible
- Status: Inactive when hidden or closed
- Attached display: Current display unless Qt can truthfully identify another display label
- Toggle: Ctrl+Shift+F9
- Hotkey status: Not registered
- Click-through: Not enabled - not verified
- Summary: Custom | Bottom strip | 66% opacity | Final output

## Support Truth

Hotkey support:

- Toggle hotkey is configured as `Ctrl+Shift+F9`.
- Global hotkey registration is not implemented.
- Hotkey status remains `Not registered`.

Click-through support:

- Click-through remains disabled by default.
- Platform click-through behavior is not implemented.
- Click-through status remains `Not enabled - not verified`.

Always-on-top support:

- Always-on-top is config-backed through Qt window flags when enabled.
- It does not imply game attachment, graphics injection, live hardware runtime, or output verification.

## Current Runtime Truth

Observed conservative runtime truth during verification:

- Bridge lifecycle: `Simulated`
- Runtime truth: `blocked_missing_device`
- HOTAS status: HOTAS Not Connected
- vJoy status: vJoy Detected
- vJoy detected, output writes unverified
- `output_verified`: `false`
- Full Live Runtime Ready: `false`

## Final Phase 12 Boundary

Phase 12 is Live Overlay Foundation. It is now complete.

Phase 12C does not add:

- Flight Recorder;
- clip capture;
- video encoding;
- clip library;
- clip preview;
- hindsight buffer;
- recorder hotkey Ctrl+Shift+F10;
- real HOTAS polling;
- live physical input streaming;
- vJoy writes;
- output verification;
- automatic Bridge launch;
- UI-launched child process;
- service install;
- login auto-start;
- tray manager;
- installer launch;
- StartBridge/StopBridge/RestartBridge behavior;
- real process scanner;
- real runtime activation;
- game injection;
- DirectX/OpenGL/Vulkan hooking;
- screen capture;
- cloud AI or LLM behavior;
- auto-save.

## Verification

Final verification results:

- `python -m pytest` - passed, 265 tests.
- `python -m pytest tests\test_phase9k_boundary_freeze.py` - passed, 7 tests.
- `python -m pytest tests\test_phase10e_helm_final_polish_boundary.py` - passed, 7 tests.
- `python -m pytest tests\test_phase11c_help_perf_boundary_freeze.py` - passed, 6 tests.
- `python -m pytest tests\test_phase12a_live_overlay_foundation.py` - passed, 6 tests.
- `python -m pytest tests\test_phase12b_live_overlay_window_renderer.py` - passed, 6 tests.
- `python -m pytest tests\test_phase12c_live_overlay_polish_boundary.py` - passed, 5 tests.
- `$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250` - passed.
- `python -m bridge_app.main --once` - passed.
- `python -m bridge_app.main --run-for-ms 250` - passed.
- `python -m bridge_app.main --status` - passed with `lifecycle=Simulated`, `truth=blocked_missing_device`, and `output_verified=False`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun` - passed. Thrustmaster software detected, vJoy detected, HOTAS Not Connected, Simulation Mode Active unless physical input and output writes are both verified, Full Live Runtime Ready false, and no installers launched.
- `git diff --check` - passed.

## Recommended Next Phase

The next prompt-book phase is Phase 13: Flight Recorder, Clip Library, and Hindsight Buffer.

Phase 13 should reuse shared overlay colors and trace concepts where appropriate. It must not pretend clip capture, video encoding, clip library behavior, clip preview, hindsight buffering, or recorder hotkey behavior exists until those features are implemented and verified.
