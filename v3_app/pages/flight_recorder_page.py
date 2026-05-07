from __future__ import annotations

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
from v3_app.pages.page_helpers import card, card_header, card_layout, page_intro
from v3_app.recorder.clip_library import ClipLibrary
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
    ) -> None:
        super().__init__()
        self.setObjectName("flightRecorderPage")
        self._state = state
        self._workspace = workspace
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self.settings = settings or FlightRecorderSettings.defaults()
        self.recorder_state = recorder_state or RecorderState.default()
        self.clip_library = ClipLibrary(self.settings.destination_folder)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)
        root.addWidget(
            page_intro(
                "Flight Recorder",
                "Capture the desktop on demand, then composite a time-matched axis trace overlay into the finished video.",
                "Use the hotkey when you want a clean replay of what happened on-screen with the matched HOTAS signal history baked into the clip. Capture/export backend is not active yet.",
            )
        )
        root.addWidget(self._status_card())

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        grid.addWidget(self._recorder_settings_card(), 0, 0)
        grid.addWidget(self._axis_overlay_card(), 0, 1)
        grid.addWidget(self._recording_library_card(), 1, 0)
        grid.addWidget(self._clip_preview_card(), 1, 1)
        root.addLayout(grid)
        root.addStretch(1)

    def _status_card(self) -> QWidget:
        frame = card("recorderStatusCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Recorder Status", "Truthful recorder state before capture and encoding backends exist."))
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(status_chip("UI Ready", tone="success", object_name="recorderUiReadyChip"))
        row.addWidget(status_chip(self.recorder_state.status_label, tone="warning", object_name="recorderBackendMissingChip"))
        row.addWidget(status_chip("Hotkey not registered", tone="warning", object_name="recorderHotkeyChip"))
        row.addWidget(status_chip(f"{self.settings.overlay_source} source", tone="neutral", object_name="recorderOverlaySourceChip"))
        row.addWidget(status_chip("Buffering unavailable", tone="warning", object_name="recorderBufferingChip"))
        row.addWidget(status_chip("Recording unavailable", tone="warning", object_name="recorderRecordingChip"))
        row.addStretch(1)
        layout.addLayout(row)
        layout.addLayout(
            _row_grid(
                {
                    "Runtime truth": self._runtime_status.truth.value,
                    "Output verified": str(self._runtime_status.live_output_writes_verified).lower(),
                    "Full Live Runtime Ready": str(_full_live_runtime_ready(self._runtime_status)).lower(),
                    "Capture backend": "missing",
                    "Recorder mode": "UI only / backend missing",
                    "Hotkey status": "Not registered",
                    "Hindsight video buffering": "Unavailable - deferred",
                }
            )
        )
        layout.addWidget(
            _body(
                "Telemetry buffering may exist for Live Overlay traces, but hindsight video buffering is not implemented yet. "
                "Save Last Clip cannot save video until capture and buffer backends exist."
            )
        )
        self.action_status = QLabel(self.recorder_state.message)
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
        self.record_now_button = action_button("Record Now", object_name="recordNowButton")
        self.record_now_button.setEnabled(False)
        self.record_now_button.clicked.connect(self.record_now)
        self.save_last_clip_button = action_button("Save Last Clip", object_name="saveLastClipButton")
        self.save_last_clip_button.setEnabled(False)
        self.save_last_clip_button.clicked.connect(self.save_last_clip)
        for button in (browse, open_folder, self.record_now_button, self.save_last_clip_button):
            button_row.addWidget(button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        layout.addWidget(
            _body(
                "Capture backend missing. Hindsight buffer not implemented yet. "
                "Recording backend is not active in this phase. Recording backend unavailable."
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
        layout.addWidget(card_header("Recording Library", "Read-only shell for clips once capture and encoding exist."))
        controls = QHBoxLayout()
        sort = QComboBox()
        sort.setObjectName("recordingLibrarySortDropdown")
        sort.addItem("Newest First")
        refresh = action_button("Refresh", object_name="recordingLibraryRefreshButton")
        refresh.setEnabled(False)
        controls.addWidget(QLabel("Sort"))
        controls.addWidget(sort)
        controls.addWidget(refresh)
        controls.addStretch(1)
        layout.addLayout(controls)
        self.library_table = QTableWidget(0, 4)
        self.library_table.setObjectName("recordingLibraryTable")
        self.library_table.setHorizontalHeaderLabels(("Clip", "Recorded", "Duration", "Opened"))
        self.library_table.setFrameShape(QFrame.Shape.NoFrame)
        self.library_table.setMinimumHeight(160)
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
        preview = QLabel("Select a recorded clip to preview.\nClip preview backend is not implemented yet.")
        preview.setObjectName("clipPreviewUnavailableState")
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumHeight(180)
        preview.setWordWrap(True)
        layout.addWidget(preview)
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
        metadata = QLabel("Filename: none | Overlay source: Final output | Resolution: Unavailable | Length: Unavailable")
        metadata.setObjectName("clipPreviewMetadata")
        metadata.setWordWrap(True)
        layout.addWidget(metadata)
        return frame

    def _populate_library(self) -> None:
        clips = self.clip_library.scan()
        self.library_table.setRowCount(len(clips))
        for row, clip in enumerate(clips):
            for column, value in enumerate((clip.clip, clip.recorded, clip.duration, clip.opened)):
                self.library_table.setItem(row, column, QTableWidgetItem(value))

    def record_now(self) -> None:
        self.action_status.setText("Capture backend missing; Record Now is unavailable in Phase 13A.")

    def save_last_clip(self) -> None:
        record_text = "Capture backend missing; Record Now is unavailable in Phase 13A."
        save_text = "Hindsight video buffer is not implemented yet; Save Last Clip cannot save video."
        current = self.action_status.text()
        if record_text in current:
            self.action_status.setText(f"{record_text} {save_text}")
        else:
            self.action_status.setText(save_text)


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


def _full_live_runtime_ready(runtime_status: RuntimePreflightStatus) -> bool:
    return bool(runtime_status.live_output_writes_verified and runtime_status.truth.value == "live_verified")
