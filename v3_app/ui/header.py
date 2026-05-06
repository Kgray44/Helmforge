from __future__ import annotations

from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QWidget

from v3_app.services.app_state import AppState
from v3_app.ui.status_chips import action_button, status_chip


HEADER_SUBTITLE = "HOTAS Control Panel V3, professional tuning, live inspection, and assistant-guided diagnostics."


class Header(QWidget):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.setObjectName("appHeader")
        self._state = state
        self._runtime_chip: QLabel | None = None
        self._saved_chip: QLabel | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(24)

        title_area = QVBoxLayout()
        title_area.setSpacing(16)
        title = QLabel("HelmForge")
        title.setObjectName("headerTitle")
        subtitle = QLabel(HEADER_SUBTITLE)
        subtitle.setObjectName("headerSubtitle")
        subtitle.setWordWrap(True)
        title_area.addWidget(title)
        title_area.addWidget(subtitle)

        clusters = QVBoxLayout()
        clusters.setSpacing(10)
        clusters.addWidget(self._build_status_cluster())
        clusters.addWidget(self._build_assistant_cluster())

        root.addLayout(title_area, 1)
        root.addLayout(clusters)

    def _build_status_cluster(self) -> QWidget:
        cluster = QWidget()
        cluster.setObjectName("statusCluster")
        layout = QHBoxLayout(cluster)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        label = QLabel("STATUS")
        label.setObjectName("clusterLabel")
        self._saved_chip = status_chip("Saved" if self._state.saved else "Unsaved", tone="success" if self._state.saved else "warning")
        self._runtime_chip = status_chip(
            self._state.runtime.header_truth_label,
            tone=self._state.runtime.tone,
            object_name="runtimeTruthChip",
        )
        layout.addWidget(label)
        layout.addWidget(status_chip("Workspace Copy", tone="success"))
        layout.addWidget(self._saved_chip)
        layout.addWidget(self._runtime_chip)
        return cluster

    def _build_assistant_cluster(self) -> QWidget:
        cluster = QWidget()
        cluster.setObjectName("assistantCluster")
        layout = QHBoxLayout(cluster)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)
        label = QLabel("ASSISTANT")
        label.setObjectName("clusterLabel")
        helm = action_button("Helm", object_name="helmButton")
        layout.addWidget(label, 1)
        layout.addWidget(helm)
        return cluster

    def update_state(self, state: AppState) -> None:
        self._state = state
        if self._saved_chip is not None:
            self._saved_chip.setText("Saved" if state.saved else "Unsaved")
            self._saved_chip.setProperty("chipTone", "success" if state.saved else "warning")
        if self._runtime_chip is not None:
            self._runtime_chip.setText(state.runtime.header_truth_label)
            self._runtime_chip.setProperty("chipTone", state.runtime.tone)
