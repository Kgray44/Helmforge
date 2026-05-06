from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

from shared_core.models.workspace import SCHEMA_VERSION, WorkspaceConfig


def to_json_data(workspace: WorkspaceConfig) -> dict[str, Any]:
    data = to_plain(workspace)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported workspace schema version: {data.get('schema_version')}")
    return data


def workspace_from_json_data(data: dict[str, Any]) -> WorkspaceConfig:
    if not isinstance(data, dict):
        raise ValueError("Workspace JSON root must be an object.")
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported workspace schema version: {version!r}")
    return WorkspaceConfig.from_dict(data)


def to_plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: to_plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [to_plain(item) for item in value]
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in value.items()}
    return value


def from_plain_dataclass(cls: type, data: dict[str, Any]):
    hints = get_type_hints(cls)
    kwargs = {}
    for field in fields(cls):
        if field.name not in data:
            continue
        kwargs[field.name] = _from_plain_value(hints[field.name], data[field.name])
    return cls(**kwargs)


def _from_plain_value(target_type: Any, value: Any) -> Any:
    origin = get_origin(target_type)
    args = get_args(target_type)

    if origin in (Union, UnionType):
        non_none = [arg for arg in args if arg is not type(None)]
        if value is None:
            return None
        for arg in non_none:
            try:
                return _from_plain_value(arg, value)
            except (TypeError, ValueError):
                continue
        return value

    if isinstance(target_type, type) and issubclass(target_type, Enum):
        return target_type(value)

    if origin is tuple:
        item_type = args[0] if args else Any
        return tuple(_from_plain_value(item_type, item) for item in value)

    if origin is dict:
        value_type = args[1] if len(args) > 1 else Any
        return {str(key): _from_plain_value(value_type, item) for key, item in value.items()}

    if isinstance(target_type, type) and is_dataclass(target_type):
        return from_plain_dataclass(target_type, value)

    return value

