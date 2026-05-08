from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy

from v3_app.services.parameter_metadata import ParameterMetadata, format_parameter_tooltip


class ParameterInfoIcon(QLabel):
    def __init__(self, metadata: ParameterMetadata) -> None:
        super().__init__("i")
        self.setObjectName("parameterInfoIcon")
        self.setProperty("metadataId", metadata.parameter_id)
        self.setToolTip(format_parameter_tooltip(metadata))
        self.setAccessibleName(f"{metadata.display_name} help")
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(18, 18)
