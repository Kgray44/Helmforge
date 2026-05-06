from __future__ import annotations

from dataclasses import dataclass

from shared_core.models.combat import CombatProfileConfig, default_combat_profile_config
from shared_core.models.filtering import FilteringConfig, default_filtering_config
from shared_core.models.mappings import MappingConfig, default_mapping_config
from shared_core.models.modes import ModeConfig, StackMode, default_mode_config
from shared_core.models.profiles import Profile, ProfileType, ProfilesConfig, default_profiles_config
from shared_core.models.rules import ConditionalRule, RuleConfig, default_rule_config
from shared_core.models.tuning import TuningConfig, default_tuning_config
from shared_core.models.runtime import KNOWN_TARGET_HARDWARE, TargetHardwareMetadata


SCHEMA_VERSION = "3.0.0"
CONFIG_FILENAME = "hotas_bridge_config_v3.json"
LEGACY_V2_CONFIG_FILENAME = "hotas_bridge_config_v2.json"


@dataclass(frozen=True)
class WorkspaceState:
    dirty: bool = False
    saved: bool = True
    last_saved_at: str | None = None


@dataclass(frozen=True)
class WorkspaceConfig:
    schema_version: str
    product_name: str
    technical_subtitle: str
    target_hardware: TargetHardwareMetadata
    active_profile: str
    mappings: MappingConfig
    modes: ModeConfig
    tuning: TuningConfig
    filtering: FilteringConfig
    combat: CombatProfileConfig
    rules: RuleConfig
    profiles: ProfilesConfig
    state: WorkspaceState
    source_path: str = CONFIG_FILENAME
    legacy_source_note: str = f"Recovered V2 used {LEGACY_V2_CONFIG_FILENAME}."

    @classmethod
    def from_dict(cls, data: dict) -> "WorkspaceConfig":
        from shared_core.persistence.schema import from_plain_dataclass

        return from_plain_dataclass(cls, data)


def create_default_workspace() -> WorkspaceConfig:
    return WorkspaceConfig(
        schema_version=SCHEMA_VERSION,
        product_name="HelmForge",
        technical_subtitle="HOTAS Control Panel V3",
        target_hardware=KNOWN_TARGET_HARDWARE,
        active_profile="current-workspace",
        mappings=default_mapping_config(),
        modes=default_mode_config(),
        tuning=default_tuning_config(),
        filtering=default_filtering_config(),
        combat=default_combat_profile_config(),
        rules=default_rule_config(),
        profiles=default_profiles_config(),
        state=WorkspaceState(),
    )
