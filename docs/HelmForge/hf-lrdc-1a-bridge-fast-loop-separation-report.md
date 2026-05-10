# HF-LRDC-1A Bridge Fast Loop Separation and Timing Truth Report

## Problem Summary

The Bridge fast tick was doing slow discovery work on every `run_once()` call. That made the live runtime path vulnerable to repeated HOTAS discovery/preflight work, including Windows PnP or PowerShell-backed scanning, while the Live Monitor expected low-latency input/output updates.

HF-LRDC-1A separates that slow lane from the fast tick and adds timing telemetry so Bridge latency can be inspected honestly.

## Slow Work Removed From The Fast Tick

- `BridgeService.run_once()` no longer calls full HOTAS discovery unconditionally.
- Startup still performs an initial discovery refresh.
- Fast ticks consume commands, use cached discovery state, refresh runtime I/O, build the runtime frame, and publish telemetry.
- Slow discovery is now handled through `_refresh_device_discovery_if_due(force=False)` and `_run_slow_discovery()`.
- Discovery failures keep the last cached discovery result when one exists and surface a warning instead of silently clearing runtime state.

## Continuous Bridge Mode

`bridge_app.main` now supports:

```text
python -m bridge_app.main --run
```

Continuous mode calls `BridgeService.run_forever()` and respects `tick_interval_ms`. `KeyboardInterrupt` exits cleanly. Existing bounded and test modes remain:

```text
python -m bridge_app.main --once
python -m bridge_app.main --run-for-ms 500
python -m bridge_app.main --status
```

## Discovery Cache And Throttle Behavior

- New option: `BridgeServiceOptions.discovery_refresh_interval_seconds`, default `2.0`.
- The service clamps the slow interval to at least 2 seconds.
- Startup forces discovery once.
- `RunPreflight` forces discovery immediately.
- Regular fast ticks reuse cached discovery until the slow interval is due.
- `Status` reports current cached state through the normal one-tick path and does not reintroduce per-tick discovery.

## Timing Telemetry Fields

Telemetry now includes a `bridge_timing` block:

```text
bridge_pid
bridge_started_at
tick_count
tick_interval_target_ms
last_tick_duration_ms
last_command_duration_ms
last_discovery_duration_ms
last_discovery_age_ms
last_runtime_io_duration_ms
last_runtime_frame_duration_ms
last_input_read_duration_ms
last_pipeline_duration_ms
last_output_write_duration_ms
last_telemetry_publish_duration_ms
fast_loop_status
slow_lane_status
```

`v3_app/services/bridge_client.py` passes this block through without changing existing required telemetry parsing.

## Tests Added

Added `tests/test_hf_lrdc_1a_bridge_fast_loop_separation.py` covering:

- CLI parser support for `--run`, while preserving `--once`, `--run-for-ms`, and `--status`.
- Startup discovery runs once.
- Multiple fast ticks do not repeat discovery before the slow interval.
- `RunPreflight` forces discovery without making every later tick a discovery tick.
- Timing telemetry is present and numeric where required.
- `BridgeTelemetryClient` accepts `bridge_timing`.
- Output verification and Full Live Runtime Ready gates remain conservative.

## Runtime Truth Preservation

HF-LRDC-1A does not weaken runtime readiness. Physical input alone is still not Full Live Runtime Ready. vJoy detection is still not output verification. Output intent remains separate from output write proof. JSON telemetry freshness remains separate from vJoy write proof. Simulation fallback remains available.

## Intentionally Deferred

- HF-LRDC-1B: Raw Input / HID / DirectInput physical input backend upgrade.
- HF-LRDC-1C: Live Monitor frame dedupe.
- HF-LRDC-1D: Bridge/UI workspace config handshake.

This phase also did not add unsupported runtime authority, fake vJoy proof, game injection, graphics API hooking, cloud behavior, or auto-save.
