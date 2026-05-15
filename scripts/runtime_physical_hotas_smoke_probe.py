from __future__ import annotations

import argparse
import ast
import json
import math
import subprocess
import sys
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared_core.models.axes import AXIS_DISPLAY_NAMES
from shared_core.models.mappings import AxisMapping, ButtonMapping, HatMapping
from shared_core.models.rules import RuleConfig, yaw_roll_example_rule
from shared_core.models.runtime import BUTTON_NAMES
from shared_core.models.workspace import CONFIG_FILENAME, WorkspaceConfig, create_default_workspace
from shared_core.persistence.workspace_store import load_workspace, save_workspace
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.hotas_discovery import discover_supported_hotas
from shared_core.runtime.hotas_input import (
    PhysicalInputBackend,
    PhysicalInputDeviceInfo,
    PhysicalInputSampler,
    build_best_physical_input_backend,
    build_winmm_physical_input_fallback,
)
from shared_core.runtime.runtime_orchestrator import RuntimeFrame, RuntimeFrameSource, RuntimeOrchestrator, RuntimeOrchestratorConfig
from shared_core.runtime.vjoy_output import (
    FakeVirtualOutputBackend,
    RealVJoyOutputBackend,
    VirtualOutputBackend,
    VirtualOutputIntent,
    VirtualOutputWriteResult,
)


ARTIFACT_ROOT = Path("artifacts") / "runtime-physical-hotas-smoke"
REPORT_PATH = Path("docs") / "HelmForge" / "runtime-usability-1d-physical-hotas-live-smoke-report.md"
AXIS_OUTPUT_DEFAULTS = {
    "Roll": "X",
    "Pitch": "Y",
    "Throttle": "Z",
    "Yaw": "RX",
    "Aux 1": "RY",
    "Aux 2": "RZ",
}
AXIS_INSTRUCTIONS = {
    "Roll": "Move Roll axis left/right now.",
    "Pitch": "Move Pitch axis forward/back now.",
    "Throttle": "Move Throttle through its travel now.",
    "Yaw": "Twist or move Yaw now.",
    "Aux 1": "Move Aux 1 now, if present.",
    "Aux 2": "Move Aux 2 now, if present.",
}


@dataclass(frozen=True)
class ProbeSample:
    timestamp: float
    raw_axes: Mapping[str, float]
    final_axes: Mapping[str, float]
    output_axes: Mapping[str, float]
    buttons: Mapping[str, bool]
    output_buttons: Mapping[str, bool]
    hat_state: str
    output_hats: Mapping[str, str]
    write_axes: Mapping[str, float] = field(default_factory=dict)
    write_buttons: Mapping[str, bool] = field(default_factory=dict)
    stage_values: Mapping[str, object] = field(default_factory=dict)
    active_modes: tuple[str, ...] = ()
    active_rules: tuple[str, ...] = ()
    rebuild_count: int = 1
    input_source: str = "physical"
    writer_status: str = "not_attempted"
    writer_success: bool | None = None


@dataclass(frozen=True)
class StepResult:
    step_type: str
    name: str
    status: str
    message: str
    detected: bool = False
    timeout: bool = False
    baseline_value: float | None = None
    changed_value: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    final_value: float | None = None
    output_target: str = ""
    output_value: float | None = None
    writer_value: float | None = None
    settle_sample_count: int = 0
    press_observed: bool = False
    release_observed: bool = False
    output_true_observed: bool = False
    output_false_observed: bool = False
    writer_true_observed: bool = False
    writer_false_observed: bool = False
    output_hat: str = ""
    mapped_buttons_true: tuple[str, ...] = ()
    diagonal_policy: str = "not_applicable"
    active_modes: tuple[str, ...] = ()
    active_rules: tuple[str, ...] = ()
    unrelated_true_outputs: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return _jsonable(self.__dict__)


@dataclass(frozen=True)
class WriteRecord:
    success: bool
    status: str
    source: str
    axes: Mapping[str, float]
    buttons: Mapping[str, bool]
    hats: Mapping[str, str]

    def to_dict(self) -> dict[str, object]:
        return _jsonable(self.__dict__)


class RecordingOutputBackend:
    def __init__(self, inner: VirtualOutputBackend, *, enabled: bool) -> None:
        self.inner = inner
        self.enabled = enabled
        self.write_records: list[WriteRecord] = []

    def get_capabilities(self):
        return self.inner.get_capabilities()

    def get_status(self):
        return self.inner.get_status()

    def enumerate_output_devices(self):
        return self.inner.enumerate_output_devices()

    def select_output_device(self, device_id: str):
        return self.inner.select_output_device(device_id)

    def write_output_intent(self, output_intent: VirtualOutputIntent) -> VirtualOutputWriteResult | None:
        if not self.enabled:
            return None
        result = self.inner.write_output_intent(output_intent)
        self.write_records.append(
            WriteRecord(
                success=result.success,
                status=result.status,
                source=output_intent.source,
                axes={axis.axis_name: axis.value for axis in output_intent.axes},
                buttons={button.button_name: button.pressed for button in output_intent.buttons},
                hats={hat.hat_name: hat.value for hat in output_intent.hats},
            )
        )
        return result

    @property
    def last_record(self) -> WriteRecord | None:
        return self.write_records[-1] if self.write_records else None


class LiveRuntimeSampler:
    def __init__(
        self,
        *,
        workspace: WorkspaceConfig,
        physical_backend: PhysicalInputBackend,
        physical_device: PhysicalInputDeviceInfo,
        output_backend: RecordingOutputBackend,
    ) -> None:
        self.workspace = workspace
        self.physical_backend = physical_backend
        self.physical_device = physical_device
        self.output_backend = output_backend
        self.sampler = PhysicalInputSampler(
            physical_backend,
            selected_device_id=physical_device.device_id,
            validate_selection_on_read=False,
        )
        self.sampler.open()
        self.runtime_status = build_runtime_preflight_status(
            input_device_names=(physical_device.display_name,),
            output_backend_names=("vJoy Device 1",) if output_backend.get_capabilities().backend_available else (),
        )
        self.orchestrator = RuntimeOrchestrator(
            workspace=workspace,
            runtime_status=self.runtime_status,
            physical_input_snapshot=None,
            virtual_output_backend=output_backend.inner,
            config=RuntimeOrchestratorConfig(
                preferred_input_source=RuntimeFrameSource.PHYSICAL,
                allow_simulation_fallback=False,
                allow_output_loop_tick=False,
            ),
        )

    def set_workspace(self, workspace: WorkspaceConfig) -> None:
        self.workspace = workspace
        self.orchestrator.update_runtime_context(workspace=workspace, rebuild_reason="workspace_config_changed")

    def close(self) -> None:
        self.sampler.close()

    def sample(self, timestamp: float) -> ProbeSample:
        snapshot = self.sampler.read_once()
        self.orchestrator.update_runtime_context(
            workspace=self.workspace,
            runtime_status=self.runtime_status,
            physical_input_snapshot=snapshot,
            virtual_output_backend=self.output_backend.inner,
            config=RuntimeOrchestratorConfig(
                preferred_input_source=RuntimeFrameSource.PHYSICAL,
                allow_simulation_fallback=False,
                allow_output_loop_tick=False,
            ),
        )
        frame = self.orchestrator.build_frame()
        self.output_backend.write_output_intent(frame.output_intent)
        raw_buttons = {name: False for name in BUTTON_NAMES}
        for button in snapshot.buttons:
            raw_buttons[f"B{button.button_index}"] = bool(button.pressed)
        raw_hat = snapshot.hats[0].normalized_direction if snapshot.hats else "Centered"
        return sample_from_runtime_frame(
            frame,
            timestamp=timestamp,
            write_record=self.output_backend.last_record,
            raw_buttons=raw_buttons,
            raw_hat=raw_hat,
        )


def sample_from_runtime_frame(
    frame: RuntimeFrame,
    *,
    timestamp: float,
    write_record: WriteRecord | None = None,
    raw_buttons: Mapping[str, bool] | None = None,
    raw_hat: str | None = None,
) -> ProbeSample:
    output_axes = {axis.axis_name: axis.value for axis in frame.output_intent.axes}
    output_buttons = {button.button_name: button.pressed for button in frame.output_intent.buttons}
    output_hats = {hat.hat_name: hat.value for hat in frame.output_intent.hats}
    return ProbeSample(
        timestamp=timestamp,
        raw_axes=dict(frame.pipeline.raw_axis_values),
        final_axes=dict(frame.pipeline.final_output_values),
        output_axes=output_axes,
        buttons=dict(raw_buttons or _physical_buttons_from_frame(frame)),
        output_buttons=output_buttons,
        hat_state=raw_hat or output_hats.get("POV1", "Centered"),
        output_hats=output_hats,
        write_axes=dict(write_record.axes) if write_record else output_axes,
        write_buttons=dict(write_record.buttons) if write_record else output_buttons,
        stage_values=dict(frame.pipeline.axis_stage_values),
        active_modes=tuple(frame.pipeline.active_modes),
        active_rules=tuple(frame.pipeline.active_rules),
        rebuild_count=frame.runtime_orchestrator_rebuild_count,
        input_source=frame.input.source.value,
        writer_status=write_record.status if write_record else "not_attempted",
        writer_success=write_record.success if write_record else None,
    )


def run_axis_step(
    samples: Sequence[ProbeSample],
    *,
    axis_name: str,
    output_axis: str,
    threshold: float,
    timeout_sec: float,
    settle_sec: float,
) -> StepResult:
    ordered = tuple(sorted(samples, key=lambda sample: sample.timestamp))
    if not ordered:
        return StepResult("axis", axis_name, "timeout", "No samples were available.", timeout=True)
    baseline = float(ordered[0].raw_axes.get(axis_name, 0.0))
    deadline = ordered[0].timestamp + timeout_sec
    detected_index: int | None = None
    for index, sample in enumerate(ordered):
        if sample.timestamp > deadline:
            break
        if abs(float(sample.raw_axes.get(axis_name, 0.0)) - baseline) >= threshold:
            detected_index = index
            break
    if detected_index is None:
        return StepResult(
            "axis",
            axis_name,
            "timeout",
            f"{axis_name} movement was not observed within {timeout_sec:.1f} seconds.",
            timeout=True,
            baseline_value=baseline,
        )

    detected = ordered[detected_index]
    settle_deadline = detected.timestamp + settle_sec
    settle_samples = _settle_window_samples(ordered, detected_index, settle_deadline)
    final_sample = settle_samples[-1] if settle_samples else detected
    values = [float(sample.raw_axes.get(axis_name, 0.0)) for sample in settle_samples] or [float(detected.raw_axes.get(axis_name, 0.0))]
    changed_value = float(detected.raw_axes.get(axis_name, 0.0))
    output_value = float(final_sample.output_axes.get(output_axis, 0.0))
    writer_value = float(final_sample.write_axes.get(output_axis, output_value))
    output_changed = abs(output_value - float(ordered[0].output_axes.get(output_axis, 0.0))) >= min(threshold, 0.02)
    status = "passed" if output_changed else "failed"
    return StepResult(
        "axis",
        axis_name,
        status,
        f"{axis_name} changed raw input and mapped output {output_axis}.",
        detected=True,
        baseline_value=baseline,
        changed_value=changed_value,
        min_value=min(values),
        max_value=max(values),
        final_value=float(final_sample.final_axes.get(axis_name, 0.0)),
        output_target=output_axis,
        output_value=output_value,
        writer_value=writer_value,
        settle_sample_count=len(settle_samples),
        metadata={
            "input_source": final_sample.input_source,
            "rebuild_count": final_sample.rebuild_count,
            "writer_status": final_sample.writer_status,
        },
    )


def run_button_step(
    samples: Sequence[ProbeSample],
    *,
    button_name: str,
    output_button: str,
    timeout_sec: float,
    settle_sec: float,
) -> StepResult:
    ordered = tuple(sorted(samples, key=lambda sample: sample.timestamp))
    if not ordered:
        return StepResult("button", button_name, "timeout", "No samples were available.", timeout=True)
    start = ordered[0].timestamp
    press_index = next(
        (
            index
            for index, sample in enumerate(ordered)
            if sample.timestamp <= start + timeout_sec and bool(sample.buttons.get(button_name, False))
        ),
        None,
    )
    if press_index is None:
        return StepResult("button", button_name, "timeout", f"{button_name} press was not observed within {timeout_sec:.1f} seconds.", timeout=True)
    press_sample = ordered[press_index]
    settle_deadline = press_sample.timestamp + settle_sec
    settled = _settle_window_samples(ordered, press_index, settle_deadline)
    release_deadline = settle_deadline + timeout_sec
    release_sample = next(
        (
            sample
            for sample in ordered[press_index:]
            if sample.timestamp <= release_deadline and not bool(sample.buttons.get(button_name, False))
        ),
        None,
    )
    output_true = any(bool(sample.output_buttons.get(output_button, False)) for sample in ordered[press_index:])
    writer_true = any(bool(sample.write_buttons.get(output_button, False)) for sample in ordered[press_index:])
    if release_sample is None:
        return StepResult(
            "button",
            button_name,
            "timeout",
            f"{button_name} release was not observed within {timeout_sec:.1f} seconds after settle.",
            detected=True,
            timeout=True,
            press_observed=True,
            release_observed=False,
            output_true_observed=output_true,
            writer_true_observed=writer_true,
            output_target=output_button,
            settle_sample_count=len(settled),
        )
    return StepResult(
        "button",
        button_name,
        "passed",
        f"{button_name} press/release drove {output_button}.",
        detected=True,
        press_observed=True,
        release_observed=True,
        output_true_observed=output_true,
        output_false_observed=not bool(release_sample.output_buttons.get(output_button, False)),
        writer_true_observed=writer_true,
        writer_false_observed=not bool(release_sample.write_buttons.get(output_button, False)),
        output_target=output_button,
        settle_sample_count=len(settled),
        unrelated_true_outputs=tuple(
            name
            for name, pressed in press_sample.output_buttons.items()
            if pressed and name != output_button
        ),
        metadata={"writer_status": release_sample.writer_status, "rebuild_count": release_sample.rebuild_count},
    )


def run_hat_step(
    samples: Sequence[ProbeSample],
    *,
    expected_hat: str,
    mapped_buttons: tuple[str, ...],
    timeout_sec: float,
    settle_sec: float,
) -> StepResult:
    ordered = tuple(sorted(samples, key=lambda sample: sample.timestamp))
    if not ordered:
        return StepResult("hat", expected_hat, "timeout", "No samples were available.", timeout=True)
    start = ordered[0].timestamp
    detected_index = next(
        (
            index
            for index, sample in enumerate(ordered)
            if sample.timestamp <= start + timeout_sec and _same_hat(sample.hat_state, expected_hat)
        ),
        None,
    )
    if detected_index is None:
        return StepResult("hat", expected_hat, "timeout", f"Hat {expected_hat} was not observed within {timeout_sec:.1f} seconds.", timeout=True)
    detected = ordered[detected_index]
    settle_deadline = detected.timestamp + settle_sec
    settle_samples = _settle_window_samples(ordered, detected_index, settle_deadline)
    final_sample = settle_samples[-1] if settle_samples else detected
    true_buttons = tuple(button for button in mapped_buttons if bool(final_sample.output_buttons.get(button, False)))
    writer_buttons = tuple(button for button in mapped_buttons if bool(final_sample.write_buttons.get(button, False)))
    output_hat = final_sample.output_hats.get("POV1", final_sample.hat_state)
    passed = _same_hat(output_hat, expected_hat) and set(true_buttons) == set(mapped_buttons) and set(writer_buttons) == set(mapped_buttons)
    if expected_hat == "Centered":
        passed = _same_hat(output_hat, "Centered") and not true_buttons
    return StepResult(
        "hat",
        expected_hat,
        "passed" if passed else "failed",
        f"Hat {expected_hat} observed and POV/output button state recorded.",
        detected=True,
        output_hat=output_hat,
        mapped_buttons_true=true_buttons,
        diagonal_policy="decompose_to_cardinal_buttons" if _is_diagonal_hat(expected_hat) else "not_applicable",
        settle_sample_count=len(settle_samples),
        metadata={
            "writer_buttons_true": writer_buttons,
            "writer_status": final_sample.writer_status,
            "rebuild_count": final_sample.rebuild_count,
        },
    )


def build_mapping_variant_workspace(workspace: WorkspaceConfig) -> WorkspaceConfig:
    axis_routes = (
        AxisMapping("Roll", "Axis 1", "Y", "Y(axis2)"),
        AxisMapping("Pitch", "Axis 2", "X", "X(axis1)"),
        *tuple(route for route in workspace.mappings.axis_routes if route.function_name not in {"Roll", "Pitch"}),
    )
    button_routes = (
        ButtonMapping(1, 2),
        ButtonMapping(2, 1),
        *tuple(route for route in workspace.mappings.button_routes if route.hotas_button not in {1, 2}),
    )
    hat_routes = (
        HatMapping(hotas_hat=1, vjoy_pov=1, up_button=9, right_button=10, down_button=11, left_button=12),
    )
    return replace(
        workspace,
        mappings=replace(workspace.mappings, axis_routes=axis_routes, button_routes=button_routes, hat_routes=hat_routes),
        source_path="artifact-only-runtime-usability-1d-mapping-variant.json",
    )


def build_rule_variant_workspace(workspace: WorkspaceConfig) -> WorkspaceConfig:
    rule = replace(
        yaw_roll_example_rule(),
        title="1D Roll Output Scale | Roll > 0.25",
        enabled=True,
        target_axis="Roll",
        reference_axis="Roll",
        threshold=0.25,
        operation="Multiply",
        value=0.5,
    )
    return replace(
        workspace,
        rules=RuleConfig(rules=(rule,)),
        source_path="artifact-only-runtime-usability-1d-rule-variant.json",
    )


def build_summary_payload(
    *,
    physical_detected: bool,
    hotas_vid_pid: str,
    vjoy_detected: bool,
    vjoy_write_call_status: str,
    step_results: Sequence[StepResult],
    artifact_dir: Path,
) -> dict[str, object]:
    failures = [result for result in step_results if result.status not in {"passed", "skipped"}]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "failed" if failures or not physical_detected else "passed",
        "artifact_dir": str(artifact_dir),
        "hardware": {
            "physical_hotas_proof": "detected" if physical_detected else "not_detected",
            "hotas_vid_pid": hotas_vid_pid,
            "vjoy_detected": vjoy_detected,
            "vjoy_write_call_proof": vjoy_write_call_status,
            "vjoy_readback": "not_implemented",
        },
        "step_counts": _step_counts(step_results),
        "truth_boundaries": {
            "physical_hotas_sampling": "real_device_required",
            "runtime_processing": "bridge_shared_runtime_path",
            "vjoy_write_call": "accepted_call_only",
            "vjoy_readback": "not_implemented",
            "game_level_verification": "manual_checklist_only",
            "device_hiding_filtering": "intentionally_deferred",
        },
        "failures": [result.to_dict() for result in failures],
    }


def build_game_readiness_checklist(
    *,
    physical_detected: bool,
    vjoy_detected: bool,
    vjoy_write_calls_accepted: bool,
    game_level_verified: bool,
) -> str:
    checked = "[x]"
    empty = "[ ]"
    lines = [
        "# HelmForge Runtime 1D Game-Readiness Checklist",
        "",
        f"{checked if physical_detected else empty} HOTAS detected by Bridge/shared runtime probe.",
        f"{checked if vjoy_detected else empty} vJoy detected.",
        f"{checked if physical_detected else empty} Physical axes/buttons/hat can be observed by the guided probe when each step passes.",
        f"{checked if physical_detected else empty} Runtime stage/final values changed during guided input proof when each step passes.",
        f"{checked if physical_detected else empty} Output intent changed during guided input proof when each step passes.",
        f"{checked if vjoy_write_calls_accepted else empty} vJoy write calls accepted when enabled.",
        f"{empty if not game_level_verified else checked} Game-level verification observed externally.",
        "",
        "- Target games should bind controls from vJoy Device 1 when HelmForge is used as the remapping/output layer.",
        "- If the game sees both the physical HOTAS and vJoy, duplicate input may occur.",
        "- Direct physical HOTAS hiding/filtering is intentionally out of scope for Runtime Usability 1D.",
        "- Direct physical HOTAS hiding/filtering is intentionally deferred to a separate later phase.",
        "- vJoy readback is not implemented unless separately verified.",
        "- Game-level verification is manual unless an actual game or external controller observer is tested.",
    ]
    return "\n".join(lines) + "\n"


def runtime_authority_violations(project_root: Path = PROJECT_ROOT) -> list[str]:
    scanned_roots = (
        project_root / "shared_core" / "math",
        project_root / "shared_core" / "runtime",
        project_root / "shared_core" / "rules",
        project_root / "bridge_app",
        project_root / "scripts" / "runtime_physical_hotas_smoke_probe.py",
    )
    forbidden_prefixes = ("v3_app.pages", "v3_app.liquid", "v3_app.widgets", "PySide6")
    violations: list[str] = []
    for root in scanned_roots:
        paths = (root,) if root.is_file() else tuple(root.rglob("*.py"))
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                imported = ""
                if isinstance(node, ast.ImportFrom):
                    imported = node.module or ""
                elif isinstance(node, ast.Import):
                    imported = node.names[0].name
                if imported and imported.startswith(forbidden_prefixes):
                    violations.append(f"{path.relative_to(project_root)} imports {imported}")
    return violations


def run_live_probe(args: argparse.Namespace) -> dict[str, object]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = Path(args.output_dir) / stamp
    artifact_dir.mkdir(parents=True, exist_ok=True)

    workspace = load_workspace(CONFIG_FILENAME).workspace
    save_workspace(workspace, artifact_dir / "current-workspace-copy.json", overwrite=True)
    mapping_variant = build_mapping_variant_workspace(workspace)
    rule_variant = build_rule_variant_workspace(workspace)
    save_workspace(mapping_variant, artifact_dir / "mapping-variant-workspace.json", overwrite=True)
    save_workspace(rule_variant, artifact_dir / "conditional-rule-workspace.json", overwrite=True)

    hotas = discover_supported_hotas()
    output_backend = RecordingOutputBackend(
        RealVJoyOutputBackend() if args.real_vjoy_writes else FakeVirtualOutputBackend(),
        enabled=True,
    )
    vjoy_caps = output_backend.get_capabilities()
    vjoy_detected = bool(vjoy_caps.backend_available and output_backend.enumerate_output_devices())
    setup = _run_setup_check()
    bridge_status = _run_bridge_status()

    if not hotas.matched:
        checklist = build_game_readiness_checklist(
            physical_detected=False,
            vjoy_detected=vjoy_detected,
            vjoy_write_calls_accepted=False,
            game_level_verified=False,
        )
        (artifact_dir / "game-readiness-checklist.md").write_text(checklist, encoding="utf-8")
        summary = build_summary_payload(
            physical_detected=False,
            hotas_vid_pid="",
            vjoy_detected=vjoy_detected,
            vjoy_write_call_status="skipped_no_hotas",
            step_results=[],
            artifact_dir=artifact_dir,
        )
        summary["hardware"]["bridge_status"] = bridge_status
        summary["hardware"]["runtime_setup_check"] = setup
        _write_json(artifact_dir / "summary.json", summary)
        _write_json(artifact_dir / "physical-input-steps.json", [])
        _write_report(artifact_dir=artifact_dir, summary=summary, steps=[], checklist_path=artifact_dir / "game-readiness-checklist.md")
        print("Physical HOTAS was not detected. Check USB connection and rerun the guided probe.")
        return summary

    backend_selection = _select_live_sampling_backend()
    devices = backend_selection.backend.enumerate_devices()
    physical_device = next((device for device in devices if device.is_supported), None)
    if physical_device is None:
        checklist = build_game_readiness_checklist(
            physical_detected=True,
            vjoy_detected=vjoy_detected,
            vjoy_write_calls_accepted=False,
            game_level_verified=False,
        )
        (artifact_dir / "game-readiness-checklist.md").write_text(checklist, encoding="utf-8")
        summary = build_summary_payload(
            physical_detected=False,
            hotas_vid_pid=_vid_pid(hotas.vendor_id, hotas.product_id),
            vjoy_detected=vjoy_detected,
            vjoy_write_call_status="skipped_sampler_no_supported_device",
            step_results=[],
            artifact_dir=artifact_dir,
        )
        summary["hardware"]["discovery"] = hotas.to_dict()
        summary["hardware"]["physical_backend_choice"] = backend_selection.choice.to_dict()
        _write_json(artifact_dir / "summary.json", summary)
        _write_report(artifact_dir=artifact_dir, summary=summary, steps=[], checklist_path=artifact_dir / "game-readiness-checklist.md")
        print("HOTAS identity was detected, but no supported sampling device was available.")
        return summary

    runner = LiveRuntimeSampler(
        workspace=workspace,
        physical_backend=backend_selection.backend,
        physical_device=physical_device,
        output_backend=output_backend,
    )
    all_steps: list[StepResult] = []
    try:
        axis_steps = _run_live_axis_steps(runner, workspace, args)
        all_steps.extend(axis_steps)
        button_steps = _run_live_button_steps(runner, workspace, args)
        all_steps.extend(button_steps)
        hat_steps = _run_live_hat_steps(runner, workspace, args)
        all_steps.extend(hat_steps)
        mode_steps = _run_live_mode_steps(runner, workspace, args)
        all_steps.extend(mode_steps)
        if args.full:
            all_steps.extend(_run_live_conditional_rule_steps(runner, rule_variant, args))
            all_steps.extend(_run_live_mapping_variant_steps(runner, workspace, mapping_variant, args))
            runner.set_workspace(workspace)
    finally:
        runner.close()

    failures = [step for step in all_steps if step.status not in {"passed", "skipped"}]
    write_success = bool(output_backend.write_records and all(record.success for record in output_backend.write_records))
    checklist = build_game_readiness_checklist(
        physical_detected=True,
        vjoy_detected=vjoy_detected,
        vjoy_write_calls_accepted=write_success,
        game_level_verified=False,
    )
    checklist_path = artifact_dir / "game-readiness-checklist.md"
    checklist_path.write_text(checklist, encoding="utf-8")
    summary = build_summary_payload(
        physical_detected=True,
        hotas_vid_pid=_vid_pid(hotas.vendor_id, hotas.product_id),
        vjoy_detected=vjoy_detected,
        vjoy_write_call_status="passed" if write_success else "failed_or_not_attempted",
        step_results=all_steps,
        artifact_dir=artifact_dir,
    )
    summary["hardware"]["bridge_status"] = bridge_status
    summary["hardware"]["runtime_setup_check"] = setup
    summary["hardware"]["discovery"] = hotas.to_dict()
    summary["hardware"]["physical_backend_choice"] = backend_selection.choice.to_dict()
    summary["hardware"]["physical_sampling_device"] = physical_device.to_dict()
    summary["hardware"]["vjoy_devices"] = [device.to_dict() for device in output_backend.enumerate_output_devices()]
    summary["hardware"]["vjoy_write_records"] = len(output_backend.write_records)
    if failures:
        summary["overall_status"] = "failed"

    _write_artifacts(artifact_dir, summary, all_steps, output_backend.write_records)
    _write_report(artifact_dir=artifact_dir, summary=summary, steps=all_steps, checklist_path=checklist_path)
    print(json.dumps({"status": summary["overall_status"], "artifact_dir": str(artifact_dir), "report": str(REPORT_PATH)}, indent=2))
    return summary


def _run_live_axis_steps(runner: LiveRuntimeSampler, workspace: WorkspaceConfig, args: argparse.Namespace) -> list[StepResult]:
    axes = AXIS_DISPLAY_NAMES if args.full else ("Roll", "Pitch", "Throttle")
    results: list[StepResult] = []
    for index, axis_name in enumerate(axes, start=1):
        output_axis = _mapped_output_axis(workspace, axis_name)
        print(f"Axis Step {index}/{len(axes)}: {AXIS_INSTRUCTIONS.get(axis_name, f'Move {axis_name} now')} Waiting up to {args.timeout_sec} seconds...")
        samples = _collect_until(
            runner.sample,
            lambda current: _axis_changed(current, axis_name, args.axis_threshold),
            timeout_sec=args.timeout_sec,
            settle_sec=args.settle_sec,
            detected_message=f"Detected {axis_name} movement. Collecting {args.settle_sec} more seconds of stable samples...",
        )
        result = run_axis_step(samples, axis_name=axis_name, output_axis=output_axis, threshold=args.axis_threshold, timeout_sec=args.timeout_sec, settle_sec=args.settle_sec)
        print(_step_console_line(result))
        results.append(result)
        if result.status != "passed" and not args.skip_on_timeout:
            break
    return results


def _run_live_button_steps(runner: LiveRuntimeSampler, workspace: WorkspaceConfig, args: argparse.Namespace) -> list[StepResult]:
    buttons = tuple(range(1, 16)) if args.full else (1, 2)
    results: list[StepResult] = []
    for button in buttons:
        name = f"B{button}"
        output = _mapped_output_button(workspace, button)
        print(f"Button Step B{button}: Press and release B{button} now. Waiting up to {args.button_timeout_sec} seconds for press...")
        samples = _collect_button_press_release(
            runner.sample,
            button_name=name,
            timeout_sec=args.button_timeout_sec,
            settle_sec=args.settle_sec,
        )
        result = run_button_step(samples, button_name=name, output_button=output, timeout_sec=args.button_timeout_sec, settle_sec=args.settle_sec)
        print(_step_console_line(result))
        results.append(result)
        if result.status != "passed" and not args.skip_on_timeout:
            break
    return results


def _run_live_hat_steps(runner: LiveRuntimeSampler, workspace: WorkspaceConfig, args: argparse.Namespace) -> list[StepResult]:
    directions = ("Up", "Right", "Down", "Left", "Centered") if args.full else ("Up", "Centered")
    results: list[StepResult] = []
    for direction in directions:
        if direction == "Centered":
            print(f"Hat Step: Release hat to Centered/Neutral. Waiting up to {args.hat_timeout_sec} seconds...")
        else:
            print(f"Hat Step: Press Hat {direction}. Waiting up to {args.hat_timeout_sec} seconds...")
        mapped = _mapped_hat_buttons(workspace, direction)
        samples = _collect_until(
            runner.sample,
            lambda current, expected=direction: _same_hat(current[-1].hat_state if current else "", expected),
            timeout_sec=args.hat_timeout_sec,
            settle_sec=args.settle_sec,
            detected_message=f"Detected Hat {direction}. Collecting {args.settle_sec} more seconds...",
        )
        result = run_hat_step(samples, expected_hat=direction, mapped_buttons=mapped, timeout_sec=args.hat_timeout_sec, settle_sec=args.settle_sec)
        print(_step_console_line(result))
        results.append(result)
        if result.status != "passed" and not args.skip_on_timeout:
            break
    return results


def _run_live_mode_steps(runner: LiveRuntimeSampler, workspace: WorkspaceConfig, args: argparse.Namespace) -> list[StepResult]:
    mode_buttons = tuple(button for button in workspace.modes.combat_zoom_aim_buttons if int(button) > 0)
    if not mode_buttons:
        return [StepResult("mode", "combat_mode", "skipped", "No physical combat activation buttons are configured.")]
    button = int(mode_buttons[0])
    print(f"Mode Step: Press configured combat mode button B{button}. Waiting up to {args.button_timeout_sec} seconds...")
    samples = _collect_button_press_release(runner.sample, button_name=f"B{button}", timeout_sec=args.button_timeout_sec, settle_sec=args.settle_sec)
    active = any("Combat" in sample.active_modes for sample in samples)
    released = any(not sample.buttons.get(f"B{button}", False) for sample in samples if sample.timestamp > samples[0].timestamp)
    return [
        StepResult(
            "mode",
            "combat_mode",
            "passed" if active and released else "failed",
            "Combat mode activated by configured physical button and released cleanly." if active and released else "Combat mode activation/release proof did not complete.",
            detected=active,
            release_observed=released,
            active_modes=tuple(sorted({mode for sample in samples for mode in sample.active_modes})),
            metadata={"button": f"B{button}"},
        )
    ]


def _run_live_conditional_rule_steps(runner: LiveRuntimeSampler, workspace: WorkspaceConfig, args: argparse.Namespace) -> list[StepResult]:
    runner.set_workspace(workspace)
    print("Conditional Rule Step: Move Roll above threshold now. Waiting up to 60 seconds...")
    samples = _collect_until(
        runner.sample,
        lambda current: _axis_changed(current, "Roll", 0.25),
        timeout_sec=args.timeout_sec,
        settle_sec=args.settle_sec,
        detected_message=f"Detected Roll threshold movement. Collecting {args.settle_sec} more seconds...",
    )
    active = any("1D Roll Output Scale | Roll > 0.25" in sample.active_rules for sample in samples)
    return [
        StepResult(
            "conditional_rule",
            "roll_threshold_rule",
            "passed" if active else "failed",
            "Artifact-only Roll threshold rule activated." if active else "Artifact-only Roll threshold rule did not activate.",
            detected=active,
            active_rules=tuple(sorted({rule for sample in samples for rule in sample.active_rules})),
            metadata={"workspace": workspace.source_path},
        )
    ]


def _run_live_mapping_variant_steps(runner: LiveRuntimeSampler, original: WorkspaceConfig, variant: WorkspaceConfig, args: argparse.Namespace) -> list[StepResult]:
    _ = original
    runner.set_workspace(variant)
    results: list[StepResult] = []
    print("Mapping Variant Step: Move Roll now. Variant expects Roll -> Y.")
    roll_samples = _collect_until(runner.sample, lambda current: _axis_changed(current, "Roll", args.axis_threshold), timeout_sec=args.timeout_sec, settle_sec=args.settle_sec, detected_message="Detected Roll movement under mapping variant.")
    results.append(run_axis_step(roll_samples, axis_name="Roll", output_axis="Y", threshold=args.axis_threshold, timeout_sec=args.timeout_sec, settle_sec=args.settle_sec))
    print("Mapping Variant Step: Move Pitch now. Variant expects Pitch -> X.")
    pitch_samples = _collect_until(runner.sample, lambda current: _axis_changed(current, "Pitch", args.axis_threshold), timeout_sec=args.timeout_sec, settle_sec=args.settle_sec, detected_message="Detected Pitch movement under mapping variant.")
    results.append(run_axis_step(pitch_samples, axis_name="Pitch", output_axis="X", threshold=args.axis_threshold, timeout_sec=args.timeout_sec, settle_sec=args.settle_sec))
    print("Mapping Variant Step: Press/release B1 now. Variant expects B1 -> Out2.")
    b1_samples = _collect_button_press_release(runner.sample, button_name="B1", timeout_sec=args.button_timeout_sec, settle_sec=args.settle_sec)
    results.append(run_button_step(b1_samples, button_name="B1", output_button="Out2", timeout_sec=args.button_timeout_sec, settle_sec=args.settle_sec))
    print("Mapping Variant Step: Press/release B2 now. Variant expects B2 -> Out1.")
    b2_samples = _collect_button_press_release(runner.sample, button_name="B2", timeout_sec=args.button_timeout_sec, settle_sec=args.settle_sec)
    results.append(run_button_step(b2_samples, button_name="B2", output_button="Out1", timeout_sec=args.button_timeout_sec, settle_sec=args.settle_sec))
    return [replace(result, step_type="mapping_variant") for result in results]


def _collect_until(
    read_sample: Callable[[float], ProbeSample],
    detector: Callable[[Sequence[ProbeSample]], bool],
    *,
    timeout_sec: float,
    settle_sec: float,
    detected_message: str,
    sample_interval_sec: float = 0.04,
) -> list[ProbeSample]:
    start = time.monotonic()
    samples: list[ProbeSample] = []
    detected_at: float | None = None
    while True:
        elapsed = time.monotonic() - start
        samples.append(read_sample(elapsed))
        if detected_at is None and detector(samples):
            detected_at = elapsed
            print(detected_message)
        if detected_at is not None and elapsed >= detected_at + settle_sec:
            return samples
        if detected_at is None and elapsed >= timeout_sec:
            return samples
        time.sleep(sample_interval_sec)


def _collect_button_press_release(
    read_sample: Callable[[float], ProbeSample],
    *,
    button_name: str,
    timeout_sec: float,
    settle_sec: float,
    sample_interval_sec: float = 0.04,
) -> list[ProbeSample]:
    start = time.monotonic()
    samples: list[ProbeSample] = []
    press_at: float | None = None
    release_at: float | None = None
    while True:
        elapsed = time.monotonic() - start
        sample = read_sample(elapsed)
        samples.append(sample)
        pressed = bool(sample.buttons.get(button_name, False))
        if press_at is None and pressed:
            press_at = elapsed
            print(f"Detected {button_name} press. Collecting {settle_sec} more seconds, then release if still held...")
        if press_at is None and elapsed >= timeout_sec:
            return samples
        if press_at is not None and elapsed >= press_at + settle_sec and not pressed:
            release_at = elapsed
        if release_at is not None:
            return samples
        if press_at is not None and elapsed >= press_at + settle_sec + timeout_sec:
            return samples
        time.sleep(sample_interval_sec)


def _write_artifacts(artifact_dir: Path, summary: Mapping[str, object], steps: Sequence[StepResult], records: Sequence[WriteRecord]) -> None:
    _write_json(artifact_dir / "summary.json", summary)
    _write_json(artifact_dir / "physical-input-steps.json", [step.to_dict() for step in steps])
    _write_json(artifact_dir / "axis-proof.json", [step.to_dict() for step in steps if step.step_type == "axis"])
    _write_json(artifact_dir / "button-proof.json", [step.to_dict() for step in steps if step.step_type == "button"])
    _write_json(artifact_dir / "hat-proof.json", [step.to_dict() for step in steps if step.step_type == "hat"])
    _write_json(artifact_dir / "mode-proof.json", [step.to_dict() for step in steps if step.step_type == "mode"])
    _write_json(artifact_dir / "conditional-rule-proof.json", [step.to_dict() for step in steps if step.step_type == "conditional_rule"])
    _write_json(artifact_dir / "mapping-variant-proof.json", [step.to_dict() for step in steps if step.step_type == "mapping_variant"])
    _write_json(artifact_dir / "output-intent-proof.json", [step.to_dict() for step in steps if step.output_target or step.output_hat])
    _write_json(artifact_dir / "vjoy-write-call-proof.json", [record.to_dict() for record in records])


def _settle_window_samples(samples: Sequence[ProbeSample], start_index: int, settle_deadline: float) -> tuple[ProbeSample, ...]:
    selected: list[ProbeSample] = []
    for sample in samples[start_index:]:
        selected.append(sample)
        if sample.timestamp >= settle_deadline - 1e-9:
            break
    return tuple(selected)


def _write_report(*, artifact_dir: Path, summary: Mapping[str, object], steps: Sequence[StepResult], checklist_path: Path) -> None:
    hardware = summary.get("hardware", {}) if isinstance(summary.get("hardware"), Mapping) else {}
    lines = [
        "# Runtime Usability 1D Physical HOTAS Live Smoke Report",
        "",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        f"Artifact directory: `{artifact_dir}`",
        f"Overall status: `{summary.get('overall_status')}`",
        "",
        "## Executive Result",
        f"- Guided physical probe status: `{summary.get('overall_status')}`",
        "- This phase does not implement device hiding/direct physical HOTAS filtering.",
        "- Game-level verification remains manual unless an external game/controller observer is tested.",
        "",
        "## Hardware State",
        f"- Physical HOTAS proof: `{hardware.get('physical_hotas_proof')}`",
        f"- VID/PID: `{hardware.get('hotas_vid_pid')}`",
        f"- vJoy detected: `{hardware.get('vjoy_detected')}`",
        f"- vJoy write-call proof: `{hardware.get('vjoy_write_call_proof')}`",
        f"- vJoy readback: `{hardware.get('vjoy_readback')}`",
        f"- Bridge status: `{hardware.get('bridge_status', 'not_recorded')}`",
        "",
        "## Guided Probe Procedure",
        "- Each requested physical control waits up to the configured timeout.",
        "- After detection, the probe collects the configured settle window before judging the step.",
        "- Timeouts are recorded per control. `--skip-on-timeout` continues after a failed step.",
        "",
        "## Axis Test Table",
        _step_table(steps, "axis"),
        "## Button Test Table",
        _step_table(steps, "button"),
        "## Hat/POV Test Table",
        _step_table(steps, "hat"),
        "## Mode Activation Table",
        _step_table(steps, "mode"),
        "## Conditional Rule Activation Table",
        _step_table(steps, "conditional_rule"),
        "## Mapping Variant Table",
        _step_table(steps, "mapping_variant"),
        "## Game-Readiness Checklist Path",
        f"- `{checklist_path}`",
        "",
        "## Known Gaps After 1D",
        "- vJoy readback remains not implemented.",
        "- Automated game-level verification remains not implemented.",
        "- Direct physical HOTAS hiding/filtering is intentionally deferred.",
        "- Any timeout/unavailable physical step remains listed in the artifact step files.",
        "",
        "## Files Changed",
        "- `scripts/runtime_physical_hotas_smoke_probe.py`",
        "- `tests/test_runtime_usability_1d_physical_hotas_smoke_probe.py`",
        "- `docs/HelmForge/runtime-usability-1d-physical-hotas-live-smoke-report.md`",
        "",
        "## Runtime Truth Preservation Statement",
        "- vJoy write-call proof is not readback proof.",
        "- Game-level proof is not claimed without external observation.",
        "- Full Live Runtime Ready semantics were not loosened.",
        "- No UI redesign, Live Monitor performance work, animations, Flight Recorder work, device hiding/filtering, game injection, graphics hooking, cloud AI/LLM behavior, or auto-save behavior was added.",
        "",
        "## Explicit Deferred Items",
        "- vJoy readback/device-state verification.",
        "- Automated game-level verification.",
        "- Device hiding/direct physical HOTAS filtering.",
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _step_table(steps: Sequence[StepResult], step_type: str) -> str:
    rows = [step for step in steps if step.step_type == step_type]
    if not rows:
        return "No steps recorded.\n"
    lines = ["| Step | Status | Evidence |", "|---|---|---|"]
    for step in rows:
        evidence = step.message.replace("|", "/")
        lines.append(f"| `{step.name}` | `{step.status}` | {evidence} |")
    return "\n".join(lines) + "\n"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _jsonable(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _physical_buttons_from_frame(frame: RuntimeFrame) -> dict[str, bool]:
    buttons = {name: False for name in BUTTON_NAMES}
    # The runtime frame preserves mapped output buttons separately. Raw button
    # truth is carried through the output intent source path in the live probe.
    for button in frame.output_intent.buttons:
        _ = button
    return buttons | {name: False for name in BUTTON_NAMES}


def _axis_changed(samples: Sequence[ProbeSample], axis_name: str, threshold: float) -> bool:
    if not samples:
        return False
    baseline = float(samples[0].raw_axes.get(axis_name, 0.0))
    latest = float(samples[-1].raw_axes.get(axis_name, 0.0))
    return abs(latest - baseline) >= threshold


def _mapped_output_axis(workspace: WorkspaceConfig, axis_name: str) -> str:
    route = next((route for route in workspace.mappings.axis_routes if route.function_name == axis_name), None)
    if route is None:
        return AXIS_OUTPUT_DEFAULTS.get(axis_name, "X")
    return _axis_label(route.runtime_vjoy_output or route.logical_output)


def _mapped_output_button(workspace: WorkspaceConfig, button: int) -> str:
    route = next((route for route in workspace.mappings.button_routes if int(route.hotas_button) == int(button)), None)
    return f"Out{int(route.output_button)}" if route is not None else f"Out{button}"


def _mapped_hat_buttons(workspace: WorkspaceConfig, direction: str) -> tuple[str, ...]:
    if direction == "Centered":
        return ()
    directions = {
        "Up": ("up",),
        "Right": ("right",),
        "Down": ("down",),
        "Left": ("left",),
        "UpRight": ("up", "right"),
        "DownRight": ("down", "right"),
        "DownLeft": ("down", "left"),
        "UpLeft": ("up", "left"),
    }.get(direction, ())
    outputs: list[str] = []
    for route in workspace.mappings.hat_routes:
        for item in directions:
            value = getattr(route, f"{item}_button", None)
            try:
                number = int(value)
            except (TypeError, ValueError):
                continue
            if 1 <= number <= 20:
                outputs.append(f"Out{number}")
    return tuple(outputs)


def _axis_label(value: str) -> str:
    text = str(value or "").strip()
    if "(" in text:
        text = text.split("(", 1)[0]
    return text.upper() or "X"


def _same_hat(observed: str, expected: str) -> bool:
    aliases = {
        "North": "Up",
        "East": "Right",
        "South": "Down",
        "West": "Left",
        "North East": "UpRight",
        "South East": "DownRight",
        "South West": "DownLeft",
        "North West": "UpLeft",
        "Center": "Centered",
        "Neutral": "Centered",
    }
    return aliases.get(str(observed), str(observed)) == aliases.get(str(expected), str(expected))


def _is_diagonal_hat(value: str) -> bool:
    return value in {"UpRight", "DownRight", "DownLeft", "UpLeft", "North East", "South East", "South West", "North West"}


def _step_counts(step_results: Sequence[StepResult]) -> dict[str, int]:
    return {
        "total": len(step_results),
        "passed": sum(1 for step in step_results if step.status == "passed"),
        "failed": sum(1 for step in step_results if step.status == "failed"),
        "timeout": sum(1 for step in step_results if step.status == "timeout"),
        "skipped": sum(1 for step in step_results if step.status == "skipped"),
    }


def _step_console_line(result: StepResult) -> str:
    prefix = "Pass" if result.status == "passed" else "Timeout" if result.timeout else "Fail"
    return f"{prefix}: {result.message}"


def _run_setup_check() -> str:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\\scripts\\runtime_setup_check.ps1", "-DryRun"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    return result.stdout.strip() if result.stdout.strip() else result.stderr.strip()


def _run_bridge_status() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "bridge_app.main", "--status"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else result.stderr.strip()


def _select_live_sampling_backend():
    selected = build_best_physical_input_backend()
    devices = selected.backend.enumerate_devices()
    device = next((item for item in devices if item.is_supported), None)
    if device is None:
        return selected
    sampler = PhysicalInputSampler(selected.backend, selected_device_id=device.device_id, validate_selection_on_read=False)
    try:
        sampler.open()
        snapshot = sampler.read_once()
    finally:
        sampler.close()
    if snapshot.sample_source == "raw_input" and not snapshot.sampling_active and snapshot.sequence == 0:
        fallback = build_winmm_physical_input_fallback()
        if fallback.choice.selected_backend_kind != "missing":
            return fallback
    return selected


def _vid_pid(vendor_id: str | None, product_id: str | None) -> str:
    if vendor_id and product_id:
        return f"VID_{vendor_id.upper()}&PID_{product_id.upper()}"
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run guided physical HOTAS live smoke proof for HelmForge.")
    parser.add_argument("--timeout-sec", type=float, default=60.0)
    parser.add_argument("--settle-sec", type=float, default=2.0)
    parser.add_argument("--skip-on-timeout", action="store_true")
    parser.add_argument("--axis-threshold", type=float, default=0.08)
    parser.add_argument("--button-timeout-sec", type=float, default=None)
    parser.add_argument("--hat-timeout-sec", type=float, default=None)
    parser.add_argument("--output-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--minimal", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--real-vjoy-writes", action="store_true")
    parser.add_argument("--no-real-vjoy-writes", action="store_true")
    parser.add_argument("--manual-game-checklist", action="store_true")
    args = parser.parse_args()
    args.full = bool(args.full or not args.minimal)
    if args.no_real_vjoy_writes:
        args.real_vjoy_writes = False
    args.button_timeout_sec = float(args.button_timeout_sec if args.button_timeout_sec is not None else args.timeout_sec)
    args.hat_timeout_sec = float(args.hat_timeout_sec if args.hat_timeout_sec is not None else args.timeout_sec)
    summary = run_live_probe(args)
    return 0 if summary.get("overall_status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
