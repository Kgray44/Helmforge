# HF-LRDC-6D Embedded Runtime Stall Isolation Report

## Problem Summary

After HF-LRDC-6C, Live Monitor kept `Embedded Bridge` as the active source, but the live graph still paused for roughly one second every four to five seconds. That meant source flapping was mostly fixed, while periodic blocking work was still delaying frame delivery or UI graph refresh.

The repair keeps Embedded Bridge authoritative while fresh and isolates slow Bridge-side diagnostic work from the Qt render path.

## Root Cause Found

The default embedded runtime already used a `QThread`, but each worker tick still called `BridgeService.run_once()` with its normal JSON telemetry publish side effect before the embedded frame could be recorded and emitted. That tick could also run periodic slow-lane discovery. In test/factory mode, the embedded runtime could still run synchronously on a `QTimer`, which made it easy for slow Bridge work to block Qt timers.

Live Monitor and tuning pages also read JSON telemetry every refresh even when a fresh embedded frame was already available. That kept diagnostic file reads in the live graph path.

## Worker And Nonblocking Changes

`EmbeddedBridgeRuntime` now supports explicit threaded factory mode for tests and custom service factories. The embedded worker calls:

- `BridgeService.run_once(publish_telemetry=False)` for the in-memory live frame;
- `BridgeService.build_telemetry_payload()` to preserve the full telemetry payload in the embedded memory cache;
- queued Qt signal delivery for the UI callback;
- a latest-frame async JSON publisher after the in-memory frame is available.

The UI does not wait for `BridgeService.run_once()` in threaded mode, and it does not wait for diagnostic JSON publishing.

## JSON Publish Decoupling

Embedded live telemetry is now delivered from memory first. JSON snapshot writing remains a diagnostic/fallback side effect, handled by a latest-frame background publisher.

If JSON publishing is slow or locked, the embedded frame can still reach Live Monitor and tuning pages. JSON success or failure does not affect output verification, Full Live Runtime Ready, or output proof.

## Slow-Lane Behavior

`BridgeServiceOptions.enable_periodic_discovery_refresh` was added. CLI/external Bridge behavior keeps periodic discovery enabled by default. The embedded app-owned Bridge disables periodic discovery refresh after startup so Windows discovery/PnP checks do not recur in the live graph cadence.

Explicit preflight and forced discovery remain available through the existing command path.

## Stall Diagnostics

Bridge timing telemetry now includes:

- `last_slow_lane_duration_ms`
- `last_discovery_blocked_ms`
- `last_json_publish_retry_count`
- `last_json_publish_blocked_ms`
- `last_worker_tick_duration_ms`
- `embedded_worker_late_tick_count`

Live Monitor has lightweight UI frame stall tracking:

- last UI frame delta;
- UI stall count;
- last UI stall duration;
- last stall timestamp.

The Live State text now reports UI frame cadence and stall count.

## Live Monitor And Tuning Graph Fixes

Live Monitor and `LiveAxisSampleSource` now short-circuit to fresh Embedded Bridge memory telemetry before reading stream/JSON sources. Bridge Stream and JSON remain fallback/diagnostic sources when embedded telemetry is stale or unavailable.

Base Tuning, Filtering, and Combat Profile use `LiveAxisSampleSource`, so their live dots/graphs avoid synchronous JSON reads while embedded telemetry is fresh.

## Tests Added

Added `tests/test_hf_lrdc_6d_embedded_runtime_stall_isolation.py`.

Coverage includes:

- embedded Bridge ticks can skip JSON publish and periodic discovery;
- threaded embedded runtime does not block Qt timers during slow Bridge ticks;
- async JSON submit returns quickly while the writer is slow;
- tuning live source skips JSON reads when embedded memory telemetry is fresh;
- embedded memory frames retain the full Bridge payload, including `bridge_timing` and `physical_input_fidelity`;
- UI stall monitor records only large frame gaps.

## Remaining Limitations

Manual Windows/HOTAS validation is still required to prove the visible 60-second Live Monitor and tuning-page freeze is gone on the physical device. This pass does not implement full native Raw Input, change mapping/tuning behavior, or enable output writes.

JSON remains a diagnostic/fallback snapshot. If embedded telemetry truly becomes stale or unavailable, the UI can still fall back to Bridge Stream, JSON, or simulation with truthful labels.

## Runtime Truth Preservation

Embedded Bridge telemetry freshness does not prove vJoy writes. Fresh graph frames do not prove output verification. Output intent remains separate from output write proof. vJoy detection is not output verification. Simulation and JSON fallback remain available. No fake output verification, fake Full Live Runtime Ready, game injection, graphics hooking, cloud behavior, auto-save, or unsafe output enablement was added.
