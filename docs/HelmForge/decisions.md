# HelmForge Decisions

## Phase 0 Foundation

- User-facing product name: **HelmForge**.
- Technical subtitle / legacy descriptor: **HOTAS Control Panel V3**.
- UI stack starts with PySide6 / Qt Widgets, matching the recovered rebuild direction.
- Graph dependency starts with pyqtgraph, matching the recovered rebuild direction.
- Runtime strategy is simulation-first. No real HOTAS or vJoy support is implemented in Phase 0.
- Known target hardware is the Thrustmaster T-Flight HOTAS One, but it is only documented as a future target in Phase 0.
- Recovered forensic documents and PNG screenshots remain in their original folder and are referenced from `docs/recovery/` to avoid evidence drift.

## Phase 2 Workspace Schema

- Starting schema version: `3.0.0`.
- V3 workspace/config filename: `hotas_bridge_config_v3.json`.
- Recovered V2 filename preserved as provenance: `hotas_bridge_config_v2.json`.
- Per-axis model dictionaries use canonical axis IDs while each record preserves the recovered display name.
- JSON persistence uses the standard library and refuses silent overwrites by default.

## Phase 3 Math Pipeline

- Centered axes use the recovered cubic-blend S-curve: `y = (1-k)x + kx^3`.
- Linear graph reference data is generated independently as true `y=x`.
- Deadzone remaps the remaining range after the threshold so full travel can still reach full output.
- Filtering uses center/edge alpha plus same-direction and reverse-direction slew limits.
- Simulation final outputs now pass through the shared-core stack while runtime truth remains simulated unless live hardware/output is genuinely verified.
