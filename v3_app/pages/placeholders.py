from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from shared_core.runtime.driver_setup import VJOY_SETUP_SOURCE_URL
from shared_core.runtime.setup_guidance import OFFICIAL_THRUSTMASTER_SUPPORT_PAGE
from v3_app.services.app_state import PAGE_IDS
from v3_app.ui.status_chips import action_button, status_chip


@dataclass(frozen=True)
class PageDefinition:
    page_id: str
    title: str
    subtitle: str
    shell_note: str


PAGE_DEFINITIONS = (
    PageDefinition("mapping", "Mapping", "Map raw HOTAS axes, buttons, and hats to bridge outputs.", "Routing tables and live route summaries will be rebuilt here."),
    PageDefinition("modes", "Modes", "Configure precision, combat, zoom, and extra mode behavior.", "Mode gates and button bindings will arrive after the shell is reviewed."),
    PageDefinition("base_tuning", "Base Tuning", "Shape the underlying axis response before mode-specific modifiers get involved.", "Curve controls, deadzone settings, and previews will be rebuilt in this workspace."),
    PageDefinition("filtering", "Filtering", "Tune smoothing, edge response, and same/reverse-direction slew limits.", "Step response and filtering controls will be added without moving processing into the UI."),
    PageDefinition("combat_profile", "Combat Profile", "Adjust combat-focused curve, scale, filtering, and slew behavior.", "Combat profile controls will remain configuration-only for the future Bridge."),
    PageDefinition("profiles", "Profiles", "Manage built-in and personal workspaces for different flight styles.", "Profile library and detail cards will be reconstructed in a later phase."),
    PageDefinition("conditional_rules", "Conditional Rules", "Build responsive modifier rules, track their live state, and see exactly where they inject into the response stack.", "Rule list, detail, editor, and live status are rebuilt in the rules phase."),
    PageDefinition("effective_response_stack", "Effective Response Stack", "Inspect every stage from raw input through final output.", "Stage cards will be powered by the shared-core stack results."),
    PageDefinition("live_monitor", "Live Monitor", "Watch runtime truth, simulated telemetry, and future Bridge snapshots.", "Live graphs and button grids come later; output remains unverified for now."),
    PageDefinition("flight_recorder", "Flight Recorder", "Prepare capture, clip review, and telemetry overlay workflows.", "Recorder controls are placeholders until capture/compositor work begins."),
    PageDefinition("help_docs", "Help / Docs", "Browse runtime setup guidance, tuning concepts, and recovery notes.", "Documentation navigation and setup links live here while detailed articles grow."),
    PageDefinition("perf_diagnostics", "Perf / Diagnostics", "Inspect shell timing, runtime truth, and future Bridge diagnostics.", "Diagnostics hooks are seeded without adding heavy live instrumentation."),
)

assert tuple(page.page_id for page in PAGE_DEFINITIONS) == PAGE_IDS


def page_definition_by_id(page_id: str) -> PageDefinition:
    for page in PAGE_DEFINITIONS:
        if page.page_id == page_id:
            return page
    raise KeyError(page_id)


def create_placeholder_page(page: PageDefinition, *, runtime_label: str) -> QWidget:
    container = QWidget()
    container.setObjectName(f"page_{page.page_id}")
    layout = QVBoxLayout(container)
    layout.setContentsMargins(24, 22, 24, 28)
    layout.setSpacing(18)

    title = QLabel(page.title)
    title.setObjectName("pageTitle")
    subtitle = QLabel(page.subtitle)
    subtitle.setObjectName("pageSubtitle")
    subtitle.setWordWrap(True)

    chip_row = QWidget()
    chip_layout = QHBoxLayout(chip_row)
    chip_layout.setContentsMargins(0, 0, 0, 0)
    chip_layout.setSpacing(8)
    chip_layout.addWidget(status_chip("Workspace Copy", tone="success"))
    chip_layout.addWidget(status_chip(runtime_label, tone="warning"))
    chip_layout.addStretch(1)

    card = QWidget()
    card.setObjectName("placeholderCard")
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(24, 22, 24, 24)
    card_layout.setSpacing(12)

    card_title = QLabel(f"{page.title} workspace")
    card_title.setObjectName("cardTitle")
    body = QLabel(
        f"{page.shell_note} Navigation, runtime status, and layout are active while detailed controls wait for their reviewed phase."
    )
    body.setObjectName("cardBody")
    body.setWordWrap(True)

    card_layout.addWidget(card_title)
    card_layout.addWidget(body)
    if page.page_id == "help_docs":
        card_layout.addSpacing(8)
        support_button = QPushButton("Open Official Thrustmaster Support Page")
        support_button.setObjectName("supportButton")
        support_button.setProperty("uiRole", "actionButton")
        support_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(OFFICIAL_THRUSTMASTER_SUPPORT_PAGE))
        )
        vjoy_button = action_button("Open vJoy Setup Source", object_name="vjoyButton")
        vjoy_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(VJOY_SETUP_SOURCE_URL)))
        card_layout.addWidget(support_button)
        card_layout.addWidget(vjoy_button)

    layout.addWidget(title)
    layout.addWidget(subtitle)
    layout.addWidget(chip_row)
    layout.addWidget(card)
    layout.addStretch(1)
    return container
