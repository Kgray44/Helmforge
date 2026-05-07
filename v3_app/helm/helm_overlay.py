from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.models.workspace import WorkspaceConfig
from v3_app.helm.context import HelmContext
from v3_app.helm.diff_model import HelmDiff, apply_selected_diffs, revert_applied_diffs
from v3_app.helm.helm_engine import HelmEngine, HelmRecommendationGroup, HelmRecommendationResult
from v3_app.helm.symptom_library import SYMPTOM_CHIPS
from v3_app.pages.page_helpers import card, card_header, card_layout
from v3_app.ui.status_chips import action_button, status_chip


WorkspaceChanged = Callable[[WorkspaceConfig, str], None]
StatusChanged = Callable[[str], None]


class HelmOverlay(QDialog):
    def __init__(
        self,
        *,
        workspace: WorkspaceConfig,
        runtime_status: RuntimePreflightStatus,
        on_workspace_changed: WorkspaceChanged | None = None,
        on_status: StatusChanged | None = None,
        selected_axis: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("helmOverlay")
        self.setWindowTitle("Helm")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setModal(True)
        self._workspace = workspace
        self._runtime_status = runtime_status
        self._selected_axis = selected_axis
        self._on_workspace_changed = on_workspace_changed
        self._on_status = on_status
        self._engine = HelmEngine()
        self._last_result: HelmRecommendationResult | None = None
        self._last_applied_diffs: tuple[HelmDiff, ...] = ()
        self._parent_effect: QGraphicsOpacityEffect | None = None
        self._diff_checks: dict[str, QCheckBox] = {}
        self._group_checks: dict[str, QCheckBox] = {}
        self._group_diff_labels: dict[str, tuple[str, ...]] = {}
        self._follow_up_answers: dict[str, str] = {}

        self._build_ui()

    def open_for_parent(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            width = max(760, int(parent.width() * 0.70))
            height = max(620, int(parent.height() * 0.90))
            x = parent.geometry().x() + max(0, parent.width() - width - 18)
            y = parent.geometry().y() + 28
            self.setGeometry(x, y, width, height)
            self._parent_effect = QGraphicsOpacityEffect(parent)
            self._parent_effect.setOpacity(0.60)
            parent.setGraphicsEffect(self._parent_effect)
        self.show()
        self.raise_()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._restore_parent_effect()
        super().closeEvent(event)

    def _restore_parent_effect(self) -> None:
        parent = self.parentWidget()
        if parent is not None and self._parent_effect is not None:
            parent.setGraphicsEffect(None)
            self._parent_effect = None

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(18)

        root.addWidget(self._build_header())

        scroll = QScrollArea()
        scroll.setObjectName("helmOverlayScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("helmOverlayContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(18)

        intro = QLabel(
            "Describe the control problem in plain language, let me inspect the current tuning context, "
            "and review the proposed workspace changes before you apply them."
        )
        intro.setObjectName("pageBody")
        intro.setWordWrap(True)
        content_layout.addWidget(intro)
        content_layout.addWidget(status_chip("In-memory only", tone="success", object_name="helmSafetyPill"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        grid.addWidget(self._build_symptom_card(), 0, 0)
        grid.addWidget(self._build_diffs_card(), 0, 1)
        grid.addWidget(self._build_findings_card(), 1, 0)
        grid.addWidget(self._build_apply_card(), 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        content_layout.addLayout(grid)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("helmOverlayHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title_block = QVBoxLayout()
        title_block.setSpacing(8)
        title = QLabel("Helm")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Diagnosis-first tuning guidance for the current workspace.")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)

        status_panel = card("helmStatusPanel")
        status_layout = QHBoxLayout(status_panel)
        status_layout.setContentsMargins(18, 14, 18, 14)
        status_layout.setSpacing(12)
        pulse = QLabel("")
        pulse.setObjectName("helmPulseIndicator")
        pulse.setFixedSize(24, 24)
        status_text = QVBoxLayout()
        status_text.setSpacing(4)
        active = QLabel("Helm is active")
        active.setObjectName("routeSummaryValue")
        linked = QLabel("Context-linked assistant")
        linked.setObjectName("cardBody")
        status_text.addWidget(active)
        status_text.addWidget(linked)
        status_layout.addWidget(pulse)
        status_layout.addLayout(status_text)

        close = action_button("Close", object_name="helmCloseButton")
        close.clicked.connect(self.close)

        layout.addLayout(title_block, 1)
        layout.addWidget(status_panel)
        layout.addWidget(close)
        return header

    def _build_symptom_card(self) -> QWidget:
        frame = card("helmWhatsWrongCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("What's wrong?", "Describe the symptom first, then review what I recommend."))
        self.symptom_input = QPlainTextEdit()
        self.symptom_input.setObjectName("helmSymptomInput")
        self.symptom_input.setPlaceholderText("Example: Can't hold aim steady on target.")
        self.symptom_input.setMinimumHeight(148)
        layout.addWidget(self.symptom_input)

        chip_grid = QGridLayout()
        chip_grid.setHorizontalSpacing(10)
        chip_grid.setVerticalSpacing(10)
        for index, symptom in enumerate(SYMPTOM_CHIPS):
            chip = QPushButton(symptom)
            chip.setObjectName(f"helmSymptom_{_key(symptom)}")
            chip.setProperty("uiRole", "symptomChip")
            chip.clicked.connect(lambda _checked=False, text=symptom: self.select_symptom(text))
            chip_grid.addWidget(chip, index // 3, index % 3)
        layout.addLayout(chip_grid)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        analyze = action_button("Analyze", object_name="helmAnalyzeButton")
        analyze.clicked.connect(self.analyze)
        review = action_button("Review Changes", object_name="helmReviewChangesButton")
        review.clicked.connect(self.review_changes)
        cancel = action_button("Cancel", object_name="helmCancelButton")
        cancel.clicked.connect(self.cancel_draft)
        actions.addWidget(analyze)
        actions.addWidget(review)
        actions.addWidget(cancel)
        actions.addStretch(1)
        layout.addLayout(actions)
        return frame

    def _build_diffs_card(self) -> QWidget:
        frame = card("helmDiffsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("What I'd change", "Exact before-and-after diffs that can be applied to the current workspace."))
        self.diff_list = QVBoxLayout()
        self.diff_list.setSpacing(10)
        self.diff_empty_label = QLabel("I'll propose draft-only changes before anything is applied.")
        self.diff_empty_label.setObjectName("cardBody")
        self.diff_empty_label.setWordWrap(True)
        self.diff_list.addWidget(self.diff_empty_label)
        layout.addLayout(self.diff_list)
        layout.addStretch(1)
        return frame

    def _build_findings_card(self) -> QWidget:
        frame = card("helmFindingsCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("What I found", "Diagnosis, confidence, and context from the current stack and runtime state."))
        self.confidence_chip = status_chip("Idle", tone="warning", object_name="helmConfidenceChip")
        self.context_summary = QLabel("Axis context: workspace-wide\nEvidence: Workspace values\nLive analysis: not active")
        self.context_summary.setObjectName("helmContextSummary")
        self.context_summary.setWordWrap(True)
        self.findings_title = QLabel("I'm ready when you are.")
        self.findings_title.setObjectName("routeSummaryValue")
        self.findings_title.setWordWrap(True)
        self.findings_body = QLabel("Tell me what feels wrong and I'll compare it against the current workspace.")
        self.findings_body.setObjectName("cardBody")
        self.findings_body.setWordWrap(True)
        layout.addWidget(self.confidence_chip)
        layout.addWidget(self.context_summary)
        layout.addWidget(self.findings_title)
        layout.addWidget(self.findings_body)
        return frame

    def _build_apply_card(self) -> QWidget:
        frame = card("helmApplyCard")
        layout = card_layout(frame)
        layout.addWidget(card_header("Apply / Revert", "Helm updates the current workspace only. Save when you want to keep the result."))
        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.apply_button = action_button("Apply Selected Changes", object_name="helmApplySelectedButton")
        self.apply_button.clicked.connect(self.apply_selected_changes)
        self.apply_button.setEnabled(False)
        self.revert_button = action_button("Revert Last Helm Changes", object_name="helmRevertLastButton")
        self.revert_button.clicked.connect(self.revert_last_changes)
        actions.addWidget(self.apply_button)
        actions.addWidget(self.revert_button)
        actions.addStretch(1)
        self.review_summary = QLabel("Nothing has been applied yet. Selected changes are staged only after analysis.")
        self.review_summary.setObjectName("helmReviewSummary")
        self.review_summary.setWordWrap(True)
        self.apply_status = QLabel("There isn't a Helm batch to revert yet.")
        self.apply_status.setObjectName("helmApplyStatus")
        self.apply_status.setProperty("uiRole", "cardBody")
        self.apply_status.setWordWrap(True)
        layout.addLayout(actions)
        layout.addWidget(self.review_summary)
        layout.addWidget(self.apply_status)
        return frame

    def select_symptom(self, symptom: str) -> None:
        self.symptom_input.setPlainText(symptom)

    def analyze(self) -> None:
        self._last_result = self._engine.analyze(
            self.symptom_input.toPlainText(),
            self._workspace,
            runtime_truth=self._runtime_status.truth.value,
            output_verified=self._runtime_status.live_output_writes_verified,
            answers=self._follow_up_answers,
            selected_axis=self._selected_axis,
        )
        self._render_result(self._last_result)

    def review_changes(self) -> None:
        if self._last_result is None:
            self.analyze()
        else:
            self._render_result(self._last_result)

    def cancel_draft(self) -> None:
        self.symptom_input.setPlainText("")
        self._last_result = None
        self._follow_up_answers = {}
        self._clear_diffs("I'll propose draft-only changes before anything is applied.")
        self.confidence_chip.setText("Idle")
        self.confidence_chip.setProperty("chipTone", "warning")
        self.context_summary.setText("Axis context: workspace-wide\nEvidence: Workspace values\nLive analysis: not active")
        self.findings_title.setText("I'm ready when you are.")
        self.findings_body.setText("Tell me what feels wrong and I'll compare it against the current workspace.")
        self.review_summary.setText("Nothing has been applied yet. Selected changes are staged only after analysis.")
        self.apply_status.setText("There isn't a Helm batch to revert yet.")
        self.apply_button.setEnabled(False)

    def apply_selected_changes(self) -> None:
        if self._last_result is None or not self._last_result.diffs:
            self.apply_status.setText("I do not have selected changes to apply yet.")
            return
        selected_diffs = self._selected_diffs_from_ui()
        selected_count = sum(1 for diff in selected_diffs if diff.selected)
        if selected_count == 0:
            self.apply_status.setText("Select at least one change before applying.")
            self.apply_button.setEnabled(False)
            return
        updated, applied = apply_selected_diffs(self._workspace, tuple(selected_diffs))
        applied_count = sum(1 for diff in applied if diff.applied)
        self._workspace = updated
        self._last_applied_diffs = tuple(diff for diff in applied if diff.applied)
        self._last_result = replace(self._last_result, diffs=applied)
        self._render_result(self._last_result)
        self.apply_status.setText(
            f"Applied {applied_count} changes in memory. Save Workspace is still required to keep them. "
            "You can revert the last Helm batch."
        )
        if self._on_workspace_changed is not None:
            self._on_workspace_changed(updated, f"Helm staged {applied_count} in-memory changes.")
        elif self._on_status is not None:
            self._on_status(f"Helm staged {applied_count} in-memory changes.")

    def revert_last_changes(self) -> None:
        if not self._last_applied_diffs:
            self.apply_status.setText("There isn't a Helm batch to revert yet.")
            return
        reverted = revert_applied_diffs(self._workspace, self._last_applied_diffs)
        self._workspace = reverted
        self._last_applied_diffs = ()
        if self._last_result is not None:
            self._last_result = replace(
                self._last_result,
                diffs=tuple(replace(diff, applied=False) for diff in self._last_result.diffs),
            )
            self._render_result(self._last_result)
        self.apply_status.setText("Reverted the last Helm batch. The workspace is back to the prior draft values.")
        if self._on_workspace_changed is not None:
            self._on_workspace_changed(reverted, "Helm reverted the last in-memory change batch.")
        elif self._on_status is not None:
            self._on_status("Helm reverted the last in-memory change batch.")

    def _render_result(self, result: HelmRecommendationResult) -> None:
        self.confidence_chip.setText(result.confidence if result.confidence != "None" else "Idle")
        self.confidence_chip.setProperty("chipTone", "success" if result.status == "ready" else "warning")
        self.context_summary.setText(_context_summary_text(result.context))
        self.findings_title.setText(result.summary)
        self.findings_body.setText(_findings_text(result))
        if result.diffs:
            if result.groups:
                self._render_groups(result.groups)
            else:
                self._render_diffs(result.diffs)
            self.apply_status.setText("Review these before applying. Nothing has been applied yet.")
            self._update_review_summary()
        else:
            if result.follow_up_questions:
                self._render_follow_ups(result)
            elif result.status == "idle":
                self._clear_diffs(
                    "Tell me what feels wrong and I'll compare it against the current workspace. "
                    "I'll propose draft-only changes before anything is applied."
                )
            else:
                self._clear_diffs("I do not have safe diffs for that symptom yet.")
            self.review_summary.setText("Nothing has been applied yet. Selected changes are staged only after analysis.")
            self.apply_status.setText("Nothing has been applied yet.")
            self.apply_button.setEnabled(False)

    def _clear_diffs(self, message: str) -> None:
        while self.diff_list.count():
            item = self.diff_list.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._diff_checks = {}
        self._group_checks = {}
        self._group_diff_labels = {}
        label = QLabel(message)
        label.setObjectName("cardBody")
        label.setWordWrap(True)
        self.diff_empty_label = label
        self.diff_list.addWidget(label)

    def _render_diffs(self, diffs: tuple[HelmDiff, ...]) -> None:
        self._clear_diffs("")
        self.diff_empty_label.hide()
        for diff in diffs:
            self._add_diff_row(diff, self.diff_list)

    def _render_follow_ups(self, result: HelmRecommendationResult) -> None:
        self._clear_diffs("Answer these and I'll narrow the recommendation before staging changes.")
        self.diff_empty_label.hide()
        for question in result.follow_up_questions:
            question_card = card(f"helmFollowUp_{question.question_id}")
            layout = card_layout(question_card)
            prompt = QLabel(question.prompt)
            prompt.setObjectName("routeSummaryValue")
            prompt.setWordWrap(True)
            reason = QLabel(question.reason)
            reason.setObjectName("cardBody")
            reason.setWordWrap(True)
            buttons = QHBoxLayout()
            buttons.setSpacing(8)
            for option in question.options:
                button = QPushButton(_option_label(option))
                button.setObjectName(f"helmFollowUp_{question.question_id}_{option}")
                button.setProperty("uiRole", "symptomChip")
                button.clicked.connect(
                    lambda _checked=False, question_id=question.question_id, selected=option: self._answer_follow_up(
                        question_id, selected
                    )
                )
                buttons.addWidget(button)
            buttons.addStretch(1)
            layout.addWidget(prompt)
            layout.addWidget(reason)
            layout.addLayout(buttons)
            self.diff_list.addWidget(question_card)

    def _render_groups(self, groups: tuple[HelmRecommendationGroup, ...]) -> None:
        self._clear_diffs("")
        self.diff_empty_label.hide()
        for group in groups:
            group_card = card(f"helmGroup_{_key(group.label)}")
            layout = card_layout(group_card)
            check = QCheckBox("Select group")
            check.setObjectName(f"helmGroupCheck_{_key(group.label)}")
            check.setChecked(group.selected)
            title = QLabel(f"{group.label}")
            title.setObjectName("routeSummaryValue")
            confidence = QLabel(f"Confidence: {group.confidence} - {group.affected_count} parameters")
            confidence.setObjectName("sectionHint")
            summary = QLabel(group.summary)
            summary.setObjectName("cardBody")
            summary.setWordWrap(True)
            expected = QLabel(f"Expected: {_group_expected_outcome(group)}")
            expected.setObjectName("cardBody")
            expected.setWordWrap(True)
            risk = QLabel(f"Risk: {_group_risk_level(group)} - {'Selected' if group.selected else 'Not selected'}")
            risk.setObjectName("sectionHint")
            risk.setWordWrap(True)
            why = QPushButton("Why?")
            why.setObjectName(f"helmWhy_{_key(group.label)}")
            why.setProperty("uiRole", "subtleAction")
            why_detail = QLabel(f"{group.summary} I keep this staged until you choose Apply Selected Changes.")
            why_detail.setObjectName("cardBody")
            why_detail.setWordWrap(True)
            why_detail.hide()
            why.clicked.connect(lambda _checked=False, detail=why_detail: detail.setVisible(not detail.isVisible()))
            layout.addWidget(check)
            layout.addWidget(title)
            layout.addWidget(confidence)
            layout.addWidget(summary)
            layout.addWidget(expected)
            layout.addWidget(risk)
            layout.addWidget(why)
            layout.addWidget(why_detail)
            self._group_checks[group.group_id] = check
            self._group_diff_labels[group.group_id] = tuple(diff.label for diff in group.diffs)
            check.stateChanged.connect(lambda state, group_id=group.group_id: self._set_group_selected(group_id, state))
            for diff in group.diffs:
                self._add_diff_row(diff, layout)
            self.diff_list.addWidget(group_card)

    def _add_diff_row(self, diff: HelmDiff, parent_layout: QVBoxLayout) -> None:
            row = card(f"helmDiff_{_key(diff.label)}")
            layout = card_layout(row)
            check = QCheckBox("Selected")
            check.setObjectName(f"helmDiffCheck_{_key(diff.label)}")
            check.setChecked(diff.selected)
            check.stateChanged.connect(lambda _state: self._update_review_summary())
            title = QLabel(f"{diff.label} - {diff.section}")
            title.setObjectName("routeSummaryValue")
            title.setWordWrap(True)
            values = QLabel(f"{diff.value_text} - Delta {_fmt_delta(diff.delta_amount)}")
            values.setObjectName("sectionHint")
            values.setWordWrap(True)
            reason = QLabel(diff.reason)
            reason.setObjectName("cardBody")
            reason.setWordWrap(True)
            expected = QLabel(f"Expected: {diff.expected_outcome}")
            expected.setObjectName("cardBody")
            expected.setWordWrap(True)
            risk = QLabel(f"Risk: {diff.risk_level} - Confidence: {diff.confidence_score:.2f} - {diff.reversibility}")
            risk.setObjectName("sectionHint")
            risk.setWordWrap(True)
            state = QLabel("Applied" if diff.applied else "Draft")
            state.setObjectName("sectionHint")
            layout.addWidget(check)
            layout.addWidget(title)
            layout.addWidget(values)
            layout.addWidget(reason)
            layout.addWidget(expected)
            layout.addWidget(risk)
            layout.addWidget(state)
            self._diff_checks[diff.label] = check
            parent_layout.addWidget(row)

    def _answer_follow_up(self, question_id: str, answer: str) -> None:
        self._follow_up_answers[question_id] = answer
        self.apply_status.setText("I noted that answer. Press Analyze again and I'll narrow the recommendation.")

    def _set_group_selected(self, group_id: str, state: int) -> None:
        selected = state == Qt.CheckState.Checked.value or state == Qt.CheckState.Checked
        for label in self._group_diff_labels.get(group_id, ()):
            checkbox = self._diff_checks.get(label)
            if checkbox is not None and checkbox.isChecked() != selected:
                checkbox.setChecked(selected)
        self._update_review_summary()

    def _selected_diffs_from_ui(self) -> tuple[HelmDiff, ...]:
        if self._last_result is None:
            return ()
        selected_diffs: list[HelmDiff] = []
        for diff in self._last_result.diffs:
            checkbox = self._diff_checks.get(diff.label)
            diff_selected = True if checkbox is None else checkbox.isChecked()
            selected_diffs.append(replace(diff, selected=diff_selected))
        return tuple(selected_diffs)

    def _update_review_summary(self) -> None:
        if self._last_result is None or not self._last_result.diffs:
            self.apply_button.setEnabled(False)
            return
        selected = [diff for diff in self._selected_diffs_from_ui() if diff.selected]
        selected_count = len(selected)
        group_count = len(self._last_result.groups)
        parameter_count = len(self._last_result.diffs)
        axes = ", ".join(dict.fromkeys(diff.axis for diff in self._last_result.diffs))
        expected = _review_expected_summary(self._last_result)
        risk = _review_risk_summary(selected or self._last_result.diffs)
        change_word = "change is" if selected_count == 1 else "changes are"
        group_word = "group" if group_count == 1 else "groups"
        self.review_summary.setText(
            f"I found {group_count} tuning {group_word} affecting {parameter_count} parameters.\n"
            f"{selected_count} {change_word} selected.\n"
            f"affected axes: {axes}\n"
            f"Expected result: {expected}\n"
            f"Risk: {risk}; these are reversible and not saved yet.\n"
            "In-memory only. Save Workspace is still required to keep them."
        )
        if selected_count == 0:
            self.apply_status.setText("Select at least one change before applying.")
        elif not any(diff.applied for diff in self._last_result.diffs):
            self.apply_status.setText(f"{selected_count} changes ready. Review these before applying. Selected changes are staged only.")
        self.apply_button.setEnabled(selected_count > 0)


def _key(value: str) -> str:
    return value.replace("'", "").replace("/", "_").replace(" ", "_")


def _fmt_delta(delta: float) -> str:
    sign = "+" if delta > 0 else ""
    text = f"{delta:.2f}".rstrip("0").rstrip(".")
    return f"{sign}{text}" if text else "0"


def _option_label(value: str) -> str:
    return value.replace("_", " ").title()


def _group_expected_outcome(group: HelmRecommendationGroup) -> str:
    if not group.diffs:
        return "A small, reversible tuning change."
    return group.diffs[0].expected_outcome


def _group_risk_level(group: HelmRecommendationGroup) -> str:
    risks = {"Low": 1, "Medium": 2, "High": 3}
    highest = max(group.diffs, key=lambda diff: risks.get(diff.risk_level, 0), default=None)
    return highest.risk_level if highest is not None else "Low"


def _review_expected_summary(result: HelmRecommendationResult) -> str:
    if result.symptom is not None and result.symptom.symptom_id == "combat_sluggish":
        return "smoother combat recovery with less sluggish yaw response."
    if result.groups:
        labels = ", ".join(group.label for group in result.groups)
        return f"a more controlled feel across {labels}."
    return "a small, reversible tuning change."


def _review_risk_summary(diffs: tuple[HelmDiff, ...] | list[HelmDiff]) -> str:
    risks = {diff.risk_level for diff in diffs}
    if "High" in risks:
        return "high"
    if "Medium" in risks:
        return "moderate"
    return "low"


def _context_summary_text(context: HelmContext | None) -> str:
    if context is None:
        return "Axis context: workspace-wide\nEvidence: Workspace values\nLive analysis: not active"
    return "\n".join(
        (
            f"Axis context: {context.selected_axis}",
            f"Evidence: {', '.join(context.evidence_labels)}",
            f"Runtime: {context.runtime.runtime_truth}",
            f"Output verified: {str(context.runtime.output_verified).lower()}",
            f"Discovery-only status: {context.runtime.device_discovery_status}",
            "Live analysis: not active",
        )
    )


def _findings_text(result: HelmRecommendationResult) -> str:
    lines = list(result.findings)
    lines.append("I'm using workspace values only; live hardware analysis is not active.")
    if result.analysis_findings:
        lines.append("")
        grouped: dict[str, list[str]] = {}
        for finding in result.analysis_findings:
            grouped.setdefault(finding.source_group, []).append(f"- {finding.title}: {finding.text}")
        for group, entries in grouped.items():
            lines.append(group)
            lines.extend(entries)
    if result.follow_up_questions:
        lines.append("")
        lines.extend(f"Question: {question.prompt}" for question in result.follow_up_questions)
    if result.warnings:
        lines.append("")
        lines.extend(f"Warning: {warning}" for warning in result.warnings)
    return "\n".join(lines)
