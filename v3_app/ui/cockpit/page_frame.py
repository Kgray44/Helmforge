from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class CockpitPage(QWidget):
    def __init__(
        self,
        *,
        title: str,
        mission: str,
        body: QWidget,
        banner: QWidget | None = None,
        rail: QWidget | None = None,
        actions: QWidget | None = None,
        object_name: str | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName(object_name or "cockpitPage")
        self.setProperty("cockpitPageFrame", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 30)
        layout.setSpacing(16)

        header = QFrame()
        header.setObjectName("cockpitPageHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        copy = QVBoxLayout()
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(7)
        title_label = QLabel(title)
        title_label.setObjectName("cockpitPageTitle")
        mission_label = QLabel(mission)
        mission_label.setObjectName("cockpitPageMission")
        mission_label.setWordWrap(True)
        copy.addWidget(title_label)
        copy.addWidget(mission_label)

        header_layout.addLayout(copy, 1)
        if actions is not None:
            header_layout.addWidget(actions)

        layout.addWidget(header)
        if banner is not None:
            layout.addWidget(banner)
        if rail is not None:
            layout.addWidget(rail)
        layout.addWidget(body)
        layout.addStretch(1)
