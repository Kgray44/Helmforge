from __future__ import annotations


def cockpit_qss() -> str:
    return """
    QWidget#helmforgeShell[uiMode="cockpit"] {
        background: #050a10;
        color: #f4f8fb;
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: 14px;
    }

    QWidget#appSidebar[uiMode="cockpit"] {
        background: #07121b;
        border: 1px solid #24465f;
        border-radius: 8px;
    }

    QWidget#appHeader[uiMode="cockpit"],
    QWidget#appFooter[uiMode="cockpit"] {
        background: #0b1822;
        border: 1px solid #24465f;
        border-radius: 8px;
    }

    QWidget#statusCluster,
    QWidget#assistantCluster,
    QWidget#runtimeCard {
        background: #081520;
        border: 1px solid #24465f;
        border-radius: 8px;
    }

    QWidget#contentViewport[uiMode="cockpit"],
    QStackedWidget#pageStack[uiMode="cockpit"],
    QWidget#pageScrollViewport[uiMode="cockpit"] {
        background: #050a10;
        border: none;
    }

    QScrollArea#pageScrollArea[uiMode="cockpit"] {
        background: #07121b;
        border: 1px solid #173044;
        border-radius: 8px;
    }

    QWidget[cockpitPageFrame="true"] {
        background: #07121b;
        color: #f4f8fb;
    }

    QFrame#cockpitPageHeader {
        background: transparent;
        border: none;
    }

    QLabel#cockpitPageTitle {
        color: #f4f8fb;
        font-size: 26px;
        font-weight: 800;
    }

    QLabel#cockpitPageMission {
        color: #bdd2e1;
        font-size: 14px;
        line-height: 1.35;
    }

    QFrame#cockpitStatusBanner,
    QFrame#cockpitPreflightHero {
        background: #0d1d29;
        border: 1px solid #4a83a7;
        border-radius: 8px;
    }

    QFrame#cockpitToneRail,
    QFrame#cockpitTileRail {
        background: #56c7ff;
        border-radius: 2px;
    }

    QFrame#cockpitToneRail[tone="success"],
    QFrame#cockpitTileRail[tone="success"] {
        background: #79f2a6;
    }

    QFrame#cockpitToneRail[tone="warning"],
    QFrame#cockpitToneRail[tone="caution"],
    QFrame#cockpitTileRail[tone="warning"],
    QFrame#cockpitTileRail[tone="caution"] {
        background: #f2c66d;
    }

    QFrame#cockpitToneRail[tone="danger"],
    QFrame#cockpitTileRail[tone="danger"] {
        background: #ff7f7f;
    }

    QLabel#cockpitBannerTitle,
    QLabel#cockpitPanelTitle,
    QLabel#cockpitTileTitle {
        color: #f4f8fb;
        font-size: 16px;
        font-weight: 800;
    }

    QLabel#cockpitBannerState {
        color: #f4f8fb;
        font-size: 20px;
        font-weight: 800;
    }

    QLabel#cockpitBannerExplanation,
    QLabel#cockpitBannerNextAction,
    QLabel#cockpitPanelBody,
    QLabel#cockpitTileBody {
        color: #bdd2e1;
    }

    QLabel#cockpitBannerNextAction[tone="success"] {
        color: #79f2a6;
    }

    QLabel#cockpitBannerNextAction[tone="warning"],
    QLabel#cockpitBannerNextAction[tone="caution"] {
        color: #f2c66d;
    }

    QLabel#cockpitBannerNextAction[tone="danger"] {
        color: #ff7f7f;
    }

    QFrame#cockpitReadinessRail,
    QFrame#cockpitMappingRouteOverview,
    QFrame#cockpitPreflightInputMetrics,
    QFrame#cockpitPreflightSystemGrid,
    QFrame[cockpitComponent="gridSection"] {
        background: transparent;
        border: none;
    }

    QFrame#cockpitGate,
    QFrame#cockpitSystemTile,
    QFrame#cockpitMetricTile,
    QFrame#cockpitFlowRow,
    QFrame#cockpitChecklistPanel,
    QFrame#cockpitDataGridCard,
    QFrame#cockpitAdvancedPanel,
    QFrame#cockpitAdvancedTechnicalDetails,
    QFrame#cockpitMappingDetailsPanel,
    QFrame#cockpitMappingFlowSummary,
    QFrame#cockpitHotasDiagramPanel,
    QFrame#cockpitDiagnosticsDetailsPanel,
    QFrame[cockpitComponent="systemTile"],
    QFrame[cockpitComponent="metricTile"],
    QFrame[cockpitComponent="flowRow"],
    QFrame[cockpitComponent="checklistPanel"],
    QFrame[cockpitComponent="dataGridCard"],
    QFrame[cockpitComponent="advancedPanel"] {
        background: #0b1822;
        border: 1px solid #24465f;
        border-radius: 8px;
    }

    QFrame#cockpitSystemTile[tone="success"],
    QFrame#cockpitMetricTile[tone="success"],
    QFrame#cockpitGate[tone="success"] {
        border-color: #1f7f4c;
    }

    QFrame#cockpitSystemTile[tone="warning"],
    QFrame#cockpitSystemTile[tone="caution"],
    QFrame#cockpitMetricTile[tone="warning"],
    QFrame#cockpitMetricTile[tone="caution"],
    QFrame#cockpitGate[tone="warning"],
    QFrame#cockpitGate[tone="caution"] {
        border-color: #896422;
    }

    QFrame#cockpitSystemTile[tone="danger"],
    QFrame#cockpitMetricTile[tone="danger"],
    QFrame#cockpitGate[tone="danger"] {
        border-color: #8c3838;
    }

    QLabel#cockpitGateLabel,
    QLabel#cockpitMetricLabel,
    QLabel#cockpitDataGridKey {
        color: #7896aa;
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
    }

    QLabel#cockpitGateValue,
    QLabel#cockpitDataGridValue,
    QLabel#cockpitTileFact,
    QLabel#cockpitChecklistText {
        color: #bdd2e1;
    }

    QLabel#cockpitMetricValue {
        color: #f4f8fb;
        font-size: 24px;
        font-weight: 850;
    }

    QLabel#cockpitMetricValue[tone="success"] {
        color: #79f2a6;
    }

    QLabel#cockpitMetricValue[tone="warning"],
    QLabel#cockpitMetricValue[tone="caution"] {
        color: #f2c66d;
    }

    QLabel#cockpitMetricValue[tone="danger"] {
        color: #ff7f7f;
    }

    QLabel#cockpitMetricHelper {
        color: #7896aa;
    }

    QLabel#cockpitTileStatus,
    QLabel[uiRole="statusChip"] {
        background: #07121b;
        border: 1px solid #24465f;
        border-radius: 8px;
        padding: 5px 10px;
        color: #bdd2e1;
        font-weight: 700;
    }

    QLabel[chipTone="success"],
    QLabel#cockpitTileStatus[chipTone="success"] {
        color: #79f2a6;
        border-color: #1f7f4c;
    }

    QLabel[chipTone="warning"],
    QLabel[chipTone="caution"],
    QLabel#cockpitTileStatus[chipTone="warning"],
    QLabel#cockpitTileStatus[chipTone="caution"] {
        color: #f2c66d;
        border-color: #896422;
    }

    QLabel[chipTone="danger"],
    QLabel#cockpitTileStatus[chipTone="danger"] {
        color: #ff7f7f;
        border-color: #8c3838;
    }

    QLabel#cockpitRoutePill,
    QLabel[uiRole="routePill"] {
        background: #07121b;
        border: 1px solid #2f5f80;
        border-radius: 8px;
        color: #d8ecf7;
        padding: 7px 10px;
        font-weight: 700;
    }

    QLabel#cockpitFlowArrow {
        color: #56c7ff;
        font-weight: 900;
    }

    QFrame#cockpitChecklistRow,
    QFrame#cockpitDataGridRow {
        background: #07121b;
        border: 1px solid #173044;
        border-radius: 8px;
    }

    QLabel#cockpitStatusLight {
        background: #56c7ff;
        border-radius: 5px;
    }

    QLabel#cockpitStatusLight[tone="success"] {
        background: #79f2a6;
    }

    QLabel#cockpitStatusLight[tone="warning"],
    QLabel#cockpitStatusLight[tone="caution"] {
        background: #f2c66d;
    }

    QLabel#cockpitStatusLight[tone="danger"] {
        background: #ff7f7f;
    }

    QWidget[cockpitLegacyWrapped="true"],
    QWidget[cockpitLegacyWrapped="true"] QWidget {
        background: transparent;
    }

    QWidget[cockpitLegacyWrapped="true"] QLabel#pageTitle {
        color: #f4f8fb;
        font-size: 18px;
        font-weight: 800;
    }

    QWidget[cockpitLegacyWrapped="true"] QLabel#pageSubtitle,
    QWidget[cockpitLegacyWrapped="true"] QLabel#pageBody,
    QWidget[cockpitLegacyWrapped="true"] QLabel#cardBody,
    QWidget[cockpitLegacyWrapped="true"] QLabel#sectionHint,
    QWidget[cockpitLegacyWrapped="true"] QLabel#tableMutedText {
        color: #9fb8ca;
    }

    QWidget[cockpitLegacyWrapped="true"] QLabel#cardTitle,
    QWidget[cockpitLegacyWrapped="true"] QLabel#rawTraceTitle,
    QWidget[cockpitLegacyWrapped="true"] QLabel#overlayTraceTitle,
    QWidget[cockpitLegacyWrapped="true"] QLabel#helpArticleSectionTitle {
        color: #f4f8fb;
        font-size: 16px;
        font-weight: 800;
    }

    QWidget[cockpitLegacyWrapped="true"] QFrame[cardRole="pageCard"],
    QWidget[cockpitLegacyWrapped="true"] QWidget#placeholderCard,
    QWidget[cockpitLegacyWrapped="true"] QFrame#routingOverviewCard,
    QWidget[cockpitLegacyWrapped="true"] QFrame#liveRouteSummaryCard,
    QWidget[cockpitLegacyWrapped="true"] QFrame#hotasDiagramCard,
    QWidget[cockpitLegacyWrapped="true"] QFrame#routeRemapCard,
    QWidget[cockpitLegacyWrapped="true"] QFrame#axisRoutingCard,
    QWidget[cockpitLegacyWrapped="true"] QFrame#buttonRoutingCard,
    QWidget[cockpitLegacyWrapped="true"] QFrame#hatRoutingCard,
    QWidget[cockpitLegacyWrapped="true"] QFrame#helpArticleSurface,
    QWidget[cockpitLegacyWrapped="true"] QFrame#helpParameterReferenceBlock,
    QWidget[cockpitLegacyWrapped="true"] QFrame#routeInspectorPanel,
    QWidget[cockpitLegacyWrapped="true"] QFrame#stackStageCard,
    QWidget[cockpitLegacyWrapped="true"] QFrame#stackTotalChangeCard,
    QWidget[cockpitLegacyWrapped="true"] QFrame[uiRole="workflowCard"],
    QWidget[cockpitLegacyWrapped="true"] QFrame[uiRole="preflightDashboard"] {
        background: #0d1d29;
        border: 1px solid #24465f;
        border-radius: 8px;
    }

    QWidget[cockpitLegacyWrapped="true"] QTableWidget,
    QWidget[cockpitLegacyWrapped="true"] QListWidget,
    QWidget[cockpitLegacyWrapped="true"] QTreeWidget,
    QWidget[cockpitLegacyWrapped="true"] QPlainTextEdit {
        background: #07121b;
        alternate-background-color: #0b1822;
        border: 1px solid #24465f;
        border-radius: 8px;
        color: #f4f8fb;
        gridline-color: #173044;
        selection-background-color: #113752;
        selection-color: #ffffff;
    }

    QWidget[cockpitLegacyWrapped="true"] QTableWidget::item {
        min-height: 34px;
        padding: 8px 9px;
    }

    QWidget[cockpitLegacyWrapped="true"] QHeaderView::section {
        background: #0b1822;
        color: #bdd2e1;
        border: none;
        border-bottom: 1px solid #24465f;
        padding: 9px;
        font-weight: 800;
    }

    QWidget[cockpitLegacyWrapped="true"] QLineEdit,
    QWidget[cockpitLegacyWrapped="true"] QComboBox,
    QWidget[cockpitLegacyWrapped="true"] QSpinBox,
    QWidget[cockpitLegacyWrapped="true"] QDoubleSpinBox {
        background: #07121b;
        border: 1px solid #24465f;
        border-radius: 8px;
        color: #f4f8fb;
        padding: 7px 10px;
        min-height: 24px;
    }

    QWidget[cockpitLegacyWrapped="true"] QComboBox::drop-down {
        width: 28px;
        border-left: 1px solid #24465f;
        background: #0b1822;
    }

    QWidget[cockpitLegacyWrapped="true"] QPushButton,
    QPushButton[uiRole="actionButton"] {
        background: #0b2330;
        border: 1px solid #2f5f80;
        border-radius: 8px;
        color: #f4f8fb;
        padding: 8px 12px;
        font-weight: 700;
    }

    QWidget[cockpitLegacyWrapped="true"] QPushButton:hover,
    QPushButton[uiRole="actionButton"]:hover {
        background: #113752;
        border-color: #56c7ff;
    }

    QWidget[cockpitLegacyWrapped="true"] QPushButton:disabled,
    QPushButton[uiRole="actionButton"]:disabled {
        background: #07121b;
        border-color: #173044;
        color: #7896aa;
    }

    QPushButton[navItem="true"] {
        border-radius: 8px;
        min-height: 30px;
        padding: 7px 10px;
    }

    QPushButton[navItem="true"][active="true"] {
        background: #0e3146;
        border-color: #56c7ff;
        color: #ffffff;
    }

    QLabel#activeAccent {
        background: #56c7ff;
        border-radius: 2px;
    }

    QPushButton#applyWorkspaceButton {
        background: #0d3025;
        border-color: #1f7f4c;
        color: #dcffe8;
    }

    QPushButton#saveWorkspaceButton {
        background: #0f2d45;
        border-color: #2f6f9a;
        color: #e1f4ff;
    }

    QScrollBar:vertical {
        background: #07121b;
        width: 10px;
        margin: 2px;
    }

    QScrollBar::handle:vertical {
        background: #2f5f80;
        border-radius: 4px;
        min-height: 60px;
    }
    """
