from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from shared_core.models.runtime import AXIS_NAMES, BUTTON_NAMES, HAT_CENTERED
from shared_core.runtime.hotas_input import (
    PhysicalInputBackend,
    PhysicalInputSelectionStatus,
    PhysicalInputSamplingStatus,
    PhysicalInputSnapshot,
    resolve_physical_input_selection,
)


@dataclass(frozen=True)
class PhysicalInputSourceStatus:
    source_label: str
    source_status: str
    selected_device_name: str
    sample_age_text: str
    sample_source: str
    sampling_active: bool
    warning_text: str
    error_text: str
    fallback_behavior: str
    axis_count: int = 0
    button_count: int = 0
    hat_count: int = 0
    is_fresh_physical_sample: bool = False
    is_stale: bool = False


def build_input_source_status(
    *,
    backend: PhysicalInputBackend | None,
    selected_device_id: str | None,
    latest_snapshot: PhysicalInputSnapshot | None,
    now: datetime | None = None,
    stale_after_seconds: float = 2.0,
) -> PhysicalInputSourceStatus:
    now = now or datetime.now(timezone.utc)
    if latest_snapshot is None:
        selected_name = "None"
        if backend is not None:
            selection = resolve_physical_input_selection(backend, selected_device_id=selected_device_id)
            selected_name = selection.selected_device_display_name
            if selected_device_id:
                if selection.selection_status is PhysicalInputSelectionStatus.BACKEND_UNAVAILABLE:
                    return PhysicalInputSourceStatus(
                        source_label="Simulation",
                        source_status="Backend unavailable",
                        selected_device_name=selected_name,
                        sample_age_text="Unavailable",
                        sample_source="unavailable",
                        sampling_active=False,
                        warning_text="Simulation fallback remains available.",
                        error_text="None",
                        fallback_behavior="Simulation fallback active; physical input backend unavailable.",
                    )
                if selection.selection_status is PhysicalInputSelectionStatus.SELECTED_DEVICE_MISSING:
                    return PhysicalInputSourceStatus(
                        source_label="Physical unavailable",
                        source_status="Selected physical device missing",
                        selected_device_name=selected_name,
                        sample_age_text="Unavailable",
                        sample_source="unavailable",
                        sampling_active=False,
                        warning_text="Simulation fallback remains available.",
                        error_text="Selected physical input device is missing.",
                        fallback_behavior="Simulation fallback active; selected physical input device is missing.",
                    )
                if selection.selection_status is PhysicalInputSelectionStatus.UNSUPPORTED_DEVICE_SELECTED:
                    return PhysicalInputSourceStatus(
                        source_label="Physical unavailable",
                        source_status="Unsupported physical device selected",
                        selected_device_name=selected_name,
                        sample_age_text="Unavailable",
                        sample_source="unavailable",
                        sampling_active=False,
                        warning_text="Simulation fallback remains available.",
                        error_text="Selected physical input device is unsupported.",
                        fallback_behavior="Simulation fallback active; selected physical input device is unsupported.",
                    )
                if selection.selection_status is PhysicalInputSelectionStatus.SELECTED_DEVICE_AVAILABLE:
                    return PhysicalInputSourceStatus(
                        source_label="Physical unavailable",
                        source_status="Sampling unavailable",
                        selected_device_name=selected_name,
                        sample_age_text="Unavailable",
                        sample_source="unavailable",
                        sampling_active=False,
                        warning_text="Simulation fallback remains available.",
                        error_text="None",
                        fallback_behavior="Simulation fallback active; no current physical input sample is available.",
                    )
            elif selection.selection_status is PhysicalInputSelectionStatus.NO_DEVICE_SELECTED:
                return PhysicalInputSourceStatus(
                    source_label="Simulation",
                    source_status="No physical device selected",
                    selected_device_name=selected_name,
                    sample_age_text="Unavailable",
                    sample_source="simulation",
                    sampling_active=False,
                    warning_text="Simulation fallback remains available.",
                    error_text="None",
                    fallback_behavior="Simulation fallback active; no physical input device is selected.",
                )
        return PhysicalInputSourceStatus(
            source_label="Simulation",
            source_status="Simulation fallback",
            selected_device_name=selected_name,
            sample_age_text="Unavailable",
            sample_source="simulation",
            sampling_active=False,
            warning_text="None",
            error_text="None",
            fallback_behavior="Using simulation/fallback input values.",
        )

    age = _sample_age_seconds(latest_snapshot, now)
    age_text = "Unavailable" if age is None else f"{age:.1f}s"
    warnings = "; ".join(latest_snapshot.warnings) if latest_snapshot.warnings else "None"
    errors = "; ".join(latest_snapshot.errors) if latest_snapshot.errors else "None"
    selected_name = latest_snapshot.device_name or "None"

    if latest_snapshot.sampling_status is PhysicalInputSamplingStatus.ERROR:
        return PhysicalInputSourceStatus(
            source_label="Physical unavailable",
            source_status="Physical sample error",
            selected_device_name=selected_name,
            sample_age_text=age_text,
            sample_source=latest_snapshot.sample_source,
            sampling_active=False,
            warning_text=warnings,
            error_text=errors,
            fallback_behavior="Physical sample error; falling back to simulation/fallback input values.",
            axis_count=latest_snapshot.axis_count,
            button_count=latest_snapshot.button_count,
            hat_count=latest_snapshot.hat_count,
        )

    if age is not None and age > stale_after_seconds:
        return PhysicalInputSourceStatus(
            source_label="Physical unavailable",
            source_status="Physical sample stale",
            selected_device_name=selected_name,
            sample_age_text=age_text,
            sample_source=latest_snapshot.sample_source,
            sampling_active=False,
            warning_text=warnings,
            error_text=errors,
            fallback_behavior="Physical sample is stale; falling back to simulation/fallback input values.",
            axis_count=latest_snapshot.axis_count,
            button_count=latest_snapshot.button_count,
            hat_count=latest_snapshot.hat_count,
            is_stale=True,
        )

    if latest_snapshot.sampling_status is PhysicalInputSamplingStatus.ACTIVE and latest_snapshot.sampling_active:
        return PhysicalInputSourceStatus(
            source_label="Physical input",
            source_status="Physical input sampling active",
            selected_device_name=selected_name,
            sample_age_text=age_text,
            sample_source=latest_snapshot.sample_source,
            sampling_active=True,
            warning_text=warnings,
            error_text=errors,
            fallback_behavior="Using read-only physical input sample values.",
            axis_count=latest_snapshot.axis_count,
            button_count=latest_snapshot.button_count,
            hat_count=latest_snapshot.hat_count,
            is_fresh_physical_sample=True,
        )

    return PhysicalInputSourceStatus(
        source_label="Physical unavailable",
        source_status="Physical input unavailable",
        selected_device_name=selected_name,
        sample_age_text=age_text,
        sample_source=latest_snapshot.sample_source,
        sampling_active=False,
        warning_text=warnings,
        error_text=errors,
        fallback_behavior="Using simulation/fallback input values.",
        axis_count=latest_snapshot.axis_count,
        button_count=latest_snapshot.button_count,
        hat_count=latest_snapshot.hat_count,
    )


def raw_axes_from_physical_snapshot(snapshot: PhysicalInputSnapshot) -> dict[str, float]:
    values = {axis: 0.0 for axis in AXIS_NAMES}
    for axis in snapshot.axes:
        logical = axis.logical_name or axis.raw_name
        if logical in values:
            values[logical] = float(axis.normalized_value)
    return values


def buttons_from_physical_snapshot(snapshot: PhysicalInputSnapshot) -> dict[str, bool]:
    values = {button: False for button in BUTTON_NAMES}
    for button in snapshot.buttons:
        name = f"B{button.button_index}"
        if name in values:
            values[name] = bool(button.pressed)
    return values


def hat_from_physical_snapshot(snapshot: PhysicalInputSnapshot) -> str:
    return snapshot.hats[0].normalized_direction if snapshot.hats else HAT_CENTERED


def _sample_age_seconds(snapshot: PhysicalInputSnapshot, now: datetime) -> float | None:
    if snapshot.sampled_at is None:
        return None
    sampled_at = snapshot.sampled_at
    if sampled_at.tzinfo is None:
        sampled_at = sampled_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return max(0.0, (now - sampled_at).total_seconds())
