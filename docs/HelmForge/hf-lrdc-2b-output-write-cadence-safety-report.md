# HF-LRDC-2B Output Write Cadence and Safety Hardening Report

## Problem Summary

HF-LRDC-2A made the Bridge output loop persistent, but the loop still needed stronger cadence and safety truth. HF-LRDC-2B adds explicit accounting for attempted ticks, accepted writes, successful writes, failed writes, skipped writes, rate-limited skips, disabled/unsafe skips, neutral restore proof, and safety-stop state.

## Cadence Accounting

`VirtualOutputWriteLoop` now tracks:

- configured target write rate;
- attempted output-loop ticks;
- backend write attempts;
- successful writes;
- failed writes;
- skipped writes;
- rate-limited skips;
- disabled skips;
- unsafe/unverified skips;
- safety-stopped skips;
- last allowed write timestamp;
- last skipped write reason;
- estimated actual accepted write rate.

Skipped writes are never counted as successful writes. The actual write-rate estimate is based only on accepted successful writes.

## Write, Skip, And Failure Classification

Loop tick results now classify outcomes with explicit statuses such as:

- `fake_write_recorded` / real backend success statuses;
- `skipped_rate_limited`;
- `skipped_disabled`;
- `skipped_unverified`;
- `skipped_safety_stopped`;
- `backend_unavailable`;
- `write_failed`;
- `error`;
- neutral restore backend statuses.

The loop catches backend write exceptions and converts them into safety-stopped write failures instead of crashing the Bridge.

## Safety Stop Behavior

Write failure handling now:

- increments failed-write counters;
- increments consecutive failure count;
- disables the loop;
- moves state to `safety_stopped`;
- preserves `safety_stop_reason`;
- records `safety_stop_timestamp`;
- refuses subsequent writes while safety-stopped;
- records subsequent ticks as `skipped_safety_stopped`.

No auto-resume behavior was added.

## Neutral Restore Proof

Neutral restore now reports:

- whether restore was attempted;
- restore status;
- restore timestamp;
- restore duration;
- restore message;
- restore error.

Neutral restore is only reported as restored when the backend reports success. If it was not needed, it remains `not_attempted`.

## Telemetry Fields Added

`output_loop_runtime` now includes cadence and safety fields:

- `actual_write_rate_hz`
- `tick_count`
- `write_attempt_count`
- `write_success_count`
- `write_failure_count`
- `write_skipped_count`
- `write_skipped_rate_limited_count`
- `write_skipped_disabled_count`
- `write_skipped_safety_count`
- `write_skipped_unsafe_count`
- `consecutive_write_failures`
- `last_write_duration_ms`
- `last_allowed_write_at`
- `last_skipped_write_reason`
- `neutral_restore_attempted`
- `neutral_restore_timestamp`
- `neutral_restore_message`
- `neutral_restore_error`
- `neutral_restore_duration_ms`
- `safety_stop_timestamp`

Bridge timing also exposes:

- `last_output_loop_tick_duration_ms`
- `last_output_loop_status`
- `output_loop_rate_limited`
- `output_loop_safety_stopped`

## Live Monitor Truth Update

The Live Monitor compact output-loop row now includes target rate, actual rate, successful/failed/skipped counts, rate-limited skip count, last write status, last skipped reason, neutral restore status, and safety reason.

The UI still does not claim verified/live/ready output unless telemetry and the existing readiness gate prove it.

## Tests Added

Added `tests/test_hf_lrdc_2b_output_write_cadence_safety.py`, covering:

- rate-limit skip accounting;
- disabled and unverified skip classification;
- failed write safety stop;
- backend exception safety stop;
- neutral restore not-attempted/success/failure truth;
- Bridge telemetry cadence/safety fields;
- Bridge timing output-loop fields;
- Bridge client pass-through;
- Live Monitor output-loop truth text;
- Full Live Runtime Ready remains false from skipped/fake writes.

## Deferred Work

Low-latency telemetry transport design is intentionally deferred to HF-LRDC-3A. Any later transport work should preserve the same output safety truth fields rather than replacing them with implicit freshness claims.

HF-LRDC-2B also does not add new physical input backends, Raw Input event-loop ownership, mapping/tuning behavior changes, broad UI redesign, unsafe output-enable commands, auto-save, game injection, graphics hooking, or cloud behavior.

## Runtime Truth Preservation

vJoy detected is not output verification. vJoy backend availability is not output verification. Output intent is not output write proof. A rate-limited or skipped write is not a successful write. Neutral restore attempted is not neutral restore succeeded unless the backend reports success. Full Live Runtime Ready still requires physical input proof, pipeline proof, real output verification, output loop running, and real write proof. Simulation fallback remains available, and the readiness gate was not weakened.
