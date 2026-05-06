from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from shared_core.models.workspace import WorkspaceConfig, create_default_workspace
from shared_core.persistence.schema import to_json_data, workspace_from_json_data


class WorkspaceJsonError(ValueError):
    pass


@dataclass(frozen=True)
class WorkspaceLoadResult:
    workspace: WorkspaceConfig
    status: str
    path: Path
    error: str | None = None


def save_workspace(workspace: WorkspaceConfig, path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing workspace without overwrite=True: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    payload = to_json_data(workspace)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_workspace(path: str | Path) -> WorkspaceLoadResult:
    source = Path(path)
    if not source.exists():
        return WorkspaceLoadResult(
            workspace=create_default_workspace(),
            status="missing_default",
            path=source,
        )

    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkspaceJsonError(f"Invalid workspace JSON in {source}: {exc}") from exc

    try:
        workspace = workspace_from_json_data(data)
    except (TypeError, ValueError, KeyError) as exc:
        raise WorkspaceJsonError(f"Invalid workspace schema in {source}: {exc}") from exc

    return WorkspaceLoadResult(workspace=workspace, status="loaded", path=source)

