from __future__ import annotations


def app_qss() -> str:
    return """
    QMainWindow, QWidget#helmforgeShell {
        background: #07111d;
        color: #f5f9ff;
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: 15px;
    }

    QWidget#appSidebar,
    QWidget#appHeader,
    QWidget#appFooter,
    QWidget#runtimeCard,
    QWidget#placeholderCard {
        background: #101d2a;
        border: 1px solid #28496a;
        border-radius: 18px;
    }

    QWidget#contentViewport,
    QScrollArea#pageScrollArea,
    QStackedWidget#pageStack {
        background: #07111d;
        border: none;
    }

    QScrollArea#pageScrollArea > QWidget > QWidget {
        background: #07111d;
    }

    QLabel {
        color: #f5f9ff;
        background: transparent;
        border: none;
    }

    QLabel#brandTitle,
    QLabel#headerTitle {
        color: #ffffff;
        font-weight: 800;
    }

    QLabel#brandTitle {
        font-size: 28px;
    }

    QLabel#headerTitle {
        font-size: 30px;
    }

    QLabel#pageTitle {
        font-size: 23px;
        font-weight: 750;
    }

    QLabel#cardTitle {
        font-size: 18px;
        font-weight: 750;
    }

    QLabel#brandSubtitle,
    QLabel#headerSubtitle,
    QLabel#pageSubtitle,
    QLabel#cardBody,
    QLabel#footerDetail,
    QLabel#footerPageDetail {
        color: #a8c3dc;
    }

    QLabel#sectionLabel,
    QLabel#clusterLabel {
        color: #6f8daa;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0px;
    }

    QLabel#sectionHint {
        color: #6f8daa;
        font-size: 12px;
    }

    QLabel[uiRole="statusChip"] {
        background: #050b12;
        border: 1px solid #28496a;
        border-radius: 9px;
        padding: 7px 14px;
        color: #b9d4ec;
    }

    QLabel[chipTone="success"] {
        color: #96ffc5;
        border-color: #2f8f60;
    }

    QLabel[chipTone="warning"],
    QLabel[chipTone="caution"] {
        color: #f0c46a;
        border-color: #8d6c24;
    }

    QLabel[chipTone="danger"] {
        color: #ff9a9a;
        border-color: #8d3d3d;
    }

    QPushButton {
        background: #0b1724;
        border: 1px solid #385a7c;
        border-radius: 10px;
        padding: 9px 14px;
        color: #f5f9ff;
    }

    QPushButton:hover {
        background: #15283a;
        border-color: #53b7ff;
    }

    QPushButton[uiRole="actionButton"] {
        background: #102f4c;
        border-color: #3e8ec5;
        font-weight: 650;
    }

    QPushButton#saveWorkspaceButton,
    QPushButton#helmButton {
        background: #174f7e;
        border-color: #53b7ff;
    }

    QPushButton[navItem="true"] {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 14px;
        padding: 11px 18px;
        text-align: left;
        color: #f5f9ff;
        font-weight: 600;
    }

    QPushButton[navItem="true"]:hover {
        background: #10283d;
        border-color: #28496a;
    }

    QPushButton[navItem="true"][active="true"] {
        background: #123d61;
        border-color: #53b7ff;
        color: #ffffff;
    }

    QLabel#activeAccent {
        background: #53b7ff;
        border-radius: 2px;
    }

    QScrollBar:vertical {
        background: #07111d;
        width: 10px;
        margin: 2px;
    }

    QScrollBar::handle:vertical {
        background: #2e5a84;
        border-radius: 4px;
        min-height: 60px;
    }

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """
