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
    hover_border = "rgba(118, 217, 255, 178)"
    pressed_fill = "rgba(4, 16, 26, 238)"
    selected_rim = "rgba(126, 224, 166, 188)"
    focus_ring = "rgba(247, 251, 255, 210)"
    subtle_glow = "rgba(118, 217, 255, 86)"
    draft_glow = "rgba(242, 198, 109, 132)"
    disabled_muted = "#25384a"


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

    QFrame#liquid_command_surface[atmosphereEnabled="true"] {{
        border-color: rgba(118, 217, 255, 112);
    }}

    QFrame#liquid_command_surface[modeAccent="preflight"] {{
        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 rgba(242, 198, 109, 30), stop: 0.42 rgba(8, 24, 38, 222), stop: 1 rgba(3, 9, 15, 238));
        border-color: rgba(242, 198, 109, 118);
    }}

    QFrame#liquid_command_surface[modeAccent="mapping"] {{
        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 rgba(118, 217, 255, 30), stop: 0.42 rgba(8, 24, 38, 222), stop: 1 rgba(3, 9, 15, 238));
        border-color: rgba(118, 217, 255, 120);
    }}

    QFrame#liquid_command_surface[modeAccent="tuning"] {{
        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 rgba(104, 220, 194, 28), stop: 0.44 rgba(8, 24, 38, 222), stop: 1 rgba(3, 9, 15, 238));
        border-color: rgba(104, 220, 194, 112);
    }}

    QFrame#liquid_command_surface[modeAccent="analysis"] {{
        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 rgba(126, 224, 166, 30), stop: 0.44 rgba(8, 24, 38, 222), stop: 1 rgba(3, 9, 15, 238));
        border-color: rgba(126, 224, 166, 118);
    }}

    QFrame#liquid_command_surface[modeAccent="recorder"] {{
        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 rgba(255, 113, 113, 28), stop: 0.44 rgba(8, 24, 38, 222), stop: 1 rgba(3, 9, 15, 238));
        border-color: rgba(242, 198, 109, 108);
    }}

    QFrame#liquid_command_surface[modeAccent="support"] {{
        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 rgba(132, 160, 188, 24), stop: 0.44 rgba(8, 24, 38, 222), stop: 1 rgba(3, 9, 15, 238));
        border-color: rgba(132, 160, 188, 104);
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

    QFrame#liquid_surface_glass_field[atmosphereEnabled="true"] {{
        border-color: rgba(118, 217, 255, 56);
    }}

    QFrame#liquid_surface_glass_field[atmosphereMode="slow_drift"] {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(126, 224, 166, 18),
            stop: 0.35 rgba(80, 190, 255, 18),
            stop: 1 rgba(4, 12, 20, 30)
        );
    }}

    QFrame#liquidQuickSwitchWheel {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(22, 58, 78, 238),
            stop: 0.48 rgba(7, 20, 33, 244),
            stop: 1 rgba(3, 9, 15, 248)
        );
        border: 1px solid rgba(126, 224, 166, 150);
        border-radius: 24px;
        min-width: 430px;
        max-width: 520px;
    }}

    QLabel#liquidQuickWheelTitle {{
        color: {colors.primary_text};
        font-size: 15px;
        font-weight: 900;
        letter-spacing: 0px;
    }}

    QLabel#liquidQuickWheelActiveMode,
    QLabel#liquidQuickWheelHint {{
        color: {colors.status_cyan};
        font-size: 11px;
        font-weight: 800;
    }}

    QPushButton[uiRole="liquidQuickWheelButton"] {{
        background: rgba(7, 20, 33, 218);
        border: 1px solid rgba(118, 217, 255, 96);
        border-radius: 14px;
        color: {colors.primary_text};
        font-size: 13px;
        font-weight: 850;
        min-height: 46px;
        padding: 8px 12px;
    }}

    QPushButton[uiRole="liquidQuickWheelButton"]:hover {{
        background: rgba(18, 46, 64, 226);
        border-color: {colors.hover_border};
    }}

    QPushButton[uiRole="liquidQuickWheelButton"]:checked,
    QPushButton[uiRole="liquidQuickWheelButton"][active="true"] {{
        background: rgba(26, 75, 70, 232);
        border-color: {colors.selected_rim};
        color: #ffffff;
    }}

    QPushButton[uiRole="liquidQuickWheelButton"]:focus {{
        border-color: {colors.focus_ring};
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

    QLabel[uiRole="liquidStatusChip"][hoverEffectsEnabled="true"]:hover {{
        border-color: {colors.hover_border};
        background: rgba(12, 31, 48, 232);
    }}

    QLabel[uiRole="liquidStatusChip"][focusRingEnabled="true"]:focus {{
        border-color: {colors.focus_ring};
    }}

    QLabel[uiRole="liquidStatusChip"][pulseEnabled="true"] {{
        background: rgba(9, 25, 38, 232);
    }}

    QLabel[uiRole="liquidStatusChip"][draftEmphasis="true"],
    QLabel[uiRole="liquidStatusChip"][pulseRole="draft"] {{
        border-color: {colors.status_amber};
        color: {colors.status_amber};
        background: rgba(37, 25, 8, 218);
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

    QPushButton[uiRole="liquidActionButton"][buttonTone="primary"] {{
        border-color: rgba(126, 224, 166, 136);
        background: rgba(13, 42, 36, 224);
    }}

    QPushButton[uiRole="liquidActionButton"][buttonTone="secondary"] {{
        border-color: rgba(118, 217, 255, 104);
    }}

    QPushButton[uiRole="liquidActionButton"][buttonTone="caution"] {{
        border-color: rgba(242, 198, 109, 142);
        background: rgba(36, 25, 9, 218);
        color: #ffe6ab;
    }}

    QPushButton[uiRole="liquidModeDockButton"]:hover {{
        border-color: {colors.hover_border};
        background: rgba(18, 46, 64, 220);
    }}

    QPushButton[uiRole="liquidActionButton"]:hover {{
        border-color: {colors.hover_border};
        background: rgba(13, 35, 55, 232);
    }}

    QPushButton[uiRole="liquidActionButton"][buttonTone="primary"]:hover {{
        border-color: {colors.selected_rim};
        background: rgba(17, 58, 48, 232);
    }}

    QPushButton[uiRole="liquidActionButton"][buttonTone="caution"]:hover {{
        border-color: {colors.status_amber};
        background: rgba(48, 32, 9, 232);
    }}

    QPushButton[uiRole="liquidActionButton"]:pressed {{
        border-color: {colors.focus_ring};
        background: {colors.pressed_fill};
    }}

    QPushButton[motionCoordinatorDriven="true"][hoverGlowStep="1"],
    QPushButton[motionCoordinatorDriven="true"][hoverGlowStep="2"],
    QPushButton[motionCoordinatorDriven="true"][hoverGlowStep="3"] {{
        border-color: rgba(118, 217, 255, 138);
        background: rgba(12, 32, 49, 224);
    }}

    QPushButton[motionCoordinatorDriven="true"][hoverGlowStep="4"],
    QPushButton[motionCoordinatorDriven="true"][hoverGlowStep="5"],
    QPushButton[motionCoordinatorDriven="true"][hoverGlowStep="6"] {{
        border-color: rgba(126, 224, 255, 176);
        background: rgba(15, 40, 60, 232);
    }}

    QPushButton[motionCoordinatorDriven="true"][hoverGlowStep="7"],
    QPushButton[motionCoordinatorDriven="true"][hoverGlowStep="8"] {{
        border-color: rgba(188, 244, 255, 212);
        background: rgba(19, 50, 72, 238);
    }}

    QPushButton[motionCoordinatorDriven="true"][pressMotionStep="1"],
    QPushButton[motionCoordinatorDriven="true"][pressMotionStep="2"],
    QPushButton[motionCoordinatorDriven="true"][pressMotionStep="3"],
    QPushButton[motionCoordinatorDriven="true"][pressMotionStep="4"],
    QPushButton[motionCoordinatorDriven="true"][pressMotionStep="5"],
    QPushButton[motionCoordinatorDriven="true"][pressMotionStep="6"],
    QPushButton[motionCoordinatorDriven="true"][pressMotionStep="7"],
    QPushButton[motionCoordinatorDriven="true"][pressMotionStep="8"] {{
        border-color: {colors.focus_ring};
        background: rgba(6, 17, 27, 238);
        padding-top: 9px;
        padding-bottom: 7px;
    }}

    QPushButton[motionCoordinatorDriven="true"][selectionMotionStep="1"],
    QPushButton[motionCoordinatorDriven="true"][selectionMotionStep="2"],
    QPushButton[motionCoordinatorDriven="true"][selectionMotionStep="3"],
    QPushButton[motionCoordinatorDriven="true"][selectionMotionStep="4"] {{
        border-color: rgba(126, 224, 166, 144);
        background: rgba(18, 54, 57, 226);
    }}

    QPushButton[motionCoordinatorDriven="true"][selectionMotionStep="5"],
    QPushButton[motionCoordinatorDriven="true"][selectionMotionStep="6"],
    QPushButton[motionCoordinatorDriven="true"][selectionMotionStep="7"],
    QPushButton[motionCoordinatorDriven="true"][selectionMotionStep="8"] {{
        border-color: {colors.selected_rim};
        background: rgba(24, 70, 70, 236);
        color: #ffffff;
    }}

    QPushButton[motionCoordinatorDriven="true"][stateChangeMotionStep="1"],
    QPushButton[motionCoordinatorDriven="true"][stateChangeMotionStep="2"],
    QPushButton[motionCoordinatorDriven="true"][stateChangeMotionStep="3"],
    QPushButton[motionCoordinatorDriven="true"][stateChangeMotionStep="4"],
    QPushButton[motionCoordinatorDriven="true"][stateChangeMotionStep="5"],
    QPushButton[motionCoordinatorDriven="true"][stateChangeMotionStep="6"],
    QPushButton[motionCoordinatorDriven="true"][stateChangeMotionStep="7"],
    QPushButton[motionCoordinatorDriven="true"][stateChangeMotionStep="8"] {{
        border-color: rgba(242, 198, 109, 174);
        background: rgba(42, 32, 16, 230);
    }}

    QPushButton[uiRole="liquidActionButton"]:checked {{
        border-color: {colors.selected_rim};
        background: rgba(24, 70, 70, 230);
        color: #ffffff;
    }}

    QPushButton[uiRole="liquidActionButton"][focusRingEnabled="true"]:focus,
    QPushButton[uiRole="liquidModeDockButton"][focusRingEnabled="true"]:focus,
    QPushButton[uiRole="liquidSubpageSelectorButton"][focusRingEnabled="true"]:focus,
    QPushButton[uiRole="liquidAxisPill"][focusRingEnabled="true"]:focus,
    QPushButton[uiRole="liquidMappingMarker"][focusRingEnabled="true"]:focus,
    QPushButton[uiRole="liquidQuickWheelButton"]:focus {{
        border-color: {colors.focus_ring};
    }}

    QPushButton[uiRole="liquidSubpageSelectorButton"]:hover {{
        border-color: {colors.hover_border};
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

    QPushButton[uiRole="liquidActionButton"][draftEmphasis="true"]:disabled {{
        border-color: rgba(242, 198, 109, 104);
        color: #9c875f;
        background: rgba(18, 17, 18, 188);
    }}

    QFrame#liquid_floating_footer_strip[draftEmphasis="true"] {{
        border-color: rgba(242, 198, 109, 134);
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 0,
            stop: 0 rgba(21, 17, 13, 220),
            stop: 0.52 rgba(33, 28, 19, 232),
            stop: 1 rgba(21, 17, 13, 220)
        );
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

    QFrame[componentRole="StatusLight"][toneRole="success"],
    QFrame[componentRole="StatusLight"][pulseRole="verified"] {{
        background: rgba(126, 224, 166, 204);
        border-color: rgba(223, 255, 235, 130);
    }}

    QFrame[componentRole="StatusLight"][toneRole="warning"],
    QFrame[componentRole="StatusLight"][pulseRole="attention"],
    QFrame[componentRole="StatusLight"][pulseRole="draft"] {{
        background: rgba(242, 198, 109, 210);
        border-color: rgba(255, 237, 191, 130);
    }}

    QFrame[componentRole="StatusLight"][toneRole="danger"],
    QFrame[componentRole="StatusLight"][pulseRole="error"] {{
        background: rgba(255, 113, 113, 218);
        border-color: rgba(255, 218, 218, 150);
    }}

    QFrame[componentRole="StatusLight"][toneRole="disabled"] {{
        background: rgba(102, 135, 159, 132);
        border-color: rgba(102, 135, 159, 84);
    }}

    QFrame[componentRole="StatusLight"][pulseEnabled="true"][pulsePhase="1"] {{
        border-color: rgba(247, 251, 255, 210);
    }}

    QFrame[microinteractionRole="interactive_card"][hoverEffectsEnabled="true"]:hover,
    QFrame[microinteractionRole="selectable_card"][hoverEffectsEnabled="true"]:hover,
    QFrame[microinteractionRole="status_card"][hoverEffectsEnabled="true"]:hover {{
        border-color: {colors.hover_border};
        background: rgba(10, 28, 43, 220);
    }}

    QFrame[motionCoordinatorDriven="true"][hoverGlowStep="1"],
    QFrame[motionCoordinatorDriven="true"][hoverGlowStep="2"],
    QFrame[motionCoordinatorDriven="true"][hoverGlowStep="3"] {{
        border-color: rgba(118, 217, 255, 132);
        background: rgba(9, 26, 40, 214);
    }}

    QFrame[motionCoordinatorDriven="true"][hoverGlowStep="4"],
    QFrame[motionCoordinatorDriven="true"][hoverGlowStep="5"],
    QFrame[motionCoordinatorDriven="true"][hoverGlowStep="6"] {{
        border-color: rgba(126, 224, 255, 168);
        background: rgba(11, 32, 47, 222);
    }}

    QFrame[motionCoordinatorDriven="true"][hoverGlowStep="7"],
    QFrame[motionCoordinatorDriven="true"][hoverGlowStep="8"] {{
        border-color: rgba(188, 244, 255, 202);
        background: rgba(13, 38, 54, 228);
    }}

    QFrame[motionCoordinatorDriven="true"][selectionMotionStep="1"],
    QFrame[motionCoordinatorDriven="true"][selectionMotionStep="2"],
    QFrame[motionCoordinatorDriven="true"][selectionMotionStep="3"],
    QFrame[motionCoordinatorDriven="true"][selectionMotionStep="4"] {{
        border-color: rgba(126, 224, 166, 136);
        background: rgba(13, 34, 39, 218);
    }}

    QFrame[motionCoordinatorDriven="true"][selectionMotionStep="5"],
    QFrame[motionCoordinatorDriven="true"][selectionMotionStep="6"],
    QFrame[motionCoordinatorDriven="true"][selectionMotionStep="7"],
    QFrame[motionCoordinatorDriven="true"][selectionMotionStep="8"] {{
        border-color: {colors.selected_rim};
        background: rgba(14, 42, 45, 228);
    }}

    QFrame[motionCoordinatorDriven="true"][stateChangeMotionStep="1"],
    QFrame[motionCoordinatorDriven="true"][stateChangeMotionStep="2"],
    QFrame[motionCoordinatorDriven="true"][stateChangeMotionStep="3"],
    QFrame[motionCoordinatorDriven="true"][stateChangeMotionStep="4"],
    QFrame[motionCoordinatorDriven="true"][stateChangeMotionStep="5"],
    QFrame[motionCoordinatorDriven="true"][stateChangeMotionStep="6"],
    QFrame[motionCoordinatorDriven="true"][stateChangeMotionStep="7"],
    QFrame[motionCoordinatorDriven="true"][stateChangeMotionStep="8"] {{
        border-color: rgba(242, 198, 109, 168);
        background: rgba(35, 29, 18, 224);
    }}

    QFrame[motionCoordinatorDriven="true"][glintMotionStep="4"],
    QFrame[motionCoordinatorDriven="true"][glintMotionStep="5"],
    QFrame[motionCoordinatorDriven="true"][glintMotionStep="6"],
    QFrame[motionCoordinatorDriven="true"][glintMotionStep="7"],
    QFrame[motionCoordinatorDriven="true"][glintMotionStep="8"] {{
        border-color: rgba(218, 251, 255, 210);
    }}

    QFrame[microinteractionRole="interactive_card"][focusRingEnabled="true"]:focus,
    QFrame[microinteractionRole="selectable_card"][focusRingEnabled="true"]:focus,
    QFrame[microinteractionRole="status_card"][focusRingEnabled="true"]:focus {{
        border-color: {colors.focus_ring};
    }}

    QFrame[microinteractionRole="selectable_card"][selected="true"],
    QFrame[componentRole="ReadinessGate"][gateEmphasis="active"],
    QFrame[componentRole="ParameterRow"][draftEmphasis="true"],
    QFrame[componentRole="DraftStateIndicator"][draftEmphasis="true"] {{
        border-color: {colors.draft_glow};
        background: rgba(26, 24, 18, 218);
    }}

    QFrame[microinteractionRole="selectable_card"][selected="true"] {{
        border-color: {colors.selected_rim};
    }}

    QFrame[microinteractionRole="raw_diagnostic"],
    QFrame[rawDiagnosticSurface="true"] {{
        border-color: rgba(72, 112, 140, 58);
    }}

    QStackedWidget#liquid_page_host[pageMotionActive="true"] {{
        border: 1px solid rgba(118, 217, 255, 120);
        background: rgba(118, 217, 255, 12);
    }}

    QFrame[panelSettleEnabled="true"][panelSettleRole="hero"] {{
        border-color: rgba(118, 217, 255, 112);
    }}

    QFrame[panelSettleEnabled="true"][panelSettleRole="inspector"],
    QFrame[panelSettleEnabled="true"][panelSettleRole="detail"] {{
        border-color: rgba(126, 224, 166, 84);
    }}

    QFrame[signalPathMotionEnabled="true"] {{
        border-color: rgba(118, 217, 255, 138);
    }}

    QFrame[componentRole="AxisBar"][staleMotionFrozen="true"],
    QFrame[componentRole="AxisBarPair"][staleMotionFrozen="true"],
    QFrame[componentRole="LiveAxisTimeSeriesGraph"][staleMotionFrozen="true"] {{
        border-color: rgba(242, 198, 109, 112);
        background: rgba(18, 20, 21, 190);
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

    QPushButton[uiRole="liquidMappingMarker"]:hover {{
        border-color: {colors.hover_border};
        background: rgba(17, 42, 58, 226);
    }}

    QPushButton[uiRole="liquidMappingMarker"]:pressed {{
        border-color: {colors.focus_ring};
        background: {colors.pressed_fill};
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

    QLineEdit[componentRole="NumericParameterControl"]:focus,
    QComboBox[componentRole="DropdownParameterControl"]:focus {{
        border-color: {colors.focus_ring};
        background: rgba(8, 24, 38, 238);
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

    QPushButton[uiRole="liquidAxisPill"]:hover {{
        border-color: {colors.hover_border};
        background: rgba(18, 46, 64, 220);
    }}

    QPushButton[uiRole="liquidAxisPill"]:pressed {{
        border-color: {colors.focus_ring};
        background: {colors.pressed_fill};
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

    QFrame#liquidVisibleAtmosphereLayer,
    QFrame#liquidPageTransitionOverlay {{
        background: transparent;
        border: none;
    }}

    QFrame#liquidMotionModeCluster {{
        background: rgba(6, 16, 28, 206);
        border: 1px solid rgba(118, 217, 255, 72);
        border-radius: 12px;
    }}

    QLabel#liquidMotionModeLabel,
    QLabel#liquidMotionProofTitle {{
        color: {colors.status_cyan};
        font-size: 11px;
        font-weight: 850;
    }}

    QComboBox#liquidMotionModeControl {{
        background: rgba(4, 12, 20, 232);
        border: 1px solid rgba(118, 217, 255, 92);
        border-radius: 8px;
        color: {colors.primary_text};
        padding: 4px 7px;
        font-weight: 750;
    }}

    QComboBox#liquidMotionModeControl:focus {{
        border-color: {colors.focus_ring};
        background: rgba(8, 24, 38, 238);
    }}

    QFrame#liquidMotionProofPanel {{
        background: rgba(5, 16, 28, 222);
        border: 1px solid rgba(126, 224, 255, 112);
        border-radius: 12px;
    }}

    QLabel#liquidMotionProofSummary {{
        color: {colors.muted_text};
        font-size: 11px;
    }}

    QFrame#liquidMotionProofRail {{
        background: rgba(2, 8, 14, 156);
        border: 1px solid rgba(72, 112, 140, 90);
        border-radius: 10px;
    }}

    QLabel[statusBreathActive="true"][statusBreathStep="1"],
    QFrame[statusBreathActive="true"][statusBreathStep="1"] {{
        border-color: rgba(126, 224, 255, 168);
        background: rgba(14, 42, 58, 218);
    }}

    QLabel[statusBreathActive="true"][statusBreathStep="2"],
    QFrame[statusBreathActive="true"][statusBreathStep="2"] {{
        border-color: rgba(126, 224, 255, 210);
        background: rgba(18, 52, 70, 228);
    }}

    QLabel[statusBreathActive="true"][statusBreathStep="3"],
    QFrame[statusBreathActive="true"][statusBreathStep="3"] {{
        border-color: rgba(106, 226, 168, 178);
        background: rgba(10, 38, 44, 218);
    }}

    QFrame#liquidStatusLight[statusBreathActive="true"],
    QFrame#liquidStatusLight[pulsePhase="1"] {{
        border: 1px solid rgba(255, 255, 255, 160);
        background: rgba(126, 224, 255, 226);
    }}

    QFrame[signalSweepActive="true"][signalSweepStep="1"],
    QFrame[signalSweepActive="true"][signalSweepStep="2"] {{
        border-color: rgba(126, 224, 255, 164);
        background: rgba(12, 38, 54, 218);
    }}

    QFrame[signalSweepActive="true"][signalSweepStep="3"],
    QFrame[signalSweepActive="true"][signalSweepStep="4"] {{
        border-color: rgba(106, 226, 168, 174);
        background: rgba(9, 34, 42, 220);
    }}

    QPushButton[uiRole="liquidQuickWheelButton"][quickWheelSegmentActive="false"] {{
        color: {colors.dim_text};
        border-color: rgba(72, 112, 140, 58);
        background: rgba(4, 12, 20, 154);
    }}

    QPushButton[uiRole="liquidQuickWheelButton"][quickWheelSegmentActive="true"] {{
        border-color: rgba(126, 224, 255, 132);
        background: rgba(12, 34, 48, 218);
    }}

    QFrame#liquidPageTransitionOverlay[pageTransitionOverlayActive="true"] {{
        border: 1px solid rgba(126, 224, 255, 70);
        border-radius: 18px;
    }}
    """
