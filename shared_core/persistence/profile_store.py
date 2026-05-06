from __future__ import annotations

import json
from pathlib import Path

from shared_core.models.profiles import ProfilesConfig, default_profiles_config
from shared_core.persistence.schema import from_plain_dataclass, to_plain


def save_profiles(profiles: ProfilesConfig, path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing profiles without overwrite=True: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(to_plain(profiles), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_profiles(path: str | Path) -> ProfilesConfig:
    source = Path(path)
    if not source.exists():
        return default_profiles_config()
    return from_plain_dataclass(ProfilesConfig, json.loads(source.read_text(encoding="utf-8")))
