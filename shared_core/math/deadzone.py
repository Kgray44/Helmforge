from __future__ import annotations

from dataclasses import dataclass

from shared_core.math.curves import clamp, finite_float


@dataclass(frozen=True)
class DeadzoneResult:
    input_value: float
    output: float
    active: bool
    metadata: dict[str, float | bool]


def apply_center_deadzone(
    value: float,
    *,
    deadzone: float,
    anti_deadzone: float = 0.0,
    hysteresis: float = 0.0,
    previous_output: float | None = None,
) -> DeadzoneResult:
    x = clamp(value)
    dz = clamp(deadzone, 0.0, 1.0)
    anti = clamp(anti_deadzone, 0.0, 1.0)
    hyst = max(0.0, finite_float(hysteresis, 0.0))
    magnitude = abs(x)
    previous = None if previous_output is None else finite_float(previous_output, 0.0)

    metadata: dict[str, float | bool] = {
        "deadzone": dz,
        "anti_deadzone": anti,
        "hysteresis": hyst,
        "hysteresis_active": False,
        "remapped": False,
    }

    threshold = dz
    if hyst > 0.0 and previous is not None:
        if previous == 0.0:
            threshold = min(1.0, dz + hyst)
        else:
            threshold = max(0.0, dz - hyst)
        metadata["hysteresis_active"] = threshold != dz

    if dz >= 1.0 or magnitude <= threshold:
        return DeadzoneResult(input_value=x, output=0.0, active=True, metadata=metadata)

    remapped = (magnitude - dz) / (1.0 - dz)
    if anti > 0.0:
        remapped = anti + remapped * (1.0 - anti)

    output = clamp(remapped) * (1.0 if x >= 0.0 else -1.0)
    metadata["remapped"] = True
    return DeadzoneResult(input_value=x, output=output, active=dz > 0.0 or anti > 0.0, metadata=metadata)
