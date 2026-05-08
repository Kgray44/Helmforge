from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from v3_app.pages.page_helpers import (
    add_card_to_grid,
    apply_parameter_metadata,
    card,
    card_header,
    card_layout,
    page_intro,
    parameter_label,
)
from v3_app.recorder.clip_library import ClipLibrary
from v3_app.recorder.recorder_controller import FlightRecorderController
from v3_app.recorder.recorder_settings import FlightRecorderSettings
from v3_app.recorder.recorder_state import RecorderState
from v3_app.services.app_state import AppState
from v3_app.ui.status_chips import action_button, status_chip


class FlightRecorderPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        settings: FlightRecorderSettings | None = None,
        recorder_state: RecorderState | None = None,
        recorder_controller: FlightRecorderController | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("flightRecorderPage")
        self._state = state
        self._workspace = workspace
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self.controller = recorder_controller or FlightRecorderController(settings=settings or FlightRecorderSettings.defaults())
        self.settings = self.controller.settings
        self.recorder_state = recorder_state or self.controller.state
        self.clip_library = ClipLibrary(self.settings.destination_folder)
        self._backend_status = self.controller.refresh_status()
        self._proof_availability = self.controller.one_frame_proof_availability()
        self._last_action_text = self.recorder_state.message

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)
        root.addWidget(
            page_intro(
                "Flight Recorder",
                "Inspect the recorder shell, simulated export metadata, and future time-matched axis overlay without claiming video capture.",
                "No video captured. No encoding performed. The hotkey text is configured but not registered, and recorder exports remain metadata-only until a real capture backend exists.",
            )
        )
        root.addWidget(self._status_card())
        root.addWidget(self._capture_proof_card())
        root.addWidget(self._review_card())

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        add_card_to_grid(grid, self._recorder_settings_card(), 0, 0)
        add_card_to_grid(grid, self._axis_overlay_card(), 0, 1)
        add_card_to_grid(grid, self._recording_library_card(), 1, 0)
        add_card_to_grid(grid, self._clip_preview_card(), 1, 1)
        root.addLayout(grid)
        root.addStretch(1)

    def _status_card(self) -> QWidget:
        frame = card("recorderStatusCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Recorder Status", "Truthful recorder state before capture and encoding backends exist."))
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(status_chip("UI Ready", tone="success", object_name="recorderUiReadyChip"))
        capabilities = self._backend_status.capabilities
        backend_label = _capture_backend_chip_label(capabilities)
        row.addWidget(status_chip(backend_label, tone="warning", object_name="recorderBackendChip"))
        row.addWidget(status_chip("Hotkey not registered", tone="warning", object_name="recorderHotkeyChip"))
        row.addWidget(status_chip(f"{self.settings.overlay_source} source", tone="neutral", object_name="recorderOverlaySourceChip"))
        row.addWidget(status_chip("Telemetry buffer available", tone="neutral", object_name="recorderTelemetryBufferChip"))
        row.addWidget(status_chip("Buffering unavailable", tone="warning", object_name="recorderVideoBufferChip"))
        row.addWidget(status_chip("Recording unavailable", tone="warning", object_name="recorderRecordingChip"))
        row.addStretch(1)
        layout.addLayout(row)
        summary = self.controller.build_status_summary()
        layout.addLayout(
            _row_grid(
                {
                    "Runtime truth": self._runtime_status.truth.value,
                    "Output verified": str(self._runtime_status.live_output_writes_verified).lower(),
                    "Full Live Runtime Ready": str(_full_live_runtime_ready(self._runtime_status)).lower(),
                    "Capture backend": summary["Capture backend"],
                    "Dependency status": summary["Dependency status"],
                    "Real capture supported": summary["Real capture supported"],
                    "Frame capture": summary["Frame capture"],
                    "One-frame proof": summary["One-frame proof"],
                    "Cursor capture": summary["Cursor capture"],
                    "Display enumeration": summary["Display enumeration"],
                    "Video encoding": summary["Video encoding"],
                    "Compositor": summary["Compositor"],
                    "Recorder mode": summary["Recorder mode"],
                    "Hotkey status": summary["Hotkey status"],
                    "Telemetry hindsight": summary["Telemetry hindsight"],
                    "Video hindsight": summary["Video hindsight"],
                    "Hindsight video buffering": "unavailable",
                }
            )
        )
        layout.addWidget(
            _body(
                "Telemetry hindsight buffer available. Video hindsight buffering is not implemented yet. "
                "Video hindsight unavailable. Video encoding unavailable. "
                "Save Last Clip cannot save real video until capture and buffer backends exist. "
                "Simulated exports contain telemetry and overlay metadata only."
            )
        )
        self.action_status = QLabel(self._last_action_text)
        self.action_status.setObjectName("recorderActionStatus")
        self.action_status.setWordWrap(True)
        layout.addWidget(self.action_status)
        return frame

    def _review_card(self) -> QWidget:
        frame = card("recorderReviewCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Recorder Review", "Session summary, timeline, and local export for recorder diagnostics."))
        self.review_summary = QLabel("No reviewed recorder session yet.\nSimulated/Workspace Only\nRuntime blocked until telemetry proves otherwise.")
        self.review_summary.setObjectName("recorderReviewSummary")
        self.review_summary.setWordWrap(True)
        layout.addWidget(self.review_summary)
        self.timeline_table = QTableWidget(0, 4)
        self.timeline_table.setObjectName("recorderTimelineTable")
        self.timeline_table.setHorizontalHeaderLabels(("When", "Channel", "Change", "Detail"))
        self.timeline_table.setFrameShape(QFrame.Shape.NoFrame)
        self.timeline_table.setMinimumHeight(128)
        layout.addWidget(self.timeline_table)
        controls = QHBoxLayout()
        self.review_session_button = action_button("Review Current Session", object_name="reviewCurrentSessionButton")
        self.review_session_button.clicked.connect(self.review_current_session)
        self.export_summary_button = action_button("Export Summary JSON", object_name="exportReviewSummaryJsonButton")
        self.export_summary_button.clicked.connect(self.export_review_summary_json)
        self.export_samples_button = action_button("Export Samples CSV", object_name="exportReviewSamplesCsvButton")
        self.export_samples_button.clicked.connect(self.export_review_samples_csv)
        self.clear_review_button = action_button("Clear Review", object_name="clearReviewSessionButton")
        self.clear_review_button.clicked.connect(self.clear_review_session)
        for button in (
            self.review_session_button,
            self.export_summary_button,
            self.export_samples_button,
            self.clear_review_button,
        ):
            controls.addWidget(button)
        controls.addStretch(1)
        layout.addLayout(controls)
        layout.addWidget(
            _body(
                "Review exports are local JSON/CSV diagnostics. They include source and runtime truth fields and are not video, output verification, or Full Live Runtime Ready proof."
            )
        )
        self._update_review_widgets()
        return frame

    def _capture_proof_card(self) -> QWidget:
        frame = card("recorderCaptureProofCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Capture Proof", "Explicit one-frame diagnostic only; no recording or encoder path is started."))
        self.capture_proof_summary = QLabel("")
        self.capture_proof_summary.setObjectName("recorderCaptureProofSummary")
        self.capture_proof_summary.setWordWrap(True)
        layout.addWidget(self.capture_proof_summary)
        controls = QHBoxLayout()
        self.try_one_frame_capture_button = action_button(
            "Try One-Frame Capture",
            object_name="tryOneFrameCaptureButton",
        )
        self.try_one_frame_capture_button.clicked.connect(self.try_one_frame_capture)
        controls.addWidget(self.try_one_frame_capture_button)
        controls.addStretch(1)
        layout.addLayout(controls)
        layout.addWidget(
            _body(
                "Still-frame proof. Not video recording. Not encoded. Not previewable video. "
                "No global hotkey registered. Capture proof is not Full Live Runtime Ready."
            )
        )
        self._update_capture_proof_widgets()
        return frame

    def _recorder_settings_card(self) -> QWidget:
        frame = card("recorderSettingsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Recorder Settings", "Settings are stored in-memory for this UI shell; no video files are written."))
        settings_rows = {
            "Destination": str(self.settings.destination_folder),
            "Length": f"{self.settings.length_seconds} s",
            "Frame Rate": f"{self.settings.frame_rate_fps} fps",
            "History": f"{self.settings.history_seconds:.2f} s",
            "Overlay Source": self.settings.overlay_source,
            "Capture Source": self.settings.capture_source,
            "Display": self.settings.display_label,
            "Hotkey": self.settings.hotkey,
            "Trigger Mode": self.settings.trigger_mode,
        }
        layout.addLayout(_row_grid(settings_rows, metadata_ids=_RECORDER_SETTINGS_METADATA))
        cursor = QCheckBox("Record the cursor")
        cursor.setObjectName("recordCursorCheckbox")
        apply_parameter_metadata(cursor, "flight_recorder.record_cursor")
        cursor.setChecked(self.settings.record_cursor)
        cursor.setEnabled(False)
        layout.addWidget(cursor)
        button_row = QHBoxLayout()
        browse = action_button("Browse", object_name="recorderBrowseButton")
        browse.setEnabled(False)
        open_folder = action_button("Open Folder", object_name="recorderOpenFolderButton")
        open_folder.setEnabled(False)
        real_capture_supported = self._backend_status.capabilities.real_capture_supported
        self.record_now_button = action_button("Record Now", object_name="recordNowButton")
        self.record_now_button.setEnabled(real_capture_supported)
        self.record_now_button.clicked.connect(self.record_now)
        self.save_last_clip_button = action_button("Save Last Clip", object_name="saveLastClipButton")
        self.save_last_clip_button.setEnabled(real_capture_supported and self.settings.hindsight_video_buffer_available)
        self.save_last_clip_button.clicked.connect(self.save_last_clip)
        for button in (browse, open_folder, self.record_now_button, self.save_last_clip_button):
            button_row.addWidget(button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        layout.addWidget(
            _body(
                f"{_capture_backend_chip_label(self._backend_status.capabilities)}. Video hindsight buffer not implemented yet. "
                "Recording backend is not active in this phase. Recording backend unavailable. "
                "Injected simulated backends can write metadata-only manifests or simulated export bundles for tests."
            )
        )
        return frame

    def _axis_overlay_card(self) -> QWidget:
        frame = card("recorderAxisOverlayCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Axis Overlay", "Shared telemetry colors for the future recorded overlay composite."))
        layout.addWidget(_body("Axis colors are shared with Live Overlay so live telemetry and future recordings stay consistent."))
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        for column, heading in enumerate(("Axis", "Include", "Color")):
            label = QLabel(heading)
            label.setObjectName("tableMutedText")
            grid.addWidget(label, 0, column)
        for row, (axis, axis_config) in enumerate(self.settings.axes.items(), start=1):
            axis_label = QLabel(axis)
            axis_label.setObjectName(f"recorderAxis_{_key(axis)}")
            include = QCheckBox("Include")
            include.setObjectName(f"recorderAxisInclude_{_key(axis)}")
            include.setChecked(axis_config.include)
            include.setEnabled(False)
            color = QLabel(axis_config.color)
            color.setObjectName(f"recorderAxisColor_{_key(axis)}")
            color.setProperty("uiRole", "statusChip")
            color.setProperty("chipTone", "neutral")
            grid.addWidget(axis_label, row, 0)
            grid.addWidget(include, row, 1)
            grid.addWidget(color, row, 2)
        layout.addLayout(grid)
        return frame

    def _recording_library_card(self) -> QWidget:
        frame = card("recordingLibraryCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Recording Library", "Metadata-only recorder artifact index for simulated exports."))
        controls = QHBoxLayout()
        sort = QComboBox()
        sort.setObjectName("recordingLibrarySortDropdown")
        sort.addItem("Newest First")
        apply_parameter_metadata(sort, "flight_recorder.library_sort")
        refresh = action_button("Refresh", object_name="recordingLibraryRefreshButton")
        refresh.clicked.connect(self.refresh_library)
        controls.addWidget(parameter_label("Sort", metadata_id="flight_recorder.library_sort"))
        controls.addWidget(sort)
        controls.addWidget(refresh)
        controls.addStretch(1)
        layout.addLayout(controls)
        self.library_table = QTableWidget(0, 4)
        self.library_table.setObjectName("recordingLibraryTable")
        self.library_table.setHorizontalHeaderLabels(("Artifact or Clip", "Created/Recorded", "Duration", "Opened"))
        self.library_table.setFrameShape(QFrame.Shape.NoFrame)
        self.library_table.setMinimumHeight(160)
        self.library_table.cellClicked.connect(lambda row, _column: self.show_library_item_preview(row))
        layout.addWidget(self.library_table)
        self.empty_library_label = QLabel(f"{self.clip_library.empty_state_title} {self.clip_library.empty_state_detail}")
        self.empty_library_label.setObjectName("recordingLibraryEmptyState")
        self.empty_library_label.setWordWrap(True)
        layout.addWidget(self.empty_library_label)
        self._populate_library()
        return frame

    def _clip_preview_card(self) -> QWidget:
        frame = card("clipPreviewCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Clip Preview", "Preview shell only; playback backend is deferred."))
        self.preview_status = QLabel(
            "Select a recorder artifact to preview.\n"
            "Metadata-only preview.\n"
            "No video captured.\n"
            "No encoding performed."
        )
        self.preview_status.setObjectName("clipPreviewUnavailableState")
        self.preview_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_status.setMinimumHeight(180)
        self.preview_status.setWordWrap(True)
        layout.addWidget(self.preview_status)
        controls = QHBoxLayout()
        play = action_button("Play", object_name="clipPreviewPlayButton")
        play.setEnabled(False)
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setObjectName("clipPreviewTimeline")
        self.timeline.setEnabled(False)
        time_label = QLabel("00:00 / 00:00")
        time_label.setObjectName("clipPreviewTimeIndicator")
        reveal = action_button("Reveal File", object_name="clipPreviewRevealButton")
        reveal.setEnabled(False)
        controls.addWidget(play)
        controls.addWidget(self.timeline, 1)
        controls.addWidget(time_label)
        controls.addWidget(reveal)
        layout.addLayout(controls)
        self.preview_metadata = QLabel("Filename: none | Overlay source: Final output | Resolution: Unavailable | Length: Unavailable")
        self.preview_metadata.setObjectName("clipPreviewMetadata")
        self.preview_metadata.setWordWrap(True)
        layout.addWidget(self.preview_metadata)
        return frame

    def _populate_library(self) -> None:
        self._library_clips = self.clip_library.scan()
        clips = self._library_clips
        self.library_table.setRowCount(len(clips))
        for row, clip in enumerate(clips):
            for column, value in enumerate((clip.clip, clip.recorded, clip.duration, clip.opened)):
                self.library_table.setItem(row, column, QTableWidgetItem(value))
        if clips:
            simulated_count = sum(1 for clip in clips if clip.is_simulated)
            if simulated_count:
                export_count = sum(1 for clip in clips if "Simulated export" in clip.clip)
                if export_count:
                    self.empty_library_label.setText(
                        f"{export_count} simulated export bundle available. Simulated exports are non-video metadata."
                    )
                else:
                    self.empty_library_label.setText(
                        f"{simulated_count} simulated artifact manifest available. Simulated artifacts are non-video metadata."
                    )
            else:
                self.empty_library_label.setText("")
        else:
            self.empty_library_label.setText(f"{self.clip_library.empty_state_title} {self.clip_library.empty_state_detail}")

    def refresh_library(self) -> None:
        self._populate_library()

    def record_now(self) -> None:
        result = self.controller.record_now()
        self._apply_operation_result(result.message)
        if result.export_metadata is not None:
            self._show_export_preview(result.export_metadata)
        elif result.artifact is not None:
            self._show_artifact_preview(result.artifact)

    def save_last_clip(self) -> None:
        previous = self.action_status.text()
        result = self.controller.save_last_clip()
        message = result.message
        if not result.succeeded and previous and previous != self._last_action_text and previous != message:
            message = f"{previous} {message}"
        self._apply_operation_result(message)
        if result.export_metadata is not None:
            self._show_export_preview(result.export_metadata)
        elif result.artifact is not None:
            self._show_artifact_preview(result.artifact)

    def try_one_frame_capture(self) -> None:
        result = self.controller.try_one_frame_capture()
        self.action_status.setText(result.message)
        self._update_capture_proof_widgets()

    def _apply_operation_result(self, message: str) -> None:
        self.action_status.setText(message)
        self._populate_library()

    def review_current_session(self) -> None:
        session = self.controller.review_current_session(runtime_status=self._runtime_status, capture_mode="buffered")
        if session is None:
            self.action_status.setText("No recorder samples are available to review.")
        else:
            self.action_status.setText("Recorder review session updated; no real capture or output proof was claimed.")
        self._update_review_widgets()

    def export_review_summary_json(self) -> None:
        result = self.controller.export_review_summary_json()
        self.action_status.setText(result.message if result.path is None else f"{result.message} {result.path}")
        self._update_review_widgets()

    def export_review_samples_csv(self) -> None:
        result = self.controller.export_review_samples_csv()
        self.action_status.setText(result.message if result.path is None else f"{result.message} {result.path}")
        self._update_review_widgets()

    def clear_review_session(self) -> None:
        self.controller.clear_review_session()
        self.action_status.setText("Recorder review cleared; no files or workspace settings were deleted.")
        self._update_review_widgets()

    def _update_review_widgets(self) -> None:
        session = self.controller.reviewed_session
        has_session = session is not None
        self.export_summary_button.setEnabled(has_session)
        self.export_samples_button.setEnabled(has_session)
        self.clear_review_button.setEnabled(has_session)
        if session is None:
            self.review_summary.setText(
                "No reviewed recorder session yet.\n"
                "Simulated/Workspace Only\n"
                f"Runtime truth\n{self._runtime_status.truth.value}\n"
                f"Output verified\n{str(self._runtime_status.live_output_writes_verified).lower()}\n"
                f"Full Live Runtime Ready\n{str(_full_live_runtime_ready(self._runtime_status)).lower()}"
            )
            self.timeline_table.setRowCount(0)
            return
        axis_channels = ", ".join(session.axis_channels) if session.axis_channels else "None"
        warnings = "; ".join(session.warnings) if session.warnings else "None"
        errors = "; ".join(session.errors) if session.errors else "None"
        self.review_summary.setText(
            "Latest Session Summary\n"
            f"{session.truth_label}\n"
            f"Session id\n{session.session_id}\n"
            f"Source type\n{session.source_type}\n"
            f"Capture source\n{session.capture_source}\n"
            f"Capture mode\n{session.capture_mode}\n"
            f"Duration\n{session.duration_seconds:.2f} s\n"
            f"Samples\n{session.sample_count}\n"
            f"Events\n{session.event_count}\n"
            f"Axis channels\n{axis_channels}\n"
            f"Button channels\n{', '.join(session.button_channels) if session.button_channels else 'None'}\n"
            f"Hat channels\n{', '.join(session.hat_channels) if session.hat_channels else 'None'}\n"
            f"Runtime truth\n{session.runtime_truth_snapshot['truth']}\n"
            f"Output verified\n{str(session.runtime_truth_snapshot['output_verified']).lower()}\n"
            f"Full Live Runtime Ready\n{str(session.runtime_truth_snapshot['full_live_runtime_ready']).lower()}\n"
            f"Warnings\n{warnings}\n"
            f"Errors\n{errors}"
        )
        self.timeline_table.setRowCount(len(session.timeline_events))
        for row, event in enumerate(session.timeline_events):
            values = (
                f"+{event.relative_seconds:.2f}s",
                event.channel,
                f"{event.previous_value:.3f} -> {event.value:.3f}",
                event.description,
            )
            for column, value in enumerate(values):
                self.timeline_table.setItem(row, column, QTableWidgetItem(value))

    def _update_capture_proof_widgets(self) -> None:
        self._proof_availability = self.controller.one_frame_proof_availability()
        availability = self._proof_availability
        result = self.controller.last_frame_capture_result
        capabilities = self._backend_status.capabilities
        artifact = "None"
        dimensions = "Unavailable"
        pixel_format = "Unavailable"
        truth = "No proof attempted"
        real_capture = "false"
        simulated_capture = "false"
        warnings = "; ".join(availability.warnings) if availability.warnings else "None"
        errors = "; ".join(availability.errors) if availability.errors else "None"
        last_result = "No one-frame proof attempted"
        if result is not None:
            last_result = result.message
            artifact = str(result.artifact_path) if result.artifact_path is not None else "None"
            if result.width is not None and result.height is not None:
                dimensions = f"{result.width} x {result.height}"
            pixel_format = result.pixel_format
            truth = result.truth_label
            real_capture = str(result.real_capture).lower()
            simulated_capture = str(result.simulated_capture).lower()
            warnings = "; ".join(result.warnings) if result.warnings else "None"
            errors = "; ".join(result.errors) if result.errors else "None"
        self.capture_proof_summary.setText(
            "Backend status\n"
            f"{_capture_backend_chip_label(capabilities)}\n"
            "Dependency status\n"
            f"{'available' if capabilities.dependency_available else 'unavailable'}\n"
            "Display/source\n"
            f"{availability.source.display_label} ({availability.source.capture_source})\n"
            "One-frame proof availability\n"
            f"{availability.status_label}\n"
            "Last proof result\n"
            f"{last_result}\n"
            "Frame dimensions\n"
            f"{dimensions}\n"
            "Pixel format\n"
            f"{pixel_format}\n"
            "Artifact path\n"
            f"{artifact}\n"
            "Truth label\n"
            f"{truth}\n"
            "Real capture\n"
            f"{real_capture}\n"
            "Simulated capture\n"
            f"{simulated_capture}\n"
            "Warnings\n"
            f"{warnings}\n"
            "Errors\n"
            f"{errors}"
        )
        self.try_one_frame_capture_button.setEnabled(availability.available)

    def _show_artifact_preview(self, artifact) -> None:
        sample_count = _telemetry_sample_count(artifact.path)
        if artifact.is_simulated:
            self.preview_status.setText(f"Simulated artifact\nNo video preview available\nTelemetry samples: {sample_count}")
        else:
            self.preview_status.setText("Select a recorded clip to preview.")
        self.preview_metadata.setText(
            f"Filename: {artifact.filename} | Overlay source: {artifact.overlay_source} | "
            f"Resolution: {'No video' if not artifact.has_video else 'Unavailable'} | Length: {artifact.duration_seconds:.2f} s"
        )

    def _show_export_preview(self, metadata) -> None:
        included = ", ".join(metadata.included_axes) if metadata.included_axes else "None"
        warnings = "; ".join(metadata.warnings) if metadata.warnings else "None"
        self.preview_status.setText(
            "Simulated export\n"
            "Metadata-only preview\n"
            "No video preview available\n"
            "No desktop frames were captured.\n"
            "No encoding was performed.\n"
            f"Telemetry samples: {metadata.telemetry_sample_count}\n"
            f"Overlay source: {metadata.overlay_source}\n"
            f"Duration: {metadata.duration_seconds:.2f} s\n"
            f"Frame rate: {metadata.frame_rate} fps\n"
            f"Included axes: {included}\n"
            f"Artifact path: {metadata.path}\n"
            f"Manifest path: {metadata.manifest_path}\n"
            f"Warnings: {warnings}"
        )
        self.preview_metadata.setText(
            f"Filename: {metadata.path.name} | Overlay source: {metadata.overlay_source} | "
            "Resolution: No video | "
            f"Length: {metadata.duration_seconds:.2f} s"
        )

    def show_library_item_preview(self, row: int) -> None:
        if row < 0 or row >= len(getattr(self, "_library_clips", ())):
            self.preview_status.setText("Select a recorder artifact to preview.\nMetadata preview unavailable.")
            return
        clip = self._library_clips[row]
        if clip.export_metadata is not None:
            self._show_export_preview(clip.export_metadata)
            return
        if clip.is_simulated:
            self.preview_status.setText(
                "Simulated artifact\n"
                "Metadata-only preview\n"
                "No video preview available\n"
                f"Telemetry samples: {clip.telemetry_sample_count}\n"
                f"Artifact path: {clip.path}"
            )
            self.preview_metadata.setText(
                f"Filename: {clip.path.name} | Overlay source: {clip.overlay_source} | "
                "Resolution: No video | "
                f"Length: {clip.length}"
            )
            return
        self.preview_status.setText("Select a recorder artifact to preview.\nNo video preview available.")


_RECORDER_SETTINGS_METADATA = {
    "Destination": "flight_recorder.destination",
    "Length": "flight_recorder.length",
    "Frame Rate": "flight_recorder.frame_rate",
    "History": "flight_recorder.history",
    "Overlay Source": "flight_recorder.overlay_source",
    "Capture Source": "flight_recorder.capture_source",
    "Display": "flight_recorder.display",
    "Hotkey": "flight_recorder.hotkey",
    "Trigger Mode": "flight_recorder.trigger_mode",
}


def _row_grid(values: dict[str, str], *, metadata_ids: dict[str, str] | None = None) -> QGridLayout:
    grid = QGridLayout()
    grid.setHorizontalSpacing(14)
    grid.setVerticalSpacing(8)
    for row, (label, value) in enumerate(values.items()):
        metadata_id = metadata_ids.get(label) if metadata_ids is not None else None
        key = parameter_label(label, metadata_id=metadata_id) if metadata_id else QLabel(label)
        if metadata_id is None:
            key.setObjectName("tableMutedText")
        val = QLabel(value)
        val.setObjectName("routeSummaryValue")
        val.setWordWrap(True)
        grid.addWidget(key, row, 0)
        grid.addWidget(val, row, 1)
    return grid


def _body(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("cardBody")
    label.setWordWrap(True)
    return label


def _key(axis_name: str) -> str:
    return axis_name.replace(" ", "_")


def _capture_backend_chip_label(capabilities) -> str:
    if capabilities.backend_kind == "simulated":
        return "Simulated backend"
    if capabilities.backend_kind == "candidate":
        return "Candidate available" if capabilities.dependency_available else "Candidate unavailable"
    if capabilities.backend_kind == "test":
        return "Test backend"
    return "Capture backend missing"


def _full_live_runtime_ready(runtime_status: RuntimePreflightStatus) -> bool:
    return bool(runtime_status.live_output_writes_verified and runtime_status.truth.value == "live_verified")


def _telemetry_sample_count(path: Path) -> int:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        telemetry = payload.get("telemetry") if isinstance(payload, dict) else None
        sample_count = telemetry.get("sample_count") if isinstance(telemetry, dict) else 0
        return int(sample_count or 0)
    except (OSError, ValueError, TypeError):
        return 0
