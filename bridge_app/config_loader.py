from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shared_core.models.workspace import CONFIG_FILENAME, WorkspaceConfig, create_default_workspace
from shared_core.persistence.workspace_store import WorkspaceJsonError, load_workspace


@dataclass(frozen=True)
class BridgeConfigLoadResult:
    workspace: WorkspaceConfig
    path: Path
    status: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def load_bridge_workspace(path: str | Path | None = None) -> BridgeConfigLoadResult:
    source = Path(path or CONFIG_FILENAME)
    if not source.exists():
        return BridgeConfigLoadResult(
            workspace=create_default_workspace(),
            path=source,
            status="missing_default",
            warnings=(f"Workspace config missing at {source}; using default simulation workspace.",),
        )

    try:
        result = load_workspace(source)
    except WorkspaceJsonError as exc:
        return BridgeConfigLoadResult(
            workspace=create_default_workspace(),
            path=source,
            status="invalid_default",
            warnings=(f"Invalid workspace JSON; using default simulation workspace: {exc}",),
            errors=(str(exc),),
        )

    return BridgeConfigLoadResult(
        workspace=result.workspace,
        path=result.path,
        status=result.status,
    )
