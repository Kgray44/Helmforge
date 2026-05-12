from __future__ import annotations

from collections.abc import Iterable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def _polish_tone(tone: str) -> str:
    if tone in {"ok", "ready"}:
        return "success"
    if tone in {"waiting", "blocked"}:
        return "warning"
    if tone in {"error", "failed"}:
        return "danger"
    if tone in {"info", "success", "warning", "danger", "caution", "neutral"}:
        return tone
    return "neutral"


def _label(text: str, object_name: str, *, word_wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(word_wrap)
    return label


class CockpitStatusBanner(QFrame):
    def __init__(
        self,
        title: str,
        state: str,
        explanation: str,
        *,
        next_action: str | None = None,
        tone: str = "info",
        object_name: str = "cockpitStatusBanner",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("cockpitComponent", "statusBanner")
        self.setProperty("tone", _polish_tone(tone))
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        rail = QFrame()
        rail.setObjectName("cockpitToneRail")
        rail.setProperty("tone", _polish_tone(tone))
        rail.setFixedWidth(5)

        copy = QVBoxLayout()
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(7)

        title_label = _label(title, "cockpitBannerTitle")
        state_label = _label(state, "cockpitBannerState", word_wrap=True)
        explanation_label = _label(explanation, "cockpitBannerExplanation", word_wrap=True)
        copy.addWidget(title_label)
        copy.addWidget(state_label)
        copy.addWidget(explanation_label)
        if next_action:
            action_label = _label(next_action, "cockpitBannerNextAction", word_wrap=True)
            action_label.setProperty("tone", _polish_tone(tone))
            copy.addWidget(action_label)

        layout.addWidget(rail)
        layout.addLayout(copy, 1)


class ReadinessRail(QFrame):
    def __init__(
        self,
        items: Sequence[tuple[str, str, str]],
        *,
        object_name: str = "cockpitReadinessRail",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("cockpitComponent", "readinessRail")
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QGridLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        for index, (label, value, tone) in enumerate(items):
            gate = QFrame()
            gate.setObjectName("cockpitGate")
            gate.setProperty("tone", _polish_tone(tone))
            gate_layout = QVBoxLayout(gate)
            gate_layout.setContentsMargins(12, 10, 12, 10)
            gate_layout.setSpacing(4)
            gate_layout.addWidget(_label(label, "cockpitGateLabel"))
            gate_layout.addWidget(_label(value, "cockpitGateValue", word_wrap=True))
            layout.addWidget(gate, index // 3, index % 3)


class SystemTile(QFrame):
    def __init__(
        self,
        title: str,
        status: str,
        explanation: str,
        *,
        facts: Iterable[str] = (),
        tone: str = "info",
        object_name: str = "cockpitSystemTile",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("cockpitComponent", "systemTile")
        self.setProperty("tone", _polish_tone(tone))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        rail = QFrame()
        rail.setObjectName("cockpitTileRail")
        rail.setProperty("tone", _polish_tone(tone))
        rail.setFixedWidth(4)
        body = QVBoxLayout()
        body.setContentsMargins(16, 14, 16, 16)
        body.setSpacing(8)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(10)
        title_label = _label(title, "cockpitTileTitle", word_wrap=True)
        status_chip = _label(status, "cockpitTileStatus")
        status_chip.setProperty("uiRole", "statusChip")
        status_chip.setProperty("chipTone", _polish_tone(tone))
        top.addWidget(title_label, 1)
        top.addWidget(status_chip)

        body.addLayout(top)
        body.addWidget(_label(explanation, "cockpitTileBody", word_wrap=True))
        for fact in facts:
            fact_label = _label(fact, "cockpitTileFact", word_wrap=True)
            body.addWidget(fact_label)

        layout.addWidget(rail)
        layout.addLayout(body, 1)


class MetricTile(QFrame):
    def __init__(
        self,
        label: str,
        value: str,
        helper: str = "",
        *,
        tone: str = "neutral",
        object_name: str = "cockpitMetricTile",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("cockpitComponent", "metricTile")
        self.setProperty("tone", _polish_tone(tone))
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(6)
        layout.addWidget(_label(label, "cockpitMetricLabel", word_wrap=True))
        value_label = _label(value, "cockpitMetricValue")
        value_label.setProperty("tone", _polish_tone(tone))
        layout.addWidget(value_label)
        if helper:
            layout.addWidget(_label(helper, "cockpitMetricHelper", word_wrap=True))


class FlowRow(QFrame):
    def __init__(
        self,
        source: str,
        transform: str,
        target: str,
        *,
        object_name: str = "cockpitFlowRow",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("cockpitComponent", "flowRow")
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        for index, text in enumerate((source, transform, target)):
            pill = _label(text, "cockpitRoutePill", word_wrap=True)
            pill.setProperty("uiRole", "routePill")
            layout.addWidget(pill, 1)
            if index < 2:
                layout.addWidget(_label("->", "cockpitFlowArrow"), 0, Qt.AlignmentFlag.AlignCenter)


class ChecklistPanel(QFrame):
    def __init__(
        self,
        title: str,
        rows: Sequence[tuple[str, str]],
        *,
        object_name: str = "cockpitChecklistPanel",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("cockpitComponent", "checklistPanel")
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(_label(title, "cockpitPanelTitle"))
        for state, text in rows:
            row = QFrame()
            row.setObjectName("cockpitChecklistRow")
            row.setProperty("tone", _polish_tone(state))
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(10)
            light = QLabel()
            light.setObjectName("cockpitStatusLight")
            light.setProperty("tone", _polish_tone(state))
            light.setFixedSize(10, 10)
            row_layout.addWidget(light)
            row_layout.addWidget(_label(text, "cockpitChecklistText", word_wrap=True), 1)
            layout.addWidget(row)


class DataGridCard(QFrame):
    def __init__(
        self,
        title: str,
        explanation: str,
        *,
        rows: Sequence[tuple[str, str]] = (),
        content: QWidget | None = None,
        object_name: str = "cockpitDataGridCard",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("cockpitComponent", "dataGridCard")
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(_label(title, "cockpitPanelTitle"))
        layout.addWidget(_label(explanation, "cockpitPanelBody", word_wrap=True))
        for key, value in rows:
            row = QFrame()
            row.setObjectName("cockpitDataGridRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(12)
            row_layout.addWidget(_label(key, "cockpitDataGridKey", word_wrap=True), 1)
            row_layout.addWidget(_label(value, "cockpitDataGridValue", word_wrap=True), 2)
            layout.addWidget(row)
        if content is not None:
            content.setProperty("cockpitLegacyWrapped", True)
            layout.addWidget(content)


class AdvancedPanel(QFrame):
    def __init__(
        self,
        title: str,
        explanation: str,
        content: QWidget | None = None,
        *,
        object_name: str = "cockpitAdvancedPanel",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("cockpitComponent", "advancedPanel")
        self.setProperty("cockpitAdvancedPanel", True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(_label(title, "cockpitPanelTitle"))
        layout.addWidget(_label(explanation, "cockpitPanelBody", word_wrap=True))
        if content is not None:
            content.setProperty("cockpitLegacyWrapped", True)
            layout.addWidget(content)


class CockpitActionStrip(QFrame):
    def __init__(
        self,
        actions: Sequence[QPushButton],
        *,
        object_name: str = "cockpitActionStrip",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setProperty("cockpitComponent", "actionStrip")
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        layout.addStretch(1)
        for button in actions:
            button.setProperty("uiRole", "actionButton")
            layout.addWidget(button)
