from __future__ import annotations

import time
import os
from dataclasses import replace
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bridge_app import BRIDGE_NAME, PRODUCT_NAME, TECHNICAL_SUBTITLE
from bridge_app.config_loader import BridgeConfigLoadResult, load_bridge_workspace
from bridge_app.ipc import DEFAULT_COMMAND_PATH, DEFAULT_TELEMETRY_PATH, read_command, write_telemetry
from bridge_app.runtime_session import BridgeOutputRuntimeSession
from bridge_app.state import BridgeProcessState, lifecycle_for_preflight
from bridge_app.telemetry_stream import (
    DEFAULT_TELEMETRY_STREAM_HOST,
    DEFAULT_TELEMETRY_STREAM_PORT,
    DEFAULT_TELEMETRY_STREAM_RATE_HZ,
    TelemetryStreamOptions,
    TelemetryStreamServer,
)
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
    DeviceDiscoveryState,
    HotasDiscoveryResult,
    discover_supported_hotas,
)
from shared_core.runtime.hotas_input import (
    PhysicalInputBackend,
    PhysicalInputBackendChoice,
    PhysicalInputFidelitySnapshot,
    PhysicalInputSampler,
    build_best_physical_input_backend,
    build_physical_input_fidelity,
    build_winmm_physical_input_fallback,
)
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
from shared_core.runtime.vjoy_output import RealVJoyOutputBackend, VirtualOutputBackend, VirtualOutputWriteLoop
from shared_core.runtime.vjoy_output import VirtualOutputVerificationResult


@dataclass(frozen=True)
class BridgeServiceOptions:
    telemetry_path: Path = DEFAULT_TELEMETRY_PATH
    command_path: Path = DEFAULT_COMMAND_PATH
    config_path: Path | None = None
    simulate: bool = True
    tick_interval_ms: int = 16
    discovery_refresh_interval_seconds: float = 2.0
    enable_periodic_discovery_refresh: bool = True
    command_stale_after_seconds: int = 30
    discovery_backend: DeviceDiscoveryBackend | None = None
    physical_input_backend: PhysicalInputBackend | None = None
    virtual_output_backend: VirtualOutputBackend | None = None
    enable_live_input: bool = True
    enable_output_verification: bool = True
    enable_output_loop: bool = True
    enable_telemetry_stream: bool = False
    telemetry_stream_host: str = DEFAULT_TELEMETRY_STREAM_HOST
    telemetry_stream_port: int = DEFAULT_TELEMETRY_STREAM_PORT
    telemetry_stream_rate_hz: float = DEFAULT_TELEMETRY_STREAM_RATE_HZ
    clock: object | None = None


@dataclass
class BridgeTimingStats:
    bridge_pid: int
    bridge_started_at: datetime
    tick_interval_target_ms: int
    tick_count: int = 0
    last_tick_duration_ms: float = 0.0
    last_command_duration_ms: float = 0.0
    last_discovery_duration_ms: float = 0.0
    last_discovery_age_ms: float | None = None
    last_slow_lane_duration_ms: float = 0.0
    last_discovery_blocked_ms: float = 0.0
    last_discovery_refresh_reason: str = "startup"
    discovery_running: bool = False
    discovery_skipped_reason: str = ""
    last_runtime_io_duration_ms: float = 0.0
    last_runtime_frame_duration_ms: float = 0.0
    last_input_read_duration_ms: float = 0.0
    last_pipeline_duration_ms: float = 0.0
    last_output_write_duration_ms: float = 0.0
    last_output_loop_tick_duration_ms: float = 0.0
    last_output_loop_status: str = "unavailable"
    output_loop_rate_limited: bool = False
    output_loop_safety_stopped: bool = False
    last_telemetry_publish_duration_ms: float = 0.0
    last_json_publish_retry_count: int = 0
    last_json_publish_blocked_ms: float = 0.0
    last_worker_tick_duration_ms: float = 0.0
    embedded_worker_late_tick_count: int = 0
    selected_physical_device_id: str | None = None
    selected_physical_device_source: str = "missing"
    device_selection_refresh_count: int = 0
    device_enumeration_duration_ms: float = 0.0
    device_enumeration_skipped_cached_count: int = 0
    fast_loop_status: str = "starting"
    slow_lane_status: str = "not_checked"

    def to_dict(self) -> dict[str, object]:
        return {
            "bridge_pid": self.bridge_pid,
            "bridge_started_at": self.bridge_started_at.isoformat(),
            "tick_count": self.tick_count,
            "tick_interval_target_ms": self.tick_interval_target_ms,
            "last_tick_duration_ms": self.last_tick_duration_ms,
            "last_command_duration_ms": self.last_command_duration_ms,
            "last_discovery_duration_ms": self.last_discovery_duration_ms,
            "last_discovery_age_ms": self.last_discovery_age_ms,
            "last_slow_lane_duration_ms": self.last_slow_lane_duration_ms,
            "last_discovery_blocked_ms": self.last_discovery_blocked_ms,
            "last_discovery_refresh_reason": self.last_discovery_refresh_reason,
            "discovery_running": self.discovery_running,
            "discovery_skipped_reason": self.discovery_skipped_reason,
            "last_runtime_io_duration_ms": self.last_runtime_io_duration_ms,
            "last_runtime_frame_duration_ms": self.last_runtime_frame_duration_ms,
            "last_input_read_duration_ms": self.last_input_read_duration_ms,
            "last_pipeline_duration_ms": self.last_pipeline_duration_ms,
            "last_output_write_duration_ms": self.last_output_write_duration_ms,
            "last_output_loop_tick_duration_ms": self.last_output_loop_tick_duration_ms,
            "last_output_loop_status": self.last_output_loop_status,
            "output_loop_rate_limited": self.output_loop_rate_limited,
            "output_loop_safety_stopped": self.output_loop_safety_stopped,
            "last_telemetry_publish_duration_ms": self.last_telemetry_publish_duration_ms,
            "last_json_publish_retry_count": self.last_json_publish_retry_count,
            "last_json_publish_blocked_ms": self.last_json_publish_blocked_ms,
            "last_worker_tick_duration_ms": self.last_worker_tick_duration_ms,
            "embedded_worker_late_tick_count": self.embedded_worker_late_tick_count,
            "selected_physical_device_id": self.selected_physical_device_id,
            "selected_physical_device_source": self.selected_physical_device_source,
            "device_selection_refresh_count": self.device_selection_refresh_count,
            "device_enumeration_duration_ms": self.device_enumeration_duration_ms,
            "device_enumeration_skipped_cached_count": self.device_enumeration_skipped_cached_count,
            "fast_loop_status": self.fast_loop_status,
            "slow_lane_status": self.slow_lane_status,
        }


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
        if self.options.physical_input_backend is not None:
            self.physical_input_backend = self.options.physical_input_backend
            caps = self.physical_input_backend.get_capabilities()
            self.physical_input_backend_choice = PhysicalInputBackendChoice(
                selected_backend_name=caps.backend_name,
                selected_backend_kind=caps.backend_kind,
                selection_reason="Physical input backend was supplied explicitly.",
                candidate_backends=(f"{caps.backend_name}:{caps.backend_kind}",),
                warnings=caps.warnings,
                errors=caps.errors,
            )
        else:
            selected_backend = build_best_physical_input_backend()
            self.physical_input_backend = selected_backend.backend
            self.physical_input_backend_choice = selected_backend.choice
        self.physical_sampler: PhysicalInputSampler | None = None
        self.physical_input_fidelity: PhysicalInputFidelitySnapshot | None = None
        self.virtual_output_backend = self.options.virtual_output_backend or RealVJoyOutputBackend()
        self.output_runtime_session = BridgeOutputRuntimeSession(
            backend=self.virtual_output_backend,
            verification_enabled=bool(self.options.enable_output_verification and not self.options.simulate),
            clock=self.options.clock,
        )
        self.telemetry_stream = TelemetryStreamServer(
            TelemetryStreamOptions(
                enabled=self.options.enable_telemetry_stream,
                host=self.options.telemetry_stream_host,
                port=self.options.telemetry_stream_port,
                rate_hz=self.options.telemetry_stream_rate_hz,
            ),
            clock=self.options.clock,
        )
        self.telemetry_stream.start()
        self.virtual_output_verification = self.output_runtime_session.verification
        self.virtual_output_loop: VirtualOutputWriteLoop | None = self.output_runtime_session.output_loop
        self._force_simulation_mode = False
        self._stop_requested = False
        self._consumed_command_request_ids: set[str] = set()
        self._last_command: BridgeCommandStatusSnapshot | None = None
        self.command_execution_count = 0
        self._last_discovery_monotonic: float | None = None
        self._discovery_warnings: tuple[str, ...] = ()
        self._selected_physical_device_id: str | None = None
        self._selected_physical_device_source = "missing"
        self.timing = BridgeTimingStats(
            bridge_pid=os.getpid(),
            bridge_started_at=self.state.started_at,
            tick_interval_target_ms=self.options.tick_interval_ms,
        )
        self.telemetry_publish_status: dict[str, object] = {
            "json_success": True,
            "json_error": "",
            "json_attempts": 0,
            "json_path": str(self.options.telemetry_path),
            "last_success_at": None,
            "last_failure_at": None,
        }
        self._run_slow_discovery(reason="startup")
        self._refresh_runtime_io()

    def shutdown(self) -> None:
        if self.physical_sampler is not None:
            self.physical_sampler.close()
            self.physical_sampler = None
        self.output_runtime_session.disable()
        self.telemetry_stream.stop()

    def reload_config(self, config_path: str | Path | None = None) -> BridgeConfigLoadResult:
        requested_path = Path(config_path) if config_path else self.options.config_path
        self.config = load_bridge_workspace(requested_path)
        self.simulation = SimulatedRuntime(deterministic=False, workspace=self.config.workspace)
        self.pipeline = WorkspaceSignalPipeline(self.config.workspace)
        self.pipeline_state = self.pipeline.initial_state()
        self.state = self.state.with_messages(warnings=self.config.warnings, errors=self.config.errors)
        return self.config

    def run_once(self, *, publish_telemetry: bool = True) -> BridgeTelemetrySnapshot:
        tick_started = time.perf_counter()
        self.timing.fast_loop_status = "ok"
        self._consume_pending_command()
        self._refresh_device_discovery_for_runtime_tick()
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
        self.timing.tick_count = self.state.tick_count + 1
        self.timing.last_tick_duration_ms = _elapsed_ms(tick_started)
        if publish_telemetry:
            publish_status = self._publish_telemetry(telemetry)
            if not publish_status.get("json_success", True):
                telemetry = replace(
                    telemetry,
                    warnings=telemetry.warnings
                    + (f"Bridge telemetry JSON publish failed: {publish_status.get('json_error')}",),
                )
        else:
            self.timing.last_telemetry_publish_duration_ms = 0.0
            self.timing.last_json_publish_retry_count = 0
            self.timing.last_json_publish_blocked_ms = 0.0
            self.telemetry_publish_status = {
                "json_success": None,
                "json_error": "",
                "json_attempts": 0,
                "json_path": str(self.options.telemetry_path),
                "last_success_at": self.telemetry_publish_status.get("last_success_at"),
                "last_failure_at": self.telemetry_publish_status.get("last_failure_at"),
                "status": "skipped_in_memory_only",
            }
        self.state = self.state.next_tick()
        self.timing.tick_count = self.state.tick_count
        if self._stop_requested:
            self.timing.fast_loop_status = "stopping"
        return telemetry

    def run_forever(self) -> BridgeTelemetrySnapshot:
        telemetry = self.run_once()
        try:
            while not self._stop_requested:
                sleep_for = max(0.0, self.options.tick_interval_ms / 1000.0)
                time.sleep(sleep_for)
                telemetry = self.run_once()
        except KeyboardInterrupt:
            self._stop_requested = True
            self.timing.fast_loop_status = "stopping"
        finally:
            telemetry = self._write_lifecycle_telemetry(BridgeLifecycleState.STOPPED, message="Bridge stopped cleanly.")
            self.shutdown()
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

    def handle_command(self, command: BridgeCommandRequest) -> dict[str, object]:
        if command.command is BridgeCommandType.START_BRIDGE:
            self._stop_requested = False
            self._force_simulation_mode = False
            return {}
        if command.command is BridgeCommandType.STOP_BRIDGE:
            self._stop_requested = True
            return {}
        if command.command is BridgeCommandType.RELOAD_CONFIG:
            loaded = self.reload_config(command.config_path)
            return self._reload_config_command_details(command, loaded)
        if command.command is BridgeCommandType.RUN_PREFLIGHT:
            self._refresh_device_discovery_if_due(force=True)
            self._clear_physical_device_selection_cache()
            self.output_runtime_session.refresh_verification(force=True, reason="run_preflight")
            self.virtual_output_verification = self.output_runtime_session.verification
            self.virtual_output_loop = self.output_runtime_session.output_loop
            return {}
        if command.command is BridgeCommandType.SWITCH_TO_SIMULATION:
            self._stop_requested = False
            self._force_simulation_mode = True
            self.output_runtime_session.disable()
            return {}
        if command.command is BridgeCommandType.CLEAR_ERROR:
            self.state = BridgeProcessState.starting()
            return {}
        if command.command is BridgeCommandType.STATUS:
            return {}
        return {}

    def _reload_config_command_details(
        self,
        command: BridgeCommandRequest,
        loaded: BridgeConfigLoadResult,
    ) -> dict[str, object]:
        expected_hash = command.expected_workspace_hash
        expected_revision = command.expected_workspace_revision
        loaded_hash = loaded.workspace_hash
        loaded_revision = loaded.workspace_revision
        mismatch_reason = ""
        config_match: bool | None = None
        if expected_hash:
            config_match = expected_hash == loaded_hash
            if not config_match:
                mismatch_reason = "workspace_hash_mismatch"
        if config_match is not False and expected_revision:
            revision_match = expected_revision == loaded_revision
            config_match = revision_match if config_match is None else config_match and revision_match
            if not revision_match:
                mismatch_reason = "workspace_revision_mismatch"
        return {
            "config_path": str(loaded.path),
            "config_status": loaded.status,
            "expected_workspace_hash": expected_hash,
            "expected_workspace_revision": expected_revision,
            "loaded_workspace_hash": loaded_hash,
            "loaded_workspace_revision": loaded_revision,
            "config_match": config_match,
            "mismatch_reason": mismatch_reason,
        }

    def refresh_device_discovery(self) -> HotasDiscoveryResult:
        return self._run_slow_discovery()

    def _refresh_device_discovery_if_due(self, *, force: bool = False) -> HotasDiscoveryResult:
        now = time.monotonic()
        interval = max(2.0, float(self.options.discovery_refresh_interval_seconds))
        due = self._last_discovery_monotonic is None or (now - self._last_discovery_monotonic) >= interval
        if not force and not self.options.enable_periodic_discovery_refresh and self.device_discovery is not None:
            self.timing.slow_lane_status = "cached_periodic_disabled"
            self.timing.last_discovery_age_ms = self._discovery_age_ms()
            self.timing.last_slow_lane_duration_ms = 0.0
            self.timing.discovery_running = False
            self.timing.discovery_skipped_reason = "periodic_disabled"
            return self.device_discovery
        if force or due:
            self.timing.slow_lane_status = "refreshing"
            return self._run_slow_discovery(reason="forced" if force else "periodic_due")
        self.timing.slow_lane_status = "cached"
        self.timing.last_discovery_age_ms = self._discovery_age_ms()
        self.timing.discovery_running = False
        self.timing.discovery_skipped_reason = "not_due"
        if self.device_discovery is None:
            return self._run_slow_discovery(reason="missing_initial_result")
        return self.device_discovery

    def _refresh_device_discovery_for_runtime_tick(self) -> HotasDiscoveryResult | None:
        if self._sampler_healthy():
            self.timing.slow_lane_status = "cached_sampler_active"
            self.timing.discovery_running = False
            self.timing.discovery_skipped_reason = "active_sampler_healthy"
            self.timing.last_discovery_age_ms = self._discovery_age_ms()
            return self.device_discovery
        if not self.options.enable_periodic_discovery_refresh and self.device_discovery is not None:
            self.timing.slow_lane_status = "cached_periodic_disabled"
            self.timing.discovery_running = False
            self.timing.discovery_skipped_reason = "periodic_disabled"
            self.timing.last_discovery_age_ms = self._discovery_age_ms()
            return self.device_discovery
        return self._refresh_device_discovery_if_due()

    def _run_slow_discovery(self, *, reason: str = "startup") -> HotasDiscoveryResult:
        started = time.perf_counter()
        self.timing.discovery_running = True
        self.timing.discovery_skipped_reason = ""
        self.timing.last_discovery_refresh_reason = reason
        if self.options.simulate and self.options.discovery_backend is None:
            result = HotasDiscoveryResult(
                status=DeviceDiscoveryState.NO_SUPPORTED_DEVICE,
                backend="simulation",
                checked_at=datetime.now(timezone.utc),
                warnings=("Simulation mode skips Windows HOTAS discovery; live discovery remains available outside --simulate.",),
            )
        else:
            result = discover_supported_hotas(backend=self.options.discovery_backend)
        self.timing.last_discovery_duration_ms = _elapsed_ms(started)
        self.timing.last_slow_lane_duration_ms = self.timing.last_discovery_duration_ms
        self.timing.last_discovery_blocked_ms = self.timing.last_discovery_duration_ms
        self._last_discovery_monotonic = time.monotonic()
        self.timing.last_discovery_age_ms = 0.0
        self.timing.slow_lane_status = "refreshed"
        self.timing.discovery_running = False
        if result.status.value in {"discovery_error", "backend_unavailable"} and self.device_discovery is not None:
            self._discovery_warnings = (
                f"Slow HOTAS discovery reported {result.status.value}; keeping last cached discovery result.",
            )
            self.timing.slow_lane_status = "cached_after_error"
            return self.device_discovery
        self.device_discovery = result
        self._discovery_warnings = ()
        input_names = (result.device_name,) if result.matched and result.device_name else ()
        self.runtime_status = build_runtime_preflight_status(input_device_names=input_names)
        return result

    def _sampler_healthy(self) -> bool:
        snapshot = self.physical_sampler.latest_snapshot if self.physical_sampler is not None else None
        return bool(
            self.physical_sampler is not None
            and self.physical_sampler.selected_device_id
            and snapshot is not None
            and snapshot.sampling_active
            and not snapshot.errors
        )

    def _discovery_age_ms(self) -> float | None:
        if self._last_discovery_monotonic is None:
            return None
        return max(0.0, (time.monotonic() - self._last_discovery_monotonic) * 1000.0)

    def _refresh_runtime_io(self) -> None:
        runtime_started = time.perf_counter()
        input_started = time.perf_counter()
        latest_snapshot = None
        selected_device_id = self._select_physical_device_id()
        if self.options.enable_live_input and selected_device_id:
            if self.physical_sampler is None or self.physical_sampler.selected_device_id != selected_device_id:
                if self.physical_sampler is not None:
                    self.physical_sampler.close()
                self.physical_sampler = PhysicalInputSampler(
                    self.physical_input_backend,
                    selected_device_id=selected_device_id,
                    validate_selection_on_read=False,
                )
                self.physical_sampler.open()
            latest_snapshot = self.physical_sampler.read_once()
            if (
                latest_snapshot is not None
                and latest_snapshot.sample_source == "raw_input"
                and not latest_snapshot.sampling_active
                and latest_snapshot.sequence == 0
            ):
                fallback = build_winmm_physical_input_fallback()
                if fallback.choice.selected_backend_kind != "missing":
                    self.physical_sampler.close()
                    self.physical_input_backend = fallback.backend
                    self.physical_input_backend_choice = PhysicalInputBackendChoice(
                        selected_backend_name=fallback.choice.selected_backend_name,
                        selected_backend_kind=fallback.choice.selected_backend_kind,
                        selection_reason="Raw Input did not produce an initial WM_INPUT sample; selected WinMM fallback for continuous state reads.",
                        fallback_used=True,
                        fallback_reason="windows_raw_input produced no sample after message-loop start",
                        candidate_backends=("windows_raw_input:windows_raw_input",) + tuple(fallback.choice.candidate_backends),
                        warnings=fallback.choice.warnings + ("Raw Input fallback preserved because no sample arrived yet.",),
                        errors=fallback.choice.errors,
                    )
                    self._clear_physical_device_selection_cache()
                    selected_device_id = self._select_physical_device_id()
                    self.physical_sampler = PhysicalInputSampler(
                        self.physical_input_backend,
                        selected_device_id=selected_device_id,
                        validate_selection_on_read=False,
                    )
                    self.physical_sampler.open()
                    latest_snapshot = self.physical_sampler.read_once()
        elif self.physical_sampler is not None:
            self.physical_sampler.close()
            self.physical_sampler = None
        self.timing.last_input_read_duration_ms = _elapsed_ms(input_started)
        self.physical_input_fidelity = build_physical_input_fidelity(
            latest_snapshot,
            backend=self.physical_input_backend,
            backend_choice=self.physical_input_backend_choice,
            sampled_at=datetime.now(timezone.utc),
            read_duration_ms=self.timing.last_input_read_duration_ms,
        )

        output_allowed = (
            bool(self.options.enable_output_loop)
            and not self.options.simulate
            and not self._force_simulation_mode
            and latest_snapshot is not None
            and latest_snapshot.sampling_active
        )
        self.output_runtime_session.set_output_allowed(output_allowed)
        self.virtual_output_verification = self.output_runtime_session.verification
        self.virtual_output_loop = self.output_runtime_session.output_loop

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
                allow_output_loop_tick=output_allowed,
            ),
            clock=self.options.clock,
        )
        self.timing.last_runtime_io_duration_ms = _elapsed_ms(runtime_started)

    def _select_physical_device_id(self) -> str | None:
        if self.options.simulate or not self.options.enable_live_input:
            self._selected_physical_device_id = None
            self._selected_physical_device_source = "missing"
            self._sync_device_selection_timing()
            return None
        if self._sampler_healthy() and self._selected_physical_device_id:
            self._selected_physical_device_source = "cached"
            self.timing.device_enumeration_skipped_cached_count += 1
            self._sync_device_selection_timing()
            return self._selected_physical_device_id
        started = time.perf_counter()
        try:
            devices = self.physical_input_backend.enumerate_devices()
        except Exception:
            self.timing.device_enumeration_duration_ms = _elapsed_ms(started)
            self._selected_physical_device_id = None
            self._selected_physical_device_source = "error"
            self.timing.device_selection_refresh_count += 1
            self._sync_device_selection_timing()
            return None
        self.timing.device_enumeration_duration_ms = _elapsed_ms(started)
        self.timing.device_selection_refresh_count += 1
        supported = next((device for device in devices if device.is_supported), None)
        self._selected_physical_device_id = supported.device_id if supported is not None else None
        self._selected_physical_device_source = "refreshed" if supported is not None else "missing"
        self._sync_device_selection_timing()
        return self._selected_physical_device_id

    def _clear_physical_device_selection_cache(self) -> None:
        self._selected_physical_device_id = None
        self._selected_physical_device_source = "missing"
        self._sync_device_selection_timing()

    def _sync_device_selection_timing(self) -> None:
        self.timing.selected_physical_device_id = self._selected_physical_device_id
        self.timing.selected_physical_device_source = self._selected_physical_device_source

    def _consume_pending_command(self) -> None:
        command = read_command(self.options.command_path)
        if command is None:
            self.timing.last_command_duration_ms = 0.0
            return

        command_started = time.perf_counter()
        now = _clock_now(self.options.clock)
        age_seconds = max(0.0, (now - command.created_at).total_seconds())
        if age_seconds > max(1, self.options.command_stale_after_seconds):
            self.timing.last_command_duration_ms = _elapsed_ms(command_started)
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
            self.timing.last_command_duration_ms = 0.0
            return

        received_at = now
        try:
            command_details = self.handle_command(command)
        except Exception as exc:
            completed_at = _clock_now(self.options.clock)
            self.timing.last_command_duration_ms = _elapsed_ms(command_started)
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

        completed_at = _clock_now(self.options.clock)
        self.timing.last_command_duration_ms = _elapsed_ms(command_started)
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
            **command_details,
        )

    def _telemetry_from_runtime(self, lifecycle_state: BridgeLifecycleState) -> BridgeTelemetrySnapshot:
        frame_started = time.perf_counter()
        frame = self.runtime_orchestrator.build_frame()
        frame_duration = _elapsed_ms(frame_started)
        self.timing.last_runtime_frame_duration_ms = frame_duration
        self.timing.last_pipeline_duration_ms = frame_duration
        loop_snapshot = self.virtual_output_loop.snapshot() if self.virtual_output_loop is not None else None
        self.timing.last_output_write_duration_ms = float(loop_snapshot.last_write_duration_ms or 0.0) if loop_snapshot is not None else 0.0
        self.timing.last_output_loop_tick_duration_ms = self.timing.last_output_write_duration_ms
        self.timing.last_output_loop_status = loop_snapshot.output_write_status if loop_snapshot is not None else "unavailable"
        self.timing.output_loop_rate_limited = bool(loop_snapshot and loop_snapshot.last_skipped_write_reason == "skipped_rate_limited")
        self.timing.output_loop_safety_stopped = bool(loop_snapshot and loop_snapshot.state.value == "safety_stopped")
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
            warnings=(*self.runtime_status.warnings, *self.state.warnings, *self._discovery_warnings),
            errors=(*self.runtime_status.errors, *self.state.errors),
        )

    def _write_lifecycle_telemetry(self, lifecycle_state: BridgeLifecycleState, *, message: str) -> BridgeTelemetrySnapshot:
        self.state = self.state.with_lifecycle(lifecycle_state, self.runtime_status, message=message)
        telemetry = self._telemetry_from_runtime(lifecycle_state)
        self._publish_telemetry(telemetry)
        return telemetry

    def _publish_telemetry(self, telemetry: BridgeTelemetrySnapshot) -> dict[str, object]:
        payload = self._telemetry_payload(telemetry)
        publish_started = time.perf_counter()
        self.timing.last_telemetry_publish_duration_ms = _elapsed_ms(publish_started)
        payload["bridge_timing"] = self.timing.to_dict()
        payload["telemetry_publish"] = dict(self.telemetry_publish_status)
        payload["telemetry_stream"] = self.telemetry_stream.status().to_dict()
        self.telemetry_stream.publish(payload)
        payload["telemetry_stream"] = self.telemetry_stream.status().to_dict()
        status = self._write_telemetry_snapshot(payload, publish_started=publish_started)
        payload["telemetry_publish"] = dict(status)
        return status

    def build_telemetry_payload(self, telemetry: BridgeTelemetrySnapshot) -> dict[str, object]:
        return self._telemetry_payload(telemetry)

    def _write_telemetry_snapshot(self, payload: dict[str, object], *, publish_started: float) -> dict[str, object]:
        try:
            write_telemetry(self.options.telemetry_path, payload)
        except (PermissionError, OSError) as exc:
            self.timing.last_telemetry_publish_duration_ms = _elapsed_ms(publish_started)
            self.timing.last_json_publish_retry_count = 1
            self.timing.last_json_publish_blocked_ms = self.timing.last_telemetry_publish_duration_ms
            self.telemetry_publish_status = {
                "json_success": False,
                "json_error": str(exc),
                "json_attempts": 1,
                "json_path": str(self.options.telemetry_path),
                "last_success_at": self.telemetry_publish_status.get("last_success_at"),
                "last_failure_at": datetime.now(timezone.utc).isoformat(),
            }
            return self.telemetry_publish_status
        self.timing.last_telemetry_publish_duration_ms = _elapsed_ms(publish_started)
        self.timing.last_json_publish_retry_count = 1
        self.timing.last_json_publish_blocked_ms = self.timing.last_telemetry_publish_duration_ms
        self.telemetry_publish_status = {
            "json_success": True,
            "json_error": "",
            "json_attempts": 1,
            "json_path": str(self.options.telemetry_path),
            "last_success_at": datetime.now(timezone.utc).isoformat(),
            "last_failure_at": self.telemetry_publish_status.get("last_failure_at"),
        }
        return self.telemetry_publish_status

    def _telemetry_payload(self, telemetry: BridgeTelemetrySnapshot) -> dict[str, object]:
        payload = telemetry.to_dict()
        self.timing.last_discovery_age_ms = self._discovery_age_ms()
        payload.update(
            {
                "product_name": PRODUCT_NAME,
                "technical_subtitle": TECHNICAL_SUBTITLE,
                "bridge_name": BRIDGE_NAME,
                "bridge_process": "bridge_app",
                "config_path": str(self.config.path),
                "config_status": self.config.status,
                "bridge_workspace": self.config.bridge_workspace_payload(),
                "output_loop_runtime": self.output_runtime_session.telemetry().to_dict(),
                "tick_count": self.state.tick_count,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "bridge_timing": self.timing.to_dict(),
                "physical_input_backend_choice": self.physical_input_backend_choice.to_dict(),
                "physical_input_fidelity": self.physical_input_fidelity.to_dict() if self.physical_input_fidelity else None,
                "telemetry_stream": self.telemetry_stream.status().to_dict(),
                "telemetry_publish": dict(self.telemetry_publish_status),
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


def _elapsed_ms(started: float) -> float:
    return round(max(0.0, (time.perf_counter() - started) * 1000.0), 3)


def _clock_now(clock: object | None) -> datetime:
    if callable(clock):
        value = clock()
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
    return datetime.now(timezone.utc)
