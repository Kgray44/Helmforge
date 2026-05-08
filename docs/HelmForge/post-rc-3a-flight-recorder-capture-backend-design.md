# Post-RC 3A - Flight Recorder Capture Backend Design

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: safe capture backend design and backend seam only

## Boundary

Post-RC 3A prepares the Flight Recorder for real capture work without claiming that recording exists. Telemetry remains the truth surface. Simulated artifacts stay metadata-only. vJoy detection is not output verification, output intent is not write proof, physical input alone is not Full Live Runtime Ready, fake/test paths are not real readiness, packaged smoke is not runtime readiness, and simulation mode remains available.

This phase does not add full video recording, video encoding/export, playable preview, global recorder hotkeys, game injection, graphics API hooking, admin-level capture, new runtime behavior, hardware polling, vJoy/output behavior, Bridge lifecycle management, cloud AI/LLM behavior, or auto-save.

## Options Reviewed

| Option | Dependency impact | Packaging impact | Safety | Performance | Cursor support | Multi-monitor support | Testability | Requires admin | Game injection or graphics hooking risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qt screen grab | Uses PySide6, already part of the UI runtime. No new required package for a seam. | Lowest immediate impact because Qt ships with the app. Future frame buffering must be smoke-tested in packaged output. | Conservative if limited to explicit display/window calls from the app process. No privileged capture. | Suitable for still-frame proof and low-rate prototypes; likely not the final high-FPS recorder path. | Cursor inclusion is uncertain and platform-dependent; treat as unavailable until verified. | Qt can enumerate screens, but capture geometry and DPI behavior need explicit tests. | Good for import/status/enumeration tests and later one-frame explicit-call tests. | No. | Low when used as desktop/window grab only; no injection or graphics hooking. |
| PIL/ImageGrab | Optional Pillow dependency if not already installed. | Adds a package and native wheel considerations to PyInstaller. | Simple desktop capture path, but must stay explicit-call only. | Good for still frames; not a full recorder pipeline. | Platform behavior varies; cursor usually not reliable. | Basic monitor behavior varies by OS and DPI mode. | Good for dependency-unavailable tests; real frame tests require desktop environment. | No. | Low; no injection or graphics hooking if used directly. |
| mss | Optional dependency, not required in 3A. | Adds native package considerations and packaged smoke coverage. | Common desktop screenshot library; must remain explicit and bounded. | Better than basic still grabs for repeated frames, but still needs buffering design. | Cursor support is not a built-in guarantee. | Strong multi-monitor enumeration model. | Good with dependency gating and fake display metadata. | No. | Low; no game injection or graphics hooking. |
| Windows Graphics Capture | Future Windows-native direction. May require WinRT bindings or native helper code. | Higher packaging complexity and Windows-version testing. | Good long-term safety if using documented OS capture picker/session semantics. | Strong candidate for real recorder performance. | Cursor support can be controlled by the API, but must be verified. | Good Windows multi-monitor/window support. | Needs Windows-specific integration tests and guarded capability probes. | No for normal user capture flows. | Low if using OS capture APIs; no game injection or graphics hooking. |
| dxcam | Optional future dependency. | Adds native and GPU-adjacent packaging risk. | More specialized and higher caution. It must not become game injection. | Potentially high performance for desktop capture. | Needs verification; do not assume cursor capture. | Multi-monitor behavior needs explicit proof. | Harder to test in CI/offscreen environments. | No expected admin requirement, but environment-specific failures are likely. | Higher perception risk because it is GPU/desktop-capture oriented; must be explicitly forbidden from graphics hooking. |
| ffmpeg | Future encoding or external capture option only. | Highest operational impact: binary discovery, bundling, licensing/release notes, packaged smoke, and failure reporting. | Safe only if used as a bounded subprocess with explicit user action and no game injection. Not part of 3A. | Strong for encoding once frame sources are proven. | Depends on input source and options. | Depends on input source and options. | Testable through version probes and dry-run encoding later, but not in 3A. | No for normal encoding. | Low for encoding files; capture-device modes need strict boundaries and must avoid game hooking. |

## Recommendation

Use a conservative Qt candidate seam first. Qt is already present in the application stack, can be imported safely, and can expose candidate dependency/display truth without forcing optional capture packages. In Post-RC 3A the candidate backend reports capability status only. It does not capture frames, record video, encode video, register hotkeys, or claim readiness.

The recommended Post-RC 3B path is:

- add a single explicit one-frame proof method behind the same capability contract;
- keep it disabled by default and never automatic;
- prove display enumeration and geometry in UI/offscreen-safe tests where possible;
- preserve the simulated metadata/export path as a separate test/dev surface;
- defer frame buffering, cursor capture, encoding, and playable exports until the frame proof is stable.

Windows Graphics Capture should remain the likely future high-confidence Windows path for real capture. PIL/ImageGrab or mss can be revisited as optional fallbacks after the Qt seam proves the controller/UI contract. ffmpeg should be considered only after frame source truth is proven, and only for future encoding/capture phases with packaging coverage.

## Capability Model

Capture backends now report:

- backend name and kind;
- dependency availability;
- screen, frame, cursor, display-enumeration, and video-encoding availability;
- real capture support versus simulated capture support;
- admin requirement;
- game-injection and graphics-hooking flags;
- warnings and errors.

The model intentionally separates "candidate dependency available" from "real capture supported." A candidate backend can be present while still reporting real capture unsupported, frame capture unavailable, cursor capture unavailable, and video encoding unavailable.

## Display Source Model

Display sources are modeled with:

- display id;
- display label;
- geometry when available;
- primary display flag when available;
- capture source such as current display, selected display, or future window;
- warnings and errors.

This prepares the later frame buffer without starting capture in 3A.
