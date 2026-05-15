from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from shared_core.models.runtime import (
    InputDeviceDetection,
    OutputBackendDetection,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)
from shared_core.models.workspace import CONFIG_FILENAME, WorkspaceConfig, create_default_workspace
from shared_core.persistence.workspace_identity import compute_workspace_hash
from shared_core.persistence.workspace_store import WorkspaceJsonError, load_workspace, save_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.telemetry import BridgeTelemetrySnapshot
from v3_app.pages.base_tuning_page import BaseTuningPage
from v3_app.pages.combat_profile_page import CombatProfilePage
from v3_app.pages.conditional_rules_page import ConditionalRulesPage
from v3_app.pages.effective_response_stack_page import EffectiveResponseStackPage
from v3_app.pages.filtering_page import FilteringPage
from v3_app.pages.flight_recorder_page import FlightRecorderPage
from v3_app.pages.help_docs_page import HelpDocsPage
from v3_app.pages.live_monitor_page import LiveMonitorPage
from v3_app.pages.mapping_page import MappingPage
from v3_app.pages.modes_page import ModesPage
from v3_app.pages.placeholders import PAGE_DEFINITIONS, create_placeholder_page, page_definition_by_id
from v3_app.pages.perf_diagnostics_page import PerfDiagnosticsPage
from v3_app.pages.preflight_page import PreflightPage
from v3_app.pages.profiles_page import ProfilesPage
from v3_app.helm.helm_overlay import HelmOverlay
from v3_app.services.app_state import AppState, build_initial_app_state
from v3_app.services.bridge_commands import BridgeCommandClient
from v3_app.services.bridge_client import BridgeTelemetryClient
from v3_app.services.live_ui_scheduler import MultiCadenceScheduler
from v3_app.services.perf_diagnostics import DiagnosticsCollector
from v3_app.ui.footer import Footer
from v3_app.ui.header import Header
from v3_app.ui.sidebar import Sidebar


class HelmForgeShell(QWidget):
    def __init__(
        self,
        state: AppState | None = None,
        *,
        workspace: WorkspaceConfig | None = None,
        workspace_path: str | Path | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        diagnostics_collector: DiagnosticsCollector | None = None,
        bridge_command_path: str | Path | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("helmforgeShell")
        self.state = state or build_initial_app_state()
        self.workspace_path = Path(workspace_path or CONFIG_FILENAME)
        self._bridge_telemetry_path = None if state is None else self.workspace_path.parent / f".{self.workspace_path.name}.fixture_bridge_telemetry.json"
        self._applied_workspace_path = self.workspace_path.parent / f".{self.workspace_path.stem}.applied{self.workspace_path.suffix}"
        self._bridge_command_client = BridgeCommandClient(command_path=bridge_command_path)
        self.workspace = workspace or self._load_initial_workspace()
        self._last_saved_workspace = self.workspace
        self.state.source_config = str(self.workspace_path)
        self.state.active_profile = self.workspace.active_profile
        self.runtime_status = runtime_status or _runtime_status_from_state(self.state)
        self.active_page_id = self.state.active_page_id
        self.page_widgets: dict[str, QScrollArea] = {}
        self.helm_overlay: HelmOverlay | None = None
        self.diagnostics_collector = diagnostics_collector or DiagnosticsCollector()
        self._shell_scheduler = MultiCadenceScheduler()
        self._latest_bridge_telemetry: BridgeTelemetrySnapshot | None = None
        self._last_shell_chrome_signature: tuple[object, ...] | None = None
        self.shell_chrome_update_count = 0
        self.shell_chrome_skip_count = 0

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        self.sidebar = Sidebar(PAGE_DEFINITIONS, self.state, self.switch_page)
        self.header = Header(self.state, on_helm=self.open_helm_overlay)
        self.stack = QStackedWidget()
        self.stack.setObjectName("pageStack")
        self.footer = Footer(
            self.state,
            page_definition_by_id(self.active_page_id),
            on_import_profile=self.import_profile_placeholder,
            on_revert=self.revert_workspace,
            on_apply=self.apply_workspace,
            on_save=self.save_workspace,
        )

        main = QWidget()
        main.setObjectName("contentViewport")
        self.content_viewport = main
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        main_layout.addWidget(self.header)
        main_layout.addWidget(self.stack, 1)
        main_layout.addWidget(self.footer)

        root.addWidget(self.sidebar)
        root.addWidget(main, 1)

        self._build_pages()
        self.switch_page(self.active_page_id, record_timing=False)

    def _load_initial_workspace(self) -> WorkspaceConfig:
        if self.workspace_path.exists():
            try:
                return load_workspace(self.workspace_path).workspace
            except WorkspaceJsonError as exc:
                self.state.status_message = f"Workspace load failed; using default draft. {exc}"
                self.state.saved = False
        return create_default_workspace()

    def _build_pages(self) -> None:
        for page in PAGE_DEFINITIONS:
            if page.page_id == "perf_diagnostics":
                scroll = _LazyPageScrollArea(lambda page=page: self._create_page_content(page.page_id, page))
            else:
                scroll = QScrollArea()
            scroll.setObjectName("pageScrollArea")
            scroll.viewport().setObjectName("pageScrollViewport")
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            if not isinstance(scroll, _LazyPageScrollArea):
                content = self._create_page_content(page.page_id, page)
                scroll.setWidget(content)
            self.stack.addWidget(scroll)
            self.page_widgets[page.page_id] = scroll

    def _rebuild_pages(self) -> None:
        while self.stack.count():
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()
        self.page_widgets = {}
        self._build_pages()
        self.switch_page(self.active_page_id, record_timing=False)

    def _create_page_content(self, page_id: str, page) -> QWidget:
        common = {
            "state": self.state,
            "workspace": self.workspace,
            "runtime_status": self.runtime_status,
        }
        if page_id == "preflight":
            return PreflightPage(**common, on_status=self.set_status_message)
        if page_id == "mapping":
            return MappingPage(
                **common,
                on_dirty=self.mark_workspace_dirty,
                on_status=self.set_status_message,
                on_workspace_changed=self.update_workspace_draft,
            )
        if page_id == "modes":
            return ModesPage(**common, on_dirty=self.mark_workspace_dirty)
        if page_id == "base_tuning":
            return BaseTuningPage(
                **common,
                on_dirty=self.mark_workspace_dirty,
                on_workspace_changed=self.update_workspace_draft,
            )
        if page_id == "filtering":
            return FilteringPage(
                **common,
                on_dirty=self.mark_workspace_dirty,
                on_workspace_changed=self.update_workspace_draft,
            )
        if page_id == "combat_profile":
            return CombatProfilePage(
                **common,
                on_dirty=self.mark_workspace_dirty,
                on_workspace_changed=self.update_workspace_draft,
            )
        if page_id == "profiles":
            return ProfilesPage(**common, on_status=self.set_status_message)
        if page_id == "conditional_rules":
            return ConditionalRulesPage(
                **common,
                on_dirty=self.mark_workspace_dirty,
                on_status=self.set_status_message,
                on_workspace_changed=self.update_workspace_draft,
            )
        if page_id == "effective_response_stack":
            return EffectiveResponseStackPage(**common, diagnostics_collector=self.diagnostics_collector)
        if page_id == "live_monitor":
            return LiveMonitorPage(
                **common,
                diagnostics_collector=self.diagnostics_collector,
                telemetry_path=self._bridge_telemetry_path,
            )
        if page_id == "flight_recorder":
            return FlightRecorderPage(**common)
        if page_id == "help_docs":
            return HelpDocsPage(**common, on_open_page=self.switch_page, on_open_helm=self.open_helm_overlay)
        if page_id == "perf_diagnostics":
            return PerfDiagnosticsPage(
                **common,
                workspace_path=self.workspace_path,
                diagnostics_collector=self.diagnostics_collector,
                telemetry_client=BridgeTelemetryClient(telemetry_path=self._bridge_telemetry_path)
                if self._bridge_telemetry_path is not None
                else None,
            )
        return create_placeholder_page(page, runtime_label=self.state.runtime.runtime_card_label)

    def mark_workspace_dirty(self, message: str) -> None:
        self.state.saved = False
        self.state.status_message = message
        self.header.update_state(self.state)
        self.footer.update_state(self.state, page_definition_by_id(self.active_page_id))

    def update_workspace_draft(self, workspace: WorkspaceConfig, message: str) -> None:
        self.workspace = workspace
        self.mark_workspace_dirty(message)

    def set_status_message(self, message: str) -> None:
        self.state.status_message = message
        self.footer.update_state(self.state, page_definition_by_id(self.active_page_id))

    def apply_bridge_telemetry(self, telemetry: BridgeTelemetrySnapshot) -> None:
        self._latest_bridge_telemetry = telemetry
        self.runtime_status = _runtime_status_from_bridge_telemetry(telemetry)
        self.state.runtime = AppState.from_runtime_status(
            self.runtime_status,
            driver_detected=self.state.runtime.driver_detected,
        ).runtime
        self.state.active_profile = telemetry.active_profile
        signature = _shell_chrome_signature(self.state, self.runtime_status, self.active_page_id)
        chrome_changed = signature != self._last_shell_chrome_signature
        cadence_due = self._shell_scheduler.run("shell_chrome")
        if chrome_changed or cadence_due:
            started_at = time.perf_counter()
            self.header.update_state(self.state)
            self.sidebar.update_runtime(self.state)
            self.footer.update_state(self.state, page_definition_by_id(self.active_page_id))
            self._last_shell_chrome_signature = signature
            self.shell_chrome_update_count += 1
            self.diagnostics_collector.record_timing("shell_chrome_update", (time.perf_counter() - started_at) * 1000.0)
        else:
            self.shell_chrome_skip_count += 1
        scroll = self.page_widgets.get(self.active_page_id)
        content = scroll.widget() if scroll is not None else None
        if hasattr(content, "update_runtime_status"):
            content.update_runtime_status(self.runtime_status)

    def import_profile_placeholder(self) -> None:
        self.set_status_message("Import Profile is reserved for a later import phase; no workspace file was changed.")

    def apply_workspace(self) -> None:
        try:
            save_workspace(self.workspace, self._applied_workspace_path, overwrite=True)
            workspace_hash = compute_workspace_hash(self.workspace)
            result = self._bridge_command_client.reload_config(
                config_path=self._applied_workspace_path,
                expected_workspace_hash=workspace_hash,
                expected_workspace_revision=workspace_hash[:12],
            )
        except Exception as exc:
            self.state.status_message = f"Apply Workspace failed: {exc}"
            self.footer.update_state(self.state, page_definition_by_id(self.active_page_id))
            return
        self.state.saved = False
        self.state.status_message = (
            "Applied workspace draft to the Bridge. Save Workspace is still required to keep it."
            if result.success
            else f"Apply Workspace command failed: {result.message}"
        )
        self.header.update_state(self.state)
        self.footer.update_state(self.state, page_definition_by_id(self.active_page_id))

    def open_helm_overlay(self) -> HelmOverlay:
        if self.helm_overlay is None:
            self.helm_overlay = HelmOverlay(
                workspace=self.workspace,
                runtime_status=self.runtime_status,
                on_workspace_changed=self.update_workspace_draft,
                on_status=self.set_status_message,
                selected_axis=self.state.selected_axis,
                parent=self,
            )
        else:
            self.helm_overlay._workspace = self.workspace
            self.helm_overlay._selected_axis = self.state.selected_axis
        self.helm_overlay.open_for_parent()
        return self.helm_overlay

    def save_workspace(self) -> None:
        try:
            save_workspace(self.workspace, self.workspace_path, overwrite=True)
        except Exception as exc:
            self.state.saved = False
            self.set_status_message(f"Workspace save failed: {exc}")
            self.header.update_state(self.state)
            return
        self._last_saved_workspace = self.workspace
        self.state.saved = True
        self.state.status_message = "Saved workspace draft."
        self.header.update_state(self.state)
        self.footer.update_state(self.state, page_definition_by_id(self.active_page_id))

    def revert_workspace(self) -> None:
        if self.workspace_path.exists():
            try:
                self.workspace = load_workspace(self.workspace_path).workspace
            except WorkspaceJsonError as exc:
                self.set_status_message(f"Workspace revert failed: {exc}")
                return
        else:
            self.workspace = self._last_saved_workspace
        self._last_saved_workspace = self.workspace
        self.state.saved = True
        self.state.status_message = "Reverted the workspace to the last saved or imported state."
        self.header.update_state(self.state)
        self.footer.update_state(self.state, page_definition_by_id(self.active_page_id))
        self._rebuild_pages()

    def switch_page(self, page_id: str, *, record_timing: bool = True) -> None:
        if page_id not in self.page_widgets:
            raise KeyError(page_id)

        start = time.perf_counter()
        self.active_page_id = page_id
        self.state.active_page_id = page_id
        self.stack.setCurrentWidget(self.page_widgets[page_id])
        self.sidebar.update_active(page_id)
        self.footer.update_state(self.state, page_definition_by_id(page_id))
        if record_timing:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self.state.page_switch_timings_ms[page_id] = elapsed_ms
            self.diagnostics_collector.record_timing("page_switch", elapsed_ms)
        content = self.page_widgets[page_id].widget()
        if hasattr(content, "refresh_diagnostics"):
            content.refresh_diagnostics()


def _runtime_status_from_state(state: AppState) -> RuntimePreflightStatus:
    if state is None:
        return build_runtime_preflight_status()
    return RuntimePreflightStatus(
        mode=RuntimeMode.FULL_LIVE
        if state.runtime.truth is RuntimeTruth.LIVE_VERIFIED and state.runtime.output_verified
        else RuntimeMode.SIMULATED,
        truth=state.runtime.truth,
        input=InputDeviceDetection(status=state.runtime.input_status),
        output=OutputBackendDetection(
            status=state.runtime.output_status,
            backend_name=state.runtime.backend_name,
            live_output_writes_verified=state.runtime.output_verified,
        ),
    )


def _runtime_status_from_bridge_telemetry(telemetry: BridgeTelemetrySnapshot) -> RuntimePreflightStatus:
    return RuntimePreflightStatus(
        mode=RuntimeMode.FULL_LIVE
        if telemetry.runtime_truth is RuntimeTruth.LIVE_VERIFIED and telemetry.output_verified
        else RuntimeMode.SIMULATED,
        truth=telemetry.runtime_truth,
        input=InputDeviceDetection(status=telemetry.input_status),
        output=OutputBackendDetection(
            status=telemetry.output_status,
            backend_name=telemetry.output_verification.backend_name,
            live_output_writes_verified=telemetry.output_verified,
        ),
        warnings=telemetry.warnings,
        errors=telemetry.errors,
    )


def _shell_chrome_signature(state: AppState, runtime_status: RuntimePreflightStatus, active_page_id: str) -> tuple[object, ...]:
    return (
        runtime_status.truth.value,
        runtime_status.input.status.value,
        runtime_status.output.status.value,
        bool(runtime_status.live_output_writes_verified),
        state.active_profile,
        bool(state.saved),
        state.status_message,
        active_page_id,
    )


class _LazyPageScrollArea(QScrollArea):
    def __init__(self, content_factory) -> None:
        super().__init__()
        self._content_factory = content_factory
        self._content_built = False

    def widget(self) -> QWidget | None:  # type: ignore[override]
        self._ensure_content()
        return super().widget()

    def _ensure_content(self) -> None:
        if self._content_built:
            return
        super().setWidget(self._content_factory())
        self._content_built = True
