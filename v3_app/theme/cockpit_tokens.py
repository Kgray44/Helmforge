from __future__ import annotations


class CockpitColors:
    app_background = "#050a10"
    workspace_background = "#07121b"
    panel = "#0b1822"
    panel_elevated = "#102331"
    panel_subtle = "#0d1d29"
    border = "#24465f"
    border_strong = "#4a83a7"
    border_muted = "#173044"
    status_green = "#79f2a6"
    status_amber = "#f2c66d"
    status_red = "#ff7f7f"
    status_cyan = "#56c7ff"
    status_blue = "#5f93ff"
    text_primary = "#f4f8fb"
    text_secondary = "#bdd2e1"
    text_muted = "#7896aa"
    glow_green = "#1f7f4c"
    glow_amber = "#896422"
    glow_red = "#8c3838"
    glow_cyan = "#1f6f92"


class CockpitLayout:
    card_radius = 8
    card_padding = 18
    section_spacing = 14
    table_row_height = 34
    nav_selected_width = 4


TONE_TO_COLOR = {
    "success": CockpitColors.status_green,
    "ok": CockpitColors.status_green,
    "ready": CockpitColors.status_green,
    "warning": CockpitColors.status_amber,
    "caution": CockpitColors.status_amber,
    "waiting": CockpitColors.status_amber,
    "danger": CockpitColors.status_red,
    "error": CockpitColors.status_red,
    "info": CockpitColors.status_cyan,
    "neutral": CockpitColors.text_secondary,
}


def tone_color(tone: str) -> str:
    return TONE_TO_COLOR.get(tone, CockpitColors.text_secondary)
