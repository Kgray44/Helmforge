from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from shared_core.math.pipeline import SignalPipelineState, WorkspaceSignalPipeline, WorkspaceSignalPipelineResult
from shared_core.math.stack import ModeState
from shared_core.models.runtime import (
    AXIS_NAMES,
    BUTTON_NAMES,
    HAT_CENTERED,
    RuntimePreflightStatus,
    RuntimeSnapshot,
    simulation_fallback_status,
)
from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.runtime.hotas_input import PhysicalInputSamplingStatus, PhysicalInputSnapshot
from shared_core.runtime.simulated_runtime import SimulatedRuntime
from shared_core.runtime.vjoy_output import (
    MissingVirtualOutputBackend,
    VirtualOutputBackend,
    VirtualOutputDiagnostics,
    VirtualOutputIntent,
    VirtualOutputLoopSnapshot,
    VirtualOutputVerificationResult,
    VirtualOutputWriteLoop,
    VirtualOutputWriteLoopState,
    build_recovered_virtual_output_intent,
    build_virtual_output_diagnostics,
)


class RuntimeFrameSource(Enum):
    SIMULATION = "simulation"
    PHYSICAL = "physical"
    FAKE = "fake"
    UNAVAILABLE = "unavailable"


class RuntimeFrameStatus(Enum):
    SIMULATED_PIPELINE_READY = "simulated_pipeline_ready"
    SIMULATED_OUTPUT_INTENT_READY = "simulated_output_intent_ready"
    PHYSICAL_INPUT_READY_OUTPUT_UNVERIFIED = "physical_input_ready_output_unverified"
    PHYSICAL_INPUT_READY_OUTPUT_VERIFIED = "physical_input_ready_output_verified"
    OUTPUT_LOOP_READY_VERIFIED = "output_loop_ready_verified"
    OUTPUT_VERIFIED_RUNTIME_NOT_ENABLED = "output_verified_runtime_not_enabled"
    OUTPUT_LOOP_FAKE_RUNNING = "output_loop_fake_running"
    OUTPUT_LOOP_REAL_RUNNING_UNVERIFIED_INPUT = "output_loop_real_running_unverified_input"
    OUTPUT_LOOP_RUNNING_REAL = "output_loop_running_real"
    VERIFIED_RUNTIME_CANDIDATE = "verified_runtime_candidate"
    FULL_LIVE_RUNTIME_READY = "full_live_runtime_ready"
    BLOCKED_MISSING_DEVICE = "blocked_missing_device"
    BLOCKED_MISSING_INPUT = "blocked_missing_input"
    BLOCKED_MISSING_OUTPUT = "blocked_missing_output"
    BLOCKED_UNVERIFIED_OUTPUT = "blocked_unverified_output"
    BLOCKED_STALE_INPUT = "blocked_stale_input"
    BLOCKED_INPUT_ERROR = "blocked_input_error"
    BLOCKED_OUTPUT_LOOP_DISABLED = "blocked_output_loop_disabled"
    BLOCKED_OUTPUT_SAFETY_STOP = "blocked_output_safety_stop"
    BLOCKED_PIPELINE_ERROR = "blocked_pipeline_error"
    BLOCKED_TELEMETRY_STALE = "blocked_telemetry_stale"
    BLOCKED_FAKE_PATH_ONLY = "blocked_fake_path_only"
    BLOCKED_ERROR = "blocked_error"


@dataclass(frozen=True)
class RuntimeOrchestratorConfig:
    preferred_input_source: RuntimeFrameSource = RuntimeFrameSource.SIMULATION
    deterministic_simulation: bool = False
    allow_simulation_fallback: bool = True
    physical_sample_stale_after_seconds: float = 2.0
    allow_output_loop_tick: bool = False


@dataclass(frozen=True)
class RuntimeInputSummary:
    requested_source: RuntimeFrameSource
    source: RuntimeFrameSource
    device_name: str
    backend_name: str
    sampled_at: datetime | None
    sample_age_seconds: float | None
    axis_count: int
    button_count: int
    hat_count: int
    sample_status: str
    sample_source: str
    stale: bool = False
    error: bool = False
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimePipelineResult:
    selected_workspace: str
    active_profile: str
    active_modes: tuple[str, ...]
    active_rules: tuple[str, ...]
    active_rules_count: int
    raw_axis_values: Mapping[str, float]
    final_output_values: Mapping[str, float]
    stage_names_by_axis: Mapping[str, tuple[str, ...]]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_axis_values", MappingProxyType(dict(self.raw_axis_values)))
        object.__setattr__(self, "final_output_values", MappingProxyType(dict(self.final_output_values)))
        object.__setattr__(
            self,
            "stage_names_by_axis",
            MappingProxyType({name: tuple(stages) for name, stages in self.stage_names_by_axis.items()}),
        )


@dataclass(frozen=True)
class RuntimeOutputTruth:
    virtual_output_backend: str
    output_verification_status: str
    output_loop_state: str
    output_loop_enabled: bool
    output_loop_running: bool
    output_loop_safety_stopped: bool
    last_write_status: str
    write_count: int
    fake_output_verified: bool
    real_output_verified: bool
    output_verified: bool
    full_live_runtime_ready: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeProofState:
    input_verified_for_runtime: bool
    input_proof: str
    pipeline_ready: bool
    pipeline_proof: str
    output_verified_for_runtime: bool
    output_proof: str
    output_loop_enabled: bool
    output_loop_running: bool
    output_loop_safety_stopped: bool
    verified_runtime_candidate: bool
    proof_summary: str


@dataclass(frozen=True)
class RuntimeSafetyState:
    runtime_truth: str
    blocked_reason: str
    fallback_reason: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    full_live_runtime_ready: bool = False


@dataclass(frozen=True)
class RuntimeReadinessGateResult:
    full_live_runtime_ready: bool
    ready_state: str
    blocked_reason: str
    input_proof: str
    pipeline_proof: str
    output_proof: str
    telemetry_proof: str
    safety_proof: str
    fake_or_real_path: str
    proof_summary: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    evaluated_at: datetime | None = None


@dataclass(frozen=True)
class RuntimeFrame:
    created_at: datetime
    status: RuntimeFrameStatus
    input: RuntimeInputSummary
    pipeline: RuntimePipelineResult
    output_intent: VirtualOutputIntent
    output: RuntimeOutputTruth
    proof: RuntimeProofState
    safety: RuntimeSafetyState
    readiness: RuntimeReadinessGateResult

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "input_source": self.input.source.value,
            "requested_input_source": self.input.requested_source.value,
            "input_sample_status": self.input.sample_status,
            "input_sample_age_seconds": self.input.sample_age_seconds,
            "active_modes": self.pipeline.active_modes,
            "active_rules_count": self.pipeline.active_rules_count,
            "output_intent_ready": bool(self.output_intent.axes),
            "output_intent_source": self.output_intent.source,
            "final_output_axes": tuple(axis.axis_name for axis in self.output_intent.axes),
            "output_loop_state": self.output.output_loop_state,
            "output_verification_status": self.output.output_verification_status,
            "output_verified": self.output.output_verified,
            "real_output_verified": self.output.real_output_verified,
            "fake_output_verified": self.output.fake_output_verified,
            "full_live_runtime_ready": self.readiness.full_live_runtime_ready,
            "ready_state": self.readiness.ready_state,
            "runtime_truth": self.safety.runtime_truth,
            "blocked_reason": self.readiness.blocked_reason,
            "fallback_reason": self.safety.fallback_reason,
            "input_verified_for_runtime": self.proof.input_verified_for_runtime,
            "pipeline_ready": self.proof.pipeline_ready,
            "output_verified_for_runtime": self.proof.output_verified_for_runtime,
            "output_loop_enabled": self.proof.output_loop_enabled,
            "output_loop_running": self.proof.output_loop_running,
            "output_loop_safety_stopped": self.proof.output_loop_safety_stopped,
            "verified_runtime_candidate": self.proof.verified_runtime_candidate,
            "input_proof": self.readiness.input_proof,
            "pipeline_proof": self.readiness.pipeline_proof,
            "output_proof": self.readiness.output_proof,
            "telemetry_proof": self.readiness.telemetry_proof,
            "safety_proof": self.readiness.safety_proof,
            "fake_or_real_path": self.readiness.fake_or_real_path,
            "proof_summary": self.readiness.proof_summary,
            "evaluated_at": self.readiness.evaluated_at.isoformat() if self.readiness.evaluated_at else None,
            "warnings": self.safety.warnings,
            "errors": self.safety.errors,
        }

    def to_telemetry_dict(self, *, sequence: int | None = None) -> dict[str, object]:
        """Return the compact Phase 16B telemetry shape for UI runtime truth."""

        warnings = tuple(
            item
            for item in (
                *self.input.warnings,
                *self.pipeline.warnings,
                *self.output.warnings,
                *self.safety.warnings,
            )
            if item
        )
        errors = tuple(
            item
            for item in (
                *self.input.errors,
                *self.pipeline.errors,
                *self.output.errors,
                *self.safety.errors,
            )
            if item
        )
        age_ms = None
        if self.input.sample_age_seconds is not None:
            age_ms = int(round(max(0.0, self.input.sample_age_seconds) * 1000.0))
        frame_id = f"runtime-frame-{sequence}" if sequence is not None else f"runtime-frame-{int(self.created_at.timestamp() * 1000)}"
        return {
            "schema_version": "helmforge.runtime_frame.v1",
            "frame_id": frame_id,
            "sequence": sequence,
            "generated_at": self.created_at.isoformat(),
            "input_source": self.input.source.value,
            "input_status": self.input.sample_status,
            "input_device": self.input.device_name,
            "input_sample_age_ms": age_ms,
            "input_stale": self.input.stale,
            "pipeline_status": self.status.value,
            "active_modes": list(self.pipeline.active_modes),
            "active_rule_count": self.pipeline.active_rules_count,
            "active_rule_names": list(self.pipeline.active_rules[:8]),
            "final_output_axes": {axis.axis_name: axis.value for axis in self.output_intent.axes},
            "output_intent_ready": bool(self.output_intent.axes),
            "output_backend": self.output.virtual_output_backend,
            "output_verification_status": self.output.output_verification_status,
            "output_loop_state": self.output.output_loop_state,
            "last_output_write_status": self.output.last_write_status,
            "output_verified": self.output.output_verified,
            "full_live_runtime_ready": self.readiness.full_live_runtime_ready,
            "ready_state": self.readiness.ready_state,
            "runtime_truth": self.safety.runtime_truth,
            "blocked_reason": self.readiness.blocked_reason,
            "input_verified_for_runtime": self.proof.input_verified_for_runtime,
            "output_verified_for_runtime": self.proof.output_verified_for_runtime,
            "output_loop_enabled": self.proof.output_loop_enabled,
            "output_loop_running": self.proof.output_loop_running,
            "output_loop_safety_stopped": self.proof.output_loop_safety_stopped,
            "pipeline_ready": self.proof.pipeline_ready,
            "verified_runtime_candidate": self.proof.verified_runtime_candidate,
            "input_proof": self.readiness.input_proof,
            "pipeline_proof": self.readiness.pipeline_proof,
            "output_proof": self.readiness.output_proof,
            "telemetry_proof": self.readiness.telemetry_proof,
            "safety_proof": self.readiness.safety_proof,
            "fake_or_real_path": self.readiness.fake_or_real_path,
            "evaluated_at": self.readiness.evaluated_at.isoformat() if self.readiness.evaluated_at else None,
            "proof_summary": self.readiness.proof_summary,
            "warnings": list(warnings),
            "errors": list(errors),
        }


class FullLiveRuntimeReadyEvaluator:
    """Central deterministic gate for the final Phase 16 readiness truth."""

    def evaluate(
        self,
        *,
        input_summary: RuntimeInputSummary,
        pipeline_summary: RuntimePipelineResult,
        output_truth: RuntimeOutputTruth,
        proof: RuntimeProofState,
        output_intent_ready: bool,
        telemetry_fresh: bool = True,
        evaluated_at: datetime | None = None,
    ) -> RuntimeReadinessGateResult:
        input_proof = _input_proof(input_summary, proof.input_verified_for_runtime)
        pipeline_proof = "ok" if proof.pipeline_ready else "blocked_pipeline_error"
        output_proof = _output_proof(output_truth)
        telemetry_proof = "fresh" if telemetry_fresh else "stale"
        fake_or_real_path = _fake_or_real_path(input_summary, output_truth)
        safety_proof = _safety_proof(input_summary, pipeline_summary, output_truth)
        blocked_reason = _readiness_blocked_reason(
            input_summary=input_summary,
            pipeline_summary=pipeline_summary,
            output_truth=output_truth,
            proof=proof,
            output_intent_ready=output_intent_ready,
            telemetry_fresh=telemetry_fresh,
            fake_or_real_path=fake_or_real_path,
        )
        full_ready = not blocked_reason
        ready_state = _ready_state(full_ready, blocked_reason, input_summary, fake_or_real_path)
        errors = tuple(item for item in (*input_summary.errors, *pipeline_summary.errors, *output_truth.errors) if item)
        warnings = tuple(item for item in (*input_summary.warnings, *pipeline_summary.warnings, *output_truth.warnings) if item)
        return RuntimeReadinessGateResult(
            full_live_runtime_ready=full_ready,
            ready_state=ready_state,
            blocked_reason=blocked_reason,
            input_proof=input_proof,
            pipeline_proof=pipeline_proof,
            output_proof=output_proof,
            telemetry_proof=telemetry_proof,
            safety_proof=safety_proof,
            fake_or_real_path=fake_or_real_path,
            proof_summary=_readiness_summary(
                input_proof=input_proof,
                pipeline_proof=pipeline_proof,
                output_proof=output_proof,
                output_loop_state=output_truth.output_loop_state,
                telemetry_proof=telemetry_proof,
                safety_proof=safety_proof,
                full_ready=full_ready,
                blocked_reason=blocked_reason,
                legacy_summary=proof.proof_summary,
            ),
            warnings=warnings,
            errors=errors,
            evaluated_at=evaluated_at,
        )


def evaluate_full_live_runtime_ready(
    *,
    input_summary: RuntimeInputSummary,
    pipeline_summary: RuntimePipelineResult,
    output_truth: RuntimeOutputTruth,
    proof: RuntimeProofState,
    output_intent_ready: bool,
    telemetry_fresh: bool = True,
    evaluated_at: datetime | None = None,
) -> RuntimeReadinessGateResult:
    return FullLiveRuntimeReadyEvaluator().evaluate(
        input_summary=input_summary,
        pipeline_summary=pipeline_summary,
        output_truth=output_truth,
        proof=proof,
        output_intent_ready=output_intent_ready,
        telemetry_fresh=telemetry_fresh,
        evaluated_at=evaluated_at,
    )


class RuntimeOrchestrator:
    """Coordinates input, workspace signal processing, output intent, and guarded output-loop truth."""

    def __init__(
        self,
        *,
        workspace: WorkspaceConfig | None = None,
        config: RuntimeOrchestratorConfig | None = None,
        runtime_status: RuntimePreflightStatus | None = None,
        physical_input_snapshot: PhysicalInputSnapshot | None = None,
        virtual_output_backend: VirtualOutputBackend | None = None,
        virtual_output_verification: VirtualOutputVerificationResult | None = None,
        virtual_output_loop: VirtualOutputWriteLoop | None = None,
        clock=None,
    ) -> None:
        self._workspace = workspace or create_default_workspace()
        self._config = config or RuntimeOrchestratorConfig()
        self._runtime_status = runtime_status or simulation_fallback_status()
        self._physical_input_snapshot = physical_input_snapshot
        self._virtual_output_backend = virtual_output_backend or MissingVirtualOutputBackend()
        self._virtual_output_verification = virtual_output_verification
        self._virtual_output_loop = virtual_output_loop
        self._clock = clock
        self._pipeline = WorkspaceSignalPipeline(self._workspace)
        self._pipeline_state: SignalPipelineState = self._pipeline.initial_state()
        self._simulation = SimulatedRuntime(
            deterministic=self._config.deterministic_simulation,
            workspace=self._workspace,
        )

    def build_frame(self) -> RuntimeFrame:
        now = self._now()
        input_summary, raw_axes, _button_states, _hat_state, blocked_reason, fallback_reason = self._resolve_input(now)
        return self._build_frame_from_raw_axes(
            now=now,
            input_summary=input_summary,
            raw_axes=raw_axes,
            blocked_reason=blocked_reason,
            fallback_reason=fallback_reason,
            runtime_status=self._runtime_status,
        )

    def build_frame_from_runtime_snapshot(
        self,
        snapshot: RuntimeSnapshot,
        *,
        runtime_status: RuntimePreflightStatus | None = None,
        sequence: int | None = None,
    ) -> RuntimeFrame:
        now = self._now()
        frame_runtime_status = runtime_status or snapshot.runtime_status or self._runtime_status
        source = RuntimeFrameSource.SIMULATION if snapshot.simulated else RuntimeFrameSource.PHYSICAL
        input_summary = RuntimeInputSummary(
            requested_source=source,
            source=source,
            device_name="Simulation" if snapshot.simulated else "Physical input",
            backend_name="simulated_runtime" if snapshot.simulated else "physical_input_backend",
            sampled_at=None,
            sample_age_seconds=None,
            axis_count=len(snapshot.raw_axis_values),
            button_count=len(snapshot.button_states),
            hat_count=1,
            sample_status="simulation" if snapshot.simulated else "physical",
            sample_source=source.value,
        )
        return self._build_frame_from_raw_axes(
            now=now,
            input_summary=input_summary,
            raw_axes=dict(snapshot.raw_axis_values),
            blocked_reason="",
            fallback_reason="",
            runtime_status=frame_runtime_status,
        )

    def _build_frame_from_raw_axes(
        self,
        *,
        now: datetime,
        input_summary: RuntimeInputSummary,
        raw_axes: Mapping[str, float],
        blocked_reason: str,
        fallback_reason: str,
        runtime_status: RuntimePreflightStatus,
    ) -> RuntimeFrame:
        pipeline_blocked_reason = blocked_reason
        try:
            pipeline_result = self._pipeline.process(
                raw_axes,
                mode_state=ModeState(),
                state=self._pipeline_state,
            )
            self._pipeline_state = pipeline_result.state
            pipeline_summary = _pipeline_summary(self._workspace, pipeline_result)
        except Exception as exc:  # pragma: no cover - exercised through injected pipeline tests
            pipeline_blocked_reason = "blocked_pipeline_error"
            pipeline_summary = _pipeline_error_summary(self._workspace, raw_axes, exc)
        output_intent = build_recovered_virtual_output_intent(
            pipeline_summary.final_output_values,
            source=f"runtime_orchestrator_{input_summary.source.value}",
            timestamp=now,
        )

        loop_snapshot = _disabled_loop_snapshot()
        if self._virtual_output_loop is not None:
            if self._config.allow_output_loop_tick and _can_tick_output_loop(input_summary, pipeline_summary):
                loop_snapshot = self._virtual_output_loop.tick(output_intent)
            else:
                loop_snapshot = self._virtual_output_loop.snapshot()

        diagnostics = build_virtual_output_diagnostics(
            backend=self._virtual_output_backend,
            verification=self._virtual_output_verification,
        )
        output_truth = _output_truth(diagnostics, loop_snapshot)
        proof = _proof_state(input_summary, pipeline_summary, output_truth, pipeline_blocked_reason)
        readiness = evaluate_full_live_runtime_ready(
            input_summary=input_summary,
            pipeline_summary=pipeline_summary,
            output_truth=output_truth,
            proof=proof,
            output_intent_ready=bool(output_intent.axes),
            telemetry_fresh=True,
            evaluated_at=now,
        )
        status = _frame_status(input_summary, pipeline_summary, output_truth, proof, pipeline_blocked_reason, readiness)
        safety = _safety_state(
            status=status,
            runtime_status=runtime_status,
            fallback_reason=fallback_reason,
            input_summary=input_summary,
            output_truth=output_truth,
            proof=proof,
            readiness=readiness,
        )
        return RuntimeFrame(
            created_at=now,
            status=status,
            input=input_summary,
            pipeline=pipeline_summary,
            output_intent=output_intent,
            output=output_truth,
            proof=proof,
            safety=safety,
            readiness=readiness,
        )

    def _resolve_input(
        self,
        now: datetime,
    ) -> tuple[RuntimeInputSummary, dict[str, float], dict[str, bool], str, str, str]:
        if self._config.preferred_input_source is RuntimeFrameSource.PHYSICAL:
            physical = self._physical_input_summary(now)
            if physical is not None and not physical.stale and not physical.error:
                return (
                    physical,
                    _raw_axes_from_physical_snapshot(self._physical_input_snapshot),
                    _buttons_from_physical_snapshot(self._physical_input_snapshot),
                    _hat_from_physical_snapshot(self._physical_input_snapshot),
                    "",
                    "",
                )
            if not self._config.allow_simulation_fallback:
                reason = "blocked_missing_device"
                if physical is not None and physical.stale:
                    reason = "blocked_stale_input"
                elif physical is not None and physical.error:
                    reason = "blocked_error"
                return (
                    physical or _unavailable_input_summary(self._config.preferred_input_source),
                    {axis: 0.0 for axis in AXIS_NAMES},
                    {button: False for button in BUTTON_NAMES},
                    HAT_CENTERED,
                    reason,
                    "Simulation fallback disabled by orchestrator config.",
                )
            blocked = "blocked_missing_device"
            fallback = "Physical input unavailable; simulation fallback active."
            errors: tuple[str, ...] = ()
            warnings: tuple[str, ...] = ()
            stale = False
            error = False
            if physical is not None:
                stale = physical.stale
                error = physical.error
                warnings = physical.warnings
                errors = physical.errors
                if physical.stale:
                    blocked = "blocked_stale_input"
                    fallback = "Physical input sample is stale; simulation fallback active."
                elif physical.error:
                    blocked = "blocked_error"
                    fallback = "Physical input sample error; simulation fallback active."
            simulation_snapshot = self._simulation.snapshot(runtime_status=self._runtime_status)
            return (
                RuntimeInputSummary(
                    requested_source=RuntimeFrameSource.PHYSICAL,
                    source=RuntimeFrameSource.SIMULATION,
                    device_name="Simulation",
                    backend_name="simulated_runtime",
                    sampled_at=None,
                    sample_age_seconds=None,
                    axis_count=len(simulation_snapshot.raw_axis_values),
                    button_count=len(simulation_snapshot.button_states),
                    hat_count=1,
                    sample_status="simulation_fallback",
                    sample_source="simulation",
                    stale=stale,
                    error=error,
                    warnings=warnings,
                    errors=errors,
                ),
                dict(simulation_snapshot.raw_axis_values),
                dict(simulation_snapshot.button_states),
                simulation_snapshot.hat_state,
                blocked,
                fallback,
            )

        simulation_snapshot = self._simulation.snapshot(runtime_status=self._runtime_status)
        return (
            RuntimeInputSummary(
                requested_source=self._config.preferred_input_source,
                source=RuntimeFrameSource.SIMULATION,
                device_name="Simulation",
                backend_name="simulated_runtime",
                sampled_at=None,
                sample_age_seconds=None,
                axis_count=len(simulation_snapshot.raw_axis_values),
                button_count=len(simulation_snapshot.button_states),
                hat_count=1,
                sample_status="simulation",
                sample_source="simulation",
            ),
            dict(simulation_snapshot.raw_axis_values),
            dict(simulation_snapshot.button_states),
            simulation_snapshot.hat_state,
            "",
            "",
        )

    def _physical_input_summary(self, now: datetime) -> RuntimeInputSummary | None:
        snapshot = self._physical_input_snapshot
        if snapshot is None:
            return None
        age = _sample_age_seconds(snapshot, now)
        stale = age is not None and age > max(0.1, float(self._config.physical_sample_stale_after_seconds))
        error = snapshot.sampling_status is PhysicalInputSamplingStatus.ERROR or bool(snapshot.errors)
        active = snapshot.sampling_status is PhysicalInputSamplingStatus.ACTIVE and snapshot.sampling_active
        return RuntimeInputSummary(
            requested_source=RuntimeFrameSource.PHYSICAL,
            source=RuntimeFrameSource.PHYSICAL if active and not stale and not error else RuntimeFrameSource.UNAVAILABLE,
            device_name=snapshot.device_name or "Physical input",
            backend_name=snapshot.backend_name,
            sampled_at=snapshot.sampled_at,
            sample_age_seconds=age,
            axis_count=snapshot.axis_count,
            button_count=snapshot.button_count,
            hat_count=snapshot.hat_count,
            sample_status=snapshot.sampling_status.value,
            sample_source=snapshot.sample_source,
            stale=stale,
            error=error,
            warnings=snapshot.warnings,
            errors=snapshot.errors,
        )

    def _now(self) -> datetime:
        if callable(self._clock):
            value = self._clock()
            if isinstance(value, datetime):
                return _ensure_aware(value)
        return datetime.now(timezone.utc)


def _pipeline_summary(workspace: WorkspaceConfig, result: WorkspaceSignalPipelineResult) -> RuntimePipelineResult:
    active_rules = tuple(rule.title for rule in workspace.rules.rules if rule.enabled)
    return RuntimePipelineResult(
        selected_workspace=workspace.product_name,
        active_profile=workspace.active_profile,
        active_modes=(),
        active_rules=active_rules,
        active_rules_count=len(active_rules),
        raw_axis_values=result.raw_axis_values,
        final_output_values=result.final_output_values,
        stage_names_by_axis={
            axis_name: tuple(stage.stage_name for stage in axis_result.stages)
            for axis_name, axis_result in result.axis_results.items()
        },
    )


def _pipeline_error_summary(workspace: WorkspaceConfig, raw_axes: Mapping[str, float], exc: Exception) -> RuntimePipelineResult:
    active_rules = tuple(rule.title for rule in workspace.rules.rules if rule.enabled)
    return RuntimePipelineResult(
        selected_workspace=workspace.product_name,
        active_profile=workspace.active_profile,
        active_modes=(),
        active_rules=active_rules,
        active_rules_count=len(active_rules),
        raw_axis_values={name: float(raw_axes.get(name, 0.0)) for name in AXIS_NAMES},
        final_output_values={name: 0.0 for name in AXIS_NAMES},
        stage_names_by_axis={name: ("pipeline_error",) for name in AXIS_NAMES},
        errors=(f"blocked_pipeline_error: {exc}",),
    )


def _output_truth(
    diagnostics: VirtualOutputDiagnostics,
    loop_snapshot: VirtualOutputLoopSnapshot,
) -> RuntimeOutputTruth:
    loop_safety_stopped = loop_snapshot.state is VirtualOutputWriteLoopState.SAFETY_STOPPED or (
        loop_snapshot.safety_stop_reason not in {"", "None"}
    )
    return RuntimeOutputTruth(
        virtual_output_backend=diagnostics.virtual_output_backend,
        output_verification_status=diagnostics.output_verification_status,
        output_loop_state=loop_snapshot.state.value,
        output_loop_enabled=loop_snapshot.enabled,
        output_loop_running=loop_snapshot.state is VirtualOutputWriteLoopState.RUNNING,
        output_loop_safety_stopped=loop_safety_stopped,
        last_write_status=loop_snapshot.output_write_status,
        write_count=loop_snapshot.write_count,
        fake_output_verified=diagnostics.fake_output_verified,
        real_output_verified=diagnostics.real_output_verified,
        output_verified=diagnostics.output_verified,
        full_live_runtime_ready=False,
    )


def _proof_state(
    input_summary: RuntimeInputSummary,
    pipeline_summary: RuntimePipelineResult,
    output_truth: RuntimeOutputTruth,
    blocked_reason: str,
) -> RuntimeProofState:
    input_verified = _input_verified_for_runtime(input_summary)
    pipeline_ready = not pipeline_summary.errors
    output_verified = output_truth.real_output_verified
    output_loop_running = output_truth.output_loop_running
    output_loop_safety_stopped = output_truth.output_loop_safety_stopped
    candidate = (
        input_verified
        and pipeline_ready
        and output_verified
        and output_truth.output_loop_enabled
        and output_loop_running
        and not output_loop_safety_stopped
        and output_truth.write_count > 0
    )
    runtime_block = _runtime_blocked_reason(input_summary, pipeline_summary, output_truth, blocked_reason)
    input_proof = _input_proof(input_summary, input_verified)
    pipeline_proof = "ok" if pipeline_ready else "blocked_pipeline_error"
    output_proof = _output_proof(output_truth)
    loop_proof = "running" if output_loop_running else ("enabled" if output_truth.output_loop_enabled else "disabled")
    summary_parts = [
        f"input={input_proof.replace(' ', '_')}",
        f"pipeline={pipeline_proof}",
        f"output={output_proof.replace(' ', '_')}",
        f"loop={loop_proof}",
        "ready=candidate" if candidate else "ready=false",
    ]
    if candidate:
        summary_parts.append("candidate=true")
        summary_parts.append("policy=phase16d_final_gate")
    elif runtime_block:
        summary_parts.append(f"blocked={runtime_block}")
    return RuntimeProofState(
        input_verified_for_runtime=input_verified,
        input_proof=input_proof,
        pipeline_ready=pipeline_ready,
        pipeline_proof=pipeline_proof,
        output_verified_for_runtime=output_verified,
        output_proof=output_proof,
        output_loop_enabled=output_truth.output_loop_enabled,
        output_loop_running=output_loop_running,
        output_loop_safety_stopped=output_loop_safety_stopped,
        verified_runtime_candidate=candidate,
        proof_summary="; ".join(summary_parts),
    )


def _frame_status(
    input_summary: RuntimeInputSummary,
    pipeline_summary: RuntimePipelineResult,
    output_truth: RuntimeOutputTruth,
    proof: RuntimeProofState,
    blocked_reason: str,
    readiness: RuntimeReadinessGateResult,
) -> RuntimeFrameStatus:
    if readiness.full_live_runtime_ready:
        return RuntimeFrameStatus.FULL_LIVE_RUNTIME_READY
    if readiness.blocked_reason == RuntimeFrameStatus.BLOCKED_FAKE_PATH_ONLY.value:
        return RuntimeFrameStatus.BLOCKED_FAKE_PATH_ONLY
    if readiness.blocked_reason == RuntimeFrameStatus.BLOCKED_TELEMETRY_STALE.value:
        return RuntimeFrameStatus.BLOCKED_TELEMETRY_STALE
    runtime_block = _runtime_blocked_reason(input_summary, pipeline_summary, output_truth, blocked_reason)
    if proof.verified_runtime_candidate:
        return RuntimeFrameStatus.VERIFIED_RUNTIME_CANDIDATE
    if runtime_block == "blocked_pipeline_error":
        return RuntimeFrameStatus.BLOCKED_PIPELINE_ERROR
    if runtime_block == "blocked_stale_input":
        return RuntimeFrameStatus.BLOCKED_STALE_INPUT
    if runtime_block == "blocked_input_error":
        return RuntimeFrameStatus.BLOCKED_INPUT_ERROR
    if runtime_block == "blocked_error":
        return RuntimeFrameStatus.BLOCKED_ERROR
    if runtime_block == "blocked_missing_input":
        return RuntimeFrameStatus.BLOCKED_MISSING_INPUT
    if runtime_block == "blocked_output_safety_stop":
        return RuntimeFrameStatus.BLOCKED_OUTPUT_SAFETY_STOP
    if output_truth.output_loop_state == VirtualOutputWriteLoopState.RUNNING.value and output_truth.fake_output_verified:
        return RuntimeFrameStatus.OUTPUT_LOOP_FAKE_RUNNING
    if output_truth.output_loop_state == VirtualOutputWriteLoopState.RUNNING.value and output_truth.real_output_verified:
        if proof.input_verified_for_runtime:
            return RuntimeFrameStatus.OUTPUT_LOOP_RUNNING_REAL
        return RuntimeFrameStatus.OUTPUT_LOOP_REAL_RUNNING_UNVERIFIED_INPUT
    if runtime_block == "blocked_unverified_output":
        return RuntimeFrameStatus.BLOCKED_UNVERIFIED_OUTPUT
    if runtime_block == "blocked_output_loop_disabled":
        return RuntimeFrameStatus.BLOCKED_OUTPUT_LOOP_DISABLED
    if input_summary.source is RuntimeFrameSource.PHYSICAL:
        if output_truth.real_output_verified:
            return RuntimeFrameStatus.PHYSICAL_INPUT_READY_OUTPUT_VERIFIED
        return RuntimeFrameStatus.PHYSICAL_INPUT_READY_OUTPUT_UNVERIFIED
    if blocked_reason == "blocked_stale_input":
        return RuntimeFrameStatus.SIMULATED_OUTPUT_INTENT_READY
    if blocked_reason == "blocked_error":
        return RuntimeFrameStatus.SIMULATED_OUTPUT_INTENT_READY
    return RuntimeFrameStatus.SIMULATED_OUTPUT_INTENT_READY


def _safety_state(
    *,
    status: RuntimeFrameStatus,
    runtime_status: RuntimePreflightStatus,
    fallback_reason: str,
    input_summary: RuntimeInputSummary,
    output_truth: RuntimeOutputTruth,
    proof: RuntimeProofState,
    readiness: RuntimeReadinessGateResult,
) -> RuntimeSafetyState:
    warnings = tuple(item for item in (*input_summary.warnings, *readiness.warnings) if item)
    errors = tuple(
        item
        for item in (*input_summary.errors, *(() if proof.pipeline_ready else ("blocked_pipeline_error",)), *readiness.errors)
        if item
    )
    blocked_reason = readiness.blocked_reason
    runtime_truth = blocked_reason or status.value
    if readiness.full_live_runtime_ready:
        runtime_truth = RuntimeFrameStatus.FULL_LIVE_RUNTIME_READY.value
    elif proof.verified_runtime_candidate and readiness.ready_state == "candidate":
        runtime_truth = RuntimeFrameStatus.VERIFIED_RUNTIME_CANDIDATE.value
    elif output_truth.output_verified and input_summary.source is RuntimeFrameSource.PHYSICAL and not blocked_reason:
        runtime_truth = RuntimeFrameStatus.OUTPUT_VERIFIED_RUNTIME_NOT_ENABLED.value
    if not blocked_reason and runtime_status.truth.value:
        blocked_reason = ""
    return RuntimeSafetyState(
        runtime_truth=runtime_truth,
        blocked_reason=blocked_reason,
        fallback_reason=fallback_reason,
        warnings=warnings,
        errors=errors,
        full_live_runtime_ready=readiness.full_live_runtime_ready,
    )


def _runtime_blocked_reason(
    input_summary: RuntimeInputSummary,
    pipeline_summary: RuntimePipelineResult,
    output_truth: RuntimeOutputTruth,
    blocked_reason: str,
) -> str:
    if pipeline_summary.errors:
        return "blocked_pipeline_error"
    if blocked_reason == "blocked_stale_input" or input_summary.stale:
        return "blocked_stale_input"
    if blocked_reason == "blocked_input_error":
        return "blocked_input_error"
    if blocked_reason == "blocked_error" or input_summary.error:
        return "blocked_error"
    if blocked_reason in {"blocked_missing_device", "blocked_missing_input"} and input_summary.source is RuntimeFrameSource.UNAVAILABLE:
        return "blocked_missing_input"
    if output_truth.output_loop_safety_stopped:
        return "blocked_output_safety_stop"
    if _input_verified_for_runtime(input_summary) and not output_truth.real_output_verified:
        return "blocked_unverified_output"
    if _input_verified_for_runtime(input_summary) and output_truth.real_output_verified and not output_truth.output_loop_running:
        return "blocked_output_loop_disabled"
    return ""


def _readiness_blocked_reason(
    *,
    input_summary: RuntimeInputSummary,
    pipeline_summary: RuntimePipelineResult,
    output_truth: RuntimeOutputTruth,
    proof: RuntimeProofState,
    output_intent_ready: bool,
    telemetry_fresh: bool,
    fake_or_real_path: str,
) -> str:
    if not telemetry_fresh:
        return RuntimeFrameStatus.BLOCKED_TELEMETRY_STALE.value
    if input_summary.stale:
        return RuntimeFrameStatus.BLOCKED_STALE_INPUT.value
    if input_summary.error:
        return RuntimeFrameStatus.BLOCKED_INPUT_ERROR.value
    if input_summary.source is RuntimeFrameSource.SIMULATION:
        return "simulation_pipeline_only"
    if not proof.input_verified_for_runtime:
        return RuntimeFrameStatus.BLOCKED_MISSING_INPUT.value
    if pipeline_summary.errors or not proof.pipeline_ready:
        return RuntimeFrameStatus.BLOCKED_PIPELINE_ERROR.value
    if not output_intent_ready:
        return RuntimeFrameStatus.BLOCKED_PIPELINE_ERROR.value
    if output_truth.output_loop_safety_stopped:
        return RuntimeFrameStatus.BLOCKED_OUTPUT_SAFETY_STOP.value
    if fake_or_real_path == "fake_test":
        return RuntimeFrameStatus.BLOCKED_FAKE_PATH_ONLY.value
    if _output_backend_missing(output_truth):
        return RuntimeFrameStatus.BLOCKED_MISSING_OUTPUT.value
    if not output_truth.real_output_verified:
        return RuntimeFrameStatus.BLOCKED_UNVERIFIED_OUTPUT.value
    if not output_truth.output_loop_enabled or not output_truth.output_loop_running or output_truth.write_count <= 0:
        return RuntimeFrameStatus.BLOCKED_OUTPUT_LOOP_DISABLED.value
    if output_truth.errors:
        return RuntimeFrameStatus.BLOCKED_ERROR.value
    return ""


def _output_backend_missing(output_truth: RuntimeOutputTruth) -> bool:
    backend = output_truth.virtual_output_backend.lower()
    status = output_truth.output_verification_status.lower()
    return (
        "missing" in backend
        or status in {"backend_missing", "dependency_missing", "device_missing", "device_busy", "acquisition_failed"}
    )


def _fake_or_real_path(input_summary: RuntimeInputSummary, output_truth: RuntimeOutputTruth) -> str:
    backend = output_truth.virtual_output_backend.lower()
    if input_summary.sample_source == "fake" or output_truth.fake_output_verified or "fake" in backend:
        return "fake_test"
    if input_summary.source is RuntimeFrameSource.PHYSICAL or output_truth.real_output_verified:
        return "real"
    if input_summary.source is RuntimeFrameSource.SIMULATION:
        return "simulation"
    return "unavailable"


def _safety_proof(
    input_summary: RuntimeInputSummary,
    pipeline_summary: RuntimePipelineResult,
    output_truth: RuntimeOutputTruth,
) -> str:
    if output_truth.output_loop_safety_stopped:
        return "safety_stop"
    if input_summary.error or pipeline_summary.errors or output_truth.errors:
        return "error"
    if input_summary.stale:
        return "stale_input"
    return "ok"


def _ready_state(full_ready: bool, blocked_reason: str, input_summary: RuntimeInputSummary, fake_or_real_path: str) -> str:
    if full_ready:
        return "ready"
    if fake_or_real_path == "fake_test":
        return "fake_test"
    if blocked_reason == "simulation_pipeline_only" or input_summary.source is RuntimeFrameSource.SIMULATION:
        return "simulated"
    if blocked_reason:
        return "blocked"
    return "candidate"


def _readiness_summary(
    *,
    input_proof: str,
    pipeline_proof: str,
    output_proof: str,
    output_loop_state: str,
    telemetry_proof: str,
    safety_proof: str,
    full_ready: bool,
    blocked_reason: str,
    legacy_summary: str,
) -> str:
    parts = [
        f"Input: {input_proof}",
        f"Pipeline: {pipeline_proof}",
        f"Output: {output_proof}",
        f"Output loop: {output_loop_state}",
        f"Telemetry: {telemetry_proof}",
        f"Safety: {safety_proof}",
        f"Ready: {str(full_ready).lower()}",
    ]
    if blocked_reason:
        parts.append(f"Blocked: {blocked_reason}")
    if legacy_summary:
        parts.append(legacy_summary)
    return "; ".join(parts)


def _input_verified_for_runtime(input_summary: RuntimeInputSummary) -> bool:
    return (
        input_summary.source is RuntimeFrameSource.PHYSICAL
        and not input_summary.stale
        and not input_summary.error
        and input_summary.sample_status == PhysicalInputSamplingStatus.ACTIVE.value
        and input_summary.axis_count > 0
    )


def _input_proof(input_summary: RuntimeInputSummary, verified: bool) -> str:
    if verified:
        return "fresh physical sample"
    if input_summary.stale:
        return "stale physical sample"
    if input_summary.error:
        return "input error"
    if input_summary.source is RuntimeFrameSource.SIMULATION:
        return "simulation fallback"
    if input_summary.source is RuntimeFrameSource.UNAVAILABLE:
        return "input unavailable"
    return input_summary.sample_status or "unavailable"


def _output_proof(output_truth: RuntimeOutputTruth) -> str:
    if output_truth.real_output_verified:
        return "guarded real verification"
    if output_truth.fake_output_verified:
        return "fake verified test only"
    if output_truth.output_verification_status == "not_attempted":
        return "unverified"
    return output_truth.output_verification_status or "unverified"


def _can_tick_output_loop(input_summary: RuntimeInputSummary, pipeline_summary: RuntimePipelineResult) -> bool:
    if pipeline_summary.errors:
        return False
    return not input_summary.stale and not input_summary.error and input_summary.source is not RuntimeFrameSource.UNAVAILABLE


def _raw_axes_from_physical_snapshot(snapshot: PhysicalInputSnapshot | None) -> dict[str, float]:
    values = {axis: 0.0 for axis in AXIS_NAMES}
    if snapshot is None:
        return values
    for axis in snapshot.axes:
        logical = axis.logical_name or axis.raw_name
        if logical in values:
            values[logical] = float(axis.normalized_value)
    return values


def _buttons_from_physical_snapshot(snapshot: PhysicalInputSnapshot | None) -> dict[str, bool]:
    values = {button: False for button in BUTTON_NAMES}
    if snapshot is None:
        return values
    for button in snapshot.buttons:
        name = f"B{button.button_index}"
        if name in values:
            values[name] = bool(button.pressed)
    return values


def _hat_from_physical_snapshot(snapshot: PhysicalInputSnapshot | None) -> str:
    if snapshot is None or not snapshot.hats:
        return HAT_CENTERED
    return snapshot.hats[0].normalized_direction


def _sample_age_seconds(snapshot: PhysicalInputSnapshot, now: datetime) -> float | None:
    if snapshot.sampled_at is None:
        return None
    sampled_at = _ensure_aware(snapshot.sampled_at)
    return max(0.0, (_ensure_aware(now) - sampled_at).total_seconds())


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _unavailable_input_summary(requested_source: RuntimeFrameSource) -> RuntimeInputSummary:
    return RuntimeInputSummary(
        requested_source=requested_source,
        source=RuntimeFrameSource.UNAVAILABLE,
        device_name="Unavailable",
        backend_name="unknown",
        sampled_at=None,
        sample_age_seconds=None,
        axis_count=0,
        button_count=0,
        hat_count=0,
        sample_status="unavailable",
        sample_source="unavailable",
    )


def _disabled_loop_snapshot() -> VirtualOutputLoopSnapshot:
    return VirtualOutputLoopSnapshot(
        state=VirtualOutputWriteLoopState.DISABLED,
        enabled=False,
        backend_name="None",
        selected_output_device="None",
        verification_status="not_attempted",
        output_write_status="Not active",
        write_rate_hz=0.0,
    )
