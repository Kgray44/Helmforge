from __future__ import annotations


def app_qss() -> str:
    return """
    QMainWindow, QWidget#helmforgeShell {
        background: #07111d;
        color: #f5f9ff;
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: 15px;
    }

    QWidget#appHeader,
    QWidget#appFooter,
    QDialog#helmOverlay,
    QWidget#runtimeCard,
    QWidget#placeholderCard,
    QFrame[cardRole="pageCard"],
    QFrame#routingOverviewCard,
    QFrame#liveRouteSummaryCard,
    QFrame#hotasDiagramCard,
    QFrame#runtimePreflightCard,
    QFrame#axisRoutingCard,
    QFrame#buttonRoutingCard,
    QFrame#hatRoutingCard {
        background: #101d2a;
        border: 1px solid #28496a;
        border-radius: 18px;
    }

    QWidget#appSidebar {
        background: #0b1724;
        border: 1px solid #4f789f;
        border-radius: 20px;
    }

    QWidget#appSidebar:hover {
        border-color: #5f8db8;
    }

    QWidget#statusCluster,
    QWidget#assistantCluster {
        background: #0d1b29;
        border: 1px solid #41698d;
        border-radius: 14px;
    }

    QWidget#helmOverlayScrim {
        background: rgba(3, 8, 14, 132);
        border: none;
    }

    QWidget#contentViewport,
    QWidget#helmOverlayContent,
    QWidget#pageScrollViewport,
    QScrollArea#helmOverlayScrollArea,
    QStackedWidget#pageStack {
        background: #07111d;
        border: none;
    }

    QScrollArea#pageScrollArea {
        background: #0a1420;
        border: 1px solid #315577;
        border-radius: 16px;
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
        font-size: 24px;
    }

    QLabel#headerTitle {
        font-size: 30px;
    }

    QLabel#pageTitle {
        font-size: 23px;
        font-weight: 750;
    }

    QLabel#cardTitle,
    QLabel#rawTraceTitle,
    QLabel#overlayTraceTitle {
        font-size: 18px;
        font-weight: 750;
    }

    QLabel#brandSubtitle,
    QLabel#headerSubtitle,
    QLabel#pageSubtitle,
    QLabel#pageBody,
    QLabel#cardBody,
    QLabel#routingOverviewNote,
    QLabel#tableMutedText,
    QLabel#footerDetail,
    QLabel#footerPageDetail {
        color: #a8c3dc;
    }

    QLabel#brandSubtitle {
        font-size: 12px;
    }

    QLabel#routeSummaryValue {
        color: #f5f9ff;
        font-weight: 550;
    }

    QLabel[uiRole="truthNotice"] {
        background: #0b1724;
        border: 1px solid #315577;
        border-left: 4px solid #96ffc5;
        border-radius: 12px;
        color: #cdeeff;
        padding: 10px 12px;
        line-height: 1.35;
    }

    QLabel[uiRole="sectionKicker"] {
        color: #96ffc5;
        font-size: 12px;
        font-weight: 750;
        text-transform: uppercase;
    }

    QFrame[uiRole="workflowCard"] {
        border-color: #3e6b91;
        background: #0e1c2a;
    }

    QFrame#hotasDiagramWidget {
        background: #07111d;
        border: 1px solid #203a55;
        border-radius: 18px;
    }

    QFrame#routeInspectorPanel {
        background: #0b1724;
        border: 1px solid #28496a;
        border-radius: 12px;
    }

    QFrame#routeEditorPanel {
        background: #0a1622;
        border: 1px solid #3e6b91;
        border-radius: 12px;
    }

    QFrame[uiRole="preflightDashboard"],
    QFrame#stackTotalChangeCard {
        background: #0b1724;
        border: 1px solid #3e6b91;
        border-radius: 14px;
    }

    QLabel[hotasDiagramMarker="true"] {
        background: #0b1724;
        border: 1px solid #315577;
        border-radius: 10px;
        color: #f5f9ff;
        font-size: 10px;
        font-weight: 700;
        padding: 3px 5px;
    }

    QLabel[hotasDiagramMarker="true"][controlType="axis"] {
        border-color: #53b7ff;
        color: #cdeeff;
    }

    QLabel[hotasDiagramMarker="true"][controlType="button"] {
        border-color: #426f97;
        color: #dceeff;
    }

    QLabel[hotasDiagramMarker="true"][controlType="hat"] {
        border-color: #76d39b;
        color: #d9ffe7;
    }

    QLabel[hotasDiagramMarker="true"][status="unmapped"] {
        border-color: #8d6c24;
        color: #f0c46a;
    }

    QLabel[hotasDiagramMarker="true"][selected="true"] {
        background: #123d61;
        border: 2px solid #96ffc5;
        color: #ffffff;
    }

    QLabel[hotasDiagramMarker="true"][hasWarning="true"] {
        border: 2px solid #f0c46a;
        color: #fff1bc;
    }

    QLabel[hotasDiagramMarker="true"][filteredOut="true"] {
        background: #08111b;
        border-color: #20364d;
        color: #6f8daa;
    }

    QLabel[hotasDiagramMarker="true"]:focus {
        border: 2px solid #96ffc5;
    }

    QLabel[inspectorValue="true"] {
        color: #f5f9ff;
        font-weight: 600;
    }

    QLabel#hotasDiagramLegend {
        color: #a8c3dc;
    }

    QLabel#snapshotValue {
        color: #ffffff;
        font-size: 22px;
        font-weight: 800;
    }

    QLabel[metricValue="true"] {
        color: #ffffff;
        font-size: 20px;
        font-weight: 800;
    }

    QLabel#formLabel {
        color: #dceeff;
        font-weight: 650;
    }

    QLabel#parameterInfoIcon {
        background: #0b1724;
        border: 1px solid #3e6b91;
        border-radius: 9px;
        color: #a8dfff;
        font-size: 11px;
        font-weight: 800;
        min-width: 18px;
        min-height: 18px;
        max-width: 18px;
        max-height: 18px;
    }

    QLabel#parameterInfoIcon:hover {
        background: #123a58;
        border-color: #53b7ff;
        color: #ffffff;
    }

    QLabel#axisListItem,
    QPushButton#axisListItem {
        color: #f5f9ff;
        padding: 10px 14px;
        border-radius: 10px;
        text-align: left;
    }

    QPushButton#axisListItem {
        background: transparent;
        border: 1px solid transparent;
        font-weight: 650;
    }

    QPushButton#axisListItem:hover {
        background: #10283d;
        border-color: #28496a;
    }

    QLabel#axisListItem[active="true"],
    QPushButton#axisListItem[active="true"],
    QPushButton#axisListItem:checked {
        background: #153b5a;
        border-color: #53b7ff;
        color: #ffffff;
    }

    QFrame#axisListFrame {
        background: #09131e;
        border: 1px solid #28496a;
        border-radius: 12px;
    }

    QFrame#stackStageCard {
        background: #132538;
        border: 1px solid #315577;
        border-radius: 14px;
    }

    QFrame#stackStageCard[selected="true"] {
        background: #163b56;
        border-color: #53b7ff;
    }

    QFrame#stackStageCard[mostImpactful="true"] {
        border-color: #76d39b;
    }

    QLabel#sectionLabel,
    QLabel#clusterLabel {
        color: #6f8daa;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0px;
    }

    QLabel#sectionHint {
        color: #6f8daa;
        font-size: 11px;
    }

    QLabel[uiRole="statusChip"] {
        background: #050b12;
        border: 1px solid #28496a;
        border-radius: 9px;
        padding: 7px 14px;
        color: #b9d4ec;
        font-weight: 600;
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

    QPushButton,
    QToolButton {
        background: #0b1724;
        border: 1px solid #385a7c;
        border-radius: 10px;
        padding: 9px 14px;
        color: #f5f9ff;
    }

    QPushButton:hover,
    QToolButton:hover {
        background: #15283a;
        border-color: #53b7ff;
    }

    QPushButton:pressed,
    QToolButton:pressed {
        background: #174f7e;
        border-color: #96ffc5;
    }

    QPushButton:checked,
    QToolButton:checked {
        background: #123d61;
        border-color: #53b7ff;
    }

    QPushButton:focus,
    QToolButton:focus {
        border-color: #96ffc5;
    }

    QPushButton:disabled,
    QToolButton:disabled {
        background: #08111b;
        border-color: #20364d;
        color: #6f8daa;
    }

    QPushButton[uiRole="actionButton"] {
        background: #0d2236;
        border-color: #3e6b91;
        font-weight: 650;
    }

    QPushButton[uiRole="actionButton"]:hover {
        background: #123a58;
        border-color: #53b7ff;
    }

    QPushButton[uiRole="actionButton"]:pressed,
    QPushButton[uiRole="actionButton"]:checked {
        background: #174f7e;
        border-color: #96ffc5;
    }

    QPushButton[uiRole="actionButton"]:disabled {
        background: #0a1520;
        border-color: #263b52;
        color: #6f8daa;
    }

    QPushButton[routeFilterChip="true"] {
        padding: 6px 10px;
        border-radius: 9px;
        font-size: 12px;
    }

    QPushButton[routeFilterChip="true"]:checked {
        background: #153b5a;
        border-color: #96ffc5;
        color: #ffffff;
    }

    QTableWidget {
        background: #07111d;
        alternate-background-color: #0a1521;
        border: 1px solid #203a55;
        border-radius: 10px;
        color: #f5f9ff;
        gridline-color: #10263b;
        selection-background-color: #143d5f;
        selection-color: #ffffff;
    }

    QTableWidget::item {
        padding: 7px 8px;
        border: none;
    }

    QTableWidget::item:selected {
        background: #153b5a;
        color: #ffffff;
    }

    QHeaderView::section {
        background: #0d1a27;
        color: #a8c3dc;
        border: none;
        border-bottom: 1px solid #28496a;
        padding: 8px;
        font-weight: 600;
    }

    QListWidget {
        background: #07111d;
        border: 1px solid #203a55;
        border-radius: 10px;
        color: #f5f9ff;
        padding: 8px;
    }

    QListWidget::item {
        padding: 9px 10px;
        border-radius: 8px;
    }

    QListWidget::item:selected {
        background: #143d5f;
        color: #ffffff;
    }

    QListWidget::item:hover {
        background: #10283d;
    }

    QCheckBox {
        background: transparent;
        color: #f5f9ff;
        spacing: 6px;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1px solid #3e6b91;
        background: #07111d;
    }

    QCheckBox::indicator:checked {
        background: #53b7ff;
        border-color: #96ffc5;
    }

    QProgressBar {
        background: #07111d;
        border: 1px solid #10263b;
        border-radius: 6px;
        min-height: 9px;
        max-height: 9px;
    }

    QProgressBar::chunk {
        background: #53b7ff;
        border-radius: 5px;
    }

    QProgressBar[levelKind="final"]::chunk {
        background: #76d39b;
    }

    QLineEdit,
    QComboBox,
    QPlainTextEdit {
        background: #07111d;
        border: 1px solid #28496a;
        border-radius: 10px;
        color: #f5f9ff;
        padding: 8px 12px;
        min-height: 24px;
    }

    QLineEdit:focus,
    QComboBox:focus,
    QPlainTextEdit:focus {
        border-color: #53b7ff;
    }

    QComboBox {
        padding-right: 30px;
        selection-background-color: #174f7e;
        selection-color: #ffffff;
    }

    QComboBox:hover {
        border-color: #53b7ff;
        background: #0b1724;
    }

    QComboBox:disabled {
        background: #08111b;
        border-color: #20364d;
        color: #6f8daa;
    }

    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 28px;
        border-left: 1px solid #28496a;
        border-top-right-radius: 9px;
        border-bottom-right-radius: 9px;
        background: #0d1a27;
    }

    QComboBox::down-arrow {
        width: 0px;
        height: 0px;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #a8c3dc;
        margin-right: 8px;
    }

    QComboBox QAbstractItemView {
        background: #0b1724;
        color: #f5f9ff;
        border: 1px solid #315577;
        selection-background-color: #174f7e;
        selection-color: #ffffff;
        outline: 0px;
        padding: 6px;
    }

    QComboBox QAbstractItemView::item {
        min-height: 28px;
        padding: 7px 10px;
        border-radius: 7px;
        color: #f5f9ff;
        background: transparent;
    }

    QComboBox QAbstractItemView::item:hover {
        background: #123a58;
        color: #ffffff;
    }

    QComboBox QAbstractItemView::item:selected {
        background: #174f7e;
        color: #ffffff;
    }

    QPushButton[uiRole="symptomChip"] {
        background: #0c1a27;
        border-color: #2d4d6f;
        padding: 5px 9px;
        font-size: 12px;
        font-weight: 500;
    }

    QPushButton[uiRole="symptomChip"]:hover {
        background: #12314b;
        border-color: #53b7ff;
    }

    QLabel#helmActiveBulb,
    QLabel#helmPulseIndicator {
        background: qradialgradient(cx:0.42, cy:0.38, radius:0.72, fx:0.32, fy:0.28,
            stop:0 #f0fff6, stop:0.23 #96ffc5, stop:0.58 #45c97d, stop:1 #153c2b);
        border: 5px solid #2f8f60;
        border-radius: 12px;
    }

    QWidget#helmActionRow {
        border-top: 1px solid #203a55;
    }

    QFrame#helmRecommendationCard QLabel#routeSummaryValue,
    QFrame#helmFindingCard QLabel#routeSummaryValue,
    QFrame#helmApplyRevertCard QLabel#routeSummaryValue {
        color: #ffffff;
        font-size: 16px;
        font-weight: 750;
    }

    QTreeWidget {
        background: #07111d;
        border: 1px solid #28496a;
        border-radius: 12px;
        color: #f5f9ff;
        padding: 8px;
    }

    QTreeWidget::item {
        padding: 4px 6px;
    }

    QTreeWidget::item:selected {
        background: #153b5a;
    }

    QTreeWidget#helpDocsTopicTree {
        background: #07111d;
        border: 1px solid #315577;
        border-radius: 12px;
        color: #dceeff;
        padding: 8px;
        alternate-background-color: #0a1521;
    }

    QTreeWidget#helpDocsTopicTree::item {
        min-height: 24px;
        padding: 5px 8px;
        border-radius: 8px;
    }

    QTreeWidget#helpDocsTopicTree::item:selected {
        background: #143d5f;
        color: #f5f9ff;
    }

    QTreeWidget#helpDocsTopicTree::item:hover {
        background: #10283d;
        color: #f5f9ff;
    }

    QFrame#helpArticleSurface {
        background: #091622;
        border: 1px solid #254766;
        border-radius: 14px;
    }

    QFrame#helpArticleSection {
        background: transparent;
        border: none;
        border-bottom: 1px solid #173149;
        border-radius: 0px;
        padding-bottom: 8px;
    }

    QLabel#helpArticleSectionTitle {
        color: #dceeff;
        font-size: 16px;
        font-weight: 750;
    }

    QLabel#helpArticleParagraph {
        color: #b9d4ec;
        font-size: 13px;
        line-height: 1.35;
    }

    QLabel#helpArticleRelated {
        color: #8fb4d0;
        border-top: 1px solid #173149;
        padding-top: 9px;
    }

    QFrame#helpParameterReferenceBlock {
        background: #0d1d2c;
        border: 1px solid #315577;
        border-radius: 10px;
    }

    QLabel#helpParameterName {
        color: #e7f3ff;
        font-weight: 750;
    }

    QLabel#helpParameterValue {
        color: #c6ddef;
        font-weight: 550;
    }

    QLabel#helpParameterWarning {
        color: #f0c46a;
        font-weight: 600;
    }

    QPushButton#saveWorkspaceButton {
        background: #12314b;
        border-color: #4f91c0;
    }

    QPushButton#saveWorkspaceButton:hover {
        background: #174f7e;
        border-color: #53b7ff;
    }

    QPushButton#saveWorkspaceButton:pressed {
        background: #1d638f;
        border-color: #96ffc5;
    }

    QPushButton[navItem="true"] {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 10px;
        padding: 6px 10px;
        text-align: left;
        color: #f5f9ff;
        font-weight: 600;
        min-height: 28px;
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
