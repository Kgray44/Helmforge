from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping

from shared_core.models.runtime import InputStatus, OutputStatus, RuntimeTruth
from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState
from shared_core.runtime.hotas_discovery import HotasDiscoveryResult


@dataclass(frozen=True)
class AxisTelemetrySnapshot:
    values: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "values",
            MappingProxyType({name: float(value) for name, value in self.values.items()}),
        )

    def to_dict(self) -> dict[str, float]:
        return dict(self.values)


@dataclass(frozen=True)
class ButtonHatTelemetrySnapshot:
    buttons: Mapping[str, bool] = field(default_factory=dict)
    hats: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "buttons",
            MappingProxyType({name: bool(value) for name, value in self.buttons.items()}),
        )
        object.__setattr__(self, "hats", MappingProxyType(dict(self.hats)))

    def to_dict(self) -> dict[str, object]:
        return {
            "buttons": dict(self.buttons),
            "hats": dict(self.hats),
        }


@dataclass(frozen=True)
class ModeStateTelemetrySnapshot:
    precision_active: bool = False
    combat_active: bool = False
    zoom_active: bool = False
    extra_active: bool = False
    active_mode_names: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        names = list(self.active_mode_names)
        if self.precision_active and "Precision" not in names:
            names.append("Precision")
        if self.combat_active and "Combat" not in names:
            names.append("Combat")
        if self.zoom_active and "Combat Zoom/Aim" not in names:
            names.append("Combat Zoom/Aim")
        if self.extra_active and "Combat Extra" not in names:
            names.append("Combat Extra")

        return {
            "precision_active": self.precision_active,
            "combat_active": self.combat_active,
            "zoom_active": self.zoom_active,
            "extra_active": self.extra_active,
            "active_mode_names": names,
        }


@dataclass(frozen=True)
class RuleStateSummary:
    active_count: int = 0
    blocked_count: int = 0
    disabled_count: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "active_count": self.active_count,
            "blocked_count": self.blocked_count,
            "disabled_count": self.disabled_count,
        }


@dataclass(frozen=True)
class OutputVerificationState:
    verified: bool = False
    backend_name: str | None = None
    last_verified_at: datetime | None = None
    message: str = "Live output writes are not verified."

    def to_dict(self) -> dict[str, object]:
        return {
            "verified": self.verified,
            "backend_name": self.backend_name,
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "message": self.message,
        }


@dataclass(frozen=True)
class BridgeCommandStatusSnapshot:
    request_id: str
    command: str
    status: str
    received_at: datetime
    completed_at: datetime | None = None
    updated_at: datetime | None = None
    message: str = ""
    error: str | None = None
    schema_version: str = "helmforge.bridge_command_status.v1"
    config_path: str | None = None
    config_status: str | None = None
    expected_workspace_hash: str | None = None
    expected_workspace_revision: str | None = None
    loaded_workspace_hash: str | None = None
    loaded_workspace_revision: str | None = None
    config_match: bool | None = None
    mismatch_reason: str = ""

    def to_dict(self) -> dict[str, object]:
        updated = self.updated_at or self.completed_at or self.received_at
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "command": self.command,
            "status": self.status,
            "received_at": self.received_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": updated.isoformat(),
            "message": self.message,
            "error": self.error,
        }
        payload.update(
            {
                "config_path": self.config_path,
                "config_status": self.config_status,
                "expected_workspace_hash": self.expected_workspace_hash,
                "expected_workspace_revision": self.expected_workspace_revision,
                "loaded_workspace_hash": self.loaded_workspace_hash,
                "loaded_workspace_revision": self.loaded_workspace_revision,
                "config_match": self.config_match,
                "mismatch_reason": self.mismatch_reason,
            }
        )
        return payload


@dataclass(frozen=True)
class BridgeTelemetrySnapshot:
    runtime_truth: RuntimeTruth
    lifecycle_state: BridgeLifecycleState
    input_status: InputStatus
    output_status: OutputStatus
    raw_axes: AxisTelemetrySnapshot
    final_axes: AxisTelemetrySnapshot
    controls: ButtonHatTelemetrySnapshot
    active_modes: ModeStateTelemetrySnapshot
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active_profile: str = "Current Workspace"
    rule_summary: RuleStateSummary = field(default_factory=RuleStateSummary)
    output_verification: OutputVerificationState = field(default_factory=OutputVerificationState)
    runtime_frame: Mapping[str, object] | None = None
    last_command: BridgeCommandStatusSnapshot | None = None
    device_discovery: HotasDiscoveryResult | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def output_verified(self) -> bool:
        return self.output_verification.verified

    def to_dict(self) -> dict[str, object]:
        control_payload = self.controls.to_dict()
        return {
            "timestamp": self.timestamp.isoformat(),
            "runtime_truth": self.runtime_truth.value,
            "lifecycle_state": self.lifecycle_state.value,
            "input_status": self.input_status.value,
            "output_status": self.output_status.value,
            "raw_axes": self.raw_axes.to_dict(),
            "final_axes": self.final_axes.to_dict(),
            "buttons": control_payload["buttons"],
            "hats": control_payload["hats"],
            "active_profile": self.active_profile,
            "active_modes": self.active_modes.to_dict(),
            "rule_summary": self.rule_summary.to_dict(),
            "output_verification": self.output_verification.to_dict(),
            "output_verified": self.output_verified,
            "runtime_frame": dict(self.runtime_frame) if self.runtime_frame is not None else None,
            "last_command": self.last_command.to_dict() if self.last_command else None,
            "device_discovery": self.device_discovery.to_dict() if self.device_discovery else None,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }
