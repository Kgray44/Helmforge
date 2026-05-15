from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QSizePolicy, QWidget

from v3_app.liquid.components import (
    LiquidAdvancedSection,
    LiquidDetailPanel,
    LiquidHeroPanel,
    LiquidInspectorPanel,
    LiquidPage,
    LiquidPageHeader,
    LiquidStatusRail,
)
from v3_app.liquid.flow_components import ChecklistPanel
from v3_app.liquid.glass import action_button, glass_panel, mark_action_feedback
from v3_app.liquid.instruments import CapabilityRail
from v3_app.liquid.layout import grid_layout, horizontal_layout, vertical_layout
from v3_app.liquid.motion import apply_interactive_card_motion
from v3_app.liquid.models.recorder_command_model import (
    RecorderActionItem,
    RecorderArtifactItem,
    RecorderCommandModel,
    build_recorder_command_model,
)
from v3_app.liquid.status_components import MetricTile, StatusChip, TruthBadge
from v3_app.recorder.capture_backend import CaptureBackend
from v3_app.recorder.clip_library import ClipMetadata
from v3_app.recorder.recorder_settings import FlightRecorderSettings
from v3_app.recorder.recorder_state import RecorderState
from v3_app.services.app_state import AppState

RouteCallback = Callable[[str], None]


class RecorderCommandPage(LiquidPage):
    def __init__(
        self,
        *,
        route_key: str,
        state: AppState | None = None,
        settings: FlightRecorderSettings | None = None,
        recorder_state: RecorderState | None = None,
        capture_backend: CaptureBackend | None = None,
        artifacts: tuple[ClipMetadata, ...] | None = None,
        on_route_requested: RouteCallback | None = None,
    ) -> None:
        self.route_key = route_key
        self._state = state
        self._settings = settings
        self._recorder_state = recorder_state
        self._capture_backend = capture_backend
        self._artifacts = artifacts
        self._on_route_requested = on_route_requested
        self._last_signature: tuple[object, ...] | None = None
        self.render_count = 0
        self.model = self._build_model()
        super().__init__(
            title=self.model.page_title,
            subtitle=self.model.page_question,
            helper_text="RECORDER COMMAND",
            object_name="liquidRecorderCommandPage",
        )
        self.setProperty("routeKey", route_key)
        self.setProperty("modeId", "recorder")
        self.setProperty("lcdPhase", "LCD-8")
        self.setProperty("recorderTruthSurface", True)
        self.setProperty("recorderTimelineSweepEnabled", False)
        self.setProperty("recorderTimelineStatus", "deferred_metadata_only")
        self.setProperty("recorderMotionClaimsCapture", False)
        self.setProperty("recorderMotionChangesEncoding", False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._render(force=True)

    def _build_model(self) -> RecorderCommandModel:
        return build_recorder_command_model(
            route_key=self.route_key,
            state=self._state,
            settings=self._settings,
            recorder_state=self._recorder_state,
            capture_backend=self._capture_backend,
            artifacts=self._artifacts,
        )

    def update_recorder_model(
        self,
        *,
        state: AppState | None = None,
        settings: FlightRecorderSettings | None = None,
        recorder_state: RecorderState | None = None,
        capture_backend: CaptureBackend | None = None,
        artifacts: tuple[ClipMetadata, ...] | None = None,
    ) -> None:
        if state is not None:
            self._state = state
        if settings is not None:
            self._settings = settings
        if recorder_state is not None:
            self._recorder_state = recorder_state
        if capture_backend is not None:
            self._capture_backend = capture_backend
        if artifacts is not None:
            self._artifacts = artifacts
        previous = self.model.signature
        self.model = self._build_model()
        if self.model.signature != previous:
            self._render()

    def _render(self, *, force: bool = False) -> None:
        if not force and self.model.signature == self._last_signature:
            return
        self._last_signature = self.model.signature
        self.render_count += 1
        self.set_header(_header(self.model))
        self.set_status_rail(_status_rail(self.model))
        if self.route_key == "recorder.clip_library":
            self._render_clip_library()
        elif self.route_key == "recorder.capture_backend_truth":
            self._render_backend_truth()
        else:
            self._render_flight_recorder()
        self.set_advanced(_advanced_details(self.model))

    def _render_flight_recorder(self) -> None:
        self.set_hero(_status_hero(self.model, on_route_requested=self._on_route_requested))
        self.set_inspector(_capability_panel(self.model))
        self.set_detail(_action_panel(self.model, self._on_route_requested))

    def _render_clip_library(self) -> None:
        self.set_hero(
            _status_hero(
                self.model,
                body="Artifact review is metadata-first. Playback and export stay unavailable unless existing proof supports them.",
                on_route_requested=self._on_route_requested,
            )
        )
        self.set_inspector(_clip_library_panel(self.model))
        self.set_detail(_artifact_inspector(self.model))

    def _render_backend_truth(self) -> None:
        self.set_hero(
            _status_hero(
                self.model,
                body="Backend capability fields are read-only and do not start capture, buffering, or encoding.",
                on_route_requested=self._on_route_requested,
            )
        )
        self.set_inspector(_backend_truth_panel(self.model))
        self.set_detail(_backend_checklist(self.model))


def create_flight_recorder_page(**kwargs) -> RecorderCommandPage:
    return RecorderCommandPage(route_key="recorder.flight_recorder", **kwargs)


def create_clip_library_page(**kwargs) -> RecorderCommandPage:
    return RecorderCommandPage(route_key="recorder.clip_library", **kwargs)


def create_capture_backend_truth_page(**kwargs) -> RecorderCommandPage:
    return RecorderCommandPage(route_key="recorder.capture_backend_truth", **kwargs)


def _header(model: RecorderCommandModel) -> LiquidPageHeader:
    header = LiquidPageHeader(
        model.page_title,
        model.page_question,
        kicker="RECORDER COMMAND",
        object_name="liquidRecorderPageHeader",
    )
    header.setProperty("routeKey", model.route_key)
    return header


def _status_rail(model: RecorderCommandModel) -> LiquidStatusRail:
    rail = LiquidStatusRail(
        items=(
            (model.overall_label, "unavailable" if not model.real_capture_supported else "ready"),
            ("Metadata-only artifacts available", "info"),
            ("Output proof unchanged", "simulation"),
        ),
        object_name="liquidRecorderStatusRail",
    )
    return rail


def _status_hero(
    model: RecorderCommandModel,
    *,
    body: str | None = None,
    on_route_requested: RouteCallback | None = None,
) -> LiquidHeroPanel:
    hero = LiquidHeroPanel(
        model.overall_label,
        body or model.short_explanation,
        object_name="liquidRecorderStatusHero",
        state_role="ready" if model.real_capture_supported else "unavailable",
        minimum_height=250,
    )
    hero.setProperty("recorderStatusHero", True)
    layout = hero.layout()
    if layout is None:
        return hero
    chip_row = horizontal_layout(spacing=8)
    chip_row.addWidget(TruthBadge(model.status_label, state_role="info", helper_text=model.next_step))
    chip_row.addWidget(TruthBadge("Metadata-only artifacts available", state_role="info", helper_text="Metadata is not a real recording."))
    chip_row.addWidget(TruthBadge("Output proof unchanged", state_role="simulation", helper_text="Recorder state does not verify vJoy output."))
    layout.addLayout(chip_row)
    metrics = CapabilityRail(
        capabilities=tuple((label, role, caption) for label, value, caption, role in model.metrics[:4]),
        object_name="liquidRecorderCapabilityRail",
    )
    layout.addWidget(metrics)
    layout.addWidget(_recorder_command_actions(model, on_route_requested))
    return hero


def _recorder_command_actions(model: RecorderCommandModel, on_route_requested: RouteCallback | None) -> QFrame:
    actions = glass_panel("liquidRecorderCommandActions", role="liquid_recorder_command_actions")
    actions.setProperty("componentRole", "RecorderCommandActions")
    actions.setProperty("pageActionCluster", True)
    layout = horizontal_layout(actions, margins=(0, 6, 0, 2), spacing=8)
    layout.addWidget(_copy_button("Copy recorder status", "liquidRecorderCopyStatusButton", _recorder_status_text(model)))
    for label, route_key, object_name in (
        ("Open Capture Backend Truth", "recorder.capture_backend_truth", "liquidRecorderOpenBackendTruthButton"),
        ("Open Clip Library", "recorder.clip_library", "liquidRecorderOpenClipLibraryButton"),
        ("Open Flight Recorder", "recorder.flight_recorder", "liquidRecorderOpenFlightRecorderButton"),
    ):
        if route_key != model.route_key:
            layout.addWidget(_navigation_button(label, route_key, object_name, on_route_requested))
    layout.addStretch(1)
    return actions


def _capability_panel(model: RecorderCommandModel) -> LiquidInspectorPanel:
    panel = LiquidInspectorPanel(
        "Capture / Buffer / Encoding",
        "Recorder capability truth from existing recorder backend state.",
        object_name="liquidRecorderCapabilityPanel",
        state_role="info",
    )
    layout = panel.layout()
    if layout is None:
        return panel
    for capability in model.capabilities:
        layout.addWidget(TruthBadge(capability.label, state_role=capability.state_role, helper_text=capability.detail))
    return panel


def _action_panel(model: RecorderCommandModel, on_route_requested: RouteCallback | None) -> LiquidDetailPanel:
    panel = LiquidDetailPanel(
        "Recorder Actions",
        "Unavailable controls stay disabled. This page does not start capture or write video.",
        object_name="liquidRecorderActionPanel",
        state_role="info",
    )
    layout = panel.layout()
    if layout is None:
        return panel
    for action in model.actions:
        layout.addWidget(_action_row(action, on_route_requested))
    layout.addWidget(
        ChecklistPanel(
            "Recorder truth checklist",
            items=(
                ("Real recording", "done" if model.real_capture_supported else "unavailable", "Existing backend must report support."),
                ("Frame capture", "done" if model.frame_capture_available else "unavailable", "No frame polling is started here."),
                ("Encoding", "done" if model.encoding_available else "unavailable", "No video export claim without proof."),
                ("Hindsight video", "done" if model.hindsight_video_available else "unavailable", "Telemetry hindsight is separate."),
            ),
            object_name="liquidRecorderTruthChecklist",
        )
    )
    return panel


def _action_row(action: RecorderActionItem, on_route_requested: RouteCallback | None) -> QFrame:
    row = glass_panel(f"liquidRecorderAction_{action.action_id}", role="liquid_recorder_action_row")
    row.setProperty("recorderAction", True)
    apply_interactive_card_motion(row)
    layout = horizontal_layout(row, margins=(12, 9, 12, 9), spacing=8)
    route_target = "recorder.clip_library" if action.action_id == "review_artifacts" else ""
    is_navigation = bool(route_target and action.enabled and on_route_requested is not None)
    disabled_reason = action.reason
    if action.action_id in {"record_now", "save_last_clip"} and action.enabled:
        disabled_reason = "Disabled: Liquid recorder buttons do not start capture or save video without an existing safe controller callback."
    elif action.action_id == "review_artifacts" and action.enabled and on_route_requested is None:
        disabled_reason = "Disabled: artifact review navigation callback unavailable in this context."
    button = action_button(
        action.label,
        object_name=_action_object_name(action.action_id),
        enabled=is_navigation,
        action_kind="navigation" if is_navigation else "disabled_deferred",
        disabled_reason=disabled_reason if not is_navigation else "",
        route_target=route_target or None,
    )
    button.setProperty("recorderActionId", action.action_id)
    button.setToolTip(
        f"Navigate to {route_target}. This does not start capture or encode video."
        if is_navigation
        else disabled_reason
    )
    button.setStatusTip(button.toolTip())
    button.setAccessibleDescription(button.toolTip())
    if is_navigation and on_route_requested is not None:
        button.clicked.connect(lambda _checked=False, target=route_target: on_route_requested(target))
    layout.addWidget(button)
    layout.addWidget(StatusChip("Available" if is_navigation else "Unavailable", state_role=action.state_role))
    reason = QLabel(button.toolTip())
    reason.setWordWrap(True)
    reason.setObjectName("liquidRecorderActionReason")
    layout.addWidget(reason, 1)
    return row


def _navigation_button(
    text: str,
    route_key: str,
    object_name: str,
    on_route_requested: RouteCallback | None,
) -> QPushButton:
    reason = f"Navigate to {route_key}. This does not start capture, encode video, or change runtime state."
    if on_route_requested is None:
        reason = f"Disabled: {reason} Navigation callback unavailable in this context."
    button = action_button(
        text,
        object_name=object_name,
        enabled=on_route_requested is not None,
        action_kind="navigation",
        disabled_reason=reason if on_route_requested is None else "",
        route_target=route_key,
    )
    button.setProperty("navigationOnly", True)
    button.setToolTip(reason)
    button.setStatusTip(reason)
    button.setAccessibleDescription(reason)
    if on_route_requested is not None:
        button.clicked.connect(lambda _checked=False, target=route_key: on_route_requested(target))
    return button


def _copy_button(text: str, object_name: str, payload: str) -> QPushButton:
    button = action_button(text, object_name=object_name, enabled=True, action_kind="copy")
    button.setProperty("copyOnly", True)
    button.setToolTip("Copy Recorder information to the clipboard. This does not start capture or change runtime state.")
    button.setStatusTip(button.toolTip())
    button.setAccessibleDescription(button.toolTip())
    button.clicked.connect(lambda _checked=False, data=payload, target=button: _copy_to_clipboard(data, target))
    return button


def _copy_to_clipboard(text: str, button: QPushButton | None = None) -> None:
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)
        if button is not None:
            mark_action_feedback(button, "Copied recorder information to clipboard.")
    elif button is not None:
        mark_action_feedback(button, "Clipboard unavailable; nothing was copied.")


def _recorder_status_text(model: RecorderCommandModel) -> str:
    lines = [
        f"Route: {model.route_key}",
        f"Overall: {model.overall_label}",
        f"Backend: {model.backend_name} ({model.backend_kind})",
        f"Real capture supported: {model.real_capture_supported}",
        f"Frame capture available: {model.frame_capture_available}",
        f"Encoding available: {model.encoding_available}",
        f"Hindsight video available: {model.hindsight_video_available}",
        "Recorder copy action does not start capture, encode video, or verify output.",
    ]
    lines.extend(f"{label}: {value} - {caption}" for label, value, caption, _role in model.metrics)
    return "\n".join(lines)


def _clip_library_panel(model: RecorderCommandModel) -> LiquidInspectorPanel:
    panel = LiquidInspectorPanel(
        "Clip Metadata",
        "Artifact cards distinguish metadata-only manifests from verified playable files.",
        object_name="liquidRecorderClipLibraryPanel",
        state_role="info",
        minimum_height=320,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    layout.addWidget(StatusChip("Clip metadata", state_role="info"))
    if not model.artifacts:
        layout.addWidget(TruthBadge("No recorder artifacts yet", state_role="unavailable", helper_text="Metadata-only artifacts will appear here after existing recorder actions create them."))
        return panel
    for artifact in model.artifacts:
        layout.addWidget(_artifact_card(artifact))
    return panel


def _artifact_card(artifact: RecorderArtifactItem) -> QFrame:
    card = glass_panel(f"liquidRecorderArtifact_{_safe(artifact.artifact_id)}", role="liquid_recorder_artifact_card")
    card.setProperty("recorderArtifactCard", True)
    apply_interactive_card_motion(card)
    layout = vertical_layout(card, margins=(12, 10, 12, 10), spacing=7)
    title = QLabel(artifact.title)
    title.setObjectName("liquidRecorderArtifactTitle")
    title.setWordWrap(True)
    layout.addWidget(title)
    for label, value, role in (
        ("Media", artifact.media_label, artifact.state_role),
        ("Created", artifact.created_label, "info"),
        ("Duration", artifact.duration_label, "info"),
        ("Source", artifact.source_label, "info"),
        ("Playback", artifact.playback_label, "unavailable" if "unavailable" in artifact.playback_label.casefold() else "ready"),
        ("Export", artifact.export_label, "unavailable" if "unavailable" in artifact.export_label.casefold() else "ready"),
    ):
        layout.addWidget(_detail_row(label, value, role))
    layout.addWidget(TruthBadge(artifact.warning, state_role=artifact.state_role))
    return card


def _artifact_inspector(model: RecorderCommandModel) -> LiquidDetailPanel:
    panel = LiquidDetailPanel(
        "Selected Artifact Truth",
        "No playable preview or export is claimed from metadata-only artifacts.",
        object_name="liquidRecorderArtifactInspector",
        state_role="info",
    )
    layout = panel.layout()
    if layout is None:
        return panel
    selected = model.artifacts[0] if model.artifacts else None
    if selected is None:
        layout.addWidget(TruthBadge("Empty artifact library", state_role="unavailable", helper_text="Real recording unavailable."))
        return panel
    for label, value, role in (
        ("Artifact", selected.title, selected.state_role),
        ("Type", selected.media_label, selected.state_role),
        ("Path", selected.path_label, "info"),
        ("Playback", selected.playback_label, "unavailable"),
        ("Export", selected.export_label, "unavailable"),
        ("Recorder truth", "Real recording unavailable" if selected.media_label != "Real recording" else "Existing encoded clip metadata", selected.state_role),
    ):
        layout.addWidget(_detail_row(label, value, role))
    return panel


def _backend_truth_panel(model: RecorderCommandModel) -> LiquidInspectorPanel:
    panel = LiquidInspectorPanel(
        "Backend Capability Fields",
        "The normal recorder page summarizes capability; this panel shows the backend truth fields.",
        object_name="liquidRecorderBackendTruthPanel",
        state_role="info",
        minimum_height=330,
    )
    layout = panel.layout()
    if layout is None:
        return panel
    for label, value, role in model.backend_details:
        layout.addWidget(_detail_row(label, value, role))
    return panel


def _backend_checklist(model: RecorderCommandModel) -> LiquidDetailPanel:
    panel = LiquidDetailPanel(
        "Backend Boundaries",
        "Unavailable and intentionally deferred paths stay explicit.",
        object_name="liquidRecorderBackendChecklist",
        state_role="info",
    )
    layout = panel.layout()
    if layout is None:
        return panel
    layout.addWidget(
        ChecklistPanel(
            "Backend capability checklist",
            items=(
                ("Dependency", "done" if any(value == "Dependency available" for _, value, _ in model.backend_details) else "unavailable", "Existing backend dependency state."),
                ("No game injection", "done", "Recorder pages do not add game injection."),
                ("No graphics hooking", "done", "Recorder pages do not add graphics API hooks."),
                ("Encoding", "done" if model.encoding_available else "unavailable", "Existing encoder capability only."),
                ("Real capture", "done" if model.real_capture_supported else "unavailable", "Existing backend capability only."),
            ),
            object_name="liquidRecorderBackendCapabilityChecklist",
        )
    )
    for warning in model.warnings:
        layout.addWidget(StatusChip(warning, state_role="warning"))
    for error in model.errors:
        layout.addWidget(StatusChip(error, state_role="unavailable"))
    return panel


def _advanced_details(model: RecorderCommandModel) -> LiquidAdvancedSection:
    panel = LiquidAdvancedSection(
        "Advanced Recorder Details",
        "Compact raw recorder details. These do not dominate the normal command answer.",
        object_name="liquidRecorderAdvancedDetails",
        state_role="info",
    )
    panel.setProperty("advancedSecondary", True)
    panel.setProperty("visualWeight", "subdued")
    layout = panel.layout()
    if layout is None:
        return panel
    grid = glass_panel("liquidRecorderAdvancedGrid", role="liquid_recorder_advanced_grid")
    grid_layout_ = grid_layout(grid, margins=(12, 10, 12, 10), spacing=8)
    for index, (label, value) in enumerate(model.advanced_details):
        grid_layout_.addWidget(_compact_cell(label, value), index // 2, index % 2)
    layout.addWidget(grid)
    for note in model.truth_source_notes:
        layout.addWidget(TruthBadge(note, state_role="simulation"))
    return panel


def _detail_row(label_text: str, value_text: str, role: str) -> QFrame:
    row = glass_panel(f"liquidRecorderDetail_{_safe(label_text)}", role="liquid_recorder_detail_row")
    row.setProperty("componentRole", "RecorderDetailRow")
    row.setProperty("statusRole", role)
    layout = horizontal_layout(row, margins=(10, 7, 10, 7), spacing=8)
    label = QLabel(label_text)
    label.setObjectName("liquidRecorderDetailLabel")
    value = QLabel(value_text)
    value.setObjectName("liquidRecorderDetailValue")
    value.setWordWrap(True)
    layout.addWidget(label, 1)
    layout.addWidget(StatusChip(value_text, state_role=role), 2)
    return row


def _compact_cell(label_text: str, value_text: str) -> QFrame:
    cell = glass_panel(f"liquidRecorderAdvancedCell_{_safe(label_text)}", role="liquid_recorder_advanced_cell")
    layout = vertical_layout(cell, margins=(8, 6, 8, 6), spacing=4)
    label = QLabel(label_text)
    label.setObjectName("liquidRecorderAdvancedLabel")
    value = QLabel(value_text)
    value.setObjectName("liquidRecorderAdvancedValue")
    value.setWordWrap(True)
    layout.addWidget(label)
    layout.addWidget(value)
    return cell


def _action_object_name(action_id: str) -> str:
    return {
        "record_now": "liquidRecorderRecordNowButton",
        "save_last_clip": "liquidRecorderSaveLastClipButton",
        "review_artifacts": "liquidRecorderReviewArtifactsButton",
    }.get(action_id, f"liquidRecorderActionButton_{_safe(action_id)}")


def _safe(text: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in text).strip("_").lower()
