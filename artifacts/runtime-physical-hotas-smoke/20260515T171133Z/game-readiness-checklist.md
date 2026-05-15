# HelmForge Runtime 1D Game-Readiness Checklist

[x] HOTAS detected by Bridge/shared runtime probe.
[x] vJoy detected.
[x] Physical axes/buttons/hat can be observed by the guided probe when each step passes.
[x] Runtime stage/final values changed during guided input proof when each step passes.
[x] Output intent changed during guided input proof when each step passes.
[x] vJoy write calls accepted when enabled.
[ ] Game-level verification observed externally.

- Target games should bind controls from vJoy Device 1 when HelmForge is used as the remapping/output layer.
- If the game sees both the physical HOTAS and vJoy, duplicate input may occur.
- Direct physical HOTAS hiding/filtering is intentionally out of scope for Runtime Usability 1D.
- Direct physical HOTAS hiding/filtering is intentionally deferred to a separate later phase.
- vJoy readback is not implemented unless separately verified.
- Game-level verification is manual unless an actual game or external controller observer is tested.
