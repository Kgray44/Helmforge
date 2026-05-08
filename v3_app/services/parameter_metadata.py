from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from html import escape
from typing import Any


class ParameterValueType(str, Enum):
    NUMBER = "number"
    INTEGER = "integer"
    DROPDOWN = "dropdown"
    BOOLEAN = "boolean"
    TEXT = "text"


class ParameterSupportScope(str, Enum):
    WORKSPACE_ONLY = "workspace_only"
    SIMULATED_WORKSPACE_ONLY = "simulated_workspace_only"
    APP_RUNTIME_CONFIG = "app_runtime_config"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    DEFERRED_RUNTIME = "deferred_runtime"


@dataclass(frozen=True)
class ParameterRange:
    minimum: float | int
    maximum: float | int
    recommended_minimum: float | int | None = None
    recommended_maximum: float | int | None = None

    def contains(self, value: float | int) -> bool:
        return self.minimum <= value <= self.maximum


@dataclass(frozen=True)
class ParameterExample:
    label: str
    value: str
    effect: str


@dataclass(frozen=True)
class NumericValidationResult:
    acceptable: bool
    value: float | int | None = None
    clamped_value: float | int | None = None
    error: str | None = None


@dataclass(frozen=True)
class ParameterMetadata:
    parameter_id: str
    display_name: str
    category: str
    section: str
    short_description: str
    detailed_description: str
    value_type: ParameterValueType
    min_value: float | int | None = None
    max_value: float | int | None = None
    default_value: Any | None = None
    units: str | None = None
    dropdown_options: tuple[str, ...] = ()
    low_or_min_example: ParameterExample | None = None
    high_or_max_example: ParameterExample | None = None
    recommended_range: ParameterRange | None = None
    warning_text: str | None = None
    related_help_topic: str | None = None
    support_scope: ParameterSupportScope = ParameterSupportScope.WORKSPACE_ONLY

    @property
    def value_range(self) -> ParameterRange | None:
        if self.min_value is None or self.max_value is None:
            return None
        return ParameterRange(
            minimum=self.min_value,
            maximum=self.max_value,
            recommended_minimum=(
                self.recommended_range.recommended_minimum if self.recommended_range else None
            ),
            recommended_maximum=(
                self.recommended_range.recommended_maximum if self.recommended_range else None
            ),
        )

    @property
    def is_numeric(self) -> bool:
        return self.value_type in {ParameterValueType.NUMBER, ParameterValueType.INTEGER}


class ParameterHelpRegistry:
    def __init__(self, entries: tuple[ParameterMetadata, ...]) -> None:
        self._entries = {entry.parameter_id: entry for entry in entries}

    def get(self, parameter_id: str | None) -> ParameterMetadata | None:
        if not parameter_id:
            return None
        return self._entries.get(parameter_id)

    def require(self, parameter_id: str) -> ParameterMetadata:
        metadata = self.get(parameter_id)
        if metadata is None:
            raise KeyError(f"Unknown parameter metadata id: {parameter_id}")
        return metadata

    def all(self) -> tuple[ParameterMetadata, ...]:
        return tuple(self._entries.values())

    def by_category(self, category: str) -> tuple[ParameterMetadata, ...]:
        return tuple(entry for entry in self._entries.values() if entry.category == category)


def format_parameter_tooltip(metadata: ParameterMetadata) -> str:
    sections = [
        f"<b>{escape(metadata.display_name)}</b>",
        f"<b>What it does</b><br>{escape(metadata.short_description)}",
    ]
    if metadata.detailed_description:
        sections.append(escape(metadata.detailed_description))

    sections.append(f"<b>Default</b><br>{escape(_format_value(metadata.default_value))}")
    sections.append(f"<b>Scope</b><br>{escape(_format_scope(metadata.support_scope))}")

    if metadata.value_range is not None:
        units = f" {escape(metadata.units)}" if metadata.units else ""
        range_text = f"{_format_value(metadata.min_value)} to {_format_value(metadata.max_value)}{units}"
        if metadata.recommended_range is not None:
            range_text += (
                "<br>Recommended: "
                f"{_format_value(metadata.recommended_range.recommended_minimum)} to "
                f"{_format_value(metadata.recommended_range.recommended_maximum)}{units}"
            )
        sections.append(f"<b>Range</b><br>{range_text}")
    elif metadata.dropdown_options:
        options = ", ".join(escape(option) for option in metadata.dropdown_options)
        sections.append(f"<b>Options</b><br>{options}")

    examples = []
    if metadata.low_or_min_example is not None:
        examples.append(_format_example("Low", metadata.low_or_min_example))
    if metadata.high_or_max_example is not None:
        examples.append(_format_example("High", metadata.high_or_max_example))
    if examples:
        sections.append("<b>Examples</b><br>" + "<br>".join(examples))

    notes = []
    if metadata.warning_text:
        notes.append(escape(metadata.warning_text))
    if metadata.related_help_topic:
        notes.append(f"Related help: {escape(metadata.related_help_topic)}")
    if notes:
        sections.append("<b>Notes</b><br>" + "<br>".join(notes))

    return "<qt>" + "<br><br>".join(sections) + "</qt>"


def clamp_numeric_value(metadata: ParameterMetadata, value: float | int) -> float | int:
    if metadata.value_range is None:
        return value
    return max(metadata.min_value, min(metadata.max_value, value))


def validate_numeric_text(metadata: ParameterMetadata, text: str) -> NumericValidationResult:
    if not metadata.is_numeric:
        return NumericValidationResult(True)
    normalized = text.strip()
    if not normalized:
        return NumericValidationResult(False, error="empty")
    try:
        parsed = float(normalized)
    except ValueError:
        return NumericValidationResult(False, error="not_numeric")

    if metadata.value_type is ParameterValueType.INTEGER:
        if not parsed.is_integer() or "." in normalized:
            return NumericValidationResult(False, value=parsed, error="not_integer")
        value: float | int = int(parsed)
    else:
        value = parsed

    if metadata.min_value is not None and value < metadata.min_value:
        return NumericValidationResult(False, value=value, clamped_value=metadata.min_value, error="below_min")
    if metadata.max_value is not None and value > metadata.max_value:
        return NumericValidationResult(False, value=value, clamped_value=metadata.max_value, error="above_max")
    return NumericValidationResult(True, value=value, clamped_value=value)


def build_default_parameter_registry() -> ParameterHelpRegistry:
    entries = (
        *_base_tuning_metadata(),
        *_filtering_metadata(),
        *_combat_metadata(),
        *_modes_metadata(),
        *_rules_metadata(),
        *_mapping_metadata(),
        *_live_overlay_metadata(),
        *_flight_recorder_metadata(),
        *_diagnostics_metadata(),
    )
    return ParameterHelpRegistry(tuple(_with_category_scope(entry) for entry in entries))


def _number(
    parameter_id: str,
    display_name: str,
    category: str,
    section: str,
    short: str,
    detail: str,
    minimum: float,
    maximum: float,
    default: float,
    low_effect: str,
    high_effect: str,
    *,
    units: str | None = None,
    recommended: tuple[float, float] | None = None,
    warning: str | None = None,
    topic: str | None = None,
) -> ParameterMetadata:
    return ParameterMetadata(
        parameter_id=parameter_id,
        display_name=display_name,
        category=category,
        section=section,
        short_description=short,
        detailed_description=detail,
        value_type=ParameterValueType.NUMBER,
        min_value=minimum,
        max_value=maximum,
        default_value=default,
        units=units,
        low_or_min_example=ParameterExample("Low", _format_value(minimum), low_effect),
        high_or_max_example=ParameterExample("High", _format_value(maximum), high_effect),
        recommended_range=(
            ParameterRange(minimum, maximum, recommended[0], recommended[1])
            if recommended is not None
            else None
        ),
        warning_text=warning,
        related_help_topic=topic,
    )


def _integer(
    parameter_id: str,
    display_name: str,
    category: str,
    section: str,
    short: str,
    detail: str,
    minimum: int,
    maximum: int,
    default: int,
    low_effect: str,
    high_effect: str,
    *,
    units: str | None = None,
    recommended: tuple[int, int] | None = None,
    warning: str | None = None,
    topic: str | None = None,
) -> ParameterMetadata:
    return ParameterMetadata(
        parameter_id=parameter_id,
        display_name=display_name,
        category=category,
        section=section,
        short_description=short,
        detailed_description=detail,
        value_type=ParameterValueType.INTEGER,
        min_value=minimum,
        max_value=maximum,
        default_value=default,
        units=units,
        low_or_min_example=ParameterExample("Low", str(minimum), low_effect),
        high_or_max_example=ParameterExample("High", str(maximum), high_effect),
        recommended_range=(
            ParameterRange(minimum, maximum, recommended[0], recommended[1])
            if recommended is not None
            else None
        ),
        warning_text=warning,
        related_help_topic=topic,
    )


def _dropdown(
    parameter_id: str,
    display_name: str,
    category: str,
    section: str,
    short: str,
    detail: str,
    options: tuple[str, ...],
    default: str,
    low_effect: str,
    high_effect: str,
    *,
    warning: str | None = None,
    topic: str | None = None,
) -> ParameterMetadata:
    return ParameterMetadata(
        parameter_id=parameter_id,
        display_name=display_name,
        category=category,
        section=section,
        short_description=short,
        detailed_description=detail,
        value_type=ParameterValueType.DROPDOWN,
        default_value=default,
        dropdown_options=options,
        low_or_min_example=ParameterExample("Option", options[0], low_effect),
        high_or_max_example=ParameterExample("Option", options[-1], high_effect),
        warning_text=warning,
        related_help_topic=topic,
    )


def _boolean(
    parameter_id: str,
    display_name: str,
    category: str,
    section: str,
    short: str,
    detail: str,
    default: bool,
    off_effect: str,
    on_effect: str,
    *,
    warning: str | None = None,
    topic: str | None = None,
) -> ParameterMetadata:
    return ParameterMetadata(
        parameter_id=parameter_id,
        display_name=display_name,
        category=category,
        section=section,
        short_description=short,
        detailed_description=detail,
        value_type=ParameterValueType.BOOLEAN,
        default_value=default,
        low_or_min_example=ParameterExample("Off", "false", off_effect),
        high_or_max_example=ParameterExample("On", "true", on_effect),
        warning_text=warning,
        related_help_topic=topic,
    )


def _text(
    parameter_id: str,
    display_name: str,
    category: str,
    section: str,
    short: str,
    detail: str,
    default: str,
    low_effect: str,
    high_effect: str,
    *,
    warning: str | None = None,
    topic: str | None = None,
) -> ParameterMetadata:
    return ParameterMetadata(
        parameter_id=parameter_id,
        display_name=display_name,
        category=category,
        section=section,
        short_description=short,
        detailed_description=detail,
        value_type=ParameterValueType.TEXT,
        default_value=default,
        low_or_min_example=ParameterExample("Simple", "none", low_effect),
        high_or_max_example=ParameterExample("Configured", default, high_effect),
        warning_text=warning,
        related_help_topic=topic,
    )


def _base_tuning_metadata() -> tuple[ParameterMetadata, ...]:
    return (
        _dropdown("base.curve_mode", "Curve Mode", "Base Tuning", "Parameters", "Chooses the shape family used before strength is applied.", "The current runtime uses the recovered S-curve style by default. Other curve families stay hidden until implemented.", ("s",), "s", "The recovered S-curve path keeps behavior aligned with the current pipeline.", "Additional curve families stay hidden until the pipeline supports them.", topic="Base Tuning"),
        _number("base.curve_strength", "Curve Strength", "Base Tuning", "Parameters", "Controls how strongly the curve reshapes the selected axis.", "Lower values feel closer to linear. Higher values make the center or edge response more shaped.", 0.0, 1.0, 0.34, "Near zero keeps the stick close to raw input.", "Near one makes the curve shaping obvious.", recommended=(0.10, 0.70), warning="Extreme values can make fine control feel either too flat or too jumpy.", topic="Base Tuning"),
        _number("base.deadzone", "Deadzone", "Base Tuning", "Parameters", "Ignores small input near center before output starts moving.", "Use this to calm noisy center drift without hiding deliberate movement.", 0.0, 0.50, 0.03, "0.00 responds to the smallest motion.", "0.50 ignores half of the input travel near center.", recommended=(0.00, 0.08), warning="Large deadzones can make the control feel unresponsive.", topic="Base Tuning"),
        _number("base.anti_deadzone", "Anti-Deadzone", "Base Tuning", "Parameters", "Adds an initial output jump after leaving center.", "Use sparingly when a target simulator ignores tiny output values.", 0.0, 0.50, 0.0, "0.00 adds no initial jump.", "0.50 jumps aggressively after center.", recommended=(0.00, 0.10), warning="High anti-deadzone can make small corrections lurch.", topic="Base Tuning"),
        _number("base.hysteresis", "Hysteresis", "Base Tuning", "Parameters", "Adds a small hold band to reduce center chatter.", "It can calm noisy sensors, but too much can make reversals feel sticky.", 0.0, 0.50, 0.0, "0.00 tracks reversals immediately.", "0.50 strongly resists small reversals.", recommended=(0.00, 0.06), warning="High hysteresis can hide intentional small inputs.", topic="Base Tuning"),
        _number("base.output_scale", "Output Scale", "Base Tuning", "Parameters", "Multiplies the processed output before final limiting.", "Use this for broad authority changes while keeping the curve shape intact.", 0.0, 2.0, 1.0, "0.00 mutes the axis output.", "2.00 doubles authority before final limiting.", recommended=(0.50, 1.20), warning="Values above 1.00 can hit limits sooner.", topic="Base Tuning"),
        _number("base.max_output", "Max Output", "Base Tuning", "Parameters", "Caps the final output magnitude for the selected axis.", "Use this when a simulator or profile should never receive full authority.", 0.0, 1.0, 1.0, "0.00 prevents output authority.", "1.00 allows the full normalized output range.", recommended=(0.50, 1.00), warning="Low caps can make full stick travel feel weak.", topic="Base Tuning"),
        _number("base.precision_scale", "Precision Scale", "Base Tuning", "Parameters", "Scales output while precision mode is active.", "Lower values make precision mode calmer without changing normal-mode authority.", 0.0, 1.0, 0.65, "0.00 removes output authority while precision is held.", "1.00 keeps full authority in precision mode.", recommended=(0.40, 0.85), warning="Very low values can make precision mode feel stuck.", topic="Base Tuning"),
    )


def _filtering_metadata() -> tuple[ParameterMetadata, ...]:
    return (
        _number("filtering.center_alpha", "Center Alpha", "Filtering", "Parameters", "Controls smoothing strength near the center of the axis.", "Lower alpha feels smoother and slower. Higher alpha follows input more quickly.", 0.0, 1.0, 0.35, "0.00 heavily damps center changes.", "1.00 follows raw center movement immediately.", recommended=(0.20, 0.65), topic="Filtering"),
        _number("filtering.edge_alpha", "Edge Alpha", "Filtering", "Parameters", "Controls smoothing strength near the outside of the axis travel.", "Use higher edge alpha when large movements should stay responsive.", 0.0, 1.0, 0.70, "0.00 heavily damps edge changes.", "1.00 follows edge movement immediately.", recommended=(0.50, 0.90), topic="Filtering"),
        _number("filtering.same_slew_limit", "Same Slew Limit", "Filtering", "Parameters", "Limits how fast output can keep moving in the same direction.", "This is useful for damped cinematic profiles or unstable inputs.", 0.0, 1.0, 1.0, "0.00 nearly stops same-direction motion.", "1.00 allows full same-direction movement.", recommended=(0.60, 1.00), topic="Filtering"),
        _number("filtering.reverse_slew_limit", "Reverse Slew Limit", "Filtering", "Parameters", "Limits how fast output can reverse direction.", "Lower values smooth snap-backs. Higher values make reversals immediate.", 0.0, 1.0, 0.65, "0.00 resists reversals strongly.", "1.00 lets reversals track immediately.", recommended=(0.35, 0.85), warning="Very low reversal limits can make aiming feel delayed.", topic="Filtering"),
    )


def _combat_metadata() -> tuple[ParameterMetadata, ...]:
    return (
        _number("combat.combat_curve", "Combat Curve", "Combat Profile", "Parameters", "Applies extra curve shaping while combat behavior is active.", "Use it to make zoom or combat movement more precise than the base profile.", 0.0, 1.0, 0.45, "0.00 keeps combat close to baseline.", "1.00 makes combat shaping strong.", recommended=(0.20, 0.70), topic="Combat Profile"),
        _number("combat.combat_scale", "Combat Scale", "Combat Profile", "Parameters", "Scales final authority during combat behavior.", "Lower values calm movement while aiming. Higher values preserve full authority.", 0.0, 2.0, 0.85, "0.00 mutes combat output authority.", "2.00 doubles combat authority before caps.", recommended=(0.50, 1.00), warning="Values above 1.00 can hit output caps sooner.", topic="Combat Profile"),
        _number("combat.combat_center_alpha", "Combat Center Alpha", "Combat Profile", "Parameters", "Controls center smoothing while combat behavior is active.", "Lower values feel steadier for tiny aim corrections.", 0.0, 1.0, 0.25, "0.00 heavily damps center movement.", "1.00 follows center movement immediately.", recommended=(0.15, 0.55), topic="Combat Profile"),
        _number("combat.combat_edge_alpha", "Combat Edge Alpha", "Combat Profile", "Parameters", "Controls edge smoothing while combat behavior is active.", "Higher values keep large combat movements responsive.", 0.0, 1.0, 0.60, "0.00 heavily damps large movements.", "1.00 follows large movements immediately.", recommended=(0.40, 0.85), topic="Combat Profile"),
        _number("combat.combat_same_slew", "Combat Same Slew", "Combat Profile", "Parameters", "Limits same-direction movement while combat behavior is active.", "Use this to make tracking smoother without changing the base profile.", 0.0, 1.0, 0.80, "0.00 nearly stops same-direction combat motion.", "1.00 allows full same-direction combat motion.", recommended=(0.50, 1.00), topic="Combat Profile"),
        _number("combat.combat_reverse_slew", "Combat Reverse Slew", "Combat Profile", "Parameters", "Limits reversal speed while combat behavior is active.", "Lower values soften snap corrections; higher values preserve quick reversals.", 0.0, 1.0, 0.50, "0.00 resists combat reversals strongly.", "1.00 lets combat reversals track immediately.", recommended=(0.25, 0.80), warning="Very low reversal limits can feel sluggish during aiming.", topic="Combat Profile"),
    )


def _modes_metadata() -> tuple[ParameterMetadata, ...]:
    return (
        _text("modes.precision_hold_buttons", "Precision Hold Buttons", "Modes", "Precision Mode", "Lists buttons that engage precision scaling while held.", "Use comma-separated button numbers. The current default recovered button is 0.", "0", "No buttons means precision mode will not engage.", "Configured buttons can engage precision behavior.", topic="Modes"),
        _text("modes.combat_trigger_buttons", "Combat Trigger Buttons", "Modes", "Combat Mode", "Lists trigger buttons that may engage combat behavior.", "Leave empty when combat should not depend on trigger buttons.", "", "Empty keeps this trigger gate inactive.", "Configured buttons can gate combat behavior.", topic="Modes"),
        _text("modes.combat_zoom_aim_buttons", "Combat Zoom/Aim Buttons", "Modes", "Combat Mode", "Lists zoom or aim buttons that engage combat behavior.", "The recovered default uses button 5 for zoom or aim mode.", "5", "Empty removes the zoom or aim gate.", "Configured buttons can activate combat behavior while aiming.", topic="Modes"),
        _text("modes.combat_extra_buttons", "Combat Extra Buttons", "Modes", "Combat Mode", "Lists extra buttons that can also gate combat behavior.", "Use this for extra mode triggers without changing the core trigger list.", "", "Empty keeps extra gating inactive.", "Configured extra buttons add another combat entry path.", topic="Modes"),
        _dropdown("modes.stack_mode", "Stack Mode", "Modes", "Combat Mode", "Controls how precision and combat modifiers combine.", "Only multiply is currently supported by the recovered runtime model.", ("multiply",), "multiply", "Multiply preserves the current supported behavior.", "Multiply remains the only active option in this build.", topic="Modes"),
    )


def _rules_metadata() -> tuple[ParameterMetadata, ...]:
    axis_options = ("Roll", "Pitch", "Throttle", "Yaw", "Aux 1", "Aux 2")
    stages = ("Final Output", "Raw Input", "Center Conditioning", "Curve / Shape", "Base Output Limits", "Filtering", "Mode Modifiers")
    return (
        _text("rules.title", "Title", "Conditional Rules", "Action", "Names the rule in the list and detail view.", "A clear title makes rule behavior easier to audit later.", "Yaw 0.75 | Roll > 0.35", "A vague title hides rule intent.", "A specific title makes the target and condition obvious.", topic="Conditional Rules"),
        _dropdown("rules.target_axis", "Target Axis", "Conditional Rules", "Action", "Chooses the axis the rule modifies.", "A rule targets one output axis at a time.", axis_options, "Yaw", "Roll targets roll output.", "Aux 2 targets an auxiliary output.", topic="Conditional Rules"),
        _dropdown("rules.parameter", "Parameter", "Conditional Rules", "Action", "Chooses which parameter the rule changes.", "Only currently supported mutable parameters are listed.", ("Output Scale",), "Output Scale", "Output Scale changes final authority.", "Output Scale remains the supported rule target.", topic="Conditional Rules"),
        _dropdown("rules.operation", "Operation", "Conditional Rules", "Action", "Chooses how the rule applies its value.", "Set replaces the parameter; Add and Multiply are modeled as explicit operations in the rule shell.", ("Set", "Add", "Multiply"), "Set", "Set replaces the current value.", "Multiply scales the current value.", topic="Conditional Rules"),
        _number("rules.value", "Value", "Conditional Rules", "Action", "Numeric value used by the rule operation.", "The meaning depends on Set, Add, or Multiply.", -2.0, 2.0, 0.75, "Negative values can invert or subtract where supported.", "High values can amplify where supported.", recommended=(-1.0, 1.0), topic="Conditional Rules"),
        _dropdown("rules.injects_at", "Injects At", "Conditional Rules", "Action", "Chooses the pipeline stage where the rule applies.", "The default example injects at Base Output Limits.", ("Base Output Limits",), "Base Output Limits", "Base Output Limits affects final authority.", "Base Output Limits is the supported injection point.", topic="Conditional Rules"),
        _dropdown("rules.mode_gate", "Mode Gate", "Conditional Rules", "When", "Restricts a rule to a mode state.", "Always ignores mode state; Precision or Combat require those modes.", ("Always", "Precision", "Combat"), "Always", "Always can evaluate any time.", "Combat evaluates only in combat mode.", topic="Conditional Rules"),
        _text("rules.buttons", "Buttons", "Conditional Rules", "When", "Lists buttons used by the selected rule.", "Use comma-separated button numbers when a rule should depend on buttons.", "", "Empty means no button gate.", "Configured buttons can gate rule activation.", topic="Conditional Rules"),
        _dropdown("rules.button_test", "Button Test", "Conditional Rules", "When", "Chooses whether any or all listed buttons must match.", "Any is easier to trigger; All is stricter.", ("Any", "All"), "Any", "Any activates when one listed button matches.", "All requires every listed button to match.", topic="Conditional Rules"),
        _dropdown("rules.reference_axis", "Reference Axis", "Conditional Rules", "Condition", "Chooses the axis watched by the condition.", "Reference axis can be different from target axis.", axis_options, "Roll", "Roll watches roll movement.", "Aux 2 watches an auxiliary input.", topic="Conditional Rules"),
        _dropdown("rules.stage", "Stage", "Conditional Rules", "Condition", "Chooses which signal stage the condition reads.", "Later stages include more processing than earlier stages.", stages, "Final Output", "Raw Input reads before processing.", "Mode Modifiers reads after mode processing.", topic="Conditional Rules"),
        _dropdown("rules.measure", "Measure", "Conditional Rules", "Condition", "Chooses signed or absolute signal measurement.", "Absolute ignores direction; signed keeps positive and negative direction.", ("absolute", "signed", "raw"), "absolute", "Absolute triggers on magnitude.", "Raw keeps the least processed reading.", topic="Conditional Rules"),
        _dropdown("rules.comparator", "Comparator", "Conditional Rules", "Condition", "Chooses how the reference signal is compared to the threshold.", "Between and range use both threshold fields.", ("greater than", "less than", "equal", "approximately", "between", "range"), "greater than", "Greater than activates above the threshold.", "Range activates inside a band.", topic="Conditional Rules"),
        _number("rules.threshold", "Threshold", "Conditional Rules", "Condition", "Primary numeric threshold for the condition.", "For greater than and less than, this is the single activation point.", -1.0, 1.0, 0.35, "-1.00 is the minimum normalized signal.", "1.00 is the maximum normalized signal.", recommended=(-0.80, 0.80), topic="Conditional Rules"),
        _number("rules.threshold_high", "Threshold High", "Conditional Rules", "Condition", "Upper threshold for between or range conditions.", "Use this only when the comparator expects a band.", -1.0, 1.0, 0.75, "-1.00 creates a low upper band.", "1.00 creates a high upper band.", recommended=(-0.50, 1.00), topic="Conditional Rules"),
    )


def _mapping_metadata() -> tuple[ParameterMetadata, ...]:
    return (
        _dropdown("mapping.raw_axis", "Raw Axis", "Mapping", "Axis Routing", "Selects the physical/raw axis channel used by a mapped function.", "This is a workspace route selection; it does not prove live hardware is connected.", tuple(f"Axis {index}" for index in range(1, 9)), "Axis 1", "Axis 1 uses the first raw channel.", "Axis 8 uses the last supported raw channel.", topic="Mapping"),
        _dropdown("mapping.logical_output", "Logical Output", "Mapping", "Axis Routing", "Chooses the logical output channel for a mapped axis.", "Logical output naming helps keep the workspace readable before runtime output is verified.", ("X", "Y", "Z", "RX", "RY", "RZ", "SL0", "SL1"), "X", "X maps to the primary output axis.", "SL1 maps to an auxiliary slider output.", topic="Mapping"),
        _dropdown("mapping.runtime_output_axis", "Output Intent Axis", "Mapping", "Axis Routing", "Chooses the output-intent channel shown in the runtime route table.", "Output intent is not output-write proof.", ("X(axis1)", "Y(axis2)", "Z(axis3)", "RX(axis4)", "RY(axis5)", "RZ(axis6)", "SL0", "SL1"), "X(axis1)", "X(axis1) targets the primary output intent.", "SL1 targets an auxiliary output intent.", warning="Output intent remains a request model until output writes are explicitly verified.", topic="Mapping"),
        _boolean("mapping.invert_axis", "Invert", "Mapping", "Axis Routing", "Flips the sign of an axis route.", "Invert is a workspace mapping edit and does not change runtime readiness.", False, "Normal direction is preserved.", "Axis output intent is sign-flipped.", topic="Mapping"),
        _dropdown("mapping.hotas_button", "HOTAS Button", "Mapping", "Button Routing", "Selects the source button number for a button route.", "This maps a workspace route and does not prove physical button sampling.", tuple(f"B{index}" for index in range(1, 16)), "B1", "B1 uses the first source button.", "B15 uses the last supported source button.", topic="Mapping"),
        _dropdown("mapping.output_button", "Output Button", "Mapping", "Button Routing", "Selects the output button number used by the route.", "Output button mapping is not evidence of a real write.", tuple(str(index) for index in range(1, 21)), "1", "1 maps to the first output button intent.", "20 maps to the last listed output button intent.", warning="Mapped output buttons are intent until output writes are verified.", topic="Mapping"),
        _dropdown("mapping.hotas_hat", "HOTAS Hat", "Mapping", "Hat Routing", "Selects the source hat index.", "Hat routing remains workspace configuration until a fresh input sample proves physical data.", ("1", "2"), "1", "Hat 1 uses the primary hat.", "Hat 2 uses the secondary hat slot.", topic="Mapping"),
        _dropdown("mapping.output_pov", "Output POV", "Mapping", "Hat Routing", "Selects the output POV channel.", "This maps hat intent only; it does not prove output writes.", ("1", "2", "3", "4"), "1", "POV 1 uses the primary output POV intent.", "POV 4 uses the last listed POV intent.", topic="Mapping"),
        _dropdown("mapping.hat_direction_button", "Direction Button", "Mapping", "Hat Routing", "Optional button output for a hat direction.", "None means the hat direction does not emit a button intent.", ("None", *tuple(str(index) for index in range(0, 21))), "None", "None keeps the direction unbound.", "20 maps the direction to output button intent 20.", topic="Mapping"),
    )


def _live_overlay_metadata() -> tuple[ParameterMetadata, ...]:
    return (
        _dropdown("live_overlay.position", "Position", "Live Overlay", "Placement", "Places the detached overlay strip.", "The current overlay supports the bottom strip placement.", ("Bottom strip",), "Bottom strip", "Bottom strip keeps telemetry low on the screen.", "Bottom strip remains the supported placement.", topic="Live Overlay"),
        _integer("live_overlay.margin", "Margin", "Live Overlay", "Placement", "Sets screen edge padding.", "Higher margins pull the overlay away from the edge.", 0, 96, 18, "0 px hugs the screen edge.", "96 px leaves a large edge gap.", units="px", recommended=(8, 32), topic="Live Overlay"),
        _dropdown("live_overlay.attach", "Attach", "Live Overlay", "Placement", "Chooses what the overlay attaches to.", "The current app-owned overlay attaches to the display.", ("Attach to display",), "Attach to display", "Display attachment keeps it app-owned.", "Display attachment remains the supported behavior.", topic="Live Overlay"),
        _dropdown("live_overlay.width", "Width", "Live Overlay", "Placement", "Chooses width preset.", "Standard is the current supported width preset.", ("Standard",), "Standard", "Standard keeps the strip compact.", "Standard remains the supported width option.", topic="Live Overlay"),
        _number("live_overlay.height", "Height", "Live Overlay", "Placement", "Scales detached overlay height.", "Higher values make traces easier to see but take more space.", 0.2, 1.0, 0.60, "0.20 is compact.", "1.00 is tallest.", recommended=(0.40, 0.80), topic="Live Overlay"),
        _text("live_overlay.display", "Display", "Live Overlay", "Placement", "Names the display target for the app-owned overlay.", "Display text is descriptive; it is not game injection or capture.", "Primary display", "No display label makes placement harder to audit.", "A display label makes the placement target clear.", topic="Live Overlay"),
        _number("live_overlay.opacity", "Opacity", "Live Overlay", "Appearance", "Controls overall overlay opacity.", "Lower opacity is subtler. Higher opacity is easier to read.", 0.0, 1.0, 0.66, "0.00 is fully transparent.", "1.00 is fully opaque.", recommended=(0.45, 0.90), topic="Live Overlay"),
        _number("live_overlay.background", "Background", "Live Overlay", "Appearance", "Controls overlay background strength.", "Higher values improve contrast behind traces.", 0.0, 1.0, 0.82, "0.00 removes most backing.", "1.00 gives maximum backing.", recommended=(0.55, 0.95), topic="Live Overlay"),
        _number("live_overlay.line_thickness", "Line Thickness", "Live Overlay", "Appearance", "Controls trace stroke thickness.", "Higher values are easier to read but can obscure fine changes.", 1.0, 8.0, 2.80, "1.00 is thin.", "8.00 is very thick.", recommended=(1.5, 4.0), topic="Live Overlay"),
        _boolean("live_overlay.show_legend", "Legend", "Live Overlay", "Appearance", "Toggles the overlay legend.", "Legend text helps identify axis colors in the app-owned overlay.", True, "Hides the legend for a cleaner strip.", "Shows the legend for easier reading.", topic="Live Overlay"),
        _boolean("live_overlay.show_values", "Values", "Live Overlay", "Appearance", "Toggles live numeric values beside traces.", "Values are UI telemetry display only and do not claim output writes.", True, "Shows traces without numbers.", "Shows trace values for quick diagnostics.", topic="Live Overlay"),
        _boolean("live_overlay.auto_hide", "Auto-hide when target loses focus", "Live Overlay", "Behavior", "Configures whether the overlay should hide when the target loses focus.", "This remains app-owned UI behavior, not game process control.", False, "Overlay stays visible until hidden by the app.", "Overlay may hide according to app-owned focus state.", topic="Live Overlay"),
        _boolean("live_overlay.always_on_top", "Always On Top", "Live Overlay", "Behavior", "Keeps the detached overlay above normal windows when supported.", "This remains app-owned window behavior, not target injection.", True, "Overlay behaves like a normal window.", "Overlay requests topmost window behavior.", topic="Live Overlay"),
        _boolean("live_overlay.click_through", "Click-through", "Live Overlay", "Behavior", "Configured click-through preference.", "The UI truth-labels click-through as not verified unless platform support proves it.", False, "Overlay receives normal mouse interaction.", "Configured preference is on, but support remains truth-labeled.", warning="Configured click-through text is not proof of verified click-through.", topic="Live Overlay"),
        _integer("live_overlay.fps_cap", "FPS Cap", "Live Overlay", "Behavior", "Limits overlay redraw frequency.", "Lower caps reduce redraw work. Higher caps feel smoother.", 15, 144, 60, "15 fps is light but choppy.", "144 fps is smooth but heavier.", units="fps", recommended=(30, 60), topic="Live Overlay"),
        _text("live_overlay.toggle_hotkey", "Toggle Hotkey", "Live Overlay", "Behavior", "Configured hotkey text for future overlay toggling.", "The current UI labels hotkey registration truthfully and does not arm a global hotkey.", "Ctrl+Shift+O", "Empty means no configured hotkey text.", "Configured text is displayed but not registered globally.", topic="Live Overlay"),
        _dropdown("live_overlay.source", "Source", "Live Overlay", "Data", "Chooses telemetry source for traces.", "Final output is currently the supported overlay source.", ("Final output",), "Final output", "Final output shows post-pipeline values.", "Final output remains the supported data source.", topic="Live Overlay"),
        _number("live_overlay.history", "History", "Live Overlay", "Data", "Controls how many seconds of trace history are visible.", "Longer history gives context while shorter history responds visually faster.", 0.5, 60.0, 7.5, "0.50 s shows immediate motion.", "60.00 s shows long history.", units="s", recommended=(3.0, 15.0), topic="Live Overlay"),
    )


def _flight_recorder_metadata() -> tuple[ParameterMetadata, ...]:
    return (
        _text("flight_recorder.destination", "Destination", "Flight Recorder", "Recorder Settings", "Planned folder for recorder artifacts.", "Recorder artifacts remain metadata-only until real capture exists.", "recordings", "Empty destination would leave exports unavailable.", "Configured destination identifies where metadata artifacts are indexed.", topic="Flight Recorder"),
        _integer("flight_recorder.length", "Length", "Flight Recorder", "Recorder Settings", "Sets planned clip length.", "This is used for simulated metadata and future capture timing.", 5, 300, 30, "5 s is a short clip.", "300 s is a long clip.", units="s", recommended=(15, 90), topic="Flight Recorder"),
        _integer("flight_recorder.frame_rate", "Frame Rate", "Flight Recorder", "Recorder Settings", "Sets planned recording frame rate.", "The current shell stores this setting without performing real encoding.", 15, 60, 30, "15 fps is lighter.", "60 fps is smoother and heavier.", units="fps", recommended=(30, 60), topic="Flight Recorder"),
        _number("flight_recorder.history", "History", "Flight Recorder", "Recorder Settings", "Sets planned telemetry hindsight length.", "Telemetry hindsight is separate from unavailable video hindsight.", 1.0, 300.0, 30.0, "1.00 s keeps little history.", "300.00 s keeps long history.", units="s", recommended=(10.0, 90.0), topic="Flight Recorder"),
        _dropdown("flight_recorder.overlay_source", "Overlay Source", "Flight Recorder", "Recorder Settings", "Chooses which signal source appears in recorder overlay metadata.", "Final output is currently the supported source.", ("Final output",), "Final output", "Final output records post-pipeline telemetry metadata.", "Final output remains the supported source.", topic="Flight Recorder"),
        _dropdown("flight_recorder.capture_source", "Capture Source", "Flight Recorder", "Recorder Settings", "Chooses future capture source.", "Capture is unavailable in this build, so this remains descriptive metadata.", ("Display",), "Display", "Display is the planned source type.", "Display remains the placeholder capture source.", topic="Flight Recorder"),
        _text("flight_recorder.display", "Display", "Flight Recorder", "Recorder Settings", "Names the display intended for future capture.", "The current build does not capture the display.", "Primary display", "Empty display text leaves the target unnamed.", "Configured display text documents intended capture target.", topic="Flight Recorder"),
        _text("flight_recorder.hotkey", "Hotkey", "Flight Recorder", "Recorder Settings", "Configured hotkey text for future recorder control.", "The current build does not register a recorder hotkey.", "Ctrl+Shift+R", "Empty means no configured hotkey text.", "Configured text is displayed but not globally registered.", topic="Flight Recorder"),
        _boolean("flight_recorder.record_cursor", "Record Cursor", "Flight Recorder", "Recorder Settings", "Controls whether future capture would include cursor movement.", "No real capture is performed in this build.", False, "Cursor would be omitted in future capture.", "Cursor would be included in future capture.", topic="Flight Recorder"),
        _dropdown("flight_recorder.trigger_mode", "Trigger Mode", "Flight Recorder", "Recorder Settings", "Chooses how future recording is triggered.", "Current controls produce simulated metadata only.", ("Press to save previous interval",), "Press to save previous interval", "Press-to-save uses hindsight-style workflow.", "Press-to-save remains the supported trigger text.", topic="Flight Recorder"),
        _dropdown("flight_recorder.library_sort", "Recording Library Sort", "Flight Recorder", "Recording Library", "Chooses the local artifact sort order.", "Sorting changes only the local metadata list display.", ("Newest First",), "Newest First", "Newest first keeps recent simulated artifacts visible.", "Newest first remains the supported sort option.", topic="Flight Recorder"),
    )


def _diagnostics_metadata() -> tuple[ParameterMetadata, ...]:
    return (
        _boolean("diagnostics.runtime_preflight_dry_run", "Runtime Preflight Dry Run", "Perf / Diagnostics", "Runtime Setup", "Runs setup checks without launching installers.", "Dry-run diagnostics are observational and do not prove output verification.", True, "A non-dry run would require explicit future scope.", "Dry run reports setup truth without installing anything.", warning="Dry-run success is not Full Live Runtime Ready proof.", topic="Performance / Diagnostics"),
    )


def _with_category_scope(metadata: ParameterMetadata) -> ParameterMetadata:
    if metadata.category == "Live Overlay":
        return replace(metadata, support_scope=ParameterSupportScope.APP_RUNTIME_CONFIG)
    if metadata.category == "Flight Recorder":
        return replace(metadata, support_scope=ParameterSupportScope.SIMULATED_WORKSPACE_ONLY)
    if metadata.category == "Perf / Diagnostics":
        return replace(metadata, support_scope=ParameterSupportScope.DIAGNOSTIC_ONLY)
    return metadata


def _format_example(prefix: str, example: ParameterExample) -> str:
    return f"{prefix} ({escape(example.value)}): {escape(example.effect)}"


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if value is None:
        return "None"
    return str(value)


def _format_scope(scope: ParameterSupportScope) -> str:
    return scope.value.replace("_", " ")


PARAMETER_HELP = build_default_parameter_registry()
