# Runtime Preflight and vJoy Setup

HelmForge can run without vJoy, without a connected HOTAS, and without hardware drivers installed. In that case it uses simulation mode and reports the missing runtime pieces instead of failing at startup.

## Known Target Hardware

The primary physical HOTAS target is:

- **Thrustmaster T-Flight HOTAS One**
- Also written as **Thrustmaster T.Flight Hotas One**

HelmForge uses this target metadata during runtime preflight detection. Phase 1 only detects likely device names and reports status. It does not implement real HOTAS polling.

## Thrustmaster Software vs vJoy

Thrustmaster driver/software and vJoy are separate runtime pieces:

- The Thrustmaster driver/software helps Windows recognize and expose the physical HOTAS input device.
- vJoy or a future output backend provides a virtual joystick output target.
- HelmForge sits between physical input and output backend in future phases, but Phase 1 does not write live output.

Installing one does not imply the other is present. HelmForge reports input and output status separately so missing pieces are obvious.

## Runtime Status

Phase 1 exposes typed status for:

- physical HOTAS input detection,
- vJoy/output backend detection,
- selected runtime mode,
- runtime truth label,
- detected device names,
- detected output backend name,
- warnings and errors,
- whether live output writes have actually been verified.

If the target HOTAS is missing, HelmForge reports the input as missing and stays non-blocking. If vJoy is missing, HelmForge reports `vjoy_missing` and continues in simulation mode.

## Simulation Mode

Simulation mode produces safe synthetic values for:

- Roll
- Pitch
- Throttle
- Yaw
- Aux 1
- Aux 2
- Buttons B1-B15
- Hat state

Simulation snapshots are explicitly labeled as simulated. This lets development continue before physical hardware, Thrustmaster software, or vJoy are installed.

## Full Live Output Requirements

Full live output requires later implementation and verification of both:

- a detected physical HOTAS input device,
- a detected output backend with live output writes verified.

Phase 1 never claims `full_live` unless live output writes are verified. Since real vJoy writes are not implemented in Phase 1, the app should remain in simulation fallback or a blocked/unverified truth state.

## Installation Boundary

Driver installation steps are intentionally separated from detection code. Phase 1 does not:

- install Thrustmaster drivers,
- install vJoy,
- download files from driver websites,
- write real vJoy output,
- claim real HOTAS or vJoy runtime support is working.

When installation is introduced in a later reviewed phase, it should be documented as an operator action and verified separately from runtime detection.

