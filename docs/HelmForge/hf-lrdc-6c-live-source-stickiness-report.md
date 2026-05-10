# HF-LRDC-6C Live Source Stickiness Report

## Problem Summary

After HF-LRDC-6B, the app no longer lost embedded telemetry when JSON publishing hit a Windows file lock. The remaining symptom was source flapping: the live graph would run smoothly as `Embedded Bridge`, then periodically switch to `Bridge Telemetry` / JSON for a moment, freeze, and switch back.

The problem was source arbitration, not input sampling. Embedded Bridge and JSON telemetry were still being treated as competing live sources on every UI refresh.

## Why Source Flapping Occurred

Embedded telemetry had a very tight freshness window and no sticky ownership state. Every graph tick recalculated the source from scratch. If embedded delivery had a brief gap while the JSON snapshot was fresh, JSON could temporarily become the active graph source even though the embedded Bridge was still the app-owned live runtime.

That made diagnostic JSON behave like a peer live source instead of a fallback.

## Final Source Priority

The live source priority is now:

1. Fresh `Embedded Bridge`
2. Fresh `Bridge Stream`, only when embedded is unavailable or stale
3. Fresh `Bridge JSON Snapshot`, only when embedded and stream are unavailable or stale
4. `Simulation Fallback`

JSON remains diagnostic/fallback while embedded runtime is active and fresh.

## Embedded Bridge Authority Rule

Once `Embedded Bridge` is selected, it stays the active source until embedded telemetry is actually stale or unavailable beyond the embedded stale threshold. Fresh JSON updates do not supersede embedded telemetry and do not increment source-switch counts.

Current defaults:

- embedded stale threshold: `1.0s`
- source switch cooldown field tracked by the selector: `0.5s`

The selector records current source, switch count, last switch reason, fallback reason, and whether the source is locked to embedded.

## Live Monitor And Tuning Graph Changes

Added `LiveTelemetrySourceSelector` in `v3_app/services/live_source_arbitration.py`.

Live Monitor now uses the selector for embedded/stream/JSON arbitration. Base Tuning, Filtering, and Combat Profile live graph paths use `LiveAxisSampleSource`, which also uses the same selector and fresh embedded telemetry cache.

The result is:

- embedded frames drive the graph while fresh;
- JSON refreshes remain diagnostic;
- graph history is not cleared or replaced by simulation during normal embedded operation;
- fallback remains available if embedded truly becomes stale.

## Tests Added

Added `tests/test_hf_lrdc_6c_live_source_stickiness.py`.

Coverage includes:

- fresh Embedded Bridge selected over fresh JSON;
- repeated JSON refreshes do not switch away from Embedded Bridge;
- stale Embedded Bridge falls back to JSON;
- recovered Embedded Bridge regains authority;
- tuning source does not alternate between embedded, JSON, and simulation while embedded is fresh;
- Live Monitor `_read_bridge_telemetry()` keeps Embedded Bridge over fresh JSON;
- source freshness does not create output verification or Full Live Runtime Ready proof.

## Remaining Limitations

Manual Windows/HOTAS validation is still needed to confirm the visible 30-second Live Monitor and tuning-page behavior on the physical device. This pass does not add a full multi-producer lifecycle manager; it only prevents JSON/Bridge Telemetry from stealing live graph authority while embedded telemetry is fresh.

## Runtime Truth Preservation

Embedded Bridge telemetry freshness does not prove vJoy writes. JSON freshness does not prove output verification. Output intent remains separate from output write proof. vJoy detection is not output verification. Simulation and JSON fallback remain available when higher-priority live sources are missing or stale. No fake output verification, fake Full Live Runtime Ready, game injection, graphics hooking, cloud behavior, auto-save, or unsafe output enablement was added.
