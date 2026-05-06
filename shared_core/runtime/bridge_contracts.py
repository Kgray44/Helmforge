from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from shared_core.models.runtime import InputStatus, OutputStatus, RuntimeTruth
from shared_core.runtime.bridge_lifecycle import BridgeLifecycleStatus


class BridgeCommandType(str, Enum):
    START_BRIDGE = "StartBridge"
    STOP_BRIDGE = "StopBridge"
    RESTART_BRIDGE = "RestartBridge"
    SUSPEND_BRIDGE = "SuspendBridge"
    RELOAD_CONFIG = "ReloadConfig"
    RUN_PREFLIGHT = "RunPreflight"
    SWITCH_TO_SIMULATION = "SwitchToSimulation"
    VERIFY_OUTPUT = "VerifyOutput"
    CLEAR_ERROR = "ClearError"
    STATUS = "Status"


@dataclass(frozen=True)
class BridgeCommandRequest:
    command: BridgeCommandType
    request_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    config_path: str | None = None
    profile_id: str | None = None
    reason: str = ""
    options: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "options", MappingProxyType(dict(self.options)))

    def to_dict(self) -> dict[str, object]:
        return {
            "command": self.command.value,
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat(),
            "config_path": self.config_path,
            "profile_id": self.profile_id,
            "reason": self.reason,
            "options": dict(self.options),
        }


@dataclass(frozen=True)
class BridgeConfigurationReloadRequest:
    request_id: str
    config_path: str = "hotas_bridge_config_v3.json"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = "Reload active HelmForge workspace configuration."

    def to_command_request(self) -> BridgeCommandRequest:
        return BridgeCommandRequest(
            command=BridgeCommandType.RELOAD_CONFIG,
            request_id=self.request_id,
            created_at=self.created_at,
            config_path=self.config_path,
            reason=self.reason,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "config_path": self.config_path,
            "created_at": self.created_at.isoformat(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class BridgeHealthSummary:
    lifecycle: BridgeLifecycleStatus
    runtime_truth: RuntimeTruth
    input_status: InputStatus
    output_status: OutputStatus
    output_verified: bool = False
    active_profile: str = "Current Workspace"
    message: str = ""
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "lifecycle": self.lifecycle.to_dict(),
            "runtime_truth": self.runtime_truth.value,
            "input_status": self.input_status.value,
            "output_status": self.output_status.value,
            "output_verified": self.output_verified,
            "active_profile": self.active_profile,
            "message": self.message,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }
