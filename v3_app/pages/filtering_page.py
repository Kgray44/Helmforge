from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from shared_core.models.axes import AXIS_DISPLAY_NAMES, axis_by_name
from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.runtime_bridge import RuntimeBridge
from v3_app.pages.graph_data import filtering_adjusted_value, filtering_step_preview_data
from v3_app.pages.graph_widgets import GraphPreview
from v3_app.pages.page_helpers import (
    OnDirty,
    axis_list_card,
    card,
    card_header,
    card_layout,
    field_row,
    page_intro,
    signed,
)
from v3_app.services.app_state import AppState
from v3_app.services.parameter_metadata import PARAMETER_HELP


OnWorkspaceChanged = Callable[[WorkspaceConfig, str], None]
LIVE_MARKER_COLORS = {"Input": "#d7e4f0", "Filtered": "#53b7ff", "Sample": "#96ffc5"}


class FilteringPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        on_dirty: OnDirty | None = None,
        on_workspace_changed: OnWorkspaceChanged | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("filteringPage")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 28)
        root.setSpacing(18)

        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._runtime_status = runtime_status or build_runtime_preflight_status()
        self._on_dirty = on_dirty
        self._on_workspace_changed = on_workspace_changed
        self._runtime_bridge = RuntimeBridge(
            preflight_status=self._runtime_status,
            deterministic_simulation=False,
        )
        self._axis_name = state.selected_axis
        self._axis_id = axis_by_name(self._axis_name).axis_id.value
        self._settings = self._workspace.filtering.axes[self._axis_id]
        self._latest_raw_values = {axis: 0.0 for axis in AXIS_DISPLAY_NAMES}
        self._axis_buttons: dict[str, QPushButton] = {}
        self._numeric_fields: dict[str, QLineEdit] = {}
        self._snapshot_value: QLabel | None = None
        self._snapshot_rows: dict[str, QLabel] = {}
        self._guidance_rows: dict[str, QLabel] = {}
        self._validation_message: QLabel | None = None
        self._graph: GraphPreview | None = None

        root.addWidget(
            page_intro(
                "Filtering",
                "Control damping and slew behavior without rebuilding the whole response curve.",
                "Changes update the current workspace immediately and are only written out when you save.",
            )
        )
        root.addLayout(self._build_workspace())
        self._refresh_live_sample()

        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _build_workspace(self) -> QHBoxLayout:
        workspace = QHBoxLayout()
        workspace.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(18)
        axis_card = axis_list_card(selected_axis=self._axis_name, on_axis_selected=self.set_selected_axis)
        self._axis_buttons = {
            button.text(): button for button in axis_card.findChildren(QPushButton, "axisListItem")
        }
        left.addWidget(axis_card)
        left.addWidget(self._build_parameters_card())
        left.addStretch(1)

        right = QVBoxLayout()
        right.setSpacing(18)
        right.addWidget(self._build_graph_card(), 2)
        lower = QHBoxLayout()
        lower.setSpacing(18)
        lower.addWidget(self._build_live_snapshot_card(), 1, Qt.AlignmentFlag.AlignTop)
        lower.addWidget(self._build_guidance_card(), 1, Qt.AlignmentFlag.AlignTop)
        right.addLayout(lower)

        left_widget = QWidget()
        left_widget.setLayout(left)
        workspace.addWidget(left_widget, 1)
        workspace.addLayout(right, 3)
        return workspace

    def _build_parameters_card(self) -> QWidget:
        frame = card("filteringParametersCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Parameters", "Adjust values here and review the result on the live preview."))
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        self._numeric_fields = {
            "center_alpha": field_row(
                grid,
                0,
                "Center Alpha",
                f"{self._settings.center_alpha:.2f}",
                object_name="centerAlphaField",
                metadata_id="filtering.center_alpha",
            ),
            "edge_alpha": field_row(
                grid,
                1,
                "Edge Alpha",
                f"{self._settings.edge_alpha:.2f}",
                object_name="edgeAlphaField",
                metadata_id="filtering.edge_alpha",
            ),
            "same_slew_limit": field_row(
                grid,
                2,
                "Same Slew Limit",
                f"{self._settings.same_slew_limit:.2f}",
                object_name="sameSlewLimitField",
                metadata_id="filtering.same_slew_limit",
            ),
            "reverse_slew_limit": field_row(
                grid,
                3,
                "Reverse Slew Limit",
                f"{self._settings.reverse_slew_limit:.2f}",
                object_name="reverseSlewLimitField",
                metadata_id="filtering.reverse_slew_limit",
            ),
        }
        for attribute, field in self._numeric_fields.items():
            metadata_id = f"filtering.{attribute}"
            field.editingFinished.connect(
                lambda attribute=attribute, field=field, metadata_id=metadata_id: self._commit_numeric(
                    attribute,
                    field,
                    metadata_id,
                )
            )
        layout.addLayout(grid)
        self._validation_message = QLabel("")
        self._validation_message.setObjectName("sectionHint")
        self._validation_message.setWordWrap(True)
        layout.addWidget(self._validation_message)
        return frame

    def _build_graph_card(self) -> QWidget:
        frame = card("filteringGraphCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Response Preview", "Live response preview for the selected axis."))
        self._graph = GraphPreview(object_name="filteringGraph")
        self._update_graph_series()
        layout.addWidget(self._graph)
        footer = QLabel("Step preview: input vs filtered output. Dots mark the current sample.")
        footer.setObjectName("cardBody")
        footer.setWordWrap(True)
        layout.addWidget(footer)
        return frame

    def _build_live_snapshot_card(self) -> QWidget:
        frame = card("filteringLiveSnapshotCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Live Snapshot", "Current simulated/fallback values for the selected axis."))
        self._snapshot_value = QLabel("+0.00")
        self._snapshot_value.setObjectName("snapshotValue")
        layout.addWidget(self._snapshot_value)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        for row, label in enumerate(
            (
                "Input Source",
                "Selected Axis",
                "Raw Value",
                "Output Intent",
                "Runtime Truth",
                "Output Verification",
            )
        ):
            key = QLabel(label)
            key.setObjectName("tableMutedText")
            value = QLabel("")
            value.setObjectName("routeSummaryValue")
            value.setWordWrap(True)
            grid.addWidget(key, row, 0)
            grid.addWidget(value, row, 1)
            self._snapshot_rows[label] = value
        layout.addLayout(grid)
        return frame

    def _build_guidance_card(self) -> QWidget:
        frame = card("filteringGuidanceCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Guidance", "Compact filtering notes for the selected axis."))
        for title in (
            "Current feel",
            "What this setting affects",
            "Suggested range",
            "Caution",
            "Selected axis note",
        ):
            key = QLabel(title)
            key.setObjectName("sectionLabel")
            value = QLabel("")
            value.setObjectName("routeSummaryValue")
            value.setWordWrap(True)
            layout.addWidget(key)
            layout.addWidget(value)
            self._guidance_rows[title] = value
        self._update_guidance()
        return frame

    def _tick(self) -> None:
        if not self.isVisible():
            return
        self._refresh_live_sample()

    def set_selected_axis(self, axis_name: str) -> None:
        if axis_name not in AXIS_DISPLAY_NAMES:
            return
        self._axis_name = axis_name
        self._axis_id = axis_by_name(axis_name).axis_id.value
        self._state.selected_axis = axis_name
        self._settings = self._workspace.filtering.axes[self._axis_id]
        self._sync_axis_buttons()
        self._sync_parameter_fields()
        self._update_graph_series()
        self._update_guidance()
        self._refresh_live_sample(raw_axis_values=self._latest_raw_values)

    def _commit_numeric(self, attribute: str, field: QLineEdit, metadata_id: str) -> None:
        metadata = PARAMETER_HELP.require(metadata_id)
        current_value = float(getattr(self._settings, attribute))
        try:
            value = float(field.text())
        except ValueError:
            field.setText(f"{current_value:.2f}")
            self._set_validation_message(f"{metadata.display_name} rejected letters; kept {current_value:.2f}.")
            return

        clamped = value
        if metadata.min_value is not None and metadata.max_value is not None:
            clamped = max(float(metadata.min_value), min(float(metadata.max_value), value))
        field.setText(f"{clamped:.2f}")
        if clamped != value:
            self._set_validation_message(
                f"{metadata.display_name} capped to {clamped:.2f} for {self._axis_name}."
            )
        else:
            self._set_validation_message(f"{metadata.display_name} staged for {self._axis_name}.")
        if clamped != current_value:
            self._set_filtering_value(
                attribute,
                clamped,
                f"Filtering {metadata.display_name} staged for {self._axis_name}.",
            )

    def _set_filtering_value(self, attribute: str, value: float, message: str) -> None:
        self._settings = replace(self._settings, **{attribute: value})
        axes = dict(self._workspace.filtering.axes)
        axes[self._axis_id] = self._settings
        self._workspace = replace(self._workspace, filtering=replace(self._workspace.filtering, axes=axes))
        self._publish_workspace(message)
        self._update_graph_series()
        self._update_guidance()
        self._refresh_live_sample(raw_axis_values=self._latest_raw_values)

    def _publish_workspace(self, message: str) -> None:
        if self._on_workspace_changed is not None:
            self._on_workspace_changed(self._workspace, message)
        elif self._on_dirty is not None:
            self._on_dirty(message)

    def _sync_axis_buttons(self) -> None:
        for axis_name, button in self._axis_buttons.items():
            active = axis_name == self._axis_name
            button.setProperty("active", active)
            button.setChecked(active)
            button.style().unpolish(button)
            button.style().polish(button)

    def _sync_parameter_fields(self) -> None:
        values = {
            "center_alpha": self._settings.center_alpha,
            "edge_alpha": self._settings.edge_alpha,
            "same_slew_limit": self._settings.same_slew_limit,
            "reverse_slew_limit": self._settings.reverse_slew_limit,
        }
        for attribute, value in values.items():
            field = self._numeric_fields.get(attribute)
            if field is not None:
                field.setText(f"{value:.2f}")

    def _update_graph_series(self) -> None:
        if self._graph is None:
            return
        data = filtering_step_preview_data(self._settings)
        self._graph.plot_series_with_markers(
            (
                ("Input", data.raw, "#7e91a8"),
                ("Filtered", data.filtered, "#53b7ff"),
            ),
            markers=self._marker_points(),
            marker_colors=LIVE_MARKER_COLORS,
        )

    def _refresh_live_sample(self, *, raw_axis_values: dict[str, float] | None = None) -> None:
        if raw_axis_values is None:
            snapshot = self._runtime_bridge.snapshot()
            raw_axis_values = {
                axis: float(snapshot.raw_axis_values.get(axis, 0.0)) for axis in AXIS_DISPLAY_NAMES
            }
        self._latest_raw_values = {
            axis: float(raw_axis_values.get(axis, 0.0)) for axis in AXIS_DISPLAY_NAMES
        }
        raw = self._latest_raw_values[self._axis_name]
        output = filtering_adjusted_value(self._settings, raw)
        if self._snapshot_value is not None:
            self._snapshot_value.setText(signed(output))
        self._set_snapshot_row("Input Source", "Simulation/fallback sample")
        self._set_snapshot_row("Selected Axis", self._axis_name)
        self._set_snapshot_row("Raw Value", signed(raw))
        self._set_snapshot_row("Output Intent", signed(output))
        self._set_snapshot_row("Runtime Truth", self._runtime_status.truth.value)
        self._set_snapshot_row(
            "Output Verification",
            f"Output writes verified: {str(self._runtime_status.live_output_writes_verified).lower()}",
        )
        if self._graph is not None:
            self._graph.update_markers(self._marker_points(), marker_colors=LIVE_MARKER_COLORS)

    def _marker_points(self) -> dict[str, tuple[float, float]]:
        raw = self._latest_raw_values.get(self._axis_name, 0.0)
        output = filtering_adjusted_value(self._settings, raw)
        sample_x = 1.50
        return {
            "Input": (sample_x, raw),
            "Filtered": (sample_x, output),
            "Sample": (sample_x, output),
        }

    def _set_snapshot_row(self, label: str, value: str) -> None:
        row = self._snapshot_rows.get(label)
        if row is not None:
            row.setText(value)

    def _update_guidance(self) -> None:
        self._set_guidance_row(
            "Current feel",
            f"Center alpha {self._settings.center_alpha:.2f}, edge alpha {self._settings.edge_alpha:.2f}, "
            f"reverse slew {self._settings.reverse_slew_limit:.2f}.",
        )
        self._set_guidance_row(
            "What this setting affects",
            "Smoothing and slew limits after base tuning, before combat and final response presentation.",
        )
        self._set_guidance_row(
            "Suggested range",
            "Center alpha 0.20-0.65; edge alpha 0.50-0.90; reverse slew 0.35-0.85.",
        )
        caution = "Very low alpha or slew values can feel delayed during fast corrections."
        if self._settings.same_slew_limit < 0.20 or self._settings.reverse_slew_limit < 0.20:
            caution = "Extreme slew limits may visibly lag behind deliberate stick motion."
        self._set_guidance_row("Caution", caution)
        self._set_guidance_row(
            "Selected axis note",
            f"{self._axis_name} is selected; filter edits and live dots apply only to this axis draft.",
        )

    def _set_guidance_row(self, label: str, value: str) -> None:
        row = self._guidance_rows.get(label)
        if row is not None:
            row.setText(value)

    def _set_validation_message(self, message: str) -> None:
        if self._validation_message is not None:
            self._validation_message.setText(message)
