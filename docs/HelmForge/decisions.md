# HelmForge Decisions

## Phase 0 Foundation

- User-facing product name: **HelmForge**.
- Technical subtitle / legacy descriptor: **HOTAS Control Panel V3**.
- UI stack starts with PySide6 / Qt Widgets, matching the recovered rebuild direction.
- Graph dependency starts with pyqtgraph, matching the recovered rebuild direction.
- Runtime strategy is simulation-first. No real HOTAS or vJoy support is implemented in Phase 0.
- Known target hardware is the Thrustmaster T-Flight HOTAS One, but it is only documented as a future target in Phase 0.
- Recovered forensic documents and PNG screenshots remain in their original folder and are referenced from `docs/recovery/` to avoid evidence drift.

