from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy

from v3_app.services.hotas_diagram_model import (
    HotasDiagramControl,
    HotasDiagramModel,
    format_hotas_control_tooltip,
)


class HotasDiagramWidget(QFrame):
    def __init__(self, model: HotasDiagramModel) -> None:
        super().__init__()
        self.setObjectName("hotasDiagramWidget")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMouseTracking(True)
        self.setMinimumHeight(430)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._model = model
        self._markers: list[tuple[HotasDiagramControl, QLabel]] = []
        self._build_markers()

    def set_model(self, model: HotasDiagramModel) -> None:
        self._model = model
        for _control, marker in self._markers:
            marker.deleteLater()
        self._markers.clear()
        self._build_markers()
        self._position_markers()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(980, 460)

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self._position_markers()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        outer = QRectF(1, 1, self.width() - 2, self.height() - 2)
        painter.setPen(QPen(QColor("#234765"), 1.3))
        painter.setBrush(QColor("#07111d"))
        painter.drawRoundedRect(outer, 18, 18)

        diagram = self._diagram_rect()
        self._draw_panel(
            painter,
            QRectF(diagram.left() + diagram.width() * 0.05, diagram.top() + diagram.height() * 0.13, diagram.width() * 0.36, diagram.height() * 0.72),
            "THROTTLE",
            QColor("#102033"),
            QColor("#315577"),
        )
        self._draw_panel(
            painter,
            QRectF(diagram.left() + diagram.width() * 0.57, diagram.top() + diagram.height() * 0.11, diagram.width() * 0.36, diagram.height() * 0.74),
            "STICK",
            QColor("#132538"),
            QColor("#3e6b91"),
        )

        base = QRectF(diagram.left() + diagram.width() * 0.16, diagram.top() + diagram.height() * 0.74, diagram.width() * 0.68, diagram.height() * 0.16)
        painter.setPen(QPen(QColor("#426f97"), 1.2))
        painter.setBrush(QColor("#0d1a27"))
        painter.drawRoundedRect(base, 22, 22)
        self._draw_grid_lines(painter, diagram)
        self._draw_stick_shape(painter, diagram)
        self._draw_throttle_shape(painter, diagram)

    def _build_markers(self) -> None:
        for control in self._model.routed_controls:
            marker = QLabel(self)
            marker.setObjectName(f"hotasMarker_{control.control_id}")
            marker.setProperty("hotasDiagramMarker", True)
            marker.setProperty("controlType", control.control_type)
            marker.setProperty("status", control.status)
            marker.setToolTip(format_hotas_control_tooltip(control))
            marker.setAccessibleName(f"{control.display_label} mapping detail")
            marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
            marker.setWordWrap(True)
            marker.setText(_marker_text(control))
            marker.setMouseTracking(True)
            self._markers.append((control, marker))
        self._position_markers()

    def _position_markers(self) -> None:
        diagram = self._diagram_rect()
        for control, marker in self._markers:
            width = int(diagram.width() * (control.region_width or 0.10))
            height = int(diagram.height() * (control.region_height or 0.09))
            width = max(62, min(width, 128))
            height = max(34, min(height, 56))
            if control.control_type == "axis":
                width = max(width, 104)
                height = max(height, 46)
            if control.control_type == "hat":
                width = max(width, 110)
            x = int(diagram.left() + diagram.width() * control.anchor_x - width / 2)
            y = int(diagram.top() + diagram.height() * control.anchor_y - height / 2)
            marker.setGeometry(x, y, width, height)

    def _diagram_rect(self) -> QRectF:
        return QRectF(18, 16, max(1, self.width() - 36), max(1, self.height() - 32))

    def _draw_panel(
        self,
        painter: QPainter,
        rect: QRectF,
        label: str,
        fill: QColor,
        border: QColor,
    ) -> None:
        painter.setPen(QPen(border, 1.4))
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, 26, 26)
        painter.setPen(QColor("#6f8daa"))
        font = QFont(painter.font())
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect.adjusted(14, 10, -14, -10), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, label)

    def _draw_grid_lines(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#10283d"), 1))
        for fraction in (0.20, 0.40, 0.60, 0.80):
            x = rect.left() + rect.width() * fraction
            painter.drawLine(QPointF(x, rect.top() + 10), QPointF(x, rect.bottom() - 10))
        for fraction in (0.25, 0.50, 0.75):
            y = rect.top() + rect.height() * fraction
            painter.drawLine(QPointF(rect.left() + 12, y), QPointF(rect.right() - 12, y))

    def _draw_stick_shape(self, painter: QPainter, rect: QRectF) -> None:
        center = QPointF(rect.left() + rect.width() * 0.74, rect.top() + rect.height() * 0.48)
        painter.setPen(QPen(QColor("#53b7ff"), 1.2))
        painter.setBrush(QColor("#0b1724"))
        painter.drawEllipse(center, rect.width() * 0.13, rect.height() * 0.23)
        painter.setPen(QPen(QColor("#76d39b"), 1.1))
        painter.drawEllipse(center, rect.width() * 0.055, rect.height() * 0.11)

    def _draw_throttle_shape(self, painter: QPainter, rect: QRectF) -> None:
        throttle = QRectF(rect.left() + rect.width() * 0.18, rect.top() + rect.height() * 0.20, rect.width() * 0.16, rect.height() * 0.44)
        painter.setPen(QPen(QColor("#76d39b"), 1.2))
        painter.setBrush(QColor("#0b1724"))
        painter.drawRoundedRect(throttle, 18, 18)
        slot = QRectF(throttle.center().x() - 4, throttle.top() + 14, 8, throttle.height() - 28)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#315577"))
        painter.drawRoundedRect(slot, 4, 4)


def _marker_text(control: HotasDiagramControl) -> str:
    if control.control_type == "axis":
        return f"{control.display_label}\n{control.mapped_function}"
    if control.control_type == "button":
        return f"{control.display_label}\n{control.output_intent_target.removeprefix('Output intent: ')}"
    return f"{control.display_label}\n{control.mapped_function}"
