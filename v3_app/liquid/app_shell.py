from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QScrollArea, QSizePolicy, QStackedWidget, QWidget

from shared_core.models.workspace import CONFIG_FILENAME, WorkspaceConfig, create_default_workspace
from shared_core.persistence.workspace_store import WorkspaceJsonError, load_workspace
from shared_core.models.runtime import (
    InputDeviceDetection,
    OutputBackendDetection,
    RuntimeMode,
    RuntimePreflightStatus,
    RuntimeTruth,
)
from shared_core.runtime.telemetry import BridgeTelemetrySnapshot
from v3_app.liquid.atmosphere import apply_atmosphere
from v3_app.liquid.glass import action_button, glass_panel, refresh_style, status_chip
from v3_app.liquid.layout import grid_layout, horizontal_layout, vertical_layout
from v3_app.liquid.models.nav_model import (
    LiquidNavigationModel,
    LiquidNavigationState,
    build_liquid_navigation_model,
)
from v3_app.liquid.models.mapping_edit_model import (
    MappingEditResult,
    control_id_for_route_id,
    route_id_for_control_id,
    stage_mapping_route_edit,
)
from v3_app.liquid.models.helm_command_model import (
    HelmApplyResult,
    revert_helm_changes,
    stage_selected_helm_changes,
)
from v3_app.liquid.models.tuning_command_model import (
    TuningEditResult,
    stage_tuning_parameter_edit,
)
from v3_app.liquid.navigation import LIQUID_MODE_IDS, LiquidModeDock, LiquidSubpageSelector
from v3_app.liquid.pages.placeholder_pages import (
    LIQUID_ROUTE_PAGE_FACTORIES,
)
from v3_app.liquid.pages.helm_command_deck import HelmAssistantDeck
from v3_app.liquid.motion import MotionIntensity, MotionSettings, apply_status_motion, current_motion_settings, ease_out_cubic, page_motion_spec, refresh_motion_style
from v3_app.liquid.quick_switch_wheel import QUICK_WHEEL_MODE_IDS, LiquidQuickSwitchWheel
from v3_app.liquid.theme_tokens import LiquidLayout, liquid_qss
from v3_app.liquid.visible_motion import (
    LiquidAtmosphereLayer,
    LiquidMotionCoordinator,
    LiquidPageTransitionOverlay,
    LiquidRouteSweepController,
    LiquidStatusBreathController,
    MotionProofPanel,
    visible_motion_profile,
)
from v3_app.services.app_state import AppState, build_initial_app_state
from v3_app.services.live_ui_scheduler import MultiCadenceScheduler


_PAGE_ID_TO_ROUTE_KEY = {
    "preflight": "preflight.command_readiness",
    "mapping": "mapping.hotas_map",
    "profiles": "mapping.route_details",
    "modes": "mapping.advanced_route_tables",
    "base_tuning": "tuning.base_tuning",
    "filtering": "tuning.filtering",
    "combat_profile": "tuning.combat_profile",
    "conditional_rules": "tuning.conditional_rules",
    "profiles_library": "tuning.profiles_library",
    "effective_response_stack": "analysis.effective_response_stack",
    "live_monitor": "analysis.live_monitor",
    "perf_diagnostics": "support.perf_diagnostics",
    "flight_recorder": "recorder.flight_recorder",
    "help_docs": "support.help_docs",
    "setup_runtime_check": "support.setup_runtime_check",
}


def _lcd4f_trace(message: str) -> None:
    if os.environ.get("HELMFORGE_LCD4F_TRACE") == "1":
        print(f"LCD4F_TRACE: {message}", flush=True)


def _quick_wheel_enabled_from_environment() -> bool:
    value = os.environ.get("HELMFORGE_LIQUID_QUICK_WHEEL", "")
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _visible_motion_timers_allowed() -> bool:
    return os.environ.get("QT_QPA_PLATFORM", "").strip().casefold() != "offscreen"


def _route_error_fallback(route_key: str, exc: Exception) -> QFrame:
    panel = glass_panel("liquidRouteErrorFallback", role="liquid_route_error_fallback")
    panel.setProperty("componentRole", "RouteErrorFallback")
    panel.setProperty("routeKey", route_key)
    panel.setProperty("routeErrorFallback", True)
    panel.setMinimumHeight(360)
    layout = vertical_layout(panel, margins=(18, 16, 18, 16), spacing=10)
    title = QLabel("Route failed to construct")
    title.setObjectName("liquidRouteErrorTitle")
    detail = QLabel(f"{route_key}: {type(exc).__name__}: {exc}")
    detail.setObjectName("liquidRouteErrorDetail")
    detail.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(detail)
    layout.addStretch(1)
    return panel


def _status_breath_targets(root: QWidget) -> list[QWidget]:
    targets: list[QWidget] = []
    for widget in root.findChildren(QWidget):
        if widget.property("rawDiagnosticSurface") is True:
            continue
        component_role = str(widget.property("componentRole") or "")
        ui_role = str(widget.property("uiRole") or "")
        if (
            component_role in {"StatusChip", "StatusLight", "TruthBadge", "ReadinessGate", "TelemetryFreshnessRail", "DraftStateIndicator"}
            or ui_role == "liquidStatusChip"
            or widget.objectName() == "liquidStatusLight"
        ):
            targets.append(widget)
    return targets


def _route_sweep_targets(root: QWidget) -> list[QWidget]:
    return [widget for widget in root.findChildren(QWidget) if widget.property("signalPathMotionAvailable") is True]


def _interaction_motion_targets(root: QWidget) -> list[QWidget]:
    targets: list[QWidget] = []
    for widget in root.findChildren(QWidget):
        if widget.property("rawDiagnosticSurface") is True:
            continue
        ui_role = str(widget.property("uiRole") or "")
        component_role = str(widget.property("componentRole") or "")
        if (
            ui_role
            in {
                "liquidActionButton",
                "liquidModeDockButton",
                "liquidSubpageSelectorButton",
                "liquidAxisPill",
                "liquidMappingMarker",
                "liquidQuickWheelButton",
                "liquidStatusChip",
            }
            or widget.property("motionProofDemo") is not None
            or widget.property("microinteractionRole") in {"interactive_card", "selectable_card", "status_card"}
            or component_role
            in {
                "ReadinessGate",
                "TruthBadge",
                "MetricTile",
                "DraftStateIndicator",
                "TelemetryFreshnessRail",
                "RouteFlowRow",
                "SignalPipelineStage",
                "ParameterRow",
                "CapabilityRail",
                "MotionProofPanel",
            }
        ):
            targets.append(widget)
    return targets


class _LiquidRouteHost(QStackedWidget):
    def __init__(self, motion_settings: MotionSettings) -> None:
        super().__init__()
        self._motion_settings = motion_settings
        self._motion_timer_id = 0
        self._motion_ticks_remaining = 0
        self._motion_count = 0
        self._motion_frame_count = 0
        self._motion_elapsed_seconds = 0.0
        self._motion_duration_seconds = 0.22
        self._external_clock_driven = False
        self.set_motion_settings(motion_settings)
        self.setProperty("pageMotionUsesDynamicReparenting", False)
        self.setProperty("pageMotionAnimatesGeometry", False)
        self.setProperty("pageMotionUsesOpacityEffect", False)
        self.setProperty("pageMotionUsesBlurEffect", False)

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        spec = page_motion_spec(motion_settings)
        self.setProperty("motionIntensity", motion_settings.intensity.value)
        self.setProperty("pageMotionMode", spec.mode)
        self.setProperty("pageMotionEnabled", spec.enabled)
        self.setProperty("pageMotionDurationMs", spec.duration_ms)
        self.setProperty("pageMotionExitMs", spec.exit_ms)
        self.setProperty("pageMotionEnterMs", spec.enter_ms)
        self.setProperty("pageMotionPanelStaggerMs", spec.panel_stagger_ms)
        self.setProperty("pageMotionSlideOffsetPx", spec.slide_offset_px)
        if not spec.enabled:
            self._clear_route_motion()

    def set_external_clock_driven(self, enabled: bool) -> None:
        self._external_clock_driven = bool(enabled)
        if self._external_clock_driven and self._motion_timer_id:
            self.killTimer(self._motion_timer_id)
            self._motion_timer_id = 0

    def begin_route_motion(self, *, from_route: str, to_route: str) -> None:
        spec = page_motion_spec(self._motion_settings)
        if not spec.enabled or from_route == to_route:
            self._clear_route_motion()
            return
        if self._motion_timer_id:
            self.killTimer(self._motion_timer_id)
            self._motion_timer_id = 0
        self._motion_count += 1
        self._motion_frame_count = 0
        self._motion_elapsed_seconds = 0.0
        self._motion_duration_seconds = max(0.001, float(spec.duration_ms or 220) / 1000.0)
        self._motion_ticks_remaining = max(1, spec.duration_ms // 33)
        self.setProperty("pageMotionCount", self._motion_count)
        self.setProperty("pageMotionFrom", from_route)
        self.setProperty("pageMotionTo", to_route)
        self.setProperty("pageMotionActive", True)
        self.setProperty("pageMotionPhase", "enter")
        self.setProperty("pageMotionProgress", 0.0)
        if not self._external_clock_driven:
            self._motion_timer_id = self.startTimer(33)
        refresh_motion_style(self)

    def advance_motion_frame(self, *, delta_seconds: float = 1.0 / 60.0) -> None:
        if self.property("pageMotionActive") is True:
            self._advance_route_motion(delta_seconds)

    def timerEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.timerId() != self._motion_timer_id:
            super().timerEvent(event)
            return
        self._advance_route_motion(1.0 / 33.0)
        event.accept()

    def _advance_route_motion(self, delta_seconds: float) -> None:
        if self._motion_ticks_remaining <= 0:
            self._clear_route_motion()
            return
        self._motion_frame_count += 1
        self._motion_elapsed_seconds += max(0.0, delta_seconds)
        raw_progress = min(1.0, self._motion_elapsed_seconds / self._motion_duration_seconds)
        progress = ease_out_cubic(raw_progress)
        self.setProperty("pageMotionFrameCount", self._motion_frame_count)
        self.setProperty("pageMotionProgress", round(progress, 3))
        self.setProperty("pageMotionPhase", "settle" if progress >= 0.5 else "enter")
        self._motion_ticks_remaining -= 1
        refresh_motion_style(self)
        if raw_progress >= 1.0:
            self._clear_route_motion()

    def _clear_route_motion(self) -> None:
        if self._motion_timer_id:
            self.killTimer(self._motion_timer_id)
            self._motion_timer_id = 0
        self._motion_ticks_remaining = 0
        self.setProperty("pageMotionActive", False)
        self.setProperty("pageMotionPhase", "settled")
        self.setProperty("pageMotionProgress", 1.0)
        refresh_motion_style(self)


class LiquidCommandShell(QWidget):
    def __init__(
        self,
        state: AppState | None = None,
        *,
        workspace: WorkspaceConfig | None = None,
        workspace_path: str | Path | None = None,
        motion_settings: MotionSettings | None = None,
        quick_wheel_enabled: bool | None = None,
    ) -> None:
        super().__init__()
        _lcd4f_trace("constructing liquid shell")
        self.setObjectName("liquidCommandShell")
        self.setStyleSheet(liquid_qss())
        state_was_supplied = state is not None
        self.state = state or build_initial_app_state()
        self.motion_settings = motion_settings or current_motion_settings()
        self.setProperty("motionIntensity", self.motion_settings.intensity.value)
        self.setProperty("pageMotionEnabled", self.motion_settings.page_motion_enabled())
        self.quick_wheel_enabled = _quick_wheel_enabled_from_environment() if quick_wheel_enabled is None else bool(quick_wheel_enabled)
        self._quick_wheel_shortcut: QShortcut | None = None
        self.setProperty("quickWheelEnabled", self.quick_wheel_enabled)
        self.setProperty("quickWheelRequiredForNavigation", False)
        self.setProperty("quickWheelRuntimeMutation", False)
        self.setProperty("quickWheelModeIds", QUICK_WHEEL_MODE_IDS)
        self._atmosphere_signature: tuple[str, str, str] | None = None
        self.atmosphere_update_count = 0
        self.setProperty("atmosphereUpdateCount", self.atmosphere_update_count)
        apply_atmosphere(self, mode_id="preflight", motion_settings=self.motion_settings)
        self.workspace_path = Path(workspace_path or CONFIG_FILENAME)
        self.workspace = workspace or self._load_initial_workspace(load_from_disk=not state_was_supplied)
        self._mapping_base_workspace = self.workspace
        self._mapping_base_saved_state = bool(self.workspace.state.saved)
        self._selected_mapping_route_id = "axis:axis_roll"
        self._mapping_last_edit_result: MappingEditResult | None = None
        self._tuning_base_workspace = self.workspace
        self._tuning_base_saved_state = bool(self.workspace.state.saved)
        self._selected_tuning_axis_by_route = {
            "tuning.base_tuning": "Roll",
            "tuning.filtering": "Roll",
            "tuning.combat_profile": "Roll",
            "tuning.conditional_rules": "Roll",
            "tuning.profiles_library": "Roll",
        }
        self._tuning_last_edit_result: TuningEditResult | None = None
        self._selected_analysis_axis_by_route = {
            "analysis.effective_response_stack": "Roll",
            "analysis.live_monitor": "Roll",
        }
        self._helm_base_workspace = self.workspace
        self._helm_base_saved_state = bool(self.workspace.state.saved)
        self._helm_last_apply_result: HelmApplyResult | None = None
        self._helm_deck_open = False
        if not state_was_supplied:
            self.state.source_config = str(self.workspace_path)
            self.state.active_profile = self.workspace.active_profile
            self.state.saved = self.workspace.state.saved
        _lcd4f_trace("creating navigation model")
        self.navigation_model = build_liquid_navigation_model()
        self.navigation_state = _navigation_state_from_state(self.state, self.navigation_model)
        self.active_mode_id = self.navigation_state.current_mode_id
        self.active_subpage_id = self.navigation_state.current_subpage_id
        self.current_route_key = self.navigation_state.current_route.route_key
        self.page_widgets: dict[str, QWidget] = {}
        self._latest_bridge_telemetry: BridgeTelemetrySnapshot | None = None
        self._shell_scheduler = MultiCadenceScheduler()
        self._last_shell_chrome_signature: tuple[object, ...] | None = None
        self.shell_chrome_update_count = 0
        self.shell_chrome_skip_count = 0
        self.route_switch_count = 0
        self.recursive_sync_guard_count = 0
        self._route_sync_in_progress = False
        self._analysis_sync_in_progress = False
        self.setProperty("routeSwitchCount", self.route_switch_count)
        self.setProperty("recursiveRouteSyncGuardCount", self.recursive_sync_guard_count)

        root = vertical_layout(
            self,
            margins=(
                LiquidLayout.shell_margin,
                LiquidLayout.shell_margin,
                LiquidLayout.shell_margin,
                LiquidLayout.shell_margin,
            ),
            spacing=LiquidLayout.shell_spacing,
        )

        self.top_bar = _LiquidTopCommandBar(
            self.state,
            on_helm_toggled=self.toggle_helm_deck,
            motion_settings=self.motion_settings,
            on_motion_changed=self.set_motion_intensity,
        )
        self.workspace_frame = glass_panel("liquidCommandWorkspace", role="liquid_command_workspace")
        workspace_layout = vertical_layout(
            self.workspace_frame,
            margins=(0, 0, 0, 0),
            spacing=0,
        )
        self.command_surface = glass_panel("liquid_command_surface", role="liquid_command_surface")
        surface_layout = grid_layout(self.command_surface, margins=(0, 0, 0, 0), spacing=0)
        self.surface_glass_field = glass_panel("liquid_surface_glass_field", role="liquid_surface_glass_field")
        self.surface_glass_field.setProperty("footerScrim", "none")
        self.atmosphere_layer = LiquidAtmosphereLayer(motion_settings=self.motion_settings)
        self.page_transition_overlay = LiquidPageTransitionOverlay(motion_settings=self.motion_settings)
        self.status_breath_controller = LiquidStatusBreathController(motion_settings=self.motion_settings, parent=self)
        self.route_sweep_controller = LiquidRouteSweepController(motion_settings=self.motion_settings, parent=self)
        self.motion_proof_panel = MotionProofPanel(motion_settings=self.motion_settings)
        self.motion_coordinator = LiquidMotionCoordinator(motion_settings=self.motion_settings, parent=self)
        self.motion_proof_panel.setProperty("floatingMotionProofPanel", True)
        self.motion_proof_panel.setMaximumWidth(330)
        self.motion_proof_panel.setVisible(False)
        field_layout = vertical_layout(self.surface_glass_field, margins=(110, 16, 28, 0), spacing=9)
        self.mode_dock = LiquidModeDock(
            active_mode_id=self.active_mode_id,
            on_mode_selected=self.switch_mode,
            model=self.navigation_model,
        )
        self.subpage_selector = LiquidSubpageSelector(
            model=self.navigation_model,
            active_mode_id=self.active_mode_id,
            active_subpage_id=self.active_subpage_id,
            on_subpage_selected=self.switch_subpage,
        )
        self.page_host = _LiquidRouteHost(self.motion_settings)
        self.page_host.setObjectName("liquid_page_host")
        self.page_host.setProperty("liquidRole", "liquid_page_host")
        _lcd4f_trace("initializing page host")
        self._build_placeholder_pages()
        field_layout.addWidget(self.subpage_selector)
        field_layout.addWidget(self.page_host, 1)
        self.footer_clearance = glass_panel("liquid_footer_clearance", role="liquid_footer_clearance")
        self.footer_clearance.setProperty("footerClearance", True)
        self.footer_clearance.setProperty("footerClearanceTransparent", True)
        self.footer_clearance.setProperty("footerScrim", "none")
        self.footer_clearance.setProperty("footerBackdrop", "transparent_compact")
        self.footer_clearance.setFixedHeight(LiquidLayout.footer_clearance_height)
        field_layout.addWidget(self.footer_clearance)
        self.footer = _LiquidFooterActionStrip(self.state)
        self.helm_deck = HelmAssistantDeck(
            state=self.state,
            workspace=self.workspace,
            on_apply_selected=self.apply_selected_helm_changes,
            on_revert=self.revert_helm_changes,
        )
        self.helm_deck.setVisible(False)
        self.quick_wheel = LiquidQuickSwitchWheel(
            model=self.navigation_model,
            active_mode_id=self.active_mode_id,
            on_mode_selected=self._select_quick_wheel_mode,
            motion_settings=self.motion_settings,
            enabled=self.quick_wheel_enabled,
        )
        if self.quick_wheel_enabled:
            self._quick_wheel_shortcut = QShortcut(QKeySequence("Ctrl+Space"), self)
            self._quick_wheel_shortcut.activated.connect(self.toggle_quick_wheel)
        surface_layout.addWidget(self.surface_glass_field, 0, 0)
        surface_layout.addWidget(self.atmosphere_layer, 0, 0)
        surface_layout.addWidget(self.mode_dock, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        surface_layout.addWidget(self.footer, 0, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        surface_layout.addWidget(self.helm_deck, 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        surface_layout.addWidget(self.motion_proof_panel, 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        surface_layout.addWidget(self.page_transition_overlay, 0, 0)
        surface_layout.addWidget(self.quick_wheel, 0, 0, Qt.AlignmentFlag.AlignCenter)
        self.page_host.set_external_clock_driven(True)
        for name, driver in (
            ("atmosphere", self.atmosphere_layer),
            ("status_breath", self.status_breath_controller),
            ("route_sweep", self.route_sweep_controller),
            ("page_transition", self.page_transition_overlay),
            ("page_host", self.page_host),
            ("motion_proof", self.motion_proof_panel),
            ("quick_wheel", self.quick_wheel),
        ):
            self.motion_coordinator.register_passive_driver(name, driver)
        workspace_layout.addWidget(self.command_surface)

        root.addWidget(self.top_bar)
        root.addWidget(self.workspace_frame, 1)
        _lcd4f_trace("selecting initial route")
        self.switch_route(self.current_route_key)
        self._refresh_visible_motion_state()
        _lcd4f_trace("completed liquid shell init")

    def set_motion_intensity(self, intensity: MotionIntensity | str) -> None:
        if isinstance(intensity, MotionIntensity):
            active = intensity
        else:
            active = MotionIntensity(str(intensity).strip().casefold())
        self.motion_settings = MotionSettings(active)
        self.setProperty("motionIntensity", self.motion_settings.intensity.value)
        self.setProperty("pageMotionEnabled", self.motion_settings.page_motion_enabled())
        self._atmosphere_signature = None
        if hasattr(self, "top_bar"):
            self.top_bar.set_motion_settings(self.motion_settings)
        if hasattr(self, "page_host"):
            self.page_host.set_motion_settings(self.motion_settings)
        if hasattr(self, "quick_wheel"):
            self.quick_wheel.set_motion_settings(self.motion_settings)
        if hasattr(self, "atmosphere_layer"):
            self.atmosphere_layer.set_motion_settings(self.motion_settings)
        if hasattr(self, "page_transition_overlay"):
            self.page_transition_overlay.set_motion_settings(self.motion_settings)
        if hasattr(self, "status_breath_controller"):
            self.status_breath_controller.set_motion_settings(self.motion_settings)
        if hasattr(self, "route_sweep_controller"):
            self.route_sweep_controller.set_motion_settings(self.motion_settings)
        if hasattr(self, "motion_proof_panel"):
            self.motion_proof_panel.set_motion_settings(self.motion_settings)
        if hasattr(self, "motion_coordinator"):
            self.motion_coordinator.set_motion_settings(self.motion_settings)
        for current_page in self._current_route_pages():
            if hasattr(current_page, "set_motion_settings"):
                current_page.set_motion_settings(self.motion_settings)
        self._apply_route_atmosphere(self.active_mode_id, self.current_route_key)
        self._refresh_visible_motion_state()

    def advance_visible_motion_for_test(self, *, frames: int = 1) -> None:
        frame_count = max(0, int(frames))
        if hasattr(self, "motion_coordinator"):
            self.motion_coordinator.advance_for_test(frames=frame_count)
        elif hasattr(self, "atmosphere_layer"):
            self.atmosphere_layer.advance_for_test(frame_count)
        self._refresh_visible_motion_state()

    def _current_route_pages(self) -> tuple[QWidget, ...]:
        scroll = self.page_widgets.get(self.current_route_key)
        page = scroll.widget() if scroll is not None and hasattr(scroll, "widget") else None
        return (page,) if isinstance(page, QWidget) else ()

    def _refresh_visible_motion_state(self) -> None:
        profile = visible_motion_profile(self.motion_settings)
        status_targets = []
        if hasattr(self, "top_bar"):
            status_targets.extend(self.top_bar.status_breath_targets())
        current_pages = self._current_route_pages()
        for page in current_pages:
            status_targets.extend(_status_breath_targets(page))
        route_targets = []
        for page in current_pages:
            route_targets.extend(_route_sweep_targets(page))
        interaction_targets = _interaction_motion_targets(self)
        if hasattr(self, "status_breath_controller"):
            self.status_breath_controller.register_targets(status_targets[:64])
        if hasattr(self, "route_sweep_controller"):
            self.route_sweep_controller.register_targets(route_targets[:32])
        if hasattr(self, "motion_proof_panel"):
            self.motion_proof_panel.setVisible(self.current_route_key.startswith("support."))
            self.motion_proof_panel.set_motion_settings(self.motion_settings)
            interaction_targets.extend(self.motion_proof_panel.demo_widgets())
        if hasattr(self, "motion_coordinator"):
            self.motion_coordinator.register_interaction_targets(interaction_targets[:260])
            self.motion_coordinator.set_motion_settings(self.motion_settings)
        self.setProperty("visibleMotionControllerCount", profile.visible_motion_type_count)
        self.setProperty("atmosphereControllerRunning", profile.atmosphere_drift)
        self.setProperty("statusBreathControllerRunning", profile.status_breathing)
        self.setProperty("routeSweepControllerRunning", profile.route_sweep)
        self.setProperty("pageTransitionControllerEnabled", profile.page_transition_overlay)
        self.setProperty("liveEasingControllerEnabled", profile.live_easing_preview)
        self.setProperty("radialAnimationEnabled", profile.quick_wheel_animation and self.quick_wheel_enabled)
        self.setProperty("motionProofPreviewRunning", profile.live_easing_preview)
        self.setProperty("activeMotionControllerRunning", profile.active_interactions)
        refresh_motion_style(self)

    def _trigger_workspace_state_motion(self, role: str) -> None:
        coordinator = getattr(self, "motion_coordinator", None)
        if coordinator is None:
            return
        targets = [
            getattr(self.top_bar, "_saved_chip", None),
            getattr(self.footer, "_save_button", None),
            self.footer,
        ]
        for target in targets:
            if isinstance(target, QWidget):
                coordinator.trigger_status_transition(target, role=role)

    def _build_placeholder_pages(self) -> None:
        _lcd4f_trace("creating route registry pages")
        for route in self.navigation_model.routes:
            try:
                if route.route_key == "preflight.command_readiness":
                    _lcd4f_trace("constructing preflight page")
                    page = LIQUID_ROUTE_PAGE_FACTORIES[route.route_key](
                        state=self.state,
                        runtime_status=_runtime_status_from_state(self.state),
                        on_route_requested=self.switch_route,
                    )
                elif route.route_key == "mapping.hotas_map":
                    page = self._create_mapping_route_page(route.route_key)
                elif route.route_key in {"mapping.route_details", "mapping.advanced_route_tables"}:
                    page = self._create_mapping_route_page(route.route_key)
                elif route.route_key.startswith("tuning."):
                    page = self._create_tuning_route_page(route.route_key)
                elif route.route_key.startswith("analysis."):
                    page = self._create_analysis_route_page(route.route_key)
                elif route.route_key.startswith("recorder."):
                    page = self._create_recorder_route_page(route.route_key)
                elif route.route_key.startswith("support."):
                    page = self._create_support_route_page(route.route_key)
                else:
                    page = LIQUID_ROUTE_PAGE_FACTORIES[route.route_key]()
            except Exception as exc:  # pragma: no cover - defensive route-host fallback
                page = _route_error_fallback(route.route_key, exc)
            scroll = QScrollArea()
            scroll.setObjectName("liquid_page_scroll_area")
            scroll.setProperty("liquidRole", "liquid_page_scroll_area")
            scroll.setProperty("scrollbarStyle", "liquid_subtle")
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(page)
            self.page_host.addWidget(scroll)
            self.page_widgets[route.route_key] = scroll
            mode = self.navigation_model.mode_by_id(route.mode_id)
            if route.subpage_id == mode.default_subpage_id:
                self.page_widgets[route.mode_id] = scroll

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        self._set_visible_motion_runtime_active(True)

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._set_visible_motion_runtime_active(False)
        super().hideEvent(event)

    def _set_visible_motion_runtime_active(self, active: bool) -> None:
        active = bool(active and _visible_motion_timers_allowed())
        if hasattr(self, "motion_coordinator"):
            self.motion_coordinator.set_runtime_active(active)
        for controller_name in ("atmosphere_layer", "status_breath_controller", "route_sweep_controller"):
            controller = getattr(self, controller_name, None)
            if hasattr(controller, "set_runtime_active"):
                controller.set_runtime_active(active)

    def switch_mode(self, mode_id: str) -> None:
        if mode_id not in LIQUID_MODE_IDS:
            raise KeyError(mode_id)
        route = self.navigation_state.select_mode(mode_id)
        self._show_route(route.route_key)

    def switch_subpage(self, subpage_id: str) -> None:
        route = self.navigation_state.select_subpage(subpage_id)
        self._show_route(route.route_key)

    def switch_route(self, route_key: str) -> None:
        route = self.navigation_state.select_route(route_key)
        self._show_route(route.route_key)

    def _show_route(self, route_key: str) -> None:
        if self._route_sync_in_progress:
            self.recursive_sync_guard_count += 1
            self.setProperty("recursiveRouteSyncGuardCount", self.recursive_sync_guard_count)
            return
        self._route_sync_in_progress = True
        try:
            self._show_route_now(route_key)
        finally:
            self._route_sync_in_progress = False

    def _show_route_now(self, route_key: str) -> None:
        route = self.navigation_model.route_by_key(route_key)
        target_widget = self.page_widgets[route.route_key]
        already_current = self.current_route_key == route.route_key and self.page_host.currentWidget() is target_widget
        previous_route_key = self.current_route_key
        self.active_mode_id = route.mode_id
        self.active_subpage_id = route.subpage_id
        self.current_route_key = route.route_key
        if not already_current:
            previous_snapshot = self.page_host.grab() if self.page_host.size().width() > 1 and self.page_host.size().height() > 1 else None
            self.page_host.setCurrentWidget(target_widget)
            current_snapshot = self.page_host.grab() if self.page_host.size().width() > 1 and self.page_host.size().height() > 1 else None
            if hasattr(self.page_host, "begin_route_motion"):
                self.page_host.begin_route_motion(from_route=previous_route_key, to_route=route.route_key)
            if hasattr(self, "page_transition_overlay"):
                self.page_transition_overlay.begin(
                    from_route=previous_route_key,
                    to_route=route.route_key,
                    previous_snapshot=previous_snapshot,
                    current_snapshot=current_snapshot,
                )
            if hasattr(self, "motion_coordinator"):
                page = target_widget.widget() if hasattr(target_widget, "widget") else target_widget
                self.motion_coordinator.trigger_page_transition(page if isinstance(page, QWidget) else None)
            self.route_switch_count += 1
            self.setProperty("routeSwitchCount", self.route_switch_count)
            self.setProperty("lastPageMotionFrom", previous_route_key)
            self.setProperty("lastPageMotionTo", route.route_key)
            _lcd4f_trace(f"route host set page: {route.route_key}")
        else:
            _lcd4f_trace(f"route host already current: {route.route_key}")
        self._set_live_monitor_display_active(route.route_key == "analysis.live_monitor")
        self.mode_dock.update_active(route.mode_id)
        self.subpage_selector.update_for_route(route.mode_id, route.subpage_id)
        if route.route_key == "preflight.command_readiness":
            self._sync_preflight_page(
                _runtime_status_from_state(self.state),
                telemetry=self._latest_bridge_telemetry,
                state=self.state,
            )
        elif route.route_key.startswith("mapping."):
            self._sync_mapping_page_state(self.state)
        elif route.route_key.startswith("tuning."):
            self._sync_tuning_page_state(self.state)
        elif route.route_key.startswith("analysis."):
            self._sync_analysis_page_state(self.state)
        elif route.route_key.startswith("recorder."):
            self._sync_recorder_page_state(self.state)
        self._apply_route_atmosphere(route.mode_id, route.route_key)
        if hasattr(self, "quick_wheel"):
            self.quick_wheel.update_active(route.mode_id)
        self._refresh_visible_motion_state()

    def apply_bridge_telemetry(self, telemetry: BridgeTelemetrySnapshot) -> None:
        self._latest_bridge_telemetry = telemetry
        runtime_status = _runtime_status_from_bridge_telemetry(telemetry)
        self.state.runtime = AppState.from_runtime_status(
            runtime_status,
            driver_detected=self.state.runtime.driver_detected,
        ).runtime
        self.state.active_profile = telemetry.active_profile
        signature = _liquid_shell_chrome_signature(self.state, runtime_status, self.current_route_key)
        chrome_changed = signature != self._last_shell_chrome_signature
        if chrome_changed or self._shell_scheduler.run("shell_chrome"):
            self.top_bar.update_state(self.state)
            self.footer.update_state(self.state)
            self._last_shell_chrome_signature = signature
            self.shell_chrome_update_count += 1
        else:
            self.shell_chrome_skip_count += 1
        if self.current_route_key == "preflight.command_readiness":
            self._sync_preflight_page(runtime_status, telemetry=telemetry, state=self.state)
        elif self.current_route_key.startswith("mapping."):
            self._sync_mapping_page_state(self.state)
        elif self.current_route_key.startswith("tuning."):
            self._sync_tuning_page_state(self.state)
        elif self.current_route_key.startswith("analysis."):
            self._sync_analysis_page_state(self.state)
        elif self.current_route_key.startswith("recorder."):
            self._sync_recorder_page_state(self.state)
        else:
            _lcd4f_trace(f"skipping hidden preflight telemetry sync on route: {self.current_route_key}")
        if self._helm_deck_open:
            self._sync_helm_deck_state()

    def select_mapping_route(self, route_id: str) -> None:
        if route_id == self._selected_mapping_route_id:
            return
        self._selected_mapping_route_id = route_id
        self._sync_mapping_page_state(self.state)
        self._refresh_visible_motion_state()

    def select_mapping_control(self, control_id: str) -> None:
        self.select_mapping_route(route_id_for_control_id(control_id))

    def stage_mapping_route_edit(self, route_id: str, field_id: str, value: str) -> MappingEditResult:
        result = stage_mapping_route_edit(self.workspace, route_id, field_id, value)
        self._mapping_last_edit_result = result
        self._selected_mapping_route_id = result.route_id
        if result.valid:
            self.workspace = result.workspace
            self.state.saved = False
            self.state.active_profile = self.workspace.active_profile
            self.state.status_message = result.message
        else:
            self.state.status_message = result.message
        self.top_bar.update_state(self.state)
        self.footer.update_state(self.state)
        self._trigger_workspace_state_motion("unsaved" if not self.state.saved else "saved")
        self._sync_mapping_pages_after_edit()
        return result

    def revert_mapping_route_edits(self) -> None:
        self.workspace = self._mapping_base_workspace
        self.state.saved = self._mapping_base_saved_state
        self.state.active_profile = self.workspace.active_profile
        self.state.status_message = "Reverted staged Mapping route edits to the original Liquid workspace draft."
        self._mapping_last_edit_result = None
        self.top_bar.update_state(self.state)
        self.footer.update_state(self.state)
        self._trigger_workspace_state_motion("saved" if self.state.saved else "unsaved")
        self._sync_mapping_pages_after_edit()

    def select_tuning_axis(self, route_key: str, axis_name: str) -> None:
        if self._selected_tuning_axis_by_route.get(route_key) == axis_name:
            return
        self._selected_tuning_axis_by_route[route_key] = axis_name
        self._sync_tuning_page_state(self.state)
        self._refresh_visible_motion_state()

    def select_analysis_axis(self, route_key: str, axis_name: str) -> None:
        if self._selected_analysis_axis_by_route.get(route_key) == axis_name:
            return
        self._selected_analysis_axis_by_route[route_key] = axis_name
        self._sync_analysis_page_state(self.state)
        self._refresh_visible_motion_state()

    def stage_tuning_parameter_edit(
        self,
        route_key: str,
        axis_name: str,
        parameter_id: str,
        value: str,
    ) -> TuningEditResult:
        result = stage_tuning_parameter_edit(self.workspace, route_key, axis_name, parameter_id, value)
        self._tuning_last_edit_result = result
        self._selected_tuning_axis_by_route[route_key] = axis_name
        if result.valid:
            self.workspace = result.workspace
            self.state.saved = False
            self.state.active_profile = self.workspace.active_profile
            self.state.status_message = result.message
        else:
            self.state.status_message = result.message
        self.top_bar.update_state(self.state)
        self.footer.update_state(self.state)
        self._trigger_workspace_state_motion("unsaved" if not self.state.saved else "saved")
        self._sync_tuning_pages_after_edit()
        return result

    def revert_tuning_edits(self) -> None:
        self.workspace = self._tuning_base_workspace
        self.state.saved = self._tuning_base_saved_state
        self.state.active_profile = self.workspace.active_profile
        self.state.status_message = "Reverted staged Tuning edits to the original Liquid workspace draft."
        self._tuning_last_edit_result = None
        self.top_bar.update_state(self.state)
        self.footer.update_state(self.state)
        self._trigger_workspace_state_motion("saved" if self.state.saved else "unsaved")
        self._sync_tuning_pages_after_edit()

    def toggle_helm_deck(self) -> None:
        self._helm_deck_open = not self._helm_deck_open
        if self._helm_deck_open:
            self._sync_helm_deck_state()
            if not self.isVisible():
                self.show()
        self.helm_deck.setVisible(self._helm_deck_open)
        if hasattr(self, "motion_coordinator"):
            self.motion_coordinator.trigger_status_transition(self.helm_deck, role="open" if self._helm_deck_open else "closed")
        self.helm_deck.raise_()

    def open_quick_wheel(self) -> bool:
        if not self.quick_wheel_enabled:
            return False
        if not self.isVisible():
            self.show()
        self.quick_wheel.update_active(self.active_mode_id)
        return self.quick_wheel.open_wheel()

    def close_quick_wheel(self) -> bool:
        return self.quick_wheel.close_wheel()

    def toggle_quick_wheel(self) -> bool:
        if not self.quick_wheel_enabled:
            return False
        if not self.isVisible():
            self.show()
        self.quick_wheel.update_active(self.active_mode_id)
        return self.quick_wheel.toggle_wheel()

    def is_quick_wheel_open(self) -> bool:
        return bool(self.quick_wheel.isVisible())

    def _select_quick_wheel_mode(self, mode_id: str) -> None:
        self.switch_mode(mode_id)
        self.close_quick_wheel()

    def apply_selected_helm_changes(self, selected_change_ids: tuple[str, ...]) -> HelmApplyResult:
        if self._helm_last_apply_result is None or not self._helm_last_apply_result.applied_diffs:
            self._helm_base_workspace = self.workspace
            self._helm_base_saved_state = bool(self.state.saved)
        result = stage_selected_helm_changes(
            self.workspace,
            self.helm_deck.model.result,
            selected_change_ids=selected_change_ids,
        )
        self._helm_last_apply_result = result
        if result.valid:
            self.workspace = result.workspace
            self.state.saved = False
            self.state.active_profile = self.workspace.active_profile
            self.state.status_message = f"Helm staged {len(result.applied_diffs)} draft workspace change(s). Output proof unchanged."
            self._sync_tuning_pages_after_edit()
            if self.current_route_key.startswith("analysis."):
                self._sync_analysis_page_state(self.state)
        else:
            self.state.status_message = result.message
        self.top_bar.update_state(self.state)
        self.footer.update_state(self.state)
        self._trigger_workspace_state_motion("unsaved" if not self.state.saved else "saved")
        self._sync_helm_deck_state()
        return result

    def revert_helm_changes(self) -> HelmApplyResult:
        applied = self._helm_last_apply_result.applied_diffs if self._helm_last_apply_result else ()
        result = revert_helm_changes(
            self.workspace,
            applied,
            base_workspace=self._helm_base_workspace,
        )
        if result.valid:
            self.workspace = result.workspace
            self.state.saved = self._helm_base_saved_state
            self.state.active_profile = self.workspace.active_profile
            self.state.status_message = "Helm reverted the last draft change batch. Output proof unchanged."
            self._helm_last_apply_result = result
            self._sync_tuning_pages_after_edit()
            if self.current_route_key.startswith("analysis."):
                self._sync_analysis_page_state(self.state)
        else:
            self.state.status_message = result.message
            self._helm_last_apply_result = result
        self.top_bar.update_state(self.state)
        self.footer.update_state(self.state)
        self._trigger_workspace_state_motion("saved" if self.state.saved else "unsaved")
        self._sync_helm_deck_state()
        return result

    def _sync_preflight_page(
        self,
        runtime_status: RuntimePreflightStatus,
        *,
        telemetry: BridgeTelemetrySnapshot | None = None,
        state: AppState | None = None,
    ) -> None:
        preflight_scroll = self.page_widgets.get("preflight.command_readiness")
        preflight_page = preflight_scroll.widget() if preflight_scroll is not None else None
        if hasattr(preflight_page, "update_runtime_status"):
            _lcd4f_trace("syncing preflight readiness page")
            preflight_page.update_runtime_status(runtime_status, telemetry=telemetry, state=state or self.state)

    def _sync_mapping_page_state(self, state: AppState) -> None:
        mapping_scroll = self.page_widgets.get(self.current_route_key)
        mapping_page = mapping_scroll.widget() if mapping_scroll is not None else None
        scroll_value = mapping_scroll.verticalScrollBar().value() if mapping_scroll is not None else 0
        if hasattr(mapping_page, "update_mapping_workspace"):
            try:
                mapping_page.update_mapping_workspace(
                    state=state,
                    workspace=self.workspace,
                    base_workspace=self._mapping_base_workspace,
                    selected_route_id=self._selected_mapping_route_id,
                    last_edit_result=self._mapping_last_edit_result,
                )
            except Exception as exc:  # pragma: no cover - live update guard
                self.setProperty("lastMappingSyncError", str(exc))
        elif hasattr(mapping_page, "update_state"):
            try:
                mapping_page.update_state(state)
            except Exception as exc:  # pragma: no cover - live update guard
                self.setProperty("lastMappingSyncError", str(exc))
        if mapping_scroll is not None:
            bar = mapping_scroll.verticalScrollBar()
            bar.setValue(min(scroll_value, bar.maximum()))

    def _sync_mapping_pages_after_edit(self) -> None:
        for route_key in ("mapping.hotas_map", "mapping.route_details", "mapping.advanced_route_tables"):
            mapping_scroll = self.page_widgets.get(route_key)
            mapping_page = mapping_scroll.widget() if mapping_scroll is not None else None
            scroll_value = mapping_scroll.verticalScrollBar().value() if mapping_scroll is not None else 0
            if hasattr(mapping_page, "update_mapping_workspace"):
                try:
                    mapping_page.update_mapping_workspace(
                        state=self.state,
                        workspace=self.workspace,
                        base_workspace=self._mapping_base_workspace,
                        selected_route_id=self._selected_mapping_route_id,
                        last_edit_result=self._mapping_last_edit_result,
                    )
                except Exception as exc:  # pragma: no cover - live update guard
                    self.setProperty("lastMappingSyncError", str(exc))
            elif hasattr(mapping_page, "update_state"):
                try:
                    mapping_page.update_state(self.state)
                except Exception as exc:  # pragma: no cover - live update guard
                    self.setProperty("lastMappingSyncError", str(exc))
            if mapping_scroll is not None:
                bar = mapping_scroll.verticalScrollBar()
                bar.setValue(min(scroll_value, bar.maximum()))

    def _sync_tuning_page_state(self, state: AppState) -> None:
        tuning_scroll = self.page_widgets.get(self.current_route_key)
        tuning_page = tuning_scroll.widget() if tuning_scroll is not None else None
        if hasattr(tuning_page, "update_tuning_workspace"):
            try:
                tuning_page.update_tuning_workspace(
                    state=state,
                    workspace=self.workspace,
                    base_workspace=self._tuning_base_workspace,
                    selected_axis=self._selected_tuning_axis_by_route.get(self.current_route_key, "Roll"),
                    last_edit_result=self._tuning_last_edit_result,
                    telemetry=self._latest_bridge_telemetry,
                )
            except Exception as exc:  # pragma: no cover - live update guard
                self.setProperty("lastTuningSyncError", str(exc))
        elif hasattr(tuning_page, "update_state"):
            try:
                tuning_page.update_state(state)
            except Exception as exc:  # pragma: no cover - live update guard
                self.setProperty("lastTuningSyncError", str(exc))

    def _sync_tuning_pages_after_edit(self) -> None:
        for route_key in (
            "tuning.base_tuning",
            "tuning.filtering",
            "tuning.combat_profile",
            "tuning.conditional_rules",
            "tuning.profiles_library",
        ):
            tuning_scroll = self.page_widgets.get(route_key)
            tuning_page = tuning_scroll.widget() if tuning_scroll is not None else None
            if hasattr(tuning_page, "update_tuning_workspace"):
                try:
                    tuning_page.update_tuning_workspace(
                        state=self.state,
                        workspace=self.workspace,
                        base_workspace=self._tuning_base_workspace,
                        selected_axis=self._selected_tuning_axis_by_route.get(route_key, "Roll"),
                        last_edit_result=self._tuning_last_edit_result,
                        telemetry=self._latest_bridge_telemetry,
                    )
                except Exception as exc:  # pragma: no cover - live update guard
                    self.setProperty("lastTuningSyncError", str(exc))
            elif hasattr(tuning_page, "update_state"):
                try:
                    tuning_page.update_state(self.state)
                except Exception as exc:  # pragma: no cover - live update guard
                    self.setProperty("lastTuningSyncError", str(exc))

    def _sync_analysis_page_state(self, state: AppState) -> None:
        if self._analysis_sync_in_progress:
            self.recursive_sync_guard_count += 1
            self.setProperty("recursiveRouteSyncGuardCount", self.recursive_sync_guard_count)
            return
        self._analysis_sync_in_progress = True
        try:
            self._sync_analysis_page_state_now(state)
        finally:
            self._analysis_sync_in_progress = False

    def _sync_analysis_page_state_now(self, state: AppState) -> None:
        analysis_scroll = self.page_widgets.get(self.current_route_key)
        analysis_page = analysis_scroll.widget() if analysis_scroll is not None else None
        if hasattr(analysis_page, "update_analysis_snapshot"):
            try:
                analysis_page.update_analysis_snapshot(
                    state=state,
                    workspace=self.workspace,
                    telemetry=self._latest_bridge_telemetry,
                    selected_axis=self._selected_analysis_axis_by_route.get(self.current_route_key, "Roll"),
                )
            except Exception as exc:  # pragma: no cover - live update guard
                self.setProperty("lastAnalysisSyncError", str(exc))
        elif hasattr(analysis_page, "update_state"):
            try:
                analysis_page.update_state(state)
            except Exception as exc:  # pragma: no cover - live update guard
                self.setProperty("lastAnalysisSyncError", str(exc))

    def _set_live_monitor_display_active(self, active: bool) -> None:
        monitor_scroll = self.page_widgets.get("analysis.live_monitor")
        monitor_page = monitor_scroll.widget() if monitor_scroll is not None else None
        if hasattr(monitor_page, "set_live_monitor_active"):
            monitor_page.set_live_monitor_active(active)

    def _sync_recorder_page_state(self, state: AppState) -> None:
        recorder_scroll = self.page_widgets.get(self.current_route_key)
        recorder_page = recorder_scroll.widget() if recorder_scroll is not None else None
        if hasattr(recorder_page, "update_recorder_model"):
            recorder_page.update_recorder_model(state=state)
        elif hasattr(recorder_page, "update_state"):
            recorder_page.update_state(state)

    def _sync_helm_deck_state(self) -> None:
        self.helm_deck.update_helm_state(
            state=self.state,
            workspace=self.workspace,
            selected_axis=self.state.selected_axis or "Yaw",
            last_apply_result=self._helm_last_apply_result,
        )

    def _apply_route_atmosphere(self, mode_id: str, route_key: str) -> None:
        signature = (mode_id, route_key, self.motion_settings.intensity.value)
        if signature == self._atmosphere_signature:
            return
        self._atmosphere_signature = signature
        self.atmosphere_update_count += 1
        self.setProperty("atmosphereUpdateCount", self.atmosphere_update_count)
        for target in (
            self,
            self.workspace_frame,
            self.command_surface,
            self.surface_glass_field,
            self.page_host,
        ):
            apply_atmosphere(target, mode_id=mode_id, motion_settings=self.motion_settings)
        current_scroll = self.page_widgets.get(route_key)
        if current_scroll is None:
            return
        apply_atmosphere(current_scroll, mode_id=mode_id, motion_settings=self.motion_settings)
        current_page = current_scroll.widget()
        if current_page is not None:
            apply_atmosphere(current_page, mode_id=mode_id, motion_settings=self.motion_settings)
            for raw_panel in current_page.findChildren(QWidget):
                if raw_panel.property("rawDiagnosticSurface"):
                    apply_atmosphere(
                        raw_panel,
                        mode_id=mode_id,
                        motion_settings=self.motion_settings,
                        optional_enabled=False,
                        diagnostic_surface=True,
                    )

    def _create_mapping_route_page(self, route_key: str):
        kwargs = {
            "state": self.state,
            "workspace": self.workspace,
            "base_workspace": self._mapping_base_workspace,
            "selected_route_id": self._selected_mapping_route_id,
            "on_route_requested": self.switch_route,
            "on_route_selected": self.select_mapping_route,
        }
        if route_key == "mapping.hotas_map":
            return LIQUID_ROUTE_PAGE_FACTORIES[route_key](
                state=self.state,
                workspace=self.workspace,
                selected_route_id=self._selected_mapping_route_id,
                selected_control_id=control_id_for_route_id(self._selected_mapping_route_id),
                on_route_requested=self.switch_route,
                on_route_selected=self.select_mapping_route,
                on_stage_edit=self.stage_mapping_route_edit,
                on_revert=self.revert_mapping_route_edits,
                last_edit_result=self._mapping_last_edit_result,
            )
        return LIQUID_ROUTE_PAGE_FACTORIES[route_key](
            **kwargs,
            on_stage_edit=self.stage_mapping_route_edit,
            on_revert=self.revert_mapping_route_edits,
            last_edit_result=self._mapping_last_edit_result,
        )

    def _create_tuning_route_page(self, route_key: str):
        return LIQUID_ROUTE_PAGE_FACTORIES[route_key](
            state=self.state,
            workspace=self.workspace,
            base_workspace=self._tuning_base_workspace,
            selected_axis=self._selected_tuning_axis_by_route.get(route_key, "Roll"),
            telemetry=self._latest_bridge_telemetry,
            on_axis_selected=self.select_tuning_axis,
            on_stage_edit=self.stage_tuning_parameter_edit,
            on_route_requested=self.switch_route,
            on_revert=self.revert_tuning_edits,
            last_edit_result=self._tuning_last_edit_result,
        )

    def _create_analysis_route_page(self, route_key: str):
        return LIQUID_ROUTE_PAGE_FACTORIES[route_key](
            state=self.state,
            workspace=self.workspace,
            telemetry=self._latest_bridge_telemetry,
            selected_axis=self._selected_analysis_axis_by_route.get(route_key, "Roll"),
            on_axis_selected=self.select_analysis_axis,
            on_route_requested=self.switch_route,
            motion_settings=self.motion_settings,
        )

    def _create_recorder_route_page(self, route_key: str):
        return LIQUID_ROUTE_PAGE_FACTORIES[route_key](
            state=self.state,
            on_route_requested=self.switch_route,
        )

    def _create_support_route_page(self, route_key: str):
        return LIQUID_ROUTE_PAGE_FACTORIES[route_key](
            state=self.state,
            workspace=self.workspace,
            runtime_status=_runtime_status_from_state(self.state),
            workspace_path=self.workspace_path,
            on_route_requested=self.switch_route,
            motion_settings=self.motion_settings,
        )

    def _load_initial_workspace(self, *, load_from_disk: bool) -> WorkspaceConfig:
        if load_from_disk and self.workspace_path.exists():
            try:
                return load_workspace(self.workspace_path).workspace
            except WorkspaceJsonError as exc:
                self.state.status_message = f"Workspace load failed; using default draft. {exc}"
                self.state.saved = False
        return create_default_workspace()


class _LiquidTopCommandBar(QFrame):
    def __init__(
        self,
        state: AppState,
        *,
        on_helm_toggled=None,
        motion_settings: MotionSettings | None = None,
        on_motion_changed=None,
    ) -> None:
        super().__init__()
        self.setObjectName("liquidTopCommandBar")
        self.setFixedHeight(LiquidLayout.top_bar_height)
        self._state = state
        self._motion_settings = motion_settings or current_motion_settings()
        self._on_motion_changed = on_motion_changed
        self._workspace_chip: QLabel | None = None
        self._saved_chip: QLabel | None = None
        self._runtime_chip: QLabel | None = None
        self._source_chip: QLabel | None = None
        self._source_detail_label: QLabel | None = None
        self.motion_combo: QComboBox | None = None

        layout = horizontal_layout(self, margins=(14, 12, 14, 12), spacing=14)

        orb = glass_panel("liquidCommandOrb", role="liquid_command_orb")
        orb.setFixedSize(42, 42)
        orb_layout = vertical_layout(orb, margins=(0, 0, 0, 0), spacing=0)
        orb_text = QLabel("HF")
        orb_text.setObjectName("liquidOrbText")
        orb_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orb_layout.addWidget(orb_text)

        title_area = vertical_layout(spacing=3)
        title = QLabel("HelmForge")
        title.setObjectName("liquidDeckTitle")
        subtitle = QLabel("Liquid Command Deck / static command surface")
        subtitle.setObjectName("liquidDeckSubtitle")
        subtitle.setWordWrap(True)
        subtitle.setMinimumWidth(0)
        subtitle.setMaximumWidth(460)
        title_area.addWidget(title)
        title_area.addWidget(subtitle)

        status_cluster = glass_panel("liquidTopStatusCapsule", role="liquid_status_cluster")
        status_cluster.setMinimumWidth(520)
        status_cluster.setMaximumWidth(760)
        status_cluster.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        status_layout = horizontal_layout(status_cluster, margins=(12, 9, 12, 9), spacing=8)
        self._workspace_chip = status_chip(_workspace_label(state), tone="info", object_name="liquidWorkspaceChip", state_role="info")
        self._workspace_chip.setMaximumWidth(178)
        self._saved_chip = status_chip(
            _saved_label(state),
            tone=_saved_tone(state),
            object_name="liquidSavedChip",
            state_role=_saved_state_role(state),
        )
        self._saved_chip.setMaximumWidth(96)
        self._runtime_chip = status_chip(
            state.runtime.header_truth_label,
            tone=state.runtime.tone,
            object_name="liquidRuntimeTruthChip",
            state_role=_runtime_chip_role(state),
        )
        self._runtime_chip.setMaximumWidth(164)
        self._source_chip = status_chip(_source_label(state), tone="neutral", object_name="liquidSourceChip", state_role="info")
        _configure_source_chip(self._source_chip, state)
        self._source_detail_label = QLabel(_source_full_label(state), status_cluster)
        self._source_detail_label.setObjectName("liquidSourceDetailText")
        self._source_detail_label.setProperty("liquidRole", "liquid_status_source_detail")
        self._source_detail_label.setAccessibleName("Full source detail")
        self._source_detail_label.setAccessibleDescription(_source_full_label(state))
        self._source_detail_label.setVisible(False)
        for chip in (self._workspace_chip, self._saved_chip, self._runtime_chip, self._source_chip):
            chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            status_layout.addWidget(chip)

        command_cluster = glass_panel("liquidTopCommandCluster", role="liquid_command_cluster")
        command_cluster.setProperty("compactActionCluster", True)
        command_cluster.setMaximumWidth(124)
        command_cluster.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        command_layout = horizontal_layout(command_cluster, margins=(8, 8, 8, 8), spacing=7)
        status_rail = glass_panel("liquidTopStatusRail", role="liquid_status_rail")
        status_rail.setFixedSize(6, 28)
        self.helm_button = action_button("Helm", object_name="liquidHelmButton", enabled=True, action_kind="open_panel")
        self.helm_button.setMaximumWidth(64)
        self.helm_button.setToolTip("Helm")
        self.helm_button.setStatusTip("Open Liquid Helm Assistant; recommendations stage workspace draft changes only.")
        self.helm_button.setAccessibleName("Helm assistant")
        self.helm_button.setAccessibleDescription("Open the Liquid Helm Assistant deck.")
        if on_helm_toggled is not None:
            self.helm_button.clicked.connect(on_helm_toggled)
        command_layout.addWidget(status_rail)
        command_layout.addWidget(self.helm_button)

        motion_cluster = glass_panel("liquidMotionModeCluster", role="liquid_motion_mode_cluster")
        motion_cluster.setProperty("componentRole", "MotionModeCluster")
        motion_cluster.setMaximumWidth(170)
        motion_layout = horizontal_layout(motion_cluster, margins=(8, 8, 8, 8), spacing=6)
        motion_label = QLabel("Motion")
        motion_label.setObjectName("liquidMotionModeLabel")
        self.motion_combo = QComboBox()
        self.motion_combo.setObjectName("liquidMotionModeControl")
        self.motion_combo.setProperty("componentRole", "MotionModeControl")
        self.motion_combo.setProperty("motionRuntimeMutation", False)
        self.motion_combo.setAccessibleName("Motion intensity")
        self.motion_combo.setAccessibleDescription("Select Liquid motion intensity. This only changes UI presentation.")
        for option in MotionIntensity:
            self.motion_combo.addItem(option.value.title(), option.value)
        self.set_motion_settings(self._motion_settings)
        self.motion_combo.currentIndexChanged.connect(self._handle_motion_combo_changed)
        motion_layout.addWidget(motion_label)
        motion_layout.addWidget(self.motion_combo, 1)

        layout.addWidget(orb)
        layout.addLayout(title_area, 1)
        layout.addWidget(status_cluster)
        layout.addWidget(command_cluster)
        layout.addWidget(motion_cluster)

    def set_motion_settings(self, motion_settings: MotionSettings) -> None:
        self._motion_settings = motion_settings
        self.setProperty("motionIntensity", motion_settings.intensity.value)
        if self.motion_combo is not None:
            index = self.motion_combo.findData(motion_settings.intensity.value)
            if index >= 0 and self.motion_combo.currentIndex() != index:
                blocked = self.motion_combo.blockSignals(True)
                self.motion_combo.setCurrentIndex(index)
                self.motion_combo.blockSignals(blocked)
            self.motion_combo.setProperty("motionIntensity", motion_settings.intensity.value)
            refresh_style(self.motion_combo)

    def status_breath_targets(self) -> list[QWidget]:
        return [
            widget
            for widget in (self._workspace_chip, self._saved_chip, self._runtime_chip, self._source_chip)
            if widget is not None
        ]

    def _handle_motion_combo_changed(self, index: int) -> None:
        if self.motion_combo is None or self._on_motion_changed is None:
            return
        value = self.motion_combo.itemData(index)
        self._on_motion_changed(MotionIntensity(str(value)))

    def update_state(self, state: AppState) -> None:
        self._state = state
        if self._workspace_chip is not None:
            self._workspace_chip.setText(_workspace_label(state))
            apply_status_motion(self._workspace_chip, state_role="info", component_role="status_chip", hover_role="chip")
            refresh_style(self._workspace_chip)
        if self._saved_chip is not None:
            self._saved_chip.setText(_saved_label(state))
            self._saved_chip.setProperty("chipTone", _saved_tone(state))
            self._saved_chip.setProperty("statusRole", _saved_state_role(state))
            self._saved_chip.setProperty("draftEmphasis", not state.saved)
            apply_status_motion(
                self._saved_chip,
                state_role=_saved_state_role(state),
                component_role="status_chip",
                hover_role="chip",
            )
            refresh_style(self._saved_chip)
        if self._runtime_chip is not None:
            self._runtime_chip.setText(state.runtime.header_truth_label)
            self._runtime_chip.setProperty("chipTone", state.runtime.tone)
            self._runtime_chip.setProperty("statusRole", _runtime_chip_role(state))
            apply_status_motion(
                self._runtime_chip,
                state_role=_runtime_chip_role(state),
                component_role="status_chip",
                hover_role="chip",
            )
            refresh_style(self._runtime_chip)
        if self._source_chip is not None:
            self._source_chip.setText(_source_label(state))
            _configure_source_chip(self._source_chip, state)
            apply_status_motion(self._source_chip, state_role="info", component_role="status_chip", hover_role="chip")
            refresh_style(self._source_chip)
        if self._source_detail_label is not None:
            self._source_detail_label.setText(_source_full_label(state))
            self._source_detail_label.setAccessibleDescription(_source_full_label(state))


class _LiquidFooterActionStrip(QFrame):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.setObjectName("liquid_floating_footer_strip")
        self.setProperty("liquidRole", "liquid_floating_footer_strip")
        self.setProperty("floatingLayer", True)
        self.setFixedHeight(LiquidLayout.footer_height)
        self.setMinimumWidth(700)
        self._message = QLabel()
        self._message.setObjectName("liquidFooterStatusMessage")
        self._message.setWordWrap(True)
        self._save_button = None
        self._apply_button = None
        self._revert_button = None

        layout = horizontal_layout(self, margins=(18, 10, 18, 10), spacing=12)
        layout.addWidget(self._message, 1)
        footer_reason = "Disabled: global Liquid footer workspace commands are preserved for a later safe wiring pass."
        self._apply_button = action_button(
            "Apply",
            object_name="liquidFooterApplyButton",
            enabled=False,
            action_kind="disabled_deferred",
            disabled_reason=footer_reason,
        )
        layout.addWidget(self._apply_button)
        self._save_button = action_button(
            "Save",
            object_name="liquidFooterSaveButton",
            enabled=False,
            action_kind="disabled_deferred",
            disabled_reason=footer_reason,
        )
        layout.addWidget(self._save_button)
        self._revert_button = action_button(
            "Revert",
            object_name="liquidFooterRevertButton",
            enabled=False,
            action_kind="disabled_deferred",
            disabled_reason=footer_reason,
        )
        layout.addWidget(self._revert_button)
        self.update_state(state)

    def update_state(self, state: AppState) -> None:
        self._message.setText(state.status_message or "Liquid shell loaded; workspace actions are placeholders.")
        self._message.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        draft = not state.saved
        self.setProperty("draftEmphasis", draft)
        self.setProperty("statusRole", "unsaved" if draft else "saved")
        for button in (self._apply_button, self._save_button, self._revert_button):
            if button is not None:
                button.setProperty("draftEmphasis", draft and button is self._save_button)
                button.setProperty("activeInteraction", False)
                refresh_style(button)
        refresh_style(self)


def _navigation_state_from_state(state: AppState, model: LiquidNavigationModel) -> LiquidNavigationState:
    navigation_state = LiquidNavigationState(model=model)
    route_key = _PAGE_ID_TO_ROUTE_KEY.get(state.active_page_id, model.default_route.route_key)
    if route_key not in {route.route_key for route in model.routes}:
        route_key = model.default_route.route_key
    navigation_state.select_route(route_key)
    return navigation_state


def _workspace_label(state: AppState) -> str:
    return state.active_profile or "Workspace loaded"


def _saved_label(state: AppState) -> str:
    return "Saved" if state.saved else "Unsaved"


def _saved_tone(state: AppState) -> str:
    return "success" if state.saved else "warning"


def _saved_state_role(state: AppState) -> str:
    return "saved" if state.saved else "unsaved"


def _runtime_chip_role(state: AppState) -> str:
    if state.runtime.tone == "success":
        return "verified"
    if state.runtime.tone in {"warning", "caution"}:
        return "blocked"
    if state.runtime.tone == "danger":
        return "error"
    return "info"


def _source_label(state: AppState) -> str:
    if state.source_config:
        source_name = _leaf_name(state.source_config)
        if "hotas_bridge_config" in source_name.lower():
            return "Source: Bridge Config"
        return "Source: Workspace Config"
    if state.runtime.backend_name:
        return "Source: Telemetry"
    if state.runtime.truth is RuntimeTruth.SIMULATED:
        return "Source: Simulation"
    return "Source: Workspace Config"


def _source_full_label(state: AppState) -> str:
    if state.source_config:
        return f"Source: {state.source_config}"
    if state.runtime.backend_name:
        return f"Source: {state.runtime.backend_name}"
    return "Source: workspace state"


def _leaf_name(path_text: str) -> str:
    return path_text.replace("\\", "/").rstrip("/").split("/")[-1]


def _ellipsize(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return "." * max_length
    return f"{text[: max_length - 3]}..."


def _configure_source_chip(chip: QLabel, state: AppState) -> None:
    detail = _source_full_label(state)
    chip.setMaximumWidth(188)
    chip.setWordWrap(False)
    chip.setToolTip(detail)
    chip.setStatusTip(detail)
    chip.setAccessibleName(_source_label(state))
    chip.setAccessibleDescription(detail)


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


def _liquid_shell_chrome_signature(state: AppState, runtime_status: RuntimePreflightStatus, route_key: str) -> tuple[object, ...]:
    return (
        runtime_status.truth.value,
        runtime_status.input.status.value,
        runtime_status.output.status.value,
        bool(runtime_status.live_output_writes_verified),
        state.active_profile,
        bool(state.saved),
        state.status_message,
        route_key,
    )


def _runtime_status_from_state(state: AppState) -> RuntimePreflightStatus:
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
