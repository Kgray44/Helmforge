from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from shared_core.models.workspace import CONFIG_FILENAME, WorkspaceConfig, create_default_workspace
from shared_core.persistence.workspace_identity import WorkspaceConfigIdentity, build_workspace_identity
from shared_core.persistence.workspace_store import WorkspaceJsonError, load_workspace


@dataclass(frozen=True)
class BridgeConfigLoadResult:
    workspace: WorkspaceConfig
    path: Path
    status: str
    identity: WorkspaceConfigIdentity
    loaded_at: datetime
    using_default_workspace: bool = False
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def workspace_hash(self) -> str:
        return self.identity.workspace_hash

    @property
    def workspace_revision(self) -> str:
        return self.identity.workspace_revision

    def bridge_workspace_payload(self) -> dict[str, object]:
        return self.identity.to_bridge_workspace_dict(
            config_path=self.path,
            config_status=self.status,
            loaded_at=self.loaded_at,
            using_default_workspace=self.using_default_workspace,
            warnings=self.warnings,
            errors=self.errors,
        )


def load_bridge_workspace(path: str | Path | None = None) -> BridgeConfigLoadResult:
    source = Path(path or CONFIG_FILENAME)
    loaded_at = datetime.now(timezone.utc)
    if not source.exists():
        workspace = create_default_workspace()
        return BridgeConfigLoadResult(
            workspace=workspace,
            path=source,
            status="missing_default",
            identity=build_workspace_identity(workspace, path=source, status="missing_default", generated_at=loaded_at),
            loaded_at=loaded_at,
            using_default_workspace=True,
            warnings=(f"Workspace config missing at {source}; using default simulation workspace.",),
        )

    try:
        result = load_workspace(source)
    except WorkspaceJsonError as exc:
        workspace = create_default_workspace()
        return BridgeConfigLoadResult(
            workspace=workspace,
            path=source,
            status="invalid_default",
            identity=build_workspace_identity(workspace, path=source, status="invalid_default", generated_at=loaded_at),
            loaded_at=loaded_at,
            using_default_workspace=True,
            warnings=(f"Invalid workspace JSON; using default simulation workspace: {exc}",),
            errors=(str(exc),),
        )

    return BridgeConfigLoadResult(
        workspace=result.workspace,
        path=result.path,
        status=result.status,
        identity=build_workspace_identity(result.workspace, path=result.path, status=result.status, generated_at=loaded_at),
        loaded_at=loaded_at,
    )
