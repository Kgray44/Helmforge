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
from shared_core.models.runtime import InputDeviceDetection, InputStatus, OutputBackendDetection, OutputStatus, RuntimeMode, RuntimeTruth
from shared_core.rules.evaluator import status_counts
from shared_core.runtime.bridge_contracts import BridgeCommandRequest, BridgeCommandType
from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.hotas_discovery import (
    DeviceDiscoveryBackend,
    HotasDiscoveryResult,
    discover_supported_hotas,
)
from shared_core.runtime.hotas_input import PhysicalInputBackend, PhysicalInputSampler, build_default_physical_input_backend
from shared_core.runtime.runtime_orchestrator import RuntimeOrchestrator, RuntimeOrchestratorConfig
from shared_core.runtime.runtime_orchestrator import RuntimeFrameSource
from shared_core.runtime.simulated_runtime import SimulatedRuntime
from shared_core.runtime.telemetry import (
    AxisTelemetrySnapshot,
    BridgeTelemetrySnapshot,
    BridgeCommandStatusSnapshot,
    ButtonHatTelemetrySnapshot,
    ModeStateTelemetrySnapshot,
    OutputVerificationState,
    RuleStateSummary,
)
from shared_core.runtime.vjoy_output import RealVJoyOutputBackend, VirtualOutputBackend, VirtualOutputWriteLoop, build_safe_vjoy_verification_intent
from shared_core.runtime.vjoy_output import VirtualOutputVerificationResult


@dataclass(frozen=True)
class BridgeServiceOptions:
    telemetry_path: Path = DEFAULT_TELEMETRY_PATH
    command_path: Path = DEFAULT_COMMAND_PATH
    config_path: Path | None = None
    simulate: bool = True
    tick_interval_ms: int = 16
    command_stale_after_seconds: int = 30
    discovery_backend: DeviceDiscoveryBackend | None = None
    physical_input_backend: PhysicalInputBackend | None = None
    virtual_output_backend: VirtualOutputBackend | None = None
    enable_live_input: bool = True
    enable_output_verification: bool = True
    enable_output_loop: bool = True
    clock: object | None = None


class BridgeService:
    def __init__(self, options: BridgeServiceOptions | None = None) -> None:
        self.options = options or BridgeServiceOptions()
        self.config = load_bridge_workspace(self.options.config_path)
        self.device_discovery: HotasDiscoveryResult | None = None
        self.runtime_status = build_runtime_preflight_status(input_device_names=())
        self.state = BridgeProcessState.starting().with_messages(
            warnings=self.config.warnings,
            errors=self.config.errors,
        )
        self.simulation = SimulatedRuntime(deterministic=False, workspace=self.config.workspace)
        self.runtime_orchestrator = RuntimeOrchestrator(
            workspace=self.config.workspace,
            runtime_status=self.runtime_status,
            config=RuntimeOrchestratorConfig(deterministic_simulation=False),
        )
        self.pipeline = WorkspaceSignalPipeline(self.config.workspace)
        self.pipeline_state = self.pipeline.initial_state()
        self.physical_input_backend = self.options.physical_input_backend or build_default_physical_input_backend()
        self.physical_sampler: PhysicalInputSampler | None = None
        self.virtual_output_backend = self.options.virtual_output_backend or RealVJoyOutputBackend()
        self.virtual_output_verification = None
        self.virtual_output_loop: VirtualOutputWriteLoop | None = None
        self._stop_requested = False
        self._consumed_command_request_ids: set[str] = set()
        self._last_command: BridgeCommandStatusSnapshot | None = None
        self.command_execution_count = 0
        self.refresh_device_discovery()
        self._refresh_runtime_io()

    def reload_config(self, config_path: str | Path | None = None) -> None:
        requested_path = Path(config_path) if config_path else self.options.config_path
        self.config = load_bridge_workspace(requested_path)
        self.simulation = SimulatedRuntime(deterministic=False, workspace=self.config.workspace)
        self.pipeline = WorkspaceSignalPipeline(self.config.workspace)
        self.pipeline_state = self.pipeline.initial_state()
        self.state = self.state.with_messages(warnings=self.config.warnings, errors=self.config.errors)

    def run_once(self) -> BridgeTelemetrySnapshot:
        self._consume_pending_command()
        self.refresh_device_discovery()
        self._refresh_runtime_io()

        lifecycle_state = BridgeLifecycleState.STOPPING if self._stop_requested else lifecycle_for_preflight(
            self.runtime_status,
            simulate=self.options.simulate,
        )
        self.state = self.state.with_lifecycle(
            lifecycle_state,
            self.runtime_status,
            message="Bridge tick completed.",
        )
        telemetry = self._telemetry_from_runtime(lifecycle_state)
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
            self.refresh_device_discovery()
            return
        if command.command is BridgeCommandType.SWITCH_TO_SIMULATION:
            self._stop_requested = False
            return
        if command.command is BridgeCommandType.CLEAR_ERROR:
            self.state = BridgeProcessState.starting()
            return
        if command.command is BridgeCommandType.STATUS:
            return

    def refresh_device_discovery(self) -> HotasDiscoveryResult:
        self.device_discovery = discover_supported_hotas(backend=self.options.discovery_backend)
        input_names = (self.device_discovery.device_name,) if self.device_discovery.matched and self.device_discovery.device_name else ()
        self.runtime_status = build_runtime_preflight_status(input_device_names=input_names)
        return self.device_discovery

    def _refresh_runtime_io(self) -> None:
        latest_snapshot = None
        selected_device_id = self._select_physical_device_id()
        if self.options.enable_live_input and selected_device_id:
            if self.physical_sampler is None or self.physical_sampler.selected_device_id != selected_device_id:
                if self.physical_sampler is not None:
                    self.physical_sampler.close()
                self.physical_sampler = PhysicalInputSampler(self.physical_input_backend, selected_device_id=selected_device_id)
                self.physical_sampler.open()
            latest_snapshot = self.physical_sampler.read_once()
        elif self.physical_sampler is not None:
            self.physical_sampler.close()
            self.physical_sampler = None

        if self.options.simulate or not self.options.enable_output_verification:
            self.virtual_output_verification = None
        elif self.virtual_output_verification is None or not self.virtual_output_verification.real_output_verified:
            self.virtual_output_verification = self.virtual_output_backend.verify_output_write(
                build_safe_vjoy_verification_intent()
            )
        self.virtual_output_loop = VirtualOutputWriteLoop(
            backend=self.virtual_output_backend,
            verification=self.virtual_output_verification,
            clock=self.options.clock,
        )
        if self.options.enable_output_loop and not self.options.simulate and latest_snapshot is not None and latest_snapshot.sampling_active:
            self.virtual_output_loop.enable()
        else:
            self.virtual_output_loop.disable()

        self.runtime_status = _runtime_status_for_live_chain(
            base=self.runtime_status,
            physical_snapshot=latest_snapshot,
            output_verification=self.virtual_output_verification,
        )
        self.runtime_orchestrator = RuntimeOrchestrator(
            workspace=self.config.workspace,
            runtime_status=self.runtime_status,
            physical_input_snapshot=latest_snapshot,
            virtual_output_backend=self.virtual_output_backend,
            virtual_output_verification=self.virtual_output_verification,
            virtual_output_loop=self.virtual_output_loop,
            config=RuntimeOrchestratorConfig(
                preferred_input_source=RuntimeFrameSource.PHYSICAL if latest_snapshot is not None else RuntimeFrameSource.SIMULATION,
                deterministic_simulation=False,
                allow_simulation_fallback=True,
                allow_output_loop_tick=bool(self.options.enable_output_loop),
            ),
            clock=self.options.clock,
        )

    def _select_physical_device_id(self) -> str | None:
        if self.options.simulate or not self.options.enable_live_input:
            return None
        devices = self.physical_input_backend.enumerate_devices()
        supported = next((device for device in devices if device.is_supported), None)
        return supported.device_id if supported is not None else None

    def _consume_pending_command(self) -> None:
        command = read_command(self.options.command_path)
        if command is None:
            return

        now = datetime.now(timezone.utc)
        age_seconds = max(0.0, (now - command.created_at).total_seconds())
        if age_seconds > max(1, self.options.command_stale_after_seconds):
            self._last_command = BridgeCommandStatusSnapshot(
                request_id=command.request_id,
                command=command.command.value,
                status="ignored_stale",
                received_at=now,
                completed_at=now,
                updated_at=now,
                message=(
                    f"Ignored stale command request {command.request_id}; "
                    f"age {age_seconds:.1f}s exceeds {self.options.command_stale_after_seconds}s."
                ),
            )
            return

        if command.request_id in self._consumed_command_request_ids:
            return

        received_at = now
        try:
            self.handle_command(command)
        except Exception as exc:
            completed_at = datetime.now(timezone.utc)
            self._last_command = BridgeCommandStatusSnapshot(
                request_id=command.request_id,
                command=command.command.value,
                status="failed",
                received_at=received_at,
                completed_at=completed_at,
                updated_at=completed_at,
                message=f"{command.command.value} command failed in Bridge skeleton.",
                error=str(exc),
            )
            self._consumed_command_request_ids.add(command.request_id)
            return

        completed_at = datetime.now(timezone.utc)
        self.command_execution_count += 1
        self._consumed_command_request_ids.add(command.request_id)
        self._last_command = BridgeCommandStatusSnapshot(
            request_id=command.request_id,
            command=command.command.value,
            status="completed",
            received_at=received_at,
            completed_at=completed_at,
            updated_at=completed_at,
            message=f"{command.command.value} command completed by simulation-only Bridge.",
        )

    def _telemetry_from_runtime(self, lifecycle_state: BridgeLifecycleState) -> BridgeTelemetrySnapshot:
        frame = self.runtime_orchestrator.build_frame()
        raw_axes = dict(frame.pipeline.raw_axis_values)
        final_axes = dict(frame.pipeline.final_output_values)
        buttons = {f"B{index}": False for index in range(1, 16)}
        if self.physical_sampler is not None and self.physical_sampler.latest_snapshot is not None:
            for button in self.physical_sampler.latest_snapshot.buttons:
                name = f"B{button.button_index}"
                if name in buttons:
                    buttons[name] = bool(button.pressed)
        hat_state = "Centered"
        if self.physical_sampler is not None and self.physical_sampler.latest_snapshot is not None and self.physical_sampler.latest_snapshot.hats:
            hat_state = self.physical_sampler.latest_snapshot.hats[0].normalized_direction
        pipeline_result = self.pipeline.process(
            raw_axes,
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
            raw_axes=AxisTelemetrySnapshot(raw_axes),
            final_axes=AxisTelemetrySnapshot(final_axes),
            controls=ButtonHatTelemetrySnapshot(
                buttons=buttons,
                hats={"HOTAS Hat": hat_state, "Output Hat": hat_state},
            ),
            active_modes=ModeStateTelemetrySnapshot(),
            active_profile="Current Workspace",
            rule_summary=rule_summary,
            output_verification=OutputVerificationState(
                verified=self.runtime_status.live_output_writes_verified,
                backend_name=self.runtime_status.detected_output_backend_name,
                message="Live output writes are verified." if self.runtime_status.live_output_writes_verified else "Live output writes are not verified.",
            ),
            runtime_frame=frame.to_telemetry_dict(sequence=self.state.tick_count + 1),
            last_command=self._last_command,
            device_discovery=self.device_discovery,
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


def _runtime_status_for_live_chain(
    *,
    base: RuntimePreflightStatus,
    physical_snapshot,
    output_verification: VirtualOutputVerificationResult | None,
) -> RuntimePreflightStatus:
    input_detected = physical_snapshot is not None and physical_snapshot.sampling_active
    output_verified = bool(output_verification and output_verification.real_output_verified)
    output_name = output_verification.backend_name if output_verification is not None else base.detected_output_backend_name
    input_detection = InputDeviceDetection(
        status=InputStatus.DETECTED if input_detected else base.input.status,
        detected_device_names=(physical_snapshot.device_name,) if input_detected else base.detected_device_names,
        messages=("Physical HOTAS sample is active.",) if input_detected else base.input.messages,
        warnings=base.input.warnings,
        errors=base.input.errors,
    )
    output_detection = OutputBackendDetection(
        status=OutputStatus.OUTPUT_VERIFIED if output_verified else base.output.status,
        backend_name=output_name,
        live_output_writes_verified=output_verified,
        messages=("Real vJoy guarded verification succeeded.",) if output_verified else base.output.messages,
        warnings=base.output.warnings,
        errors=base.output.errors,
    )
    if input_detected and output_verified:
        return RuntimePreflightStatus(
            mode=RuntimeMode.FULL_LIVE,
            truth=RuntimeTruth.LIVE_VERIFIED,
            input=input_detection,
            output=output_detection,
            messages=("Physical HOTAS input and real vJoy output verification are active.",),
            warnings=(),
            errors=base.errors,
        )
    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=base.truth,
        input=input_detection,
        output=output_detection,
        messages=base.messages,
        warnings=base.warnings,
        errors=base.errors,
    )
