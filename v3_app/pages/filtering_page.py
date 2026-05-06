from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from shared_core.models.axes import axis_by_name
from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.runtime_bridge import RuntimeBridge
from v3_app.pages.graph_data import filtering_step_preview_data
from v3_app.pages.graph_widgets import GraphPreview
from v3_app.pages.page_helpers import (
    OnDirty,
    axis_list_card,
    card,
    card_header,
    card_layout,
    field_row,
    page_intro,
    runtime_truth_rows,
    signed,
    value_grid,
)
from v3_app.services.app_state import AppState


class FilteringPage(QWidget):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        on_dirty: OnDirty | None = None,
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
        self._axis_name = state.selected_axis
        self._axis_id = axis_by_name(self._axis_name).axis_id.value
        self._settings = self._workspace.filtering.axes[self._axis_id]
        self._snapshot = RuntimeBridge(
            preflight_status=self._runtime_status,
            deterministic_simulation=True,
        ).snapshot()

        root.addWidget(
            page_intro(
                "Filtering",
                "Control damping and slew behavior without rebuilding the whole response curve.",
                "Changes update the current workspace immediately and are only written out when you save.",
            )
        )
        root.addLayout(self._build_workspace())

    def _build_workspace(self) -> QHBoxLayout:
        workspace = QHBoxLayout()
        workspace.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(18)
        left.addWidget(axis_list_card(selected_axis=self._axis_name))
        left.addWidget(self._build_parameters_card())
        left.addStretch(1)

        right = QVBoxLayout()
        right.setSpacing(18)
        right.addWidget(self._build_graph_card(), 2)
        lower = QHBoxLayout()
        lower.setSpacing(18)
        lower.addWidget(self._build_live_snapshot_card(), 1)
        lower.addWidget(self._build_guidance_card(), 1)
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
        dirty = "Filtering parameter edit staged in the current workspace draft."
        field_row(grid, 0, "Center Alpha", f"{self._settings.center_alpha:.2f}", object_name="centerAlphaField", on_dirty=self._on_dirty, dirty_message=dirty)
        field_row(grid, 1, "Edge Alpha", f"{self._settings.edge_alpha:.2f}", object_name="edgeAlphaField", on_dirty=self._on_dirty, dirty_message=dirty)
        field_row(grid, 2, "Same Slew Limit", f"{self._settings.same_slew_limit:.2f}", object_name="sameSlewLimitField", on_dirty=self._on_dirty, dirty_message=dirty)
        field_row(grid, 3, "Reverse Slew Limit", f"{self._settings.reverse_slew_limit:.2f}", object_name="reverseSlewLimitField", on_dirty=self._on_dirty, dirty_message=dirty)
        layout.addLayout(grid)
        return frame

    def _build_graph_card(self) -> QWidget:
        frame = card("filteringGraphCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Response Preview", "Live response preview for the selected axis."))
        data = filtering_step_preview_data(self._settings)
        graph = GraphPreview(object_name="filteringGraph")
        graph.plot_series(
            (
                ("Input", data.raw, "#7e91a8"),
                ("Filtered", data.filtered, "#53b7ff"),
            )
        )
        layout.addWidget(graph)
        footer = QLabel("Step preview: input vs filtered output. Center")
        footer.setObjectName("cardBody")
        layout.addWidget(footer)
        return frame

    def _build_live_snapshot_card(self) -> QWidget:
        frame = card("filteringLiveSnapshotCard")
        layout = card_layout(frame)
        raw = self._snapshot.raw_axis_values.get(self._axis_name, 0.0)
        final = self._snapshot.final_output_values.get(self._axis_name, 0.0)
        layout.addWidget(card_header("Live Snapshot", "Current runtime values for the selected axis."))
        value = QLabel(signed(final))
        value.setObjectName("snapshotValue")
        layout.addWidget(value)
        layout.addLayout(
            value_grid(
                (
                    ("Selected Axis", self._axis_name),
                    ("Raw", signed(raw)),
                    ("Final", signed(final)),
                    ("Rules", "None"),
                    *runtime_truth_rows(self._runtime_status),
                )
            )
        )
        return frame

    def _build_guidance_card(self) -> QWidget:
        frame = card("filteringGuidanceCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Guidance", "A quick read on how the selected tuning profile is likely to feel."))
        guidance = QLabel("Feels: Stable center response, fast same-direction response, freer reversals.")
        guidance.setObjectName("routeSummaryValue")
        guidance.setWordWrap(True)
        layout.addStretch(1)
        layout.addWidget(guidance)
        return frame
