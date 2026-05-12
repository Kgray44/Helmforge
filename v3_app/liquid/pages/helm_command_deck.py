from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QCheckBox, QFrame, QLabel, QPushButton, QSizePolicy

from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from v3_app.liquid.components import LiquidFloatingPanel, LiquidHeroPanel
from v3_app.liquid.glass import action_button, glass_panel
from v3_app.liquid.layout import horizontal_layout, vertical_layout
from v3_app.liquid.models.helm_command_model import (
    HelmApplyResult,
    HelmCommandModel,
    build_helm_command_model,
)
from v3_app.liquid.status_components import DraftStateIndicator, MetricTile, StatusChip, TruthBadge
from v3_app.services.app_state import AppState


ApplySelectedCallback = Callable[[tuple[str, ...]], HelmApplyResult]
RevertCallback = Callable[[], HelmApplyResult]


class HelmAssistantDeck(LiquidFloatingPanel):
    def __init__(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig | None = None,
        selected_axis: str = "Yaw",
        on_apply_selected: ApplySelectedCallback | None = None,
        on_revert: RevertCallback | None = None,
    ) -> None:
        self._state = state
        self._workspace = workspace or create_default_workspace()
        self._selected_axis = selected_axis
        self._on_apply_selected = on_apply_selected
        self._on_revert = on_revert
        self._last_apply_result: HelmApplyResult | None = None
        self._change_checks: dict[str, QCheckBox] = {}
        self.model = self._build_model()
        super().__init__(
            "Helm Assistant",
            "Guided workspace recommendations. Selected changes stage only into the workspace draft.",
            object_name="liquidHelmAssistantDeck",
            minimum_height=520,
        )
        self.setProperty("helmSurface", True)
        self.setProperty("liquidRole", "liquid_helm_assistant_deck")
        self.setProperty("lcdPhase", "LCD-8")
        self.setMinimumWidth(560)
        self.setMaximumWidth(720)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self._render()

    def update_helm_state(
        self,
        *,
        state: AppState,
        workspace: WorkspaceConfig,
        selected_axis: str = "Yaw",
        last_apply_result: HelmApplyResult | None = None,
    ) -> None:
        self._state = state
        self._workspace = workspace
        self._selected_axis = selected_axis
        self._last_apply_result = last_apply_result
        self.model = self._build_model()
        self._render()

    def selected_change_ids(self) -> tuple[str, ...]:
        ids: list[str] = []
        for change_id, check in self._change_checks.items():
            if check.isChecked():
                ids.append(change_id)
        return tuple(ids)

    def apply_selected(self) -> HelmApplyResult:
        if self._on_apply_selected is None:
            result = HelmApplyResult(
                False,
                self._workspace,
                "Helm apply is unavailable on this surface.",
                "Helm apply unavailable",
                validation_errors=("No apply callback is attached.",),
            )
        else:
            result = self._on_apply_selected(self.selected_change_ids())
        self._last_apply_result = result
        self._workspace = result.workspace
        self.model = self._build_model()
        self._render()
        return result

    def revert_last(self) -> HelmApplyResult:
        if self._on_revert is None:
            result = HelmApplyResult(
                False,
                self._workspace,
                "Helm revert is unavailable on this surface.",
                "Helm revert unavailable",
                validation_errors=("No revert callback is attached.",),
            )
        else:
            result = self._on_revert()
        self._last_apply_result = result
        self._workspace = result.workspace
        self.model = self._build_model()
        self._render()
        return result

    def _build_model(self) -> HelmCommandModel:
        return build_helm_command_model(
            workspace=self._workspace,
            state=self._state,
            selected_axis=self._selected_axis,
            last_apply_result=self._last_apply_result,
        )

    def _render(self) -> None:
        self._change_checks = {}
        layout = self.layout()
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.setParent(None)
        layout.addWidget(_hero(self.model))
        layout.addWidget(_evidence_panel(self.model))
        layout.addWidget(_findings_panel(self.model))
        layout.addWidget(self._changes_panel())
        layout.addWidget(self._apply_panel())
        layout.addStretch(1)

    def _changes_panel(self) -> QFrame:
        panel = glass_panel("liquidHelmProposedChangesPanel", role="liquid_helm_proposed_changes")
        panel.setProperty("helmProposedChangesPanel", True)
        layout = vertical_layout(panel, margins=(14, 12, 14, 12), spacing=8)
        title = QLabel("Proposed change cards")
        title.setObjectName("liquidHelmSectionTitle")
        layout.addWidget(title)
        if not self.model.proposed_changes:
            layout.addWidget(TruthBadge("No safe recommendation is ready yet", state_role="unavailable", helper_text="Helm did not stage anything."))
            return panel
        for change in self.model.proposed_changes:
            card = glass_panel(f"liquidHelmChange_{change.change_id}", role="liquid_helm_change_card")
            card.setProperty("helmProposedChangeCard", True)
            card_layout = vertical_layout(card, margins=(12, 10, 12, 10), spacing=6)
            check = QCheckBox(f"{change.title} - {change.value_text}")
            check.setObjectName(f"liquidHelmChangeCheck_{change.change_id}")
            check.setChecked(change.selected)
            check.setProperty("changeId", change.change_id)
            self._change_checks[change.change_id] = check
            card_layout.addWidget(check)
            card_layout.addWidget(StatusChip(f"{change.group_label} / {change.section}", state_role="info"))
            card_layout.addWidget(_body(change.reason))
            card_layout.addWidget(_body(f"Expected: {change.expected_outcome}"))
            card_layout.addWidget(_body(f"Evidence source: {change.evidence_source}"))
            meta = horizontal_layout(spacing=8)
            meta.addWidget(StatusChip(f"Confidence {change.confidence}", state_role="info"))
            meta.addWidget(StatusChip(f"Risk {change.risk_level}", state_role="warning" if change.risk_level == "Medium" else "info"))
            meta.addWidget(StatusChip(change.truth_note, state_role="simulation"))
            card_layout.addLayout(meta)
            layout.addWidget(card)
        return panel

    def _apply_panel(self) -> QFrame:
        panel = glass_panel("liquidHelmApplyPanel", role="liquid_helm_apply_panel")
        panel.setProperty("helmApplyPanel", True)
        layout = vertical_layout(panel, margins=(14, 12, 14, 12), spacing=8)
        layout.addWidget(DraftStateIndicator(self.model.draft_state_label, state_role="unsaved" if self._last_apply_result and self._last_apply_result.valid else "info"))
        layout.addWidget(_body("Apply selected changes to workspace draft. Save remains the persistence action. Output proof unchanged."))
        row = horizontal_layout(spacing=8)
        self.apply_button = action_button(
            "Apply selected changes to workspace draft",
            object_name="liquidHelmApplySelectedButton",
            enabled=self.model.apply_available,
            action_kind="stage_draft",
            disabled_reason="Disabled: no deterministic Helm recommendation is available to stage." if not self.model.apply_available else "",
        )
        self.apply_button.clicked.connect(lambda _checked=False: self.apply_selected())
        self.revert_button = action_button(
            "Revert last Helm changes",
            object_name="liquidHelmRevertLastButton",
            enabled=self._last_apply_result is not None and bool(self._last_apply_result.applied_diffs),
            action_kind="revert",
            disabled_reason="Disabled: no Helm draft change batch has been applied in this session." if not (self._last_apply_result is not None and bool(self._last_apply_result.applied_diffs)) else "",
        )
        self.revert_button.clicked.connect(lambda _checked=False: self.revert_last())
        row.addWidget(self.apply_button)
        row.addWidget(self.revert_button)
        row.addStretch(1)
        layout.addLayout(row)
        if self._last_apply_result is not None:
            layout.addWidget(TruthBadge(self._last_apply_result.message, state_role="unsaved" if self._last_apply_result.valid else "warning"))
        return panel


def _hero(model: HelmCommandModel) -> LiquidHeroPanel:
    hero = LiquidHeroPanel(
        "Helm Assistant",
        model.summary or "Tell Helm what feels wrong and it will compare current workspace values.",
        object_name="liquidHelmStatusHero",
        state_role="ready" if model.apply_available else "info",
        minimum_height=220,
    )
    hero.setProperty("helmAssistantHero", True)
    layout = hero.layout()
    if layout is None:
        return hero
    row = horizontal_layout(spacing=8)
    row.addWidget(TruthBadge(model.status_label, state_role="ready" if model.apply_available else "info", helper_text=model.confidence_label))
    row.addWidget(TruthBadge("Draft Helm change review", state_role="unsaved", helper_text="Recommendations are not automatic edits."))
    row.addWidget(TruthBadge("Output proof unchanged", state_role="simulation", helper_text="Helm does not verify output."))
    layout.addLayout(row)
    metric_row = horizontal_layout(spacing=8)
    metric_row.addWidget(MetricTile("Findings", str(len(model.findings)), "grouped by evidence source", state_role="info"), 1)
    metric_row.addWidget(MetricTile("Proposals", str(len(model.proposed_changes)), "workspace draft changes", state_role="unsaved" if model.proposed_changes else "unavailable"), 1)
    metric_row.addWidget(MetricTile("Selected", str(model.selected_change_count), "ready to stage", state_role="info"), 1)
    layout.addLayout(metric_row)
    return hero


def _evidence_panel(model: HelmCommandModel) -> QFrame:
    panel = glass_panel("liquidHelmEvidencePanel", role="liquid_helm_evidence")
    layout = vertical_layout(panel, margins=(14, 12, 14, 12), spacing=7)
    layout.addWidget(QLabel("Evidence source"))
    row = horizontal_layout(spacing=8)
    for label in model.evidence_labels:
        row.addWidget(StatusChip(label, state_role="info"))
    row.addStretch(1)
    layout.addLayout(row)
    for note in model.truth_source_notes:
        layout.addWidget(TruthBadge(note, state_role="simulation"))
    return panel


def _findings_panel(model: HelmCommandModel) -> QFrame:
    panel = glass_panel("liquidHelmFindingsPanel", role="liquid_helm_findings")
    panel.setProperty("helmFindingsPanel", True)
    layout = vertical_layout(panel, margins=(14, 12, 14, 12), spacing=8)
    layout.addWidget(QLabel("Finding cards"))
    for finding in model.findings[:5]:
        card = glass_panel(f"liquidHelmFinding_{_safe(finding.title)}", role="liquid_helm_finding_card")
        card.setProperty("helmFindingCard", True)
        card_layout = vertical_layout(card, margins=(12, 9, 12, 9), spacing=5)
        card_layout.addWidget(StatusChip(finding.title, state_role=finding.state_role))
        card_layout.addWidget(_body(finding.body))
        card_layout.addWidget(_body(f"Evidence source: {finding.evidence_source}"))
        layout.addWidget(card)
    return panel


def _body(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("liquidHelmBodyText")
    label.setWordWrap(True)
    return label


def _safe(text: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in text).strip("_").lower()
