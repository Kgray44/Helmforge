# HF-LRDC-2A Persistent vJoy Output Loop Ownership Report

## Problem Summary

Before HF-LRDC-2A, Bridge runtime refresh rebuilt `VirtualOutputWriteLoop` during the fast runtime path. That meant output-loop ownership state such as write count, rate limiter timing, safety stop state, neutral restore status, and last write status could be reset on normal ticks. A real live output path needs Bridge-owned persistent state that survives across frames.

## Ownership Before vs After

Before:

- Bridge created a new `VirtualOutputWriteLoop` inside `_refresh_runtime_io()`.
- Verification and loop construction were coupled to per-tick runtime refresh.
- Loop state could be reset before the RuntimeOrchestrator built the next frame.

After:

- Bridge owns a persistent `BridgeOutputRuntimeSession`.
- The session owns the virtual output backend, cached verification result, and one persistent `VirtualOutputWriteLoop`.
- Normal fast ticks reuse the same loop object.
- Write count, rate limiter state, last write status, safety stop reason, failure count, and neutral restore status persist across ticks.

## Persistence Location

Persistence is implemented in `bridge_app/runtime_session.py`.

`BridgeService` creates one `BridgeOutputRuntimeSession` during startup and passes the persistent loop into `RuntimeOrchestrator`. Config/runtime refresh no longer creates a fresh output loop each tick.

## Verification Caching

Verification is cached in the Bridge output runtime session.

- Startup performs the existing safe verification path only when output verification is enabled and Bridge is not in simulation mode.
- Normal fast ticks reuse the cached verification result.
- `RunPreflight` can explicitly refresh verification.
- A verification refresh intentionally rebuilds the loop with the new verification result and records the recreate reason.
- Missing, disabled, fake, or failed verification does not become real output proof.

## Output Loop Lifecycle

Startup:

- Create output backend.
- Create persistent output runtime session.
- Cache verification when allowed.
- Create persistent output loop.

Fast tick:

- Read physical input if available.
- Build runtime frame.
- Reuse the persistent output loop.
- Enable/tick only if existing gates allow it.
- Keep the loop disabled when simulation, missing input, or verification gates block output.

Switch to simulation:

- Disable the output loop.
- Attempt neutral restore if the loop was enabled and had writes.
- Preserve neutral restore status in telemetry.

Safety stop:

- A write failure moves the loop to `safety_stopped`.
- Failure count and safety stop reason persist in telemetry.
- The readiness gate remains blocked.

## Telemetry Fields Added

Bridge telemetry now includes `output_loop_runtime`:

```json
{
  "backend_name": "...",
  "backend_kind": "...",
  "selected_output_device": "...",
  "verification_status": "...",
  "verification_cached": true,
  "verification_age_ms": 0.0,
  "verification_source": "...",
  "verification_real": false,
  "verification_fake": false,
  "enabled": false,
  "running": false,
  "state": "disabled",
  "write_rate_hz": 30.0,
  "write_count": 0,
  "failure_count": 0,
  "last_write_timestamp": "Unavailable",
  "last_write_status": "Not active",
  "last_write_duration_ms": null,
  "neutral_restore_status": "not_attempted",
  "safety_stop_reason": "None",
  "loop_recreated_count": 0,
  "last_recreate_reason": "startup",
  "current_output_intent_source": "None",
  "warnings": [],
  "errors": []
}
```

The Bridge client passes this optional block through, and the Live Monitor adds a compact output-loop runtime truth row.

## Tests Added

Added `tests/test_hf_lrdc_2a_persistent_vjoy_output_loop.py`, covering:

- output loop object reuse across fast ticks;
- write count persistence;
- rate limiter state not resetting during normal ticks;
- cached verification not rerun every fast tick;
- explicit `RunPreflight` verification refresh;
- disabled verification keeping output loop disabled;
- switch-to-simulation neutral restore;
- write failure safety-stop persistence;
- Bridge client pass-through.

## Deferred Work

HF-LRDC-2A intentionally does not implement detailed output write cadence/safety hardening. That remains HF-LRDC-2B.

This phase also does not add new telemetry transport, new physical input backends, full Raw Input event-loop ownership, mapping/tuning behavior changes, broad UI redesign, auto-save, game injection, graphics hooking, or cloud behavior.

## Runtime Truth Preservation

vJoy detected is not output verification. vJoy backend availability is not output verification. Output intent is not output write proof. Physical input working does not prove vJoy writes. Config match does not prove vJoy writes. Full Live Runtime Ready still requires the existing proof chain: physical input proof, pipeline proof, real output verification, output loop running, and real write proof. Simulation fallback remains available, and the readiness gate was not weakened.
