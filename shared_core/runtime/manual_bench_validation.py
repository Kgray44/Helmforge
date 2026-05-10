from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Mapping
from uuid import uuid4


DEFAULT_AXIS_THRESHOLD = 0.2
DEFAULT_TELEMETRY_STALE_SECONDS = 5.0


class ManualValidationStepStatus(str, Enum):
    NOT_STARTED = "not_started"
    WAITING_FOR_ACTION = "waiting_for_action"
    OBSERVING = "observing"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ManualValidationStep:
    step_id: str
    title: str
    instruction: str
    expected_signal: str
    pass_criteria: str
    status: ManualValidationStepStatus = ManualValidationStepStatus.NOT_STARTED
    observed_signal: str = ""
    failure_reason: str = ""
    telemetry_evidence: Mapping[str, object] = field(default_factory=dict)
    operator_note: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    kind: str = "informational"
    target: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "instruction": self.instruction,
            "expected_signal": self.expected_signal,
            "observed_signal": self.observed_signal,
            "status": self.status.value,
            "pass_criteria": self.pass_criteria,
            "failure_reason": self.failure_reason,
            "telemetry_evidence": dict(self.telemetry_evidence),
            "operator_note": self.operator_note,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "kind": self.kind,
            "target": self.target,
        }


@dataclass
class ManualValidationSession:
    session_id: str
    started_at: datetime
    mode: str = "manual"
    target_hardware: str = "Thrustmaster T.Flight HOTAS One"
    bridge_source: str = "unavailable"
    workspace_hash: str = ""
    steps: list[ManualValidationStep] = field(default_factory=list)
    completed_at: datetime | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    axis_threshold: float = DEFAULT_AXIS_THRESHOLD
    telemetry_stale_seconds: float = DEFAULT_TELEMETRY_STALE_SECONDS
    _baseline: dict[str, object] = field(default_factory=dict)
    _button_seen_pressed: dict[str, bool] = field(default_factory=dict)

    def step(self, step_id: str) -> ManualValidationStep:
        for item in self.steps:
            if item.step_id == step_id:
                return item
        raise KeyError(step_id)

    @property
    def current_step(self) -> ManualValidationStep | None:
        for step in self.steps:
            if step.status in {
                ManualValidationStepStatus.WAITING_FOR_ACTION,
                ManualValidationStepStatus.OBSERVING,
            }:
                return step
        for step in self.steps:
            if step.status is ManualValidationStepStatus.NOT_STARTED:
                return step
        return None

    def start_step(self, step_id: str) -> ManualValidationStep:
        step = self.step(step_id)
        updated = replace(
            step,
            status=ManualValidationStepStatus.OBSERVING,
            started_at=step.started_at or _now(),
        )
        self._replace_step(updated)
        self._baseline.pop(step_id, None)
        self._button_seen_pressed.pop(step_id, None)
        return updated

    def start_next(self) -> ManualValidationStep | None:
        step = self.current_step
        if step is None:
            return None
        if step.status is ManualValidationStepStatus.NOT_STARTED:
            return self.start_step(step.step_id)
        return step

    def mark_step(
        self,
        step_id: str,
        status: ManualValidationStepStatus,
        *,
        observed_signal: str = "",
        failure_reason: str = "",
    ) -> ManualValidationStep:
        step = self.step(step_id)
        updated = replace(
            step,
            status=status,
            observed_signal=observed_signal or step.observed_signal,
            failure_reason=failure_reason,
            completed_at=_now() if status in _TERMINAL_STATUSES else step.completed_at,
        )
        self._replace_step(updated)
        return updated

    def record_operator_note(self, step_id: str, note: str) -> ManualValidationStep:
        step = self.step(step_id)
        updated = replace(step, operator_note=note)
        self._replace_step(updated)
        return updated

    def evaluate_current_step(self, telemetry: Mapping[str, object]) -> ManualValidationStep | None:
        step = self.current_step
        if step is None:
            return None
        if step.status is ManualValidationStepStatus.NOT_STARTED:
            step = self.start_step(step.step_id)
        evaluated = self._evaluate_step(step, telemetry)
        self.bridge_source = str(telemetry.get("source_label") or self.bridge_source)
        workspace = telemetry.get("bridge_workspace")
        if isinstance(workspace, Mapping):
            self.workspace_hash = str(workspace.get("workspace_hash") or self.workspace_hash)
        self._replace_step(evaluated)
        return evaluated

    def summary(self) -> dict[str, object]:
        statuses = [step.status for step in self.steps]
        failed_count = sum(status is ManualValidationStepStatus.FAILED for status in statuses)
        blocked_count = sum(status is ManualValidationStepStatus.BLOCKED for status in statuses)
        passed_count = sum(status is ManualValidationStepStatus.PASSED for status in statuses)
        skipped_count = sum(status is ManualValidationStepStatus.SKIPPED for status in statuses)
        terminal_count = sum(status in _TERMINAL_STATUSES for status in statuses)
        if failed_count:
            overall = "failed"
        elif blocked_count:
            overall = "blocked"
        elif terminal_count == len(statuses):
            overall = "passed"
        else:
            overall = "in_progress"
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "mode": self.mode,
            "target_hardware": self.target_hardware,
            "bridge_source": self.bridge_source,
            "workspace_hash": self.workspace_hash,
            "overall_status": overall,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "blocked_count": blocked_count,
            "skipped_count": skipped_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "steps": [step.to_dict() for step in self.steps],
        }

    def _evaluate_step(self, step: ManualValidationStep, telemetry: Mapping[str, object]) -> ManualValidationStep:
        evidence: dict[str, object] = {}
        if step.kind == "telemetry":
            age = _float(telemetry.get("age_seconds"))
            source = str(telemetry.get("source_label") or "Simulation Fallback")
            evidence = {"source": source, "age_seconds": age}
            if source == "Simulation Fallback":
                return _blocked(step, "Simulation fallback is active; Bridge telemetry is not live.", evidence)
            if age is not None and age > self.telemetry_stale_seconds:
                return _blocked(step, "Telemetry is stale.", evidence)
            return _passed(step, f"{source} fresh", evidence)
        if step.kind == "config":
            workspace = telemetry.get("bridge_workspace")
            bridge_hash = str(workspace.get("workspace_hash") or "") if isinstance(workspace, Mapping) else ""
            ui_hash = str(telemetry.get("ui_workspace_hash") or "")
            evidence = {"bridge_workspace_hash": bridge_hash, "ui_workspace_hash": ui_hash}
            if bridge_hash and ui_hash and bridge_hash == ui_hash:
                return _passed(step, "Bridge/UI workspace hashes match.", evidence)
            return _blocked(step, "Bridge/UI workspace hashes do not match.", evidence)
        if step.kind == "hotas":
            discovery = telemetry.get("device_discovery")
            fidelity = telemetry.get("physical_input_fidelity")
            matched = bool(discovery.get("matched") or discovery.get("status") == "supported_device_detected") if isinstance(discovery, Mapping) else False
            mapping_status = str(fidelity.get("mapping_status") or "") if isinstance(fidelity, Mapping) else ""
            evidence = {"matched": matched, "mapping_status": mapping_status}
            if matched and mapping_status in {"ok", "missing_channels"}:
                return _passed(step, "Supported HOTAS detected and physical fidelity is present.", evidence)
            return _blocked(step, "Supported HOTAS or physical input fidelity unavailable.", evidence)
        if step.kind == "axis":
            return self._evaluate_axis(step, telemetry)
        if step.kind == "button":
            return self._evaluate_button(step, telemetry)
        if step.kind == "hat":
            return self._evaluate_hat(step, telemetry)
        if step.kind == "pipeline":
            raw = _mapping(telemetry.get("raw_axes"))
            final = _mapping(telemetry.get("final_axes"))
            runtime_frame = _mapping(telemetry.get("runtime_frame"))
            evidence = {"output_intent_ready": runtime_frame.get("output_intent_ready"), "raw_axes": raw, "final_axes": final}
            if runtime_frame.get("output_intent_ready") and raw and final:
                return _passed(step, "Output intent is present; this is not output write proof.", evidence)
            return _blocked(step, "Output intent telemetry unavailable.", evidence)
        if step.kind == "output":
            output_loop = _mapping(telemetry.get("output_loop_runtime"))
            output_verified = bool(telemetry.get("output_verified")) or bool(output_loop.get("verification_real"))
            evidence = {"output_status": telemetry.get("output_status"), "output_loop_runtime": output_loop, "output_verified": output_verified}
            if output_verified:
                return _passed(step, "Real output verification is reported by telemetry.", evidence)
            return _blocked(step, "Output intent is not output write proof; vJoy detected is not output verification.", evidence)
        if step.kind == "readiness":
            runtime_frame = _mapping(telemetry.get("runtime_frame"))
            full_ready = bool(runtime_frame.get("full_live_runtime_ready"))
            evidence = {"runtime_frame": runtime_frame}
            if full_ready:
                return _passed(step, "Full Live Runtime Ready is proven by runtime_frame.", evidence)
            return _blocked(step, str(runtime_frame.get("blocked_reason") or "Full Live Runtime Ready is not proven."), evidence)
        return replace(step, status=ManualValidationStepStatus.OBSERVING)

    def _evaluate_axis(self, step: ManualValidationStep, telemetry: Mapping[str, object]) -> ManualValidationStep:
        axes = _mapping(telemetry.get("raw_axes"))
        value = _float(axes.get(step.target))
        evidence = {"axis": step.target, "value": value}
        if value is None:
            return _blocked(step, f"{step.target} telemetry unavailable.", evidence)
        baseline = self._baseline.get(step.step_id)
        if baseline is None:
            self._baseline[step.step_id] = value
            return replace(step, status=ManualValidationStepStatus.OBSERVING, observed_signal=f"{step.target} baseline {value:.3f}", telemetry_evidence=evidence)
        delta = abs(value - float(baseline))
        evidence["delta"] = delta
        if delta >= self.axis_threshold:
            return _passed(step, f"{step.target} changed by {delta:.3f}.", evidence)
        return replace(step, status=ManualValidationStepStatus.OBSERVING, observed_signal=f"{step.target} delta {delta:.3f}", telemetry_evidence=evidence)

    def _evaluate_button(self, step: ManualValidationStep, telemetry: Mapping[str, object]) -> ManualValidationStep:
        buttons = _mapping(telemetry.get("buttons"))
        value = buttons.get(step.target)
        evidence = {"button": step.target, "pressed": value}
        if value is None:
            return _blocked(step, f"{step.target} telemetry unavailable.", evidence)
        if bool(value):
            self._button_seen_pressed[step.step_id] = True
            return replace(step, status=ManualValidationStepStatus.OBSERVING, observed_signal=f"{step.target} pressed", telemetry_evidence=evidence)
        if self._button_seen_pressed.get(step.step_id):
            return _passed(step, f"{step.target} pressed and released.", evidence)
        return replace(step, status=ManualValidationStepStatus.OBSERVING, observed_signal=f"{step.target} waiting for press", telemetry_evidence=evidence)

    def _evaluate_hat(self, step: ManualValidationStep, telemetry: Mapping[str, object]) -> ManualValidationStep:
        hats = _mapping(telemetry.get("hats"))
        values = {str(value).lower() for value in hats.values()}
        evidence = {"hat_values": tuple(sorted(values)), "expected": step.target}
        if not values:
            return replace(step, status=ManualValidationStepStatus.OBSERVING, observed_signal="Hat telemetry unavailable.", telemetry_evidence=evidence)
        if step.target.lower() in values:
            return _passed(step, f"Hat observed {step.target}.", evidence)
        return replace(step, status=ManualValidationStepStatus.OBSERVING, observed_signal=f"Waiting for hat {step.target}.", telemetry_evidence=evidence)

    def _replace_step(self, updated: ManualValidationStep) -> None:
        for index, step in enumerate(self.steps):
            if step.step_id == updated.step_id:
                self.steps[index] = updated
                return
        raise KeyError(updated.step_id)


@dataclass(frozen=True)
class ManualValidationResult:
    passed: bool
    overall_status: str
    summary: Mapping[str, object]
    artifact_paths: Mapping[str, Path] = field(default_factory=dict)


def create_manual_validation_session(
    *,
    session_id: str | None = None,
    axis_threshold: float = DEFAULT_AXIS_THRESHOLD,
) -> ManualValidationSession:
    return ManualValidationSession(
        session_id=session_id or uuid4().hex,
        started_at=_now(),
        axis_threshold=axis_threshold,
        steps=list(_required_steps()),
        warnings=["Manual operator confirmation does not prove vJoy writes by itself."],
    )


def export_manual_validation_session(session: ManualValidationSession, output_dir: str | Path) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "manual_validation.json"
    markdown_path = root / "manual_validation.md"
    summary = session.summary()
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(summary), encoding="utf-8")
    return {"json_path": json_path, "markdown_path": markdown_path}


def _required_steps() -> tuple[ManualValidationStep, ...]:
    steps = [
        _step("telemetry_readiness", "Bridge / telemetry readiness", "Confirm Bridge telemetry is fresh. Stream is preferred; JSON fallback is allowed when labeled.", "Fresh Bridge telemetry source", "Fresh non-simulation telemetry.", "telemetry"),
        _step("config_sync", "Config sync", "Confirm Bridge workspace hash matches the UI workspace hash.", "Matching workspace hash", "Bridge/UI hashes match.", "config"),
        _step("hotas_detection", "HOTAS detection", "Confirm supported HOTAS detection and physical sample fidelity.", "Supported HOTAS and active sample", "Supported HOTAS detected and fidelity telemetry present.", "hotas"),
    ]
    steps.extend(
        _step(f"axis_{key}", f"Move {title}", instruction, f"{title} raw/normalized value changes", f"{title} changes by threshold.", "axis", target)
        for key, title, target, instruction in (
            ("roll", "Roll", "Roll", "Move Roll left and right."),
            ("pitch", "Pitch", "Pitch", "Move Pitch forward and back."),
            ("throttle", "Throttle", "Throttle", "Move Throttle min to max."),
            ("yaw", "Yaw", "Yaw", "Move Yaw left and right."),
            ("aux1", "Aux 1", "Aux 1", "Move Aux 1 through its range if available."),
            ("aux2", "Aux 2", "Aux 2", "Move Aux 2 through its range if available."),
        )
    )
    steps.extend(
        _step(f"button_b{number}", f"Press/release B{number}", f"Press and release B{number}.", f"B{number} false -> true -> false", f"B{number} press/release transition.", "button", f"B{number}")
        for number in (1, 2, 15)
    )
    steps.extend(
        _step(f"hat_{direction.lower()}", f"Hat {direction.lower()}", f"Move hat/POV to {direction}.", f"Hat {direction}", f"Hat reports {direction}.", "hat", direction)
        for direction in ("Up", "Right", "Down", "Left", "Centered")
    )
    steps.extend(
        (
            _step("pipeline_output_intent", "Pipeline / output intent", "Move controls and confirm final output intent changes. Output intent is not output write proof.", "Final output intent changes", "runtime_frame reports output intent ready.", "pipeline"),
            _step("output_proof_status", "vJoy / output proof status", "Review vJoy/backend verification, output loop state, writes/skips/failures, neutral restore, and safety stop.", "Real output proof if available", "Real output verification is reported; otherwise block truthfully.", "output"),
            _step("final_readiness_truth", "Final readiness truth", "Review Full Live Runtime Ready, blocked reason, fake_or_real_path, and proof summary.", "Readiness proof summary", "Full Live Runtime Ready only if runtime_frame proves it.", "readiness"),
        )
    )
    return tuple(steps)


def _step(step_id: str, title: str, instruction: str, expected: str, criteria: str, kind: str, target: str = "") -> ManualValidationStep:
    return ManualValidationStep(
        step_id=step_id,
        title=title,
        instruction=instruction,
        expected_signal=expected,
        pass_criteria=criteria,
        kind=kind,
        target=target,
    )


def _passed(step: ManualValidationStep, observed: str, evidence: Mapping[str, object]) -> ManualValidationStep:
    return replace(
        step,
        status=ManualValidationStepStatus.PASSED,
        observed_signal=observed,
        telemetry_evidence=dict(evidence),
        failure_reason="",
        completed_at=_now(),
    )


def _blocked(step: ManualValidationStep, reason: str, evidence: Mapping[str, object]) -> ManualValidationStep:
    return replace(
        step,
        status=ManualValidationStepStatus.BLOCKED,
        observed_signal=reason,
        failure_reason=reason,
        telemetry_evidence=dict(evidence),
        completed_at=_now(),
    )


def _markdown(summary: Mapping[str, object]) -> str:
    lines = [
        "# Manual Bench Validation",
        "",
        f"- Session: {summary.get('session_id')}",
        f"- Overall status: {summary.get('overall_status')}",
        f"- Bridge source: {summary.get('bridge_source')}",
        f"- Workspace hash: {summary.get('workspace_hash')}",
        "",
        "Manual confirmation does not prove vJoy writes. Output intent is not output write proof.",
        "",
        "## Steps",
    ]
    for step in summary.get("steps", ()):
        if isinstance(step, Mapping):
            lines.append(f"- {step.get('title')}: {step.get('status')} - {step.get('observed_signal') or step.get('failure_reason')}")
    lines.append("")
    return "\n".join(lines)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


_TERMINAL_STATUSES = {
    ManualValidationStepStatus.PASSED,
    ManualValidationStepStatus.FAILED,
    ManualValidationStepStatus.SKIPPED,
    ManualValidationStepStatus.BLOCKED,
    ManualValidationStepStatus.UNAVAILABLE,
}
