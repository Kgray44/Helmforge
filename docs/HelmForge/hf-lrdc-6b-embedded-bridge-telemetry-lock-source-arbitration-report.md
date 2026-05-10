# HF-LRDC-6B Embedded Bridge Telemetry Lock and Source Arbitration Report

## Problem Summary

During live HOTAS testing, embedded Bridge ticks could fail when Windows denied the final replace step for `%TEMP%/helmforge_bridge_telemetry.json`. The traceback showed `PermissionError [WinError 5]` from the atomic JSON publish path. Because the UI still depended on the JSON snapshot for some live graphs, a transient diagnostic-file write failure could make pages fall back to simulation even though the embedded Bridge had just produced a fresh physical telemetry frame.

The user-visible result was source flapping: live graphs jumped between real HOTAS values and simulation values.

## Root Cause Hypothesis

The JSON snapshot is a shared diagnostic/fallback file. On Windows, readers, antivirus, indexing, or another Bridge producer can briefly lock the target path during `Path.replace()`. The old implementation treated that diagnostic write as part of the Bridge tick itself, so a locked file could prevent in-memory embedded telemetry from reaching UI consumers.

## JSON Publish Failure Handling

`BridgeService.run_once()` now treats JSON telemetry publishing as a best-effort side effect:

- the runtime frame is built first;
- JSON publish failures are caught inside `_publish_telemetry()`;
- `run_once()` still returns the fresh in-memory `BridgeTelemetrySnapshot`;
- returned telemetry includes a warning when JSON publish failed;
- `BridgeService.telemetry_publish_status` records success/failure, path, error, and timestamps.

The optional telemetry block is:

```json
"telemetry_publish": {
  "json_success": true,
  "json_error": "",
  "json_attempts": 1,
  "json_path": "...",
  "last_success_at": "...",
  "last_failure_at": null
}
```

Older telemetry parsing remains compatible because the block is optional.

## Retry Policy

`bridge_app.ipc.atomic_write_json()` now retries transient `PermissionError` / `OSError` failures during `temp_path.replace(target)`.

Policy:

- default attempts: 5;
- short incremental sleep between attempts;
- temporary file cleanup on final failure;
- success still returns the target `Path`;
- final failure still raises to callers that need strict behavior.

BridgeService catches those final failures so embedded live telemetry is not lost.

## Embedded In-Memory Telemetry

The UI now has a small embedded Bridge telemetry cache:

- `EmbeddedBridgeRuntime.tick()` records each fresh in-memory telemetry frame before emitting it;
- worker-thread ticks do the same;
- live source readers can use this frame even when JSON publishing failed;
- freshness is still enforced, so stale embedded frames can fall back to JSON or simulation truthfully.

This makes embedded Bridge telemetry the preferred UI source for embedded app runs without removing JSON diagnostics.

## Source Arbitration Rules

For affected live surfaces:

1. Fresh embedded Bridge telemetry wins.
2. Fresh Bridge stream wins when embedded telemetry is unavailable/stale.
3. Fresh Bridge JSON snapshot wins when stream is unavailable/stale/invalid.
4. Simulation fallback activates only when no fresh embedded/stream/JSON telemetry is available.

This prevents one locked JSON replace from inserting a simulation frame between physical HOTAS frames.

## Live Monitor And Tuning Graphs

Live Monitor now checks the embedded telemetry cache before stream/JSON fallback.

The tuning graph source used by Base Tuning, Filtering, and Combat Profile goes through `LiveAxisSampleSource`, which now also prefers fresh embedded telemetry before JSON and simulation. This keeps those live graphs on the same source policy without a redesign.

## Tests Added

Added `tests/test_hf_lrdc_6b_embedded_bridge_telemetry_lock_source_arbitration.py`.

Coverage includes:

- non-fatal JSON publish failure in `BridgeService.run_once()`;
- embedded runtime still emitting in-memory telemetry under JSON lock failure;
- atomic write retry success after transient `PermissionError`;
- temp cleanup after final failure;
- live axis source choosing embedded telemetry over missing JSON;
- simulation fallback still activating once embedded telemetry is stale.

## Remaining Limitations

- This pass does not implement full multi-writer arbitration or an external Bridge lifecycle manager.
- A producer identity flip warning was not added beyond existing Bridge PID/timing identity and telemetry source labels.
- Real app manual validation should still confirm the Live Monitor, Base Tuning, Filtering, and Combat Profile graphs no longer jump between HOTAS and simulation while the HOTAS is moved.

## Runtime Truth Preservation

HF-LRDC-6B does not change physical input proof, vJoy output behavior, output verification, mapping/tuning behavior, or readiness gates. Embedded telemetry freshness does not prove vJoy writes. JSON write success does not prove output verification. Output intent remains separate from output write proof. Simulation fallback remains available when all live sources are missing or stale. No fake output verification, fake Full Live Runtime Ready, game injection, graphics hooking, cloud behavior, auto-save, or unsafe output enablement was added.
