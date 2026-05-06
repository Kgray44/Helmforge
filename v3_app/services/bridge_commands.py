from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from uuid import uuid4

from shared_core.runtime.bridge_contracts import BridgeCommandType


DEFAULT_BRIDGE_COMMAND_PATH = Path(tempfile.gettempdir()) / "helmforge_bridge_command.json"

SAFE_UI_COMMANDS: frozenset[BridgeCommandType] = frozenset(
    {
        BridgeCommandType.STATUS,
        BridgeCommandType.RUN_PREFLIGHT,
        BridgeCommandType.RELOAD_CONFIG,
        BridgeCommandType.SWITCH_TO_SIMULATION,
        BridgeCommandType.CLEAR_ERROR,
    }
)


@dataclass(frozen=True)
class BridgeCommandWriteResult:
    success: bool
    path: Path
    message: str
    command: str | None = None
    request_id: str | None = None
    error: str | None = None
    payload: Mapping[str, object] = field(default_factory=dict)


class BridgeCommandClient:
    """Write safe UI command requests for the separate Bridge process."""

    def __init__(self, *, command_path: str | Path | None = None) -> None:
        self.command_path = Path(command_path) if command_path is not None else DEFAULT_BRIDGE_COMMAND_PATH

    def request_status(self) -> BridgeCommandWriteResult:
        return self.write_command(BridgeCommandType.STATUS, reason="Refresh Bridge status telemetry.")

    def run_preflight(self) -> BridgeCommandWriteResult:
        return self.write_command(BridgeCommandType.RUN_PREFLIGHT, reason="Run Bridge runtime preflight checks.")

    def reload_config(self, *, config_path: str | Path | None = None) -> BridgeCommandWriteResult:
        return self.write_command(
            BridgeCommandType.RELOAD_CONFIG,
            config_path=config_path,
            reason="Reload HelmForge V3 workspace configuration.",
        )

    def switch_to_simulation(self) -> BridgeCommandWriteResult:
        return self.write_command(BridgeCommandType.SWITCH_TO_SIMULATION, reason="Keep Bridge in simulation mode.")

    def clear_error(self) -> BridgeCommandWriteResult:
        return self.write_command(BridgeCommandType.CLEAR_ERROR, reason="Clear non-fatal Bridge error state.")

    def write_command(
        self,
        command: BridgeCommandType | str,
        *,
        config_path: str | Path | None = None,
        reason: str = "",
        options: Mapping[str, object] | None = None,
    ) -> BridgeCommandWriteResult:
        parsed = self._parse_command(command)
        if parsed is None:
            command_text = str(command.value if isinstance(command, BridgeCommandType) else command)
            return BridgeCommandWriteResult(
                success=False,
                path=self.command_path,
                command=command_text,
                message=f"Bridge command {command_text} is not allowed from the UI in Phase 9D.",
                error="unsupported_command",
            )
        if parsed not in SAFE_UI_COMMANDS:
            return BridgeCommandWriteResult(
                success=False,
                path=self.command_path,
                command=parsed.value,
                message=f"Bridge command {parsed.value} is not allowed from the UI in Phase 9D.",
                error="unsafe_command",
            )

        request_id = str(uuid4())
        payload: dict[str, object] = {
            "command": parsed.value,
            "request_id": request_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "v3_app",
            "product_name": "HelmForge",
            "technical_subtitle": "HOTAS Control Panel V3",
            "reason": reason or "UI requested safe Bridge command.",
            "options": dict(options or {}),
        }
        if config_path is not None:
            payload["config_path"] = str(config_path)

        try:
            self._atomic_write_json(self.command_path, payload)
        except OSError as exc:
            return BridgeCommandWriteResult(
                success=False,
                path=self.command_path,
                command=parsed.value,
                request_id=request_id,
                message=f"Command write failed: {exc}",
                error=str(exc),
                payload=payload,
            )

        return BridgeCommandWriteResult(
            success=True,
            path=self.command_path,
            command=parsed.value,
            request_id=request_id,
            message=f"{parsed.value} command requested. Awaiting Bridge telemetry.",
            payload=payload,
        )

    @staticmethod
    def _parse_command(command: BridgeCommandType | str) -> BridgeCommandType | None:
        if isinstance(command, BridgeCommandType):
            return command
        try:
            return BridgeCommandType(str(command))
        except ValueError:
            return None

    @staticmethod
    def _atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        try:
            temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            temp_path.replace(target)
        finally:
            if temp_path.exists():
                temp_path.unlink()
