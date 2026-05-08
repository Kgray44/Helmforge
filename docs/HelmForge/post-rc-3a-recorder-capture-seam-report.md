# Post-RC 3A - Recorder Capture Seam Report

Product: HelmForge
Technical subtitle: HOTAS Control Panel V3
Scope: Flight Recorder real backend design and guarded capture backend seam

## Summary

Post-RC 3A starts the real Flight Recorder backend track without implementing real recording. The recorder now has a richer capture backend capability model, a display source model, and a guarded Qt candidate backend seam that can be imported and queried safely. It does not capture desktop frames, encode video, start recording automatically, register recorder hotkeys, or claim runtime readiness.

## Backend Options Reviewed

The design pass reviewed Qt screen grab, PIL/ImageGrab, mss, Windows Graphics Capture, dxcam, and ffmpeg. Each option was compared for dependency impact, packaging impact, safety, performance, cursor support, multi-monitor support, testability, admin requirements, and game-injection/graphics-hooking risk.

## Chosen Next Implementation Path

The conservative path is the Qt candidate seam first. Qt is already part of the app runtime, so it is the least disruptive way to expose candidate dependency and display-source truth. Post-RC 3B should add an explicit one-frame proof behind the same seam before any frame buffering, cursor capture, encoder integration, playable preview, hotkey registration, or export workflow.

Windows Graphics Capture remains a possible future Windows-native path once the seam has proven the UI/controller contract. PIL/ImageGrab and mss remain optional fallback candidates. ffmpeg remains a future encoding/capture option only after real frame-source proof exists.

## Capability Model Changes

Capture backend capabilities now include:

- backend name and backend kind;
- dependency availability;
- screen, frame, cursor, and display-enumeration availability;
- real capture support versus simulated capture support;
- video encoding availability;
- admin requirement;
- game-injection and graphics-hooking flags;
- warnings and errors.

The existing missing backend remains unavailable. The simulated backend remains metadata-only and does not claim real capture. The Qt candidate backend reports candidate status but keeps real capture unsupported and frame capture unavailable in Post-RC 3A.

## UI Truth Changes

The Flight Recorder status now exposes:

- capture backend as Missing, Simulated, Candidate unavailable, or Candidate available;
- dependency status;
- real capture supported status;
- frame capture status;
- cursor capture status;
- display enumeration status;
- video encoding unavailable;
- video hindsight unavailable;
- hotkey not registered.

Record Now remains disabled unless a backend explicitly reports real capture support. Save Last Clip remains disabled for real video because no video hindsight buffer exists. Simulated artifacts and simulated export bundles remain available through the injected test backend/controller path and remain clearly metadata-only.

## Runtime Truth Preservation

Post-RC 3A preserves the Phase 19D RC truth boundaries:

- telemetry remains the truth surface;
- vJoy detected is not output verification;
- physical input alone is not Full Live Runtime Ready;
- output intent is not output write proof;
- fake/test paths are not real readiness;
- packaged smoke is not runtime readiness;
- simulation mode remains available.

No runtime authority was added. No Bridge lifecycle management was added. No hardware polling, vJoy writes, output verification changes, recorder capture/encoding, game injection, graphics API hooking, cloud AI/LLM behavior, or auto-save was added.

## What Remains For Post-RC 3B

Post-RC 3B should implement the first explicit, guarded one-frame proof if the team chooses Qt as the initial real source. It should still avoid automatic capture and should report failure as unavailable rather than crashing. After that proof, later phases can consider frame buffering, cursor support, hindsight video buffering, encoder selection, playable preview, and export packaging.
