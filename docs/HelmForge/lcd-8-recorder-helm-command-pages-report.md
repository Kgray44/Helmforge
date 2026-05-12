# LCD-8 Recorder and Helm Command Pages

## Why LCD-8 Was Needed

LCD-8 replaces the Recorder route placeholders with real Liquid command pages and adds a Liquid Helm Assistant deck. The work keeps the Liquid Command Deck recomposition pattern: new UI surfaces use existing non-visual state and deterministic Helm logic, while Legacy pages remain fallback/reference only.

## Routes Implemented

- `recorder.flight_recorder`
- `recorder.clip_library`
- `recorder.capture_backend_truth`

The route registry now maps those routes to real Liquid pages instead of generic placeholder pages. Preflight, Mapping, Tuning, and Analysis routes remain intact.

## Recorder Page Architecture

Recorder pages are implemented as one route-aware Liquid page class backed by a pure recorder presentation model. The model produces capability items, disabled action items, artifact rows, metrics, backend details, advanced details, warnings, errors, and truth notes. The UI renders a hero-first recorder truth surface with capability rails, compact action/detail panels, and secondary advanced details.

## Flight Recorder Page Behavior

The Flight Recorder page answers what can be captured, buffered, and reviewed. It shows recorder status, backend truth, frame capture truth, encoding truth, hindsight video truth, artifact mode, and disabled controls for unavailable actions. `Record Now` and `Save Last Clip` remain disabled unless existing backend capability data supports them.

## Capture Backend Truth Page Behavior

The Capture Backend Truth page exposes backend capability fields including backend name/kind, dependency state, screen capture, frame capture, cursor capture, display enumeration, real capture support, simulated artifact support, admin requirement, game injection, graphics hooking, and encoding. It explicitly shows "No game injection" and "No graphics hooking" when the capability model reports false.

## Clip Library / Artifacts Page Behavior

The Clip Library / Artifacts page scans existing recorder artifact metadata through the existing clip library and renders compact artifact cards. Metadata-only artifacts are labeled as metadata-only, playback unavailable, and export unavailable. Playable/export-ready claims are shown only when existing encoded clip metadata permits that claim.

## Recorder Presentation Model Structure

`v3_app/liquid/models/recorder_command_model.py` defines:

- `RecorderCapabilityItem`
- `RecorderActionItem`
- `RecorderArtifactItem`
- `RecorderCommandModel`
- `build_recorder_command_model`

The model is pure from the UI perspective. It reads existing settings, recorder state, backend capabilities, and clip metadata. It does not start capture, encode video, poll desktop frames, or create runtime authority.

## Data Surfaces Used

LCD-8 uses:

- `FlightRecorderSettings`
- `RecorderState`
- `CaptureBackendCapabilities`
- `MissingCaptureBackend` / existing capture backend interface
- `ClipLibrary` / `ClipMetadata`
- existing `AppState` runtime labels for display only
- existing deterministic Helm engine, recommendation result, and diff model

## Backend Capability Truth Behavior

Recorder capability truth is derived from existing backend capability fields. vJoy/output proof, runtime readiness, and capture capability are not conflated. Capture backend unavailable, frame capture unavailable, encoding unavailable, and hindsight video unavailable remain visible.

## Metadata-Only vs Real Recording Truth Behavior

Metadata-only artifacts are not called real recordings. Simulated artifacts are shown as metadata-only artifacts. Real recording and playable preview claims require existing encoded-clip/file proof surfaced by the current recorder artifact model.

## Disabled/Unavailable Recorder Action Behavior

Recorder action rows are rendered as disabled/unavailable when the model does not report support. Disabled actions explain the blocker. No new recorder action starts real capture, video buffering, or encoding.

## Helm Assistant Deck/Surface Architecture

The Liquid Helm Assistant deck is a static floating command surface attached to the Liquid shell. It is toggled from the existing top Helm button and renders a status hero, evidence source chips, finding cards, proposed change cards, and apply/revert controls.

## Helm Data/Logic Surfaces Used

Helm uses existing deterministic local logic only:

- `HelmEngine`
- `HelmRecommendationResult`
- `HelmDiff`
- `apply_selected_diffs`
- `revert_applied_diffs`

No external service or new assistant intelligence was added.

## Helm Recommendation/Finding/Proposed-Change Behavior

Helm findings are grouped by evidence source. Proposed changes show axis, section, parameter, before/after value, expected outcome, confidence, risk, and truth note. The deck keeps "Output proof unchanged" visible next to recommendations.

## Helm Apply/Revert Semantics

Helm apply stages selected recommendations into the workspace draft using the existing safe diff helper. Save remains the persistence action. Revert restores the last Helm draft batch through existing revert semantics. These changes are recommendations/staged draft changes only using existing safe semantics.

## Recorder/Helm Truth Differs From Runtime Output Proof

Recorder capability does not imply runtime output readiness. Helm recommendations do not imply runtime application or output proof. Output intent/proposed changes remain separate from vJoy/output verification. Recorder/Helm truth differs from runtime output proof.

## Hidden-Route Rebuild Protection

Recorder pages are constructed once by the route host and are not updated on hidden telemetry bursts. Helm is only refreshed when the deck is opened or when a Helm apply/revert operation changes its local model. The LCD-4F no-hidden-rebuild principle is preserved.

## Legacy Fallback/Reference Is Preserved

Legacy `FlightRecorderPage` and Legacy `HelmOverlay` remain in place for the non-Liquid shell. Liquid routes do not wrap or reskin those Legacy widgets.

## Limitations/Deferred Recorder/Helm Features

Deferred beyond LCD-8:

- real recorder capture backend expansion
- recorder timeline animation
- playback preview UI
- video export UI beyond existing truth metadata
- Helm slide-in animation
- Support/Diagnostics page rebuild
- richer Helm symptom editing
- cloud/LLM assistant behavior

## Runtime Truth Preservation Statement

LCD-8 preserves runtime truth boundaries. Recorder pages are truth surfaces over existing recorder/backend state. Helm changes are recommendations/staged draft changes only using existing safe semantics. No runtime authority, hardware polling, vJoy/output behavior, output verification, Bridge lifecycle management, recorder capture/encoding, game injection, graphics API hooking, cloud AI/LLM behavior, or auto-save was added.

## Explicit Non-Goals Confirmed

- no Support/Diagnostics page was rebuilt
- no radial menu behavior was added
- no animations were added
- no page transitions were added
- no recorder timeline animation was added
- no Helm slide-in animation was added
- no real blur/distortion was added
- no runtime authority was changed
- no hardware polling was changed
- no vJoy/output behavior was changed
- no output verification behavior was changed
- no Bridge lifecycle management was added
- no real recorder capture/encoding was added
- no game injection was added
- no graphics API hooking was added
- no cloud AI/LLM behavior was added
- no auto-save was added

## Requirement Trace

- routes implemented
- Recorder page architecture
- Flight Recorder page behavior
- Capture Backend Truth page behavior
- Clip Library / Artifacts page behavior
- Recorder presentation model structure
- data surfaces used
- backend capability truth behavior
- metadata-only vs real recording truth behavior
- disabled/unavailable recorder action behavior
- Helm assistant deck/surface architecture
- Helm data/logic surfaces used
- Helm recommendation/finding/proposed-change behavior
- Helm apply/revert semantics
- Recorder/Helm truth differs from runtime output proof
- hidden-route rebuild protection
- Legacy fallback/reference is preserved
- limitations/deferred recorder/Helm features
- runtime truth preservation statement
- Recorder pages are truth surfaces over existing recorder/backend state
- Helm changes are recommendations/staged draft changes only using existing safe semantics
