# HF-LRDC-1C Live Monitor Frame Dedupe and Telemetry Truth Report

## Problem Summary

The Live Monitor refreshed on a fast UI timer and appended graph history every refresh. Bridge telemetry can publish slower than the UI timer, so the same Bridge frame could be appended repeatedly as if it were new runtime data. That inflated graph history with duplicate samples and made motion look chunky, delayed, and misleadingly alive.

## Frame Identity Strategy

HF-LRDC-1C adds a testable Bridge frame identity helper in `v3_app/pages/live_monitor_data.py`.

Identity priority:

1. `runtime_frame.sequence`
2. `runtime_frame.frame_id`
3. `runtime_frame.generated_at`
4. telemetry `timestamp`
5. `bridge_timing.tick_count`

The identity object keeps the source type, sequence, frame ID, generated timestamp, telemetry timestamp, tick count, identity key, and a warning when the identity source is weak.

## Dedupe Behavior

`LiveMonitorPage.refresh_snapshot()` now accepts a Bridge sample into graph/history only when the Bridge frame identity changes.

- First Bridge frame appends.
- Repeated Bridge frame updates labels but does not append.
- New sequence appends.
- New generated timestamp appends when sequence/frame ID are missing.
- Missing, stale, invalid, or errored Bridge telemetry still uses simulation fallback.

The UI timer rate was not lowered, and no fake interpolation/smoothing was added.

## Cadence Calculation

`LiveTelemetryFrameTracker` stores timestamps for a bounded window of accepted Bridge frames and estimates cadence only from accepted new frames. Repeated frames do not inflate cadence. Cadence remains unavailable until at least two accepted frames exist.

## UI Truth Labels Added

The Live State text now includes compact truth lines for:

- Bridge frame sequence/ID;
- frame age;
- Bridge tick duration;
- accepted-frame cadence;
- new vs repeated frame state;
- repeated frames skipped;
- physical input backend and kind;
- physical input sample age;
- physical input read duration;
- physical input sample rate;
- physical input mapping status.

## Bridge Timing Display

The Live Monitor reads `bridge_timing.tick_count` and `bridge_timing.last_tick_duration_ms` from the optional Bridge timing block. Missing timing remains unavailable instead of being guessed.

## Physical Input Fidelity Display

The Live Monitor reads `physical_input_fidelity` and `physical_input_backend_choice` when present, and keeps older telemetry compatible when those blocks are absent.

## Stale vs Repeated

Repeated is not stale. A repeated frame means telemetry is fresh enough but has the same frame identity as the last accepted Bridge frame. Stale means the telemetry timestamp exceeded the configured stale threshold. Missing and invalid telemetry remain separate states. Simulation fallback remains available.

## Tests Added

Added `tests/test_hf_lrdc_1c_live_monitor_frame_dedupe.py`, covering:

- identity extraction priority and weak fallback;
- repeated-frame suppression;
- generated-at fallback when sequence is missing;
- accepted-frame cadence that ignores repeats;
- Live Monitor truth labels;
- stale telemetry fallback;
- runtime truth preservation.

## Deferred Work

- HF-LRDC-1D: Bridge/UI workspace config handshake.
- Later phases: output cadence/safety hardening and transport upgrades.

HF-LRDC-1C does not add output proof, vJoy authority, new telemetry transport, full Raw Input ownership, game injection, graphics hooking, cloud behavior, or auto-save.

## Runtime Truth Preservation

Fresh telemetry is not vJoy write proof. Physical input does not mean Full Live Runtime Ready. vJoy detected is not output verification. Output intent is not output write proof. Repeated telemetry is not displayed as new data. The readiness gate remains unchanged.
