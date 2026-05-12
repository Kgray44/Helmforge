from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from v3_app.recorder.capture_backend import CaptureBackend, CaptureBackendCapabilities, MissingCaptureBackend
from v3_app.recorder.clip_library import ClipLibrary, ClipMetadata
from v3_app.recorder.recorder_settings import FlightRecorderSettings
from v3_app.recorder.recorder_state import RecorderState
from v3_app.services.app_state import AppState


@dataclass(frozen=True)
class RecorderCapabilityItem:
    label: str
    state_role: str
    detail: str


@dataclass(frozen=True)
class RecorderActionItem:
    action_id: str
    label: str
    enabled: bool
    state_role: str
    reason: str


@dataclass(frozen=True)
class RecorderArtifactItem:
    artifact_id: str
    title: str
    created_label: str
    duration_label: str
    source_label: str
    media_label: str
    playback_label: str
    export_label: str
    path_label: str
    state_role: str
    warning: str


@dataclass(frozen=True)
class RecorderCommandModel:
    route_key: str
    page_title: str
    page_question: str
    overall_label: str
    status_label: str
    short_explanation: str
    next_step: str
    backend_name: str
    backend_kind: str
    real_capture_supported: bool
    frame_capture_available: bool
    encoding_available: bool
    hindsight_video_available: bool
    simulated_artifact_supported: bool
    metadata_review_available: bool
    capabilities: tuple[RecorderCapabilityItem, ...]
    actions: tuple[RecorderActionItem, ...]
    artifacts: tuple[RecorderArtifactItem, ...]
    metrics: tuple[tuple[str, str, str, str], ...]
    backend_details: tuple[tuple[str, str, str], ...]
    advanced_details: tuple[tuple[str, str], ...]
    truth_source_notes: tuple[str, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    signature: tuple[object, ...]


def build_recorder_command_model(
    *,
    route_key: str,
    state: AppState | None = None,
    settings: FlightRecorderSettings | None = None,
    recorder_state: RecorderState | None = None,
    capture_backend: CaptureBackend | None = None,
    capabilities: CaptureBackendCapabilities | None = None,
    artifacts: Iterable[ClipMetadata] | None = None,
) -> RecorderCommandModel:
    settings = settings or FlightRecorderSettings.defaults()
    recorder_state = recorder_state or RecorderState.default()
    capture_backend = capture_backend or MissingCaptureBackend()
    capabilities = capabilities or capture_backend.capabilities()
    artifact_items = _artifact_items(
        tuple(artifacts) if artifacts is not None else _scan_artifacts(settings.destination_folder)
    )
    real_capture = bool(capabilities.real_capture_supported)
    frame_capture = bool(capabilities.frame_capture_available)
    encoding = bool(capabilities.video_encoding_available)
    hindsight_video = bool(getattr(settings, "hindsight_video_buffer_available", False))
    simulated_artifact = bool(capabilities.simulated_artifact_available or capabilities.simulated_capture_supported)
    metadata_review = True
    has_real_video_artifact = any(item.media_label == "Real recording" for item in artifact_items)
    overall_label = _overall_label(real_capture=real_capture, simulated_artifact=simulated_artifact)
    status_label = recorder_state.status_label
    short_explanation = _short_explanation(
        real_capture=real_capture,
        frame_capture=frame_capture,
        encoding=encoding,
        simulated_artifact=simulated_artifact,
        artifact_count=len(artifact_items),
    )
    actions = _actions(real_capture=real_capture, hindsight_video=hindsight_video, artifact_count=len(artifact_items))
    capability_items = _capabilities(
        capabilities=capabilities,
        frame_capture=frame_capture,
        encoding=encoding,
        hindsight_video=hindsight_video,
        simulated_artifact=simulated_artifact,
        metadata_review=metadata_review,
    )
    metrics = (
        ("Artifacts", str(len(artifact_items)), "clip metadata rows indexed", "info" if artifact_items else "unavailable"),
        ("Backend", _backend_label(capabilities), "existing recorder backend state", _role(capabilities.dependency_available)),
        ("Frame capture", "available" if frame_capture else "unavailable", "does not start capture", _role(frame_capture)),
        ("Encoding", "available" if encoding else "unavailable", "no video export claim without proof", _role(encoding)),
        (
            "Artifact mode",
            "metadata-only" if not has_real_video_artifact else "verified clip metadata",
            "metadata is not a recording",
            "info",
        ),
    )
    backend_details = _backend_details(capabilities)
    advanced_details = _advanced_details(
        state=state,
        settings=settings,
        recorder_state=recorder_state,
        capabilities=capabilities,
        artifacts=artifact_items,
    )
    notes = (
        "Recorder pages read existing recorder/backend state only.",
        "Metadata-only artifact review is not real recording.",
        "Output proof unchanged",
        "No live hardware action is launched from this Liquid page.",
    )
    signature = (
        route_key,
        overall_label,
        status_label,
        capabilities.backend_name,
        capabilities.backend_kind,
        real_capture,
        frame_capture,
        encoding,
        hindsight_video,
        tuple((artifact.artifact_id, artifact.media_label, artifact.playback_label) for artifact in artifact_items),
        state.runtime.header_truth_label if state is not None else "",
    )
    return RecorderCommandModel(
        route_key=route_key,
        page_title=_title_for_route(route_key),
        page_question=_question_for_route(route_key),
        overall_label=overall_label,
        status_label=status_label,
        short_explanation=short_explanation,
        next_step=_next_step(real_capture=real_capture, simulated_artifact=simulated_artifact),
        backend_name=capabilities.backend_name,
        backend_kind=capabilities.backend_kind,
        real_capture_supported=real_capture,
        frame_capture_available=frame_capture,
        encoding_available=encoding,
        hindsight_video_available=hindsight_video,
        simulated_artifact_supported=simulated_artifact,
        metadata_review_available=metadata_review,
        capabilities=capability_items,
        actions=actions,
        artifacts=artifact_items,
        metrics=metrics,
        backend_details=backend_details,
        advanced_details=advanced_details,
        truth_source_notes=notes,
        warnings=_dedupe(tuple(capabilities.warnings)),
        errors=_dedupe(tuple(capabilities.errors)),
        signature=signature,
    )


def _scan_artifacts(destination_folder: Path) -> tuple[ClipMetadata, ...]:
    try:
        return ClipLibrary(destination_folder).scan()
    except OSError:
        return ()


def _artifact_items(clips: tuple[ClipMetadata, ...]) -> tuple[RecorderArtifactItem, ...]:
    items: list[RecorderArtifactItem] = []
    for index, clip in enumerate(clips):
        has_verified_video = bool(clip.encoded_clip is not None and clip.has_video)
        metadata_only = not has_verified_video
        media_label = "Real recording" if has_verified_video else "Metadata-only artifact"
        playback_label = "Playback unavailable" if metadata_only else "Playable file metadata present"
        export_label = "Export unavailable" if metadata_only else "Export metadata present"
        title = clip.display_name or clip.clip or f"Artifact {index + 1}"
        warning = (
            "Metadata-only artifact; not a recording."
            if metadata_only
            else "Playable claim comes only from existing encoded-clip verification."
        )
        items.append(
            RecorderArtifactItem(
                artifact_id=f"artifact:{index}",
                title=title,
                created_label=clip.recorded or "Unavailable",
                duration_label=clip.duration or "Unavailable",
                source_label=clip.overlay_source or "Final output",
                media_label=media_label,
                playback_label=playback_label,
                export_label=export_label,
                path_label=str(clip.path),
                state_role="info" if metadata_only else "ready",
                warning=warning,
            )
        )
    return tuple(items)


def _capabilities(
    *,
    capabilities: CaptureBackendCapabilities,
    frame_capture: bool,
    encoding: bool,
    hindsight_video: bool,
    simulated_artifact: bool,
    metadata_review: bool,
) -> tuple[RecorderCapabilityItem, ...]:
    backend_label = "Capture backend unavailable"
    if capabilities.backend_kind == "candidate":
        backend_label = "Candidate backend unavailable" if not capabilities.real_capture_supported else "Candidate still-frame proof only"
    elif capabilities.backend_kind == "simulated":
        backend_label = "Simulated metadata backend"
    elif capabilities.backend_kind == "test":
        backend_label = "Test backend"
    return (
        RecorderCapabilityItem(backend_label, _role(capabilities.dependency_available), capabilities.backend_name),
        RecorderCapabilityItem(
            "Frame capture available" if frame_capture else "Frame capture unavailable",
            _role(frame_capture),
            "No capture is started by the Liquid page.",
        ),
        RecorderCapabilityItem(
            "Encoding available" if encoding else "Encoding unavailable",
            _role(encoding),
            "Playable/export claims require existing encoder proof.",
        ),
        RecorderCapabilityItem(
            "Hindsight video available" if hindsight_video else "Hindsight video unavailable",
            _role(hindsight_video),
            "Telemetry hindsight is separate from video hindsight.",
        ),
        RecorderCapabilityItem(
            "Metadata-only artifacts available" if simulated_artifact else "Metadata-only artifact review",
            "info" if metadata_review else "unavailable",
            "Clip metadata can be reviewed without claiming video capture.",
        ),
    )


def _actions(*, real_capture: bool, hindsight_video: bool, artifact_count: int) -> tuple[RecorderActionItem, ...]:
    return (
        RecorderActionItem(
            "record_now",
            "Record Now",
            real_capture,
            "ready" if real_capture else "unavailable",
            "Requires existing real capture support." if not real_capture else "Existing backend reports real capture support.",
        ),
        RecorderActionItem(
            "save_last_clip",
            "Save Last Clip",
            hindsight_video,
            "ready" if hindsight_video else "unavailable",
            "Requires existing hindsight video buffer." if not hindsight_video else "Existing video buffer reports available.",
        ),
        RecorderActionItem(
            "review_artifacts",
            "Review artifact metadata",
            artifact_count > 0,
            "info" if artifact_count > 0 else "unavailable",
            "Available when recorder metadata artifacts exist.",
        ),
    )


def _backend_details(capabilities: CaptureBackendCapabilities) -> tuple[tuple[str, str, str], ...]:
    return (
        ("Backend name", capabilities.backend_name, "info"),
        ("Backend kind", capabilities.backend_kind, "info"),
        ("Dependency", "Dependency available" if capabilities.dependency_available else "Dependency unavailable", _role(capabilities.dependency_available)),
        ("Screen capture", "Screen capture available" if capabilities.screen_capture_available else "Screen capture unavailable", _role(capabilities.screen_capture_available)),
        ("Frame capture", "Frame capture available" if capabilities.frame_capture_available else "Frame capture unavailable", _role(capabilities.frame_capture_available)),
        ("Cursor capture", "Cursor capture available" if capabilities.cursor_capture_available else "Cursor capture unavailable", _role(capabilities.cursor_capture_available)),
        (
            "Display enumeration",
            "Display enumeration available" if capabilities.display_enumeration_available else "Display enumeration unavailable",
            _role(capabilities.display_enumeration_available),
        ),
        ("Real capture", "Real capture supported" if capabilities.real_capture_supported else "Real capture unavailable", _role(capabilities.real_capture_supported)),
        (
            "Simulated capture",
            "Simulated artifact supported" if capabilities.simulated_artifact_available else "Simulated artifact unavailable",
            "info" if capabilities.simulated_artifact_available else "unavailable",
        ),
        ("Admin requirement", "Requires admin" if capabilities.requires_admin else "No admin requirement", "warning" if capabilities.requires_admin else "info"),
        ("Game injection", "Uses game injection" if capabilities.uses_game_injection else "No game injection", "warning" if capabilities.uses_game_injection else "info"),
        ("Graphics hooking", "Uses graphics hooking" if capabilities.uses_graphics_hooking else "No graphics hooking", "warning" if capabilities.uses_graphics_hooking else "info"),
        ("Encoding", "Encoding available" if capabilities.video_encoding_available else "Encoding unavailable", _role(capabilities.video_encoding_available)),
    )


def _advanced_details(
    *,
    state: AppState | None,
    settings: FlightRecorderSettings,
    recorder_state: RecorderState,
    capabilities: CaptureBackendCapabilities,
    artifacts: tuple[RecorderArtifactItem, ...],
) -> tuple[tuple[str, str], ...]:
    runtime_truth = state.runtime.header_truth_label if state is not None else "Runtime state unavailable"
    return (
        ("Route", "Recorder truth surface"),
        ("Runtime truth", runtime_truth),
        ("Recorder state", recorder_state.status_label),
        ("Recorder message", recorder_state.message),
        ("Destination", str(settings.destination_folder)),
        ("Hotkey registration", "registered" if settings.hotkey_registered else "not registered"),
        ("Capture source", settings.capture_source),
        ("Display", settings.display_label),
        ("Backend raw kind", capabilities.backend_kind),
        ("Warnings", "; ".join(capabilities.warnings) if capabilities.warnings else "None"),
        ("Errors", "; ".join(capabilities.errors) if capabilities.errors else "None"),
        ("Artifact count", str(len(artifacts))),
    )


def _overall_label(*, real_capture: bool, simulated_artifact: bool) -> str:
    if real_capture:
        return "Recorder capture capability reported"
    if simulated_artifact:
        return "Metadata-only artifacts available"
    return "Real recording unavailable"


def _short_explanation(
    *,
    real_capture: bool,
    frame_capture: bool,
    encoding: bool,
    simulated_artifact: bool,
    artifact_count: int,
) -> str:
    if real_capture and encoding:
        return "Existing backend and encoder report capability; this page still does not start capture."
    if simulated_artifact:
        return "Recorder can work with metadata-only artifacts; no desktop frames or video encoding are claimed here."
    if artifact_count:
        return "Artifact metadata can be reviewed, but real capture, buffering, and video export are unavailable."
    if frame_capture:
        return "A recorder capture seam reports limited frame capability; video recording and encoding remain unclaimed."
    return "Capture backend and encoding are unavailable; the page remains a read-only truth surface."


def _next_step(*, real_capture: bool, simulated_artifact: bool) -> str:
    if real_capture:
        return "Use existing recorder controls only where backend proof explicitly enables them."
    if simulated_artifact:
        return "Review metadata artifacts; do not treat them as video clips."
    return "Keep recorder actions disabled until a verified backend exists."


def _title_for_route(route_key: str) -> str:
    return {
        "recorder.flight_recorder": "Flight Recorder",
        "recorder.clip_library": "Clip Library / Artifacts",
        "recorder.capture_backend_truth": "Capture Backend Truth",
    }.get(route_key, "Recorder")


def _question_for_route(route_key: str) -> str:
    return {
        "recorder.flight_recorder": "What can I capture, buffer, and review?",
        "recorder.clip_library": "What metadata-only artifacts are available for review?",
        "recorder.capture_backend_truth": "What can I capture, buffer, and review?",
    }.get(route_key, "What can I capture, buffer, and review?")


def _backend_label(capabilities: CaptureBackendCapabilities) -> str:
    if capabilities.backend_kind == "candidate":
        return "candidate"
    if capabilities.backend_kind == "simulated":
        return "metadata"
    if capabilities.backend_kind == "test":
        return "test"
    return "missing"


def _role(value: bool) -> str:
    return "ready" if bool(value) else "unavailable"


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return tuple(result)
