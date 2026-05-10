from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Mapping
from uuid import uuid4


class AcceptanceGateStatus(str, Enum):
    PASSED = "passed"
    BLOCKED = "blocked"
    WARNING = "warning"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class AcceptanceProofKind(str, Enum):
    FAKE = "fake"
    REAL = "real"
    MIXED = "mixed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class RuntimeAcceptanceGate:
    gate_id: str
    title: str
    status: AcceptanceGateStatus
    proof_kind: AcceptanceProofKind
    required: bool = True
    summary: str = ""
    evidence: Mapping[str, object] = field(default_factory=dict)
    blocked_reason: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "gate_id": self.gate_id,
            "title": self.title,
            "status": self.status.value,
            "proof_kind": self.proof_kind.value,
            "required": self.required,
            "summary": self.summary,
            "evidence": dict(self.evidence),
            "blocked_reason": self.blocked_reason,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class AcceptanceResult:
    passed_count: int
    blocked_count: int
    warning_count: int
    skipped_count: int
    unavailable_count: int
    overall_status: str
    ready_for_rc: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "passed_count": self.passed_count,
            "blocked_count": self.blocked_count,
            "warning_count": self.warning_count,
            "skipped_count": self.skipped_count,
            "unavailable_count": self.unavailable_count,
            "overall_status": self.overall_status,
            "ready_for_rc": self.ready_for_rc,
        }


@dataclass
class RuntimeAcceptanceReport:
    source: str
    proof_kind: AcceptanceProofKind
    gates: list[RuntimeAcceptanceGate]
    report_id: str = field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    full_live_runtime_ready: bool = False
    fake_or_real_path: str = "unavailable"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    release_posture: str = "blocked_runtime_truth"

    def gate(self, gate_id: str) -> RuntimeAcceptanceGate:
        for gate in self.gates:
            if gate.gate_id == gate_id:
                return gate
        raise KeyError(gate_id)

    @property
    def ready_for_rc(self) -> bool:
        return self.result().ready_for_rc

    @property
    def overall_status(self) -> str:
        return self.result().overall_status

    def result(self) -> AcceptanceResult:
        passed = sum(g.status is AcceptanceGateStatus.PASSED for g in self.gates)
        blocked = sum(g.required and g.status is AcceptanceGateStatus.BLOCKED for g in self.gates)
        warning = sum(g.status is AcceptanceGateStatus.WARNING for g in self.gates)
        skipped = sum(g.status is AcceptanceGateStatus.SKIPPED for g in self.gates)
        unavailable = sum(g.status is AcceptanceGateStatus.UNAVAILABLE for g in self.gates)
        ready = blocked == 0 and all(
            (not gate.required) or gate.status in {AcceptanceGateStatus.PASSED, AcceptanceGateStatus.WARNING, AcceptanceGateStatus.NOT_APPLICABLE}
            for gate in self.gates
        )
        if blocked:
            overall = "blocked"
        elif warning:
            overall = "warning"
        elif ready:
            overall = "passed"
        else:
            overall = "unavailable"
        return AcceptanceResult(
            passed_count=passed,
            blocked_count=blocked,
            warning_count=warning,
            skipped_count=skipped,
            unavailable_count=unavailable,
            overall_status=overall,
            ready_for_rc=ready,
        )

    def to_dict(self) -> dict[str, object]:
        result = self.result()
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "source": self.source,
            "proof_kind": self.proof_kind.value,
            "overall_status": result.overall_status,
            "ready_for_rc": result.ready_for_rc,
            "full_live_runtime_ready": self.full_live_runtime_ready,
            "fake_or_real_path": self.fake_or_real_path,
            "release_posture": self.release_posture,
            "result": result.to_dict(),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "artifact_paths": dict(self.artifact_paths),
            "gates": [gate.to_dict() for gate in self.gates],
        }


@dataclass(frozen=True)
class RuntimeAcceptanceOptions:
    mode: str = "fake"
    require_hotas: bool = False
    require_vjoy: bool = False
    require_real_output: bool = False
    require_manual_validation: bool = False
    source: str = "runtime_acceptance"


def evaluate_runtime_acceptance(
    options: RuntimeAcceptanceOptions,
    *,
    telemetry: Mapping[str, object] | None = None,
    bench_summary: Mapping[str, object] | None = None,
    manual_validation: Mapping[str, object] | None = None,
) -> RuntimeAcceptanceReport:
    telemetry = telemetry or {}
    bench_summary = bench_summary or {}
    manual_validation = manual_validation or {}
    mode = options.mode if options.mode in {"fake", "real"} else "fake"
    proof_kind = _proof_kind(mode, telemetry, bench_summary, manual_validation)
    gates = [
        _bridge_fast_loop_gate(telemetry, proof_kind),
        _physical_input_gate(options, telemetry, bench_summary, proof_kind),
        _telemetry_source_gate(telemetry, bench_summary, proof_kind),
        _frame_dedupe_gate(telemetry, bench_summary, proof_kind),
        _workspace_config_gate(telemetry, proof_kind),
        _pipeline_output_intent_gate(telemetry, bench_summary, proof_kind),
        _vjoy_verification_gate(options, telemetry, bench_summary, proof_kind),
        _persistent_output_loop_gate(telemetry, proof_kind),
        _output_cadence_safety_gate(telemetry, bench_summary, proof_kind),
        _bench_harness_gate(options, bench_summary, proof_kind),
        _manual_validation_gate(options, manual_validation, proof_kind),
        _full_live_ready_gate(telemetry, proof_kind),
    ]
    rc_gate = _rc_freeze_gate(options, gates, proof_kind)
    gates.append(rc_gate)
    full_ready = _runtime_full_ready(telemetry)
    report = RuntimeAcceptanceReport(
        source=options.source,
        proof_kind=proof_kind,
        gates=gates,
        full_live_runtime_ready=full_ready,
        fake_or_real_path="real" if proof_kind is AcceptanceProofKind.REAL else "fake" if proof_kind is AcceptanceProofKind.FAKE else proof_kind.value,
        warnings=_collect_warnings(gates, bench_summary, manual_validation),
        errors=_collect_errors(gates, bench_summary, manual_validation),
        release_posture=_release_posture(options, gates, proof_kind),
    )
    return report


def export_acceptance_report(
    report: RuntimeAcceptanceReport,
    output_root: Path,
    *,
    evidence: Mapping[str, object] | None = None,
) -> dict[str, Path]:
    artifact_dir = _artifact_dir(Path(output_root), report.proof_kind.value)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_json = artifact_dir / "acceptance_summary.json"
    summary_md = artifact_dir / "acceptance_summary.md"
    gates_json = artifact_dir / "gates.json"
    evidence_json = artifact_dir / "evidence.json"
    summary_json.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_md.write_text(_markdown_summary(report), encoding="utf-8")
    gates_json.write_text(json.dumps([gate.to_dict() for gate in report.gates], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    evidence_json.write_text(json.dumps(evidence or {}, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    paths = {
        "artifact_dir": artifact_dir,
        "summary_json": summary_json,
        "summary_md": summary_md,
        "gates_json": gates_json,
        "evidence_json": evidence_json,
    }
    report.artifact_paths.update({key: str(value) for key, value in paths.items()})
    return paths


def load_json_mapping(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(data) if isinstance(data, Mapping) else {}


def _bridge_fast_loop_gate(telemetry: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    timing = _mapping(telemetry.get("bridge_timing"))
    tick_count = _int(timing.get("tick_count"))
    duration = _float(timing.get("last_tick_duration_ms"))
    discovery_age = _float(timing.get("last_discovery_age_ms"))
    status = str(timing.get("fast_loop_status") or "")
    evidence = {"tick_count": tick_count, "last_tick_duration_ms": duration, "last_discovery_age_ms": discovery_age, "fast_loop_status": status, "slow_lane_status": timing.get("slow_lane_status")}
    if tick_count is None or tick_count <= 0 or duration is None:
        return _blocked("bridge_fast_loop_health", "Bridge fast loop health", proof_kind, "Bridge timing/tick evidence is missing.", evidence)
    if discovery_age is not None and discovery_age < 1000.0:
        return _warning("bridge_fast_loop_health", "Bridge fast loop health", proof_kind, "Discovery age is very young; confirm slow discovery is not running every tick.", evidence)
    if status and status not in {"healthy", "ok", "running"}:
        return _warning("bridge_fast_loop_health", "Bridge fast loop health", proof_kind, f"Fast loop status is {status}.", evidence)
    return _passed("bridge_fast_loop_health", "Bridge fast loop health", proof_kind, "Bridge timing and fast-loop status are present.", evidence)


def _physical_input_gate(options: RuntimeAcceptanceOptions, telemetry: Mapping[str, object], bench: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    fidelity = _mapping(telemetry.get("physical_input_fidelity"))
    choice = _mapping(telemetry.get("physical_input_backend_choice"))
    bench_input = _mapping(bench.get("input"))
    backend_kind = str(fidelity.get("backend_kind") or bench_input.get("backend_kind") or "")
    evidence = {
        "backend_name": fidelity.get("backend_name") or bench_input.get("backend_name"),
        "backend_kind": backend_kind,
        "sample_age_ms": fidelity.get("sample_age_ms"),
        "read_duration_ms": fidelity.get("read_duration_ms"),
        "mapping_status": fidelity.get("mapping_status"),
        "backend_choice": choice,
        "bench_sample_count": bench_input.get("sample_count"),
    }
    if "physical_input_fidelity" in telemetry and not fidelity:
        return _blocked("physical_input_fidelity", "Physical input fidelity", proof_kind, "Physical input fidelity evidence is missing.", evidence)
    if options.mode == "real" and options.require_hotas and backend_kind == "fake":
        return _blocked("physical_input_fidelity", "Physical input fidelity", proof_kind, "Real HOTAS proof is required, but only fake physical input evidence is present.", evidence)
    if not fidelity and not bench_input:
        return _blocked("physical_input_fidelity", "Physical input fidelity", proof_kind, "Physical input fidelity evidence is missing.", evidence)
    if fidelity and (fidelity.get("sample_age_ms") is None or fidelity.get("read_duration_ms") is None):
        return _warning("physical_input_fidelity", "Physical input fidelity", proof_kind, "Physical input exists but sample age/read duration is incomplete.", evidence)
    mapping_status = str(fidelity.get("mapping_status") or "ok")
    if mapping_status not in {"ok", "missing_channels"}:
        return _warning("physical_input_fidelity", "Physical input fidelity", proof_kind, f"Mapping status is {mapping_status}.", evidence)
    return _passed("physical_input_fidelity", "Physical input fidelity", proof_kind, "Physical input backend/fidelity evidence is present.", evidence)


def _telemetry_source_gate(telemetry: Mapping[str, object], bench: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    source = _mapping(telemetry.get("telemetry_source"))
    bench_telemetry = _mapping(bench.get("telemetry"))
    fresh = source.get("fresh")
    stale = bool(source.get("stale"))
    source_name = str(source.get("source") or bench_telemetry.get("source_used") or "")
    evidence = {"source": source_name, "fresh": fresh, "stale": stale, "bench_telemetry": bench_telemetry}
    if stale or fresh is False:
        return _blocked("telemetry_source_truth", "Telemetry source truth", proof_kind, "Telemetry source is stale or invalid.", evidence)
    if not source_name:
        return _blocked("telemetry_source_truth", "Telemetry source truth", proof_kind, "Telemetry source is not labeled.", evidence)
    if "Simulation" in source_name:
        return _warning("telemetry_source_truth", "Telemetry source truth", proof_kind, "Simulation fallback is active and must stay labeled.", evidence)
    if source_name == "Bridge JSON Snapshot":
        return _warning("telemetry_source_truth", "Telemetry source truth", proof_kind, "JSON snapshot is accepted only as diagnostic/fallback telemetry.", evidence)
    return _passed("telemetry_source_truth", "Telemetry source truth", proof_kind, f"Telemetry source is labeled as {source_name}.", evidence)


def _frame_dedupe_gate(telemetry: Mapping[str, object], bench: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    monitor = _mapping(telemetry.get("live_monitor"))
    bench_telemetry = _mapping(bench.get("telemetry"))
    duplicate_accepted = bool(monitor.get("duplicate_frames_accepted"))
    repeated = _int(monitor.get("repeated_frame_count"))
    if repeated is None:
        repeated = _int(bench_telemetry.get("duplicate_or_repeated_frame_count")) or 0
    cadence = _float(monitor.get("accepted_frame_cadence_hz") or bench_telemetry.get("stream_accepted_frame_rate_hz"))
    age = _float(monitor.get("latest_bridge_frame_age_ms") or bench_telemetry.get("telemetry_frame_age_average_ms"))
    evidence = {"accepted_frame_cadence_hz": cadence, "repeated_frame_count": repeated, "duplicate_frames_accepted": duplicate_accepted, "frame_age_ms": age}
    if duplicate_accepted:
        return _blocked("frame_dedupe_cadence", "Frame dedupe/cadence", proof_kind, "Duplicate/repeated frames were accepted as new samples.", evidence)
    if cadence is None and age is None:
        return _warning("frame_dedupe_cadence", "Frame dedupe/cadence", proof_kind, "Accepted-frame cadence is unavailable.", evidence)
    return _passed("frame_dedupe_cadence", "Frame dedupe/cadence", proof_kind, "Frame identity/cadence evidence is present and duplicates are not accepted.", evidence)


def _workspace_config_gate(telemetry: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    workspace = _mapping(telemetry.get("bridge_workspace"))
    bridge_hash = str(workspace.get("workspace_hash") or "")
    ui_hash = str(telemetry.get("ui_workspace_hash") or "")
    status = str(workspace.get("config_status") or "")
    evidence = {"bridge_hash": bridge_hash, "ui_hash": ui_hash, "config_status": status, "workspace_revision": workspace.get("workspace_revision")}
    if not bridge_hash:
        return _blocked("workspace_config_sync", "Workspace config sync", proof_kind, "Bridge workspace hash is missing.", evidence)
    if ui_hash and ui_hash != bridge_hash:
        return _blocked("workspace_config_sync", "Workspace config sync", proof_kind, "Bridge/UI workspace hashes do not match.", evidence)
    if status in {"missing_default", "invalid_default"}:
        return _warning("workspace_config_sync", "Workspace config sync", proof_kind, f"Bridge is using {status}.", evidence)
    return _passed("workspace_config_sync", "Workspace config sync", proof_kind, "Bridge workspace identity is present and matches UI context when available.", evidence)


def _pipeline_output_intent_gate(telemetry: Mapping[str, object], bench: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    runtime_frame = _mapping(telemetry.get("runtime_frame"))
    raw_axes = _mapping(telemetry.get("raw_axes"))
    final_axes = _mapping(telemetry.get("final_axes"))
    bench_pipeline = _mapping(bench.get("pipeline"))
    intent_ready = bool(runtime_frame.get("output_intent_ready"))
    changes = _int(bench_pipeline.get("final_output_changes_observed")) or 0
    evidence = {"raw_axes_present": bool(raw_axes), "final_axes_present": bool(final_axes), "output_intent_ready": intent_ready, "bench_output_changes": changes}
    if not raw_axes or not final_axes:
        return _blocked("pipeline_output_intent", "Pipeline/output intent", proof_kind, "Raw/final axes are missing.", evidence)
    if not intent_ready and changes <= 0:
        return _blocked("pipeline_output_intent", "Pipeline/output intent", proof_kind, "Output intent is not present.", evidence)
    return _passed("pipeline_output_intent", "Pipeline/output intent", proof_kind, "Pipeline output intent is present; this is not output write proof.", evidence)


def _vjoy_verification_gate(options: RuntimeAcceptanceOptions, telemetry: Mapping[str, object], bench: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    loop = _mapping(telemetry.get("output_loop_runtime"))
    bench_runtime_truth = _mapping(bench.get("runtime_truth"))
    output_verified = bool(telemetry.get("output_verified"))
    verification_real = bool(loop.get("verification_real") or bench_runtime_truth.get("real_output_verified"))
    verification_fake = bool(loop.get("verification_fake") or bench_runtime_truth.get("fake_output_verified"))
    evidence = {"output_verified": output_verified, "verification_real": verification_real, "verification_fake": verification_fake, "verification_status": loop.get("verification_status"), "output_status": telemetry.get("output_status")}
    if options.require_vjoy or options.require_real_output:
        if not (output_verified and verification_real):
            return _blocked("vjoy_output_verification_truth", "vJoy/output verification truth", proof_kind, "Real vJoy output verification is required and not proven.", evidence)
    if verification_real and output_verified:
        return _passed("vjoy_output_verification_truth", "vJoy/output verification truth", AcceptanceProofKind.REAL, "Real output verification is present.", evidence)
    if verification_fake:
        return _warning("vjoy_output_verification_truth", "vJoy/output verification truth", proof_kind, "Only fake-path output verification evidence is present.", evidence)
    return _warning("vjoy_output_verification_truth", "vJoy/output verification truth", proof_kind, "vJoy detected/output intent is not output verification.", evidence)


def _persistent_output_loop_gate(telemetry: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    loop = _mapping(telemetry.get("output_loop_runtime"))
    evidence = {"state": loop.get("state"), "write_success_count": loop.get("write_success_count"), "write_skipped_count": loop.get("write_skipped_count"), "write_failure_count": loop.get("write_failure_count"), "loop_recreated_count": loop.get("loop_recreated_count")}
    if not loop:
        return _blocked("persistent_output_loop", "Persistent output loop", proof_kind, "Output loop runtime telemetry is missing.", evidence)
    recreated = _int(loop.get("loop_recreated_count")) or 0
    if recreated > 1:
        return _warning("persistent_output_loop", "Persistent output loop", proof_kind, "Output loop was recreated more than once.", evidence)
    return _passed("persistent_output_loop", "Persistent output loop", proof_kind, "Output loop runtime state and counters are present.", evidence)


def _output_cadence_safety_gate(telemetry: Mapping[str, object], bench: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    loop = _mapping(telemetry.get("output_loop_runtime"))
    bench_output = _mapping(bench.get("output"))
    write_rate = loop.get("write_rate_hz") or bench_output.get("target_write_rate_hz")
    safety = str(loop.get("safety_stop_reason") or "None")
    neutral = str(loop.get("neutral_restore_status") or bench_output.get("neutral_restore_status") or "")
    evidence = {
        "write_rate_hz": write_rate,
        "write_skipped_count": loop.get("write_skipped_count") or bench_output.get("write_skipped_count"),
        "write_skipped_rate_limited_count": loop.get("write_skipped_rate_limited_count") or bench_output.get("write_skipped_rate_limited_count"),
        "write_failure_count": loop.get("write_failure_count") or bench_output.get("write_failure_count"),
        "safety_stop_reason": safety,
        "neutral_restore_status": neutral,
    }
    if safety and safety != "None":
        return _blocked("output_cadence_safety", "Output cadence/safety", proof_kind, f"Output loop safety stop is active: {safety}.", evidence)
    if write_rate is None:
        return _blocked("output_cadence_safety", "Output cadence/safety", proof_kind, "Target write rate is missing.", evidence)
    if not neutral:
        return _warning("output_cadence_safety", "Output cadence/safety", proof_kind, "Neutral restore status is unavailable.", evidence)
    return _passed("output_cadence_safety", "Output cadence/safety", proof_kind, "Write cadence, skips/failures, safety, and neutral restore fields are present.", evidence)


def _bench_harness_gate(options: RuntimeAcceptanceOptions, bench: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    evidence = {"pass": bench.get("pass"), "mode": bench.get("mode"), "fake_or_real_path": bench.get("fake_or_real_path")}
    if not bench:
        return _blocked("bench_harness_proof", "Bench harness proof", proof_kind, "Bench harness evidence is missing.", evidence)
    if bench.get("pass") is not True:
        return _blocked("bench_harness_proof", "Bench harness proof", proof_kind, "Bench harness did not pass.", evidence)
    if options.mode == "real" and bench.get("fake_or_real_path") != "real":
        return _blocked("bench_harness_proof", "Bench harness proof", proof_kind, "Real mode requires real bench evidence.", evidence)
    return _passed("bench_harness_proof", "Bench harness proof", proof_kind, "Bench harness evidence passed for the selected proof path.", evidence)


def _manual_validation_gate(options: RuntimeAcceptanceOptions, manual: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    evidence = {"overall_status": manual.get("overall_status"), "mode": manual.get("mode"), "bridge_source": manual.get("bridge_source")}
    if not manual:
        if options.require_manual_validation:
            return _blocked("manual_validation_proof", "Manual validation proof", proof_kind, "Manual validation report is required and missing.", evidence)
        return RuntimeAcceptanceGate("manual_validation_proof", "Manual validation proof", AcceptanceGateStatus.UNAVAILABLE, proof_kind, required=False, summary="Manual validation report is unavailable; operator evidence is optional unless required.", evidence=evidence)
    if manual.get("overall_status") in {"failed", "blocked"} and options.require_manual_validation:
        return _blocked("manual_validation_proof", "Manual validation proof", proof_kind, "Manual validation report is blocked/failed.", evidence)
    return _passed("manual_validation_proof", "Manual validation proof", proof_kind, "Manual validation evidence is loaded; it does not override runtime proof gates.", evidence)


def _full_live_ready_gate(telemetry: Mapping[str, object], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    runtime_frame = _mapping(telemetry.get("runtime_frame"))
    full_ready = bool(runtime_frame.get("full_live_runtime_ready"))
    evidence = {"full_live_runtime_ready": full_ready, "blocked_reason": runtime_frame.get("blocked_reason"), "runtime_truth": telemetry.get("runtime_truth")}
    if full_ready:
        return _passed("full_live_runtime_ready", "Full Live Runtime Ready gate", AcceptanceProofKind.REAL, "Existing runtime readiness evaluator reports Full Live Runtime Ready.", evidence)
    return _passed("full_live_runtime_ready", "Full Live Runtime Ready gate", proof_kind, "Full Live Runtime Ready remains false; acceptance did not force it.", evidence)


def _rc_freeze_gate(options: RuntimeAcceptanceOptions, gates: list[RuntimeAcceptanceGate], proof_kind: AcceptanceProofKind) -> RuntimeAcceptanceGate:
    blocking = [gate for gate in gates if gate.required and gate.status is AcceptanceGateStatus.BLOCKED]
    evidence = {"blocking_gates": [gate.gate_id for gate in blocking], "mode": options.mode, "proof_kind": proof_kind.value}
    if blocking:
        reason = "; ".join(gate.blocked_reason or gate.title for gate in blocking[:4])
        if options.mode == "real":
            reason = f"Missing or blocked real hardware proof: {reason}"
        return _blocked("rc_freeze", "RC freeze gate", proof_kind, reason, evidence)
    return _passed("rc_freeze", "RC freeze gate", proof_kind, "All required runtime acceptance gates pass for the selected proof path.", evidence)


def _proof_kind(mode: str, telemetry: Mapping[str, object], bench: Mapping[str, object], manual: Mapping[str, object]) -> AcceptanceProofKind:
    labels = {
        str(bench.get("fake_or_real_path") or ""),
        str(_mapping(telemetry.get("runtime_frame")).get("fake_or_real_path") or ""),
        str(manual.get("fake_or_real_path") or ""),
    }
    if "fake" in labels and "real" in labels:
        return AcceptanceProofKind.MIXED
    if mode == "real" or "real" in labels:
        return AcceptanceProofKind.REAL
    if mode == "fake" or "fake" in labels:
        return AcceptanceProofKind.FAKE
    return AcceptanceProofKind.UNAVAILABLE


def _release_posture(options: RuntimeAcceptanceOptions, gates: list[RuntimeAcceptanceGate], proof_kind: AcceptanceProofKind) -> str:
    if any(g.status is AcceptanceGateStatus.BLOCKED and g.required for g in gates):
        if options.require_real_output:
            return "blocked_output_verification"
        if options.require_hotas or options.require_vjoy:
            return "blocked_missing_hardware_proof"
        return "blocked_runtime_truth"
    if proof_kind is AcceptanceProofKind.FAKE:
        return "fake_path_pass_real_path_unproven"
    if proof_kind is AcceptanceProofKind.REAL:
        return "rc_freeze_ready"
    return "real_path_candidate"


def _collect_warnings(gates: list[RuntimeAcceptanceGate], bench: Mapping[str, object], manual: Mapping[str, object]) -> list[str]:
    warnings: list[str] = []
    for gate in gates:
        warnings.extend(gate.warnings)
    for item in bench.get("warnings", ()) or ():
        warnings.append(str(item))
    for item in manual.get("warnings", ()) or ():
        warnings.append(str(item))
    return warnings


def _collect_errors(gates: list[RuntimeAcceptanceGate], bench: Mapping[str, object], manual: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    for gate in gates:
        errors.extend(gate.errors)
    for item in bench.get("errors", ()) or ():
        errors.append(str(item))
    for item in manual.get("errors", ()) or ():
        errors.append(str(item))
    return errors


def _runtime_full_ready(telemetry: Mapping[str, object]) -> bool:
    return bool(_mapping(telemetry.get("runtime_frame")).get("full_live_runtime_ready"))


def _passed(gate_id: str, title: str, proof_kind: AcceptanceProofKind, summary: str, evidence: Mapping[str, object]) -> RuntimeAcceptanceGate:
    return RuntimeAcceptanceGate(gate_id, title, AcceptanceGateStatus.PASSED, proof_kind, summary=summary, evidence=dict(evidence))


def _blocked(gate_id: str, title: str, proof_kind: AcceptanceProofKind, reason: str, evidence: Mapping[str, object]) -> RuntimeAcceptanceGate:
    return RuntimeAcceptanceGate(gate_id, title, AcceptanceGateStatus.BLOCKED, proof_kind, summary=reason, evidence=dict(evidence), blocked_reason=reason)


def _warning(gate_id: str, title: str, proof_kind: AcceptanceProofKind, summary: str, evidence: Mapping[str, object]) -> RuntimeAcceptanceGate:
    return RuntimeAcceptanceGate(gate_id, title, AcceptanceGateStatus.WARNING, proof_kind, summary=summary, evidence=dict(evidence), warnings=(summary,))


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _artifact_dir(root: Path, mode: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return root / f"{stamp}-{mode}"


def _markdown_summary(report: RuntimeAcceptanceReport) -> str:
    data = report.to_dict()
    lines = [
        "# HF-LRDC Runtime Acceptance Summary",
        "",
        f"- Overall status: {data['overall_status']}",
        f"- Ready for RC: {data['ready_for_rc']}",
        f"- Proof kind: {data['proof_kind']}",
        f"- Full Live Runtime Ready: {data['full_live_runtime_ready']}",
        f"- Release posture: {data['release_posture']}",
        "",
        "| Gate | Status | Proof | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for gate in report.gates:
        summary = (gate.blocked_reason or gate.summary).replace("\n", " ")
        lines.append(f"| {gate.title} | {gate.status.value} | {gate.proof_kind.value} | {summary} |")
    blocked = [gate for gate in report.gates if gate.status is AcceptanceGateStatus.BLOCKED]
    lines.extend(["", "## Blocking Reasons"])
    if blocked:
        lines.extend(f"- {gate.title}: {gate.blocked_reason}" for gate in blocked)
    else:
        lines.append("- None for the selected proof path.")
    lines.extend(
        [
            "",
            "## Runtime Truth Boundary",
            "Fake-path acceptance does not equal real Full Live Runtime Ready. Output intent, telemetry freshness, config match, and vJoy detection do not prove vJoy writes.",
        ]
    )
    return "\n".join(lines) + "\n"
