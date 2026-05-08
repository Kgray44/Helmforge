from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


APP_DISPLAY_NAME = "HelmForge"
APP_INTERNAL_NAME = "HelmForge"
TECHNICAL_SUBTITLE = "HOTAS Control Panel V3"


@dataclass(frozen=True)
class AppUserDataPaths:
    root: Path
    config: Path
    profiles: Path
    logs: Path
    recordings: Path
    artifacts: Path

    def as_dict(self) -> dict[str, Path]:
        return {
            "root": self.root,
            "config": self.config,
            "profiles": self.profiles,
            "logs": self.logs,
            "recordings": self.recordings,
            "artifacts": self.artifacts,
        }


def _env_path(name: str, env: Mapping[str, str]) -> Path | None:
    value = env.get(name)
    if not value:
        return None
    return Path(value).expanduser()


def local_app_data_root(env: Mapping[str, str] | None = None) -> Path:
    values = env or os.environ
    return (
        _env_path("LOCALAPPDATA", values)
        or _env_path("APPDATA", values)
        or (Path.home() / "AppData" / "Local")
    )


def get_user_data_paths(env: Mapping[str, str] | None = None) -> AppUserDataPaths:
    root = local_app_data_root(env) / APP_INTERNAL_NAME
    return AppUserDataPaths(
        root=root,
        config=root / "config",
        profiles=root / "profiles",
        logs=root / "logs",
        recordings=root / "recordings",
        artifacts=root / "artifacts",
    )


def source_tree_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_resource_root(pyinstaller_root: str | os.PathLike[str] | None = None) -> Path:
    if pyinstaller_root is not None:
        return Path(pyinstaller_root).resolve()

    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root).resolve()

    return source_tree_root()


def resolve_resource_path(*parts: str, pyinstaller_root: str | os.PathLike[str] | None = None) -> Path:
    return get_resource_root(pyinstaller_root) / Path(*parts)


def get_assets_root(pyinstaller_root: str | os.PathLike[str] | None = None) -> Path:
    return resolve_resource_path("assets", pyinstaller_root=pyinstaller_root)
