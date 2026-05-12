from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPageLayout, QPageSize, QPdfWriter
from PySide6.QtWidgets import QApplication


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a PDF report from Liquid UI screenshots.")
    parser.add_argument("--phase", default="lcd-7w", help="Artifact phase id.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    artifact_dir = project_root / "artifacts" / "liquid-ui" / args.phase
    manifest_path = artifact_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Missing screenshot manifest: {manifest_path}")

    app = QApplication.instance() or QApplication([str(project_root)])
    app.setApplicationName("HelmForge Liquid Visual Report")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pdf_path = artifact_dir / f"liquid-ui-{args.phase}-visual-report.pdf"
    writer = QPdfWriter(str(pdf_path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
    writer.setPageMargins(QMarginsF(24, 24, 24, 24), QPageLayout.Unit.Point)
    painter = QPainter(writer)
    try:
        for index, entry in enumerate(manifest):
            if index:
                writer.newPage()
            _draw_page(painter, artifact_dir, entry)
    finally:
        painter.end()
    return 0


def _draw_page(painter: QPainter, artifact_dir: Path, entry: dict[str, str]) -> None:
    page = painter.viewport()
    painter.fillRect(page, QColor(8, 14, 24))
    painter.setPen(QColor(245, 250, 255))
    title_font = QFont("Segoe UI", 18, QFont.Weight.DemiBold)
    body_font = QFont("Segoe UI", 9)
    painter.setFont(title_font)
    painter.drawText(QRectF(28, 24, page.width() - 56, 34), entry["title"])
    painter.setFont(body_font)
    note = (
        f"Route: {entry['route']}\n"
        f"Status: {entry['status']}\n"
        f"Purpose: Visual QA screenshot for the {artifact_dir.name.upper()} Liquid command surface.\n"
        f"Known limitations: static screenshot; runtime output proof is not inferred.\n"
        f"Note: {entry.get('note', '')}"
    )
    painter.setPen(QColor(178, 205, 228))
    painter.drawText(QRectF(28, 58, page.width() - 56, 76), note)

    image_path = artifact_dir / entry["file"]
    image = QImage(str(image_path))
    if image.isNull():
        painter.setPen(QColor(255, 140, 120))
        painter.drawText(QRectF(28, 150, page.width() - 56, 40), f"Screenshot unavailable: {image_path.name}")
        return
    target = QRectF(28, 146, page.width() - 56, page.height() - 174)
    scaled = image.scaled(
        int(target.width()),
        int(target.height()),
        aspectMode=Qt.AspectRatioMode.KeepAspectRatio,
        mode=Qt.TransformationMode.SmoothTransformation,
    )
    x = target.x() + (target.width() - scaled.width()) / 2
    y = target.y() + (target.height() - scaled.height()) / 2
    painter.drawImage(QRectF(x, y, scaled.width(), scaled.height()), scaled)


if __name__ == "__main__":
    raise SystemExit(main())
