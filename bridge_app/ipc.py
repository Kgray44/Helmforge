from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from shared_core.runtime.bridge_contracts import BridgeCommandRequest, BridgeCommandType


DEFAULT_TELEMETRY_PATH = Path(tempfile.gettempdir()) / "helmforge_bridge_telemetry.json"
DEFAULT_COMMAND_PATH = Path(tempfile.gettempdir()) / "helmforge_bridge_command.json"


def write_telemetry(path: str | Path, payload: Mapping[str, Any]) -> Path:
    return atomic_write_json(path, payload)


def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(target)
    return target


def read_command(path: str | Path | None) -> BridgeCommandRequest | None:
    if path is None:
        return None
    source = Path(path)
    if not source.exists():
        return None
    data = json.loads(source.read_text(encoding="utf-8"))
    return parse_command_payload(data)


def parse_command_payload(payload: Mapping[str, Any]) -> BridgeCommandRequest:
    command_value = str(payload.get("command", "Status"))
    try:
        command = BridgeCommandType(command_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported bridge command: {command_value}") from exc

    created_raw = payload.get("created_at")
    if isinstance(created_raw, str) and created_raw:
        try:
            created_at = datetime.fromisoformat(created_raw)
        except ValueError:
            created_at = datetime.now(timezone.utc)
    else:
        created_at = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    else:
        created_at = created_at.astimezone(timezone.utc)

    request_id = str(payload.get("request_id") or uuid4())
    options = payload.get("options")
    return BridgeCommandRequest(
        command=command,
        request_id=request_id,
        created_at=created_at,
        config_path=_optional_str(payload.get("config_path")),
        profile_id=_optional_str(payload.get("profile_id")),
        reason=str(payload.get("reason") or ""),
        options=options if isinstance(options, Mapping) else {},
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None
