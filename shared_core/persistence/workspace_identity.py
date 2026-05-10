from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared_core.models.workspace import WorkspaceConfig
from shared_core.persistence.schema import to_json_data


VOLATILE_WORKSPACE_FIELDS = frozenset({"state", "source_path", "legacy_source_note"})


@dataclass(frozen=True)
class WorkspaceConfigIdentity:
    config_path: str
    schema_version: str
    product_name: str
    active_profile: str
    workspace_hash: str
    workspace_revision: str
    source_status: str
    generated_at: datetime

    @property
    def short_hash(self) -> str:
        return self.workspace_hash[:8]

    def to_dict(self) -> dict[str, object]:
        return {
            "config_path": self.config_path,
            "schema_version": self.schema_version,
            "product_name": self.product_name,
            "active_profile": self.active_profile,
            "workspace_hash": self.workspace_hash,
            "workspace_revision": self.workspace_revision,
            "source_status": self.source_status,
            "generated_at": self.generated_at.isoformat(),
            "short_hash": self.short_hash,
        }

    def to_bridge_workspace_dict(
        self,
        *,
        config_path: str | Path | None = None,
        config_status: str | None = None,
        loaded_at: datetime | None = None,
        using_default_workspace: bool = False,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
    ) -> dict[str, object]:
        loaded = _aware(loaded_at or self.generated_at)
        return {
            "config_path": str(config_path if config_path is not None else self.config_path),
            "config_status": config_status or self.source_status,
            "schema_version": self.schema_version,
            "product_name": self.product_name,
            "active_profile": self.active_profile,
            "workspace_hash": self.workspace_hash,
            "workspace_revision": self.workspace_revision,
            "loaded_at": loaded.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "using_default_workspace": bool(using_default_workspace),
            "warnings": list(warnings),
            "errors": list(errors),
        }


def canonical_workspace_payload(workspace: WorkspaceConfig) -> dict[str, Any]:
    payload = dict(to_json_data(workspace))
    for field in VOLATILE_WORKSPACE_FIELDS:
        payload.pop(field, None)
    return payload


def compute_workspace_hash(workspace: WorkspaceConfig) -> str:
    canonical = json.dumps(
        canonical_workspace_payload(workspace),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_workspace_identity(
    workspace: WorkspaceConfig,
    *,
    path: str | Path,
    status: str,
    generated_at: datetime | None = None,
) -> WorkspaceConfigIdentity:
    workspace_hash = compute_workspace_hash(workspace)
    return WorkspaceConfigIdentity(
        config_path=str(path),
        schema_version=workspace.schema_version,
        product_name=workspace.product_name,
        active_profile=workspace.active_profile,
        workspace_hash=workspace_hash,
        workspace_revision=workspace_hash[:12],
        source_status=str(status),
        generated_at=_aware(generated_at or datetime.now(timezone.utc)),
    )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
