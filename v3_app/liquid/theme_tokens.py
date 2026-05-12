from __future__ import annotations


class LiquidColors:
    dark_base = "#050b12"
    deck_base = "#07131f"
    deck_base_alt = "#0a1826"
    glass_panel_fill = "rgba(12, 28, 43, 224)"
    glass_panel_fill_alt = "rgba(16, 39, 57, 214)"
    glass_panel_deep = "rgba(5, 14, 24, 238)"
    glass_panel_soft = "rgba(20, 48, 68, 178)"
    dock_fill = "rgba(8, 19, 31, 232)"
    page_fill = "rgba(9, 21, 34, 238)"
    border_highlight = "#78d9ff"
    border_muted = "#264963"
    border_warm = "#576573"
    primary_text = "#f7fbff"
    muted_text = "#9fb9cf"
    dim_text = "#66879f"
    status_green = "#7ee0a6"
    status_amber = "#f2c66d"
    status_red = "#ff7171"
    status_cyan = "#76d9ff"
    shadow = "rgba(0, 0, 0, 120)"


class LiquidLayout:
    window_width = 1840
    window_height = 1040
    window_min_width = 1360
    window_min_height = 800
    shell_margin = 18
    shell_spacing = 12
    top_bar_height = 76
    footer_height = 56
    footer_clearance_height = 86
    mode_dock_width = 88
    mode_button_height = 48
    panel_radius = 22
    inner_radius = 16


def liquid_qss() -> str:
    colors = LiquidColors
    return f"""
    QWidget#liquidCommandShell {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 {colors.dark_base},
            stop: 0.44 {colors.deck_base},
            stop: 1 #02060b
        );
        color: {colors.primary_text};
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: 14px;
    }}

    QToolTip {{
        background-color: rgba(5, 15, 25, 238);
        border: 1px solid rgba(118, 217, 255, 150);
        border-radius: 9px;
        color: {colors.primary_text};
        padding: 7px 9px;
        font-weight: 750;
    }}

    QFrame#liquidTopCommandBar {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 0,
            stop: 0 rgba(15, 38, 57, 230),
            stop: 0.5 rgba(9, 23, 37, 214),
            stop: 1 rgba(17, 42, 57, 224)
        );
        border: 1px solid rgba(120, 217, 255, 120);
        border-radius: {LiquidLayout.panel_radius}px;
    }}

    QFrame#liquidCommandWorkspace {{
        background: transparent;
        border: none;
    }}

    QFrame#liquid_command_surface {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(34, 80, 108, 142),
            stop: 0.42 rgba(8, 24, 38, 220),
            stop: 1 rgba(3, 9, 15, 238)
        );
        border: 1px solid rgba(120, 217, 255, 90);
        border-radius: 26px;
    }}

    QFrame#liquid_surface_glass_field {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(80, 190, 255, 18),
            stop: 0.44 rgba(11, 34, 52, 42),
            stop: 1 rgba(4, 12, 20, 28)
        );
        border: 1px solid rgba(118, 217, 255, 42);
        border-radius: 22px;
    }}

    QFrame#liquid_footer_clearance {{
        background: transparent;
        border: none;
    }}

    QFrame#liquid_subpage_selector {{
        background: rgba(5, 15, 25, 132);
        border: 1px solid rgba(118, 217, 255, 58);
        border-radius: 14px;
    }}

    QFrame#liquid_subpage_selector[singleRouteMode="true"] {{
        background: rgba(5, 15, 25, 72);
        border-color: rgba(118, 217, 255, 34);
        border-radius: 12px;
    }}

    QScrollArea#liquid_page_scroll_area {{
        background: transparent;
        border: none;
    }}

    QScrollArea#liquid_page_scroll_area > QWidget > QWidget {{
        background: transparent;
    }}

    QScrollBar:vertical {{
        background: rgba(3, 10, 18, 58);
        border: none;
        border-radius: 3px;
        margin: 2px 0px 2px 0px;
        width: 5px;
    }}

    QScrollBar::handle:vertical {{
        background: rgba(92, 139, 164, 82);
        border-radius: 3px;
        min-height: 28px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: rgba(118, 217, 255, 116);
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        background: transparent;
        border: none;
        height: 0px;
    }}

    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QFrame#liquid_floating_mode_dock {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 rgba(15, 38, 53, 226),
            stop: 0.52 rgba(6, 16, 28, 232),
            stop: 1 rgba(12, 28, 40, 224)
        );
        border: 1px solid rgba(118, 217, 255, 104);
        border-radius: 24px;
    }}

    QFrame#liquid_radial_anchor_orb {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(247, 251, 255, 150),
            stop: 0.22 rgba(118, 217, 255, 130),
            stop: 0.58 rgba(16, 62, 78, 230),
            stop: 1 rgba(4, 12, 20, 240)
        );
        border: 1px solid rgba(126, 224, 166, 156);
        border-radius: 24px;
    }}

    QFrame#liquid_floating_footer_strip {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 0,
            stop: 0 rgba(7, 18, 29, 218),
            stop: 0.52 rgba(13, 36, 52, 230),
            stop: 1 rgba(7, 18, 29, 218)
        );
        border: 1px solid rgba(118, 217, 255, 96);
        border-radius: 20px;
    }}

    QStackedWidget#liquid_page_host {{
        background: transparent;
        border: none;
    }}

    QFrame[liquidRole="placeholderPage"] {{
        background: transparent;
        border: none;
    }}

    QFrame[liquidRole="liquid_status_cluster"],
    QFrame[liquidRole="liquid_command_cluster"] {{
        background: rgba(5, 15, 25, 188);
        border: 1px solid rgba(118, 217, 255, 96);
        border-radius: 17px;
    }}

    QFrame[liquidRole="liquid_command_cluster"][compactActionCluster="true"] {{
        background: rgba(5, 15, 25, 150);
        border-color: rgba(118, 217, 255, 72);
    }}

    QFrame[liquidRole="liquid_status_rail"] {{
        background: rgba(126, 224, 166, 92);
        border: 1px solid rgba(126, 224, 166, 150);
        border-radius: 5px;
    }}

    QFrame[liquidRole="liquid_command_orb"] {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(247, 251, 255, 156),
            stop: 0.22 rgba(118, 217, 255, 130),
            stop: 0.58 rgba(17, 55, 77, 230),
            stop: 1 rgba(4, 12, 20, 240)
        );
        border: 1px solid rgba(126, 224, 166, 150);
        border-radius: 21px;
    }}

    QFrame[liquidRole="liquid_hero_region"] {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(25, 63, 86, 218),
            stop: 0.54 rgba(9, 28, 45, 236),
            stop: 1 rgba(4, 12, 20, 238)
        );
        border: 1px solid rgba(118, 217, 255, 108);
        border-radius: 24px;
    }}

    QFrame[liquidRole="liquid_context_inspector_region"],
    QFrame[liquidRole="liquid_detail_action_region"] {{
        background: rgba(7, 20, 33, 206);
        border: 1px solid rgba(72, 112, 140, 116);
        border-radius: 18px;
    }}

    QFrame[liquidRole="liquid_advanced_region"] {{
        background: rgba(6, 17, 28, 172);
        border: 1px solid rgba(72, 112, 140, 82);
        border-radius: 16px;
    }}

    QLabel#liquidDeckTitle {{
        color: {colors.primary_text};
        font-size: 24px;
        font-weight: 800;
    }}

    QLabel#liquidOrbText {{
        color: #eaffff;
        font-size: 12px;
        font-weight: 900;
    }}

    QLabel#liquidDeckSubtitle,
    QLabel#liquidPlaceholderPurpose,
    QLabel#liquidPlaceholderNotice,
    QLabel#liquidPanelBody,
    QLabel#liquidFooterStatusMessage {{
        color: {colors.muted_text};
    }}

    QLabel#liquidModeKicker,
    QLabel#liquidPlaceholderKicker,
    QLabel#liquidPanelKicker {{
        color: {colors.status_cyan};
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0px;
        text-transform: uppercase;
    }}

    QLabel#liquidPlaceholderTitle {{
        color: {colors.primary_text};
        font-size: 26px;
        font-weight: 800;
    }}

    QLabel#liquidPlaceholderSubpageTitle {{
        color: {colors.status_cyan};
        font-size: 18px;
        font-weight: 800;
    }}

    QLabel#liquidHeroTitle {{
        color: #ffffff;
        font-size: 34px;
        font-weight: 800;
    }}

    QLabel[uiRole="liquidStatusChip"] {{
        background: rgba(7, 17, 29, 218);
        border: 1px solid {colors.border_muted};
        border-radius: 11px;
        color: {colors.primary_text};
        padding: 7px 11px;
        font-weight: 700;
    }}

    QLabel[uiRole="liquidStatusChip"][chipTone="success"] {{
        border-color: {colors.status_green};
        color: {colors.status_green};
    }}

    QLabel[uiRole="liquidStatusChip"][chipTone="warning"],
    QLabel[uiRole="liquidStatusChip"][chipTone="caution"] {{
        border-color: {colors.status_amber};
        color: {colors.status_amber};
    }}

    QLabel[uiRole="liquidStatusChip"][chipTone="danger"] {{
        border-color: {colors.status_red};
        color: {colors.status_red};
    }}

    QLabel[uiRole="liquidStatusChip"][chipTone="info"],
    QLabel[uiRole="liquidStatusChip"][chipTone="neutral"] {{
        border-color: {colors.status_cyan};
        color: {colors.status_cyan};
    }}

    QPushButton[uiRole="liquidModeDockButton"] {{
        background: rgba(8, 20, 32, 188);
        border: 1px solid rgba(72, 112, 140, 120);
        border-radius: 18px;
        color: {colors.primary_text};
        font-size: 18px;
        font-weight: 900;
        min-height: {LiquidLayout.mode_button_height}px;
        max-height: {LiquidLayout.mode_button_height}px;
        padding: 0px;
    }}

    QLabel#liquidSubpageSelectorModeLabel {{
        color: {colors.status_cyan};
        font-size: 11px;
        font-weight: 850;
        padding: 5px 7px 5px 3px;
    }}

    QPushButton[uiRole="liquidSubpageSelectorButton"] {{
        background: rgba(8, 20, 32, 188);
        border: 1px solid rgba(72, 112, 140, 120);
        border-radius: 12px;
        color: {colors.primary_text};
        font-weight: 760;
        padding: 6px 9px;
    }}

    QPushButton[uiRole="liquidSubpageSelectorButton"][selectorDensity="single_route_chip"] {{
        background: rgba(8, 20, 32, 96);
        border-color: rgba(118, 217, 255, 44);
        border-radius: 10px;
        color: {colors.muted_text};
        padding: 4px 8px;
    }}

    QPushButton[uiRole="liquidActionButton"] {{
        background: rgba(9, 22, 35, 218);
        border: 1px solid {colors.border_muted};
        border-radius: 12px;
        color: {colors.primary_text};
        font-weight: 750;
        padding: 8px 12px;
    }}

    QPushButton[uiRole="liquidModeDockButton"]:hover {{
        border-color: {colors.status_cyan};
        background: rgba(18, 46, 64, 220);
    }}

    QPushButton[uiRole="liquidActionButton"]:hover {{
        border-color: {colors.status_cyan};
        background: rgba(13, 35, 55, 232);
    }}

    QPushButton[uiRole="liquidSubpageSelectorButton"]:hover {{
        border-color: {colors.status_cyan};
        background: rgba(18, 46, 64, 220);
    }}

    QPushButton[uiRole="liquidModeDockButton"][active="true"],
    QPushButton[uiRole="liquidModeDockButton"]:checked {{
        border-color: {colors.status_green};
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(126, 224, 166, 145),
            stop: 0.38 rgba(34, 78, 92, 236),
            stop: 1 rgba(8, 22, 34, 238)
        );
        color: #ffffff;
    }}

    QPushButton[uiRole="liquidSubpageSelectorButton"][active="true"],
    QPushButton[uiRole="liquidSubpageSelectorButton"]:checked {{
        border-color: {colors.status_green};
        background: rgba(28, 75, 72, 220);
        color: #ffffff;
    }}

    QLabel#liquidDockActiveLabel {{
        background: rgba(7, 18, 29, 180);
        border: 1px solid rgba(118, 217, 255, 92);
        border-radius: 10px;
        color: {colors.status_cyan};
        font-size: 10px;
        font-weight: 800;
        padding: 5px 4px;
    }}

    QLabel#liquidDockHoverLabel {{
        background: rgba(5, 15, 25, 214);
        border: 1px solid rgba(118, 217, 255, 86);
        border-radius: 10px;
        color: {colors.primary_text};
        font-size: 10px;
        font-weight: 800;
        padding: 5px 4px;
    }}

    QPushButton[uiRole="liquidActionButton"]:disabled {{
        background: rgba(8, 15, 24, 188);
        border-color: #1d3448;
        color: {colors.dim_text};
    }}

    QFrame[liquidComponent="true"] {{
        background: rgba(7, 20, 33, 204);
        border: 1px solid rgba(72, 112, 140, 116);
        border-radius: 16px;
    }}

    QFrame[componentRole="LiquidPage"],
    QFrame[liquidRole="liquid_page_slot"] {{
        background: transparent;
        border: none;
    }}

    QFrame[componentRole="LiquidPageHeader"],
    QFrame[componentRole="LiquidStatusRail"] {{
        background: rgba(5, 15, 25, 188);
        border: 1px solid rgba(118, 217, 255, 96);
        border-radius: 17px;
    }}

    QFrame#liquidPreflightStatusRail[mergedIntoHero="true"] {{
        background: transparent;
        border: none;
        min-height: 0px;
        max-height: 0px;
    }}

    QFrame#liquidPreflightPageHeader {{
        background: rgba(5, 15, 25, 104);
        border: 1px solid rgba(118, 217, 255, 42);
        border-radius: 14px;
    }}

    QFrame[componentRole="LiquidPlaceholderHeader"] {{
        background: rgba(5, 15, 25, 146);
        border: 1px solid rgba(118, 217, 255, 64);
        border-radius: 16px;
    }}

    QFrame[liquidRole="liquid_placeholder_header_title_region"],
    QFrame[liquidRole="liquid_placeholder_header_subtitle_region"],
    QFrame[liquidRole="liquid_placeholder_header_chip_region"] {{
        background: transparent;
        border: none;
    }}

    QFrame[componentRole="LiquidHeroPanel"],
    QFrame[componentRole="LiquidInstrumentPanel"] {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(25, 63, 86, 218),
            stop: 0.54 rgba(9, 28, 45, 236),
            stop: 1 rgba(4, 12, 20, 238)
        );
        border: 1px solid rgba(118, 217, 255, 108);
        border-radius: 22px;
    }}

    QFrame#liquidPreflightHeroGoNoGo[preflightVisualRole="primary_go_no_go"] {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(41, 92, 112, 236),
            stop: 0.34 rgba(9, 31, 49, 242),
            stop: 1 rgba(4, 12, 20, 244)
        );
        border: 1px solid rgba(118, 217, 255, 142);
        border-radius: 24px;
    }}

    QFrame#liquidPreflightHeroGoNoGo QLabel#liquidComponentTitle {{
        font-size: 30px;
        font-weight: 900;
    }}

    QFrame#liquidPreflightHeroGoNoGo QLabel#liquidComponentBody {{
        font-size: 15px;
        color: {colors.primary_text};
    }}

    QFrame#liquidPreflightHeroTruthChips,
    QFrame#liquidPreflightReadinessGates {{
        background: transparent;
        border: none;
        border-radius: 0px;
    }}

    QFrame[componentRole="ReadinessGate"][preflightGateVisual="compact_scan"] {{
        background: rgba(7, 20, 33, 146);
        border: 1px solid rgba(72, 112, 140, 88);
        border-radius: 14px;
    }}

    QFrame[componentRole="ReadinessGate"][preflightGateVisual="compact_scan"][gateEmphasis="subtle"] {{
        background: rgba(7, 25, 32, 126);
        border-color: rgba(126, 224, 166, 66);
    }}

    QFrame[componentRole="LiquidInspectorPanel"],
    QFrame[componentRole="LiquidDetailPanel"],
    QFrame[componentRole="LiquidCommandSurfaceSection"],
    QFrame[componentRole="LiquidFloatingPanel"],
    QFrame[componentRole="ReadinessGate"],
    QFrame[componentRole="TruthBadge"],
    QFrame[componentRole="MetricTile"],
    QFrame[componentRole="DraftStateIndicator"],
    QFrame[componentRole="TelemetryFreshnessRail"],
    QFrame[componentRole="RouteFlowRow"],
    QFrame[componentRole="SignalPipelineStage"],
    QFrame[componentRole="ChecklistPanel"],
    QFrame[componentRole="ParameterRow"],
    QFrame[componentRole="GuidanceBlock"],
    QFrame[componentRole="LiveSnapshotBlock"],
    QFrame[componentRole="AxisBar"],
    QFrame[componentRole="AxisBarPair"],
    QFrame[componentRole="ButtonIlluminationGrid"],
    QFrame[componentRole="HatDirectionIndicator"],
    QFrame[componentRole="ControlMarker"],
    QFrame[componentRole="MiniCurvePreview"],
    QFrame[componentRole="CapabilityRail"] {{
        background: rgba(7, 20, 33, 206);
        border: 1px solid rgba(72, 112, 140, 116);
        border-radius: 16px;
    }}

    QFrame[componentRole="StatusLight"][indicatorShape="status-dot"] {{
        background: rgba(118, 217, 255, 180);
        border: 1px solid rgba(247, 251, 255, 96);
        border-radius: 5px;
    }}

    QFrame[componentRole="ResponseCurveGraph"],
    QFrame[componentRole="LiveAxisTimeSeriesGraph"] {{
        background: rgba(5, 15, 25, 120);
        border: 1px solid rgba(118, 217, 255, 90);
        border-radius: 16px;
    }}

    QFrame[componentRole="LiquidAdvancedSection"] {{
        background: rgba(7, 20, 33, 166);
        border: 1px solid rgba(72, 112, 140, 78);
        border-radius: 16px;
    }}

    QFrame#liquidPreflightSystemDetails,
    QFrame#liquidPreflightActionPanel {{
        background: rgba(7, 20, 33, 178);
        border-color: rgba(72, 112, 140, 90);
    }}

    QFrame[componentRole="PreflightSystemDetailGroup"],
    QFrame[componentRole="PreflightChecklistPanel"] {{
        background: rgba(5, 15, 25, 92);
        border: 1px solid rgba(72, 112, 140, 58);
        border-radius: 13px;
    }}

    QFrame[componentRole="PreflightDetailRow"][detailRowStyle="soft"] {{
        background: transparent;
        border: none;
        border-radius: 0px;
    }}

    QFrame[componentRole="PreflightChecklistItem"][actionRowStyle="breathing"] {{
        background: rgba(7, 20, 33, 112);
        border: 1px solid rgba(72, 112, 140, 52);
        border-radius: 12px;
    }}

    QFrame#liquidPreflightAdvancedDiagnostics[visualWeight="subdued"] {{
        background: rgba(5, 14, 24, 108);
        border-color: rgba(72, 112, 140, 46);
    }}

    QFrame#liquidPreflightAdvancedDiagnosticsGrid[diagnosticsDensity="subdued"],
    QFrame#liquidPreflightAdvancedSummary[visualWeight="subdued"] {{
        background: rgba(5, 15, 25, 70);
        border: 1px solid rgba(72, 112, 140, 42);
        border-radius: 12px;
    }}

    QFrame#liquidMappingHotasHero[mappingVisualRole="primary_hotas_map"] {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(35, 82, 104, 232),
            stop: 0.35 rgba(8, 29, 48, 242),
            stop: 1 rgba(4, 12, 20, 244)
        );
        border: 1px solid rgba(118, 217, 255, 132);
        border-radius: 24px;
    }}

    QFrame#liquidMappingHotasMap,
    QFrame#liquidMappingHeroSummary,
    QFrame#liquidMappingMetrics {{
        background: rgba(5, 15, 25, 82);
        border: 1px solid rgba(72, 112, 140, 48);
        border-radius: 14px;
    }}

    QFrame#liquidMappingIntentRail {{
        background: transparent;
        border: none;
    }}

    QFrame#liquidMappingInspector,
    QFrame#liquidMappingRouteFlowPanel {{
        background: rgba(7, 20, 33, 178);
        border-color: rgba(72, 112, 140, 90);
    }}

    QFrame#liquidMappingAdvancedRouteDetails[visualWeight="subdued"] {{
        background: rgba(5, 14, 24, 108);
        border-color: rgba(72, 112, 140, 46);
    }}

    QFrame#liquidMappingAdvancedRouteList,
    QFrame#liquidMappingAdvancedSummary,
    QFrame#liquidMappingAdvancedCounts,
    QFrame#liquidMappingSelectedAdvancedRoute,
    QFrame#liquidMappingAdvancedPreviewList,
    QFrame#liquidMappingDeferredActions {{
        background: rgba(5, 15, 25, 70);
        border: 1px solid rgba(72, 112, 140, 42);
        border-radius: 12px;
    }}

    QFrame[componentRole="MappingDetailRow"],
    QFrame[componentRole="MappingAdvancedRouteRow"],
    QFrame[componentRole="MappingAdvancedCell"],
    QFrame[componentRole="MappingInspectorHeader"],
    QFrame[componentRole="MappingTruthNotes"] {{
        background: rgba(7, 20, 33, 112);
        border: 1px solid rgba(72, 112, 140, 52);
        border-radius: 12px;
    }}

    QPushButton[uiRole="liquidMappingMarker"] {{
        background: rgba(8, 20, 32, 204);
        border: 1px solid rgba(118, 217, 255, 98);
        border-radius: 12px;
        color: {colors.primary_text};
        font-size: 11px;
        font-weight: 850;
        padding: 4px 7px;
    }}

    QPushButton[uiRole="liquidMappingMarker"][mappedState="unmapped"],
    QPushButton[uiRole="liquidMappingMarker"][statusRole="warning"] {{
        border-color: rgba(242, 198, 109, 138);
        color: {colors.status_amber};
    }}

    QPushButton[uiRole="liquidMappingMarker"][selected="true"],
    QPushButton[uiRole="liquidMappingMarker"]:checked {{
        background: rgba(35, 86, 82, 226);
        border: 2px solid rgba(126, 224, 166, 176);
        color: #ffffff;
    }}

    QFrame[toneRole="success"],
    QLabel[toneRole="success"] {{
        border-color: {colors.status_green};
        color: {colors.status_green};
    }}

    QFrame[toneRole="warning"],
    QLabel[toneRole="warning"] {{
        border-color: {colors.status_amber};
        color: {colors.status_amber};
    }}

    QFrame[toneRole="danger"],
    QLabel[toneRole="danger"] {{
        border-color: {colors.status_red};
        color: {colors.status_red};
    }}

    QFrame[toneRole="info"],
    QLabel[toneRole="info"] {{
        border-color: {colors.status_cyan};
        color: {colors.status_cyan};
    }}

    QFrame[toneRole="disabled"],
    QLabel[toneRole="disabled"] {{
        border-color: #25384a;
        color: {colors.dim_text};
    }}

    QLabel[uiRole="liquidGlassCapsule"] {{
        background: rgba(7, 17, 29, 218);
        border: 1px solid {colors.border_muted};
        border-radius: 11px;
        color: {colors.primary_text};
        padding: 7px 11px;
        font-weight: 700;
    }}

    QLabel#liquidComponentKicker,
    QLabel#liquidMetricTileLabel,
    QLabel#liquidGuidanceTitle {{
        color: {colors.status_cyan};
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0px;
        text-transform: uppercase;
    }}

    QLabel#liquidComponentTitle,
    QLabel#liquidChecklistTitle,
    QLabel#liquidSignalPipelineStageName,
    QLabel#liquidMetricTileValue {{
        color: {colors.primary_text};
        font-size: 18px;
        font-weight: 800;
    }}

    QLabel#liquidPreflightSystemGroupTitle,
    QLabel#liquidPreflightChecklistLabel {{
        color: {colors.primary_text};
        font-size: 14px;
        font-weight: 850;
    }}

    QLabel#liquidComponentBody,
    QLabel#liquidComponentHelper,
    QLabel#liquidReadinessGateDetail,
    QLabel#liquidRouteFlowHelper,
    QLabel#liquidSignalPipelineStageSummary,
    QLabel#liquidChecklistItemReason,
    QLabel#liquidGuidanceBody,
    QLabel#liquidLiveSnapshotLabel,
    QLabel#liquidMetricTileCaption,
    QLabel#liquidControlMarkerSummary,
    QLabel#liquidMiniCurveBody {{
        color: {colors.muted_text};
    }}

    QLabel#liquidPreflightDetailLabel,
    QLabel#liquidPreflightChecklistReason,
    QLabel#liquidPreflightAdvancedSummaryText {{
        color: {colors.muted_text};
    }}

    QLabel#liquidPreflightDetailValue {{
        color: {colors.primary_text};
        font-weight: 750;
    }}

    QLineEdit[componentRole="NumericParameterControl"],
    QComboBox[componentRole="DropdownParameterControl"] {{
        background: rgba(6, 16, 28, 232);
        border: 1px solid rgba(118, 217, 255, 92);
        border-radius: 10px;
        color: {colors.primary_text};
        padding: 7px 9px;
    }}

    QLineEdit[validationState="invalid"] {{
        border-color: {colors.status_red};
        color: {colors.status_red};
    }}

    QPushButton[uiRole="liquidAxisPill"] {{
        background: rgba(8, 20, 32, 188);
        border: 1px solid rgba(72, 112, 140, 120);
        border-radius: 12px;
        color: {colors.primary_text};
        font-weight: 750;
        padding: 7px 10px;
    }}

    QPushButton[uiRole="liquidAxisPill"][active="true"],
    QPushButton[uiRole="liquidAxisPill"]:checked {{
        border-color: {colors.status_green};
        background: rgba(28, 75, 72, 220);
        color: #ffffff;
    }}

    QProgressBar#liquidAxisBarValue {{
        background: rgba(4, 12, 20, 220);
        border: 1px solid rgba(72, 112, 140, 120);
        border-radius: 8px;
        color: {colors.primary_text};
        text-align: center;
    }}

    QProgressBar#liquidAxisBarValue::chunk {{
        background: rgba(118, 217, 255, 150);
        border-radius: 8px;
    }}
    """
