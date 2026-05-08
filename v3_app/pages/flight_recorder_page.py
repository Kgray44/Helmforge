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
from v3_app.pages.page_helpers import add_card_to_grid, card, card_header, card_layout, page_intro
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

    def _recorder_settings_card(self) -> QWidget:
        frame = card("recorderSettingsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Recorder Settings", "Settings are stored in-memory for this UI shell; no video files are written."))
        layout.addLayout(
            _row_grid(
                {
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
            )
        )
        cursor = QCheckBox("Record the cursor")
        cursor.setObjectName("recordCursorCheckbox")
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
        refresh = action_button("Refresh", object_name="recordingLibraryRefreshButton")
        refresh.clicked.connect(self.refresh_library)
        controls.addWidget(QLabel("Sort"))
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

    def _apply_operation_result(self, message: str) -> None:
        self.action_status.setText(message)
        self._populate_library()

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


def _row_grid(values: dict[str, str]) -> QGridLayout:
    grid = QGridLayout()
    grid.setHorizontalSpacing(14)
    grid.setVerticalSpacing(8)
    for row, (label, value) in enumerate(values.items()):
        key = QLabel(label)
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
