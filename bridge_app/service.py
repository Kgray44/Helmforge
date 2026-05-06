from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bridge_app import BRIDGE_NAME, PRODUCT_NAME, TECHNICAL_SUBTITLE
from bridge_app.config_loader import BridgeConfigLoadResult, load_bridge_workspace
from bridge_app.ipc import DEFAULT_COMMAND_PATH, DEFAULT_TELEMETRY_PATH, read_command, write_telemetry
from bridge_app.state import BridgeProcessState, lifecycle_for_preflight
from shared_core.math.pipeline import WorkspaceSignalPipeline
from shared_core.math.stack import ModeState
from shared_core.models.runtime import RuntimePreflightStatus
from shared_core.rules.evaluator import status_counts
from shared_core.runtime.bridge_contracts import BridgeCommandRequest, BridgeCommandType
from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.simulated_runtime import SimulatedRuntime
from shared_core.runtime.telemetry import (
    AxisTelemetrySnapshot,
    BridgeTelemetrySnapshot,
    ButtonHatTelemetrySnapshot,
    ModeStateTelemetrySnapshot,
    OutputVerificationState,
    RuleStateSummary,
)


@dataclass(frozen=True)
class BridgeServiceOptions:
    telemetry_path: Path = DEFAULT_TELEMETRY_PATH
    command_path: Path = DEFAULT_COMMAND_PATH
    config_path: Path | None = None
    simulate: bool = True
    tick_interval_ms: int = 50


class BridgeService:
    def __init__(self, options: BridgeServiceOptions | None = None) -> None:
        self.options = options or BridgeServiceOptions()
        self.config = load_bridge_workspace(self.options.config_path)
        self.runtime_status = build_runtime_preflight_status()
        self.state = BridgeProcessState.starting().with_messages(
            warnings=self.config.warnings,
            errors=self.config.errors,
        )
        self.simulation = SimulatedRuntime(deterministic=False, workspace=self.config.workspace)
        self.pipeline = WorkspaceSignalPipeline(self.config.workspace)
        self.pipeline_state = self.pipeline.initial_state()
        self._stop_requested = False

    def reload_config(self, config_path: str | Path | None = None) -> None:
        requested_path = Path(config_path) if config_path else self.options.config_path
        self.config = load_bridge_workspace(requested_path)
        self.simulation = SimulatedRuntime(deterministic=False, workspace=self.config.workspace)
        self.pipeline = WorkspaceSignalPipeline(self.config.workspace)
        self.pipeline_state = self.pipeline.initial_state()
        self.state = self.state.with_messages(warnings=self.config.warnings, errors=self.config.errors)

    def run_once(self) -> BridgeTelemetrySnapshot:
        command = read_command(self.options.command_path)
        if command is not None:
            self.handle_command(command)

        lifecycle_state = BridgeLifecycleState.STOPPING if self._stop_requested else lifecycle_for_preflight(
            self.runtime_status,
            simulate=self.options.simulate,
        )
        self.state = self.state.with_lifecycle(
            lifecycle_state,
            self.runtime_status,
            message="Simulation-only Bridge tick completed.",
        )
        snapshot = self.simulation.snapshot(self.runtime_status)
        telemetry = self._telemetry_from_snapshot(snapshot, lifecycle_state)
        write_telemetry(self.options.telemetry_path, self._telemetry_payload(telemetry))
        self.state = self.state.next_tick()
        return telemetry

    def run_for_ms(self, duration_ms: int) -> BridgeTelemetrySnapshot:
        deadline = time.monotonic() + max(0, duration_ms) / 1000.0
        telemetry = self.run_once()
        while not self._stop_requested and time.monotonic() < deadline:
            sleep_for = max(0.0, self.options.tick_interval_ms / 1000.0)
            time.sleep(sleep_for)
            telemetry = self.run_once()
        return telemetry

    def status(self) -> BridgeTelemetrySnapshot:
        return self.run_once()

    def handle_command(self, command: BridgeCommandRequest) -> None:
        if command.command is BridgeCommandType.START_BRIDGE:
            self._stop_requested = False
            return
        if command.command is BridgeCommandType.STOP_BRIDGE:
            self._stop_requested = True
            return
        if command.command is BridgeCommandType.RELOAD_CONFIG:
            self.reload_config(command.config_path)
            return
        if command.command is BridgeCommandType.RUN_PREFLIGHT:
            self.runtime_status = build_runtime_preflight_status()
            return
        if command.command is BridgeCommandType.SWITCH_TO_SIMULATION:
            self._stop_requested = False
            return
        if command.command is BridgeCommandType.CLEAR_ERROR:
            self.state = BridgeProcessState.starting()
            return
        if command.command is BridgeCommandType.STATUS:
            return

    def _telemetry_from_snapshot(self, snapshot, lifecycle_state: BridgeLifecycleState) -> BridgeTelemetrySnapshot:
        pipeline_result = self.pipeline.process(
            snapshot.raw_axis_values,
            mode_state=ModeState(),
            state=self.pipeline_state,
        )
        self.pipeline_state = pipeline_result.state
        counts = status_counts(pipeline_result.rule_evaluations)
        rule_summary = RuleStateSummary(
            active_count=counts["active"],
            blocked_count=counts["blocked"],
            disabled_count=counts["disabled"],
        )
        return BridgeTelemetrySnapshot(
            runtime_truth=self.runtime_status.truth,
            lifecycle_state=lifecycle_state,
            input_status=self.runtime_status.input.status,
            output_status=self.runtime_status.output.status,
            raw_axes=AxisTelemetrySnapshot(snapshot.raw_axis_values),
            final_axes=AxisTelemetrySnapshot(snapshot.final_output_values),
            controls=ButtonHatTelemetrySnapshot(
                buttons=snapshot.button_states,
                hats={"HOTAS Hat": snapshot.hat_state, "Output Hat": snapshot.hat_state},
            ),
            active_modes=ModeStateTelemetrySnapshot(),
            active_profile="Current Workspace",
            rule_summary=rule_summary,
            output_verification=OutputVerificationState(
                verified=False,
                backend_name=self.runtime_status.detected_output_backend_name,
                message="Live output writes are not verified.",
            ),
            warnings=(*self.runtime_status.warnings, *self.state.warnings),
            errors=(*self.runtime_status.errors, *self.state.errors),
        )

    def _telemetry_payload(self, telemetry: BridgeTelemetrySnapshot) -> dict[str, object]:
        payload = telemetry.to_dict()
        payload.update(
            {
                "product_name": PRODUCT_NAME,
                "technical_subtitle": TECHNICAL_SUBTITLE,
                "bridge_name": BRIDGE_NAME,
                "bridge_process": "bridge_app",
                "config_path": str(self.config.path),
                "config_status": self.config.status,
                "tick_count": self.state.tick_count,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return payload
