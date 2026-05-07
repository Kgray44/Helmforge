from __future__ import annotations

from dataclasses import dataclass


SYMPTOM_CHIPS = (
    "Can't hold aim steady",
    "Too twitchy near center",
    "Overshoots target",
    "Combat mode feels sluggish",
    "Reversals feel sticky",
    "Hard to track smoothly",
    "Combat aim overshoots",
    "Roll feels too sensitive",
    "Controls feel inconsistent",
)


@dataclass(frozen=True)
class MatchedSymptom:
    symptom_id: str
    label: str
    confidence_hint: str = "Medium"
    category: str = "General"
    needs_follow_up: bool = False


@dataclass(frozen=True)
class SymptomDefinition:
    symptom_id: str
    label: str
    category: str
    confidence_hint: str
    keywords: tuple[str, ...]
    needs_follow_up: bool = False


SYMPTOM_DEFINITIONS = (
    SymptomDefinition(
        "combat_sluggish",
        "Combat mode feels sluggish",
        "Aim / Combat",
        "High",
        ("combat sluggish", "combat slow", "combat lag", "combat heavy", "combat mode feels sluggish"),
    ),
    SymptomDefinition(
        "combat_overshoot",
        "Combat aim overshoots",
        "Aim / Combat",
        "Medium",
        ("combat aim overshoots", "overshoots target", "aim overshoots", "overshoot"),
    ),
    SymptomDefinition(
        "aim_twitchy",
        "Aim feels twitchy",
        "Aim / Combat",
        "Medium",
        ("aim feels twitchy", "too twitchy near center", "twitchy", "jittery"),
    ),
    SymptomDefinition(
        "tracking_unstable",
        "Tracking feels unstable",
        "Aim / Combat",
        "Medium",
        ("tracking feels unstable", "hard to track smoothly", "cant hold aim steady", "can't hold aim steady"),
    ),
    SymptomDefinition(
        "small_movements_ignored",
        "Small movements feel ignored",
        "Aim / Combat",
        "Medium",
        ("small movements feel ignored", "small corrections are difficult", "center response feels weak"),
    ),
    SymptomDefinition(
        "recenter_aggressive",
        "Re-centering feels too aggressive",
        "Aim / Combat",
        "Medium",
        ("re-centering feels too aggressive", "recentering feels too aggressive", "reversals feel sticky"),
    ),
    SymptomDefinition(
        "roll_sensitive",
        "Roll feels too sensitive",
        "Flight",
        "Medium",
        ("roll feels too sensitive", "banking feels jerky", "roll sensitive"),
    ),
    SymptomDefinition(
        "pitch_inconsistent",
        "Pitch response feels inconsistent",
        "Flight",
        "Medium",
        ("pitch response feels inconsistent", "pitch inconsistent"),
    ),
    SymptomDefinition(
        "rudder_delayed",
        "Rudder feels delayed",
        "Flight",
        "Medium",
        ("rudder feels delayed", "yaw delayed", "yaw feels delayed"),
    ),
    SymptomDefinition(
        "hover_unstable",
        "Helicopter hover feels unstable",
        "Flight",
        "Medium",
        ("helicopter hover feels unstable", "hover feels unstable", "aircraft drifts while aiming"),
    ),
    SymptomDefinition(
        "steering_oscillates",
        "Steering oscillates",
        "Racing / Ground",
        "Medium",
        ("steering oscillates", "steering snaps too quickly", "vehicle feels too heavy"),
    ),
    SymptomDefinition(
        "controls_inconsistent",
        "Controls feel inconsistent",
        "General",
        "Low",
        ("controls feel inconsistent", "controls feel fatiguing", "curves feel unpredictable"),
        needs_follow_up=True,
    ),
)


def match_symptom(text: str) -> MatchedSymptom | None:
    normalized = _normalize(text)
    if not normalized:
        return None
    for definition in SYMPTOM_DEFINITIONS:
        if _normalize(definition.label) == normalized:
            return _match(definition)
    for definition in SYMPTOM_DEFINITIONS:
        if any(_normalize(keyword) in normalized for keyword in definition.keywords):
            return _match(definition)
    for chip in SYMPTOM_CHIPS:
        if _normalize(chip) == normalized:
            return MatchedSymptom(symptom_id=_normalize(chip).replace(" ", "_"), label=chip)
    return MatchedSymptom(symptom_id="general", label=text.strip() or "Unspecified symptom", needs_follow_up=True)


def _match(definition: SymptomDefinition) -> MatchedSymptom:
    return MatchedSymptom(
        symptom_id=definition.symptom_id,
        label=definition.label,
        confidence_hint=definition.confidence_hint,
        category=definition.category,
        needs_follow_up=definition.needs_follow_up,
    )


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("'", "").replace("â€™", "").split())
