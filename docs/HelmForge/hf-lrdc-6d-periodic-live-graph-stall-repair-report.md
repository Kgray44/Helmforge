# HF-LRDC-6E Periodic Live Graph Stall Repair Report

Note: the requested artifact path uses `6d` in the filename, but this report covers HF-LRDC-6E only.

## Problem Summary

After source stickiness was repaired, Live Monitor stayed on `Embedded Bridge`, but the graph still paused roughly every four to five seconds. That pointed to slow work still happening in the live lane rather than source arbitration.

The remaining stall candidates were:

- periodic Bridge discovery checks during `BridgeService.run_once()`;
- repeated physical device enumeration while a sampler was already open;
- synchronous JSON fallback reads from tuning/live graph refreshes;
- double JSON snapshot writes on successful telemetry publish.

## Root Causes Found

`BridgeService.run_once()` still refreshed discovery from the fast tick path when due. `_refresh_runtime_io()` selected a physical device every tick by enumerating backend devices. `PhysicalInputSampler.read_once()` also validated selection on every read, which caused another enumeration. The WinMM backend also re-enumerated the selected joystick inside `read_current_state()`.

On the UI side, Live Monitor and tuning pages already prefer Embedded Bridge after HF-LRDC-6D, but they now expose JSON-read skip diagnostics so the lazy behavior is visible.

`BridgeService._publish_telemetry()` wrote JSON twice on success to include the final publish status in the same file snapshot. That doubled diagnostic file I/O.

## Discovery Decoupling

Discovery now runs at startup and on explicit forced refresh such as `RUN_PREFLIGHT`. During normal runtime ticks, the Bridge skips discovery when the active physical sampler is healthy.

New timing telemetry includes:

- `last_discovery_refresh_reason`
- `discovery_running`
- `discovery_skipped_reason`
- `last_discovery_duration_ms`
- `last_discovery_age_ms`

`RUN_PREFLIGHT` still forces discovery and clears the selected-device cache so device selection is refreshed afterward.

## Selected Device Caching

The Bridge now caches the selected physical device ID after discovery/selection. While the sampler is healthy, later ticks reuse the cached ID and skip backend enumeration.

New timing telemetry includes:

- `selected_physical_device_id`
- `selected_physical_device_source`
- `device_selection_refresh_count`
- `device_enumeration_duration_ms`
- `device_enumeration_skipped_cached_count`

The embedded live path uses `PhysicalInputSampler(validate_selection_on_read=False)` after opening the device, so read ticks do not re-enumerate. The WinMM backend caches the opened device info and relies on `joyGetPosEx` truth for missing/error states instead of enumerating every read.

## Lazy JSON Fallback

`LiveAxisSampleSource` reads Embedded Bridge telemetry first. If embedded telemetry is fresh, it returns immediately and skips JSON fallback reads. JSON is read only when embedded telemetry is missing, stale, or invalid.

Live Monitor follows the same rule: fresh Embedded Bridge memory telemetry bypasses stream/JSON file reads for the active graph frame. JSON remains available as fallback when embedded telemetry is not usable.

Diagnostics now track JSON read duration and whether JSON was skipped because embedded telemetry was fresh.

## JSON Double-Write Removal

`BridgeService._publish_telemetry()` now writes the JSON snapshot once per publish. The current publish status is retained in memory/telemetry state and appears in following payloads instead of forcing a second disk write.

This keeps JSON as a diagnostic/fallback snapshot while avoiding unnecessary file I/O in the Bridge publish path.

## Tests Added

Added `tests/test_hf_lrdc_6d_periodic_live_graph_stall_repair.py`.

Coverage includes:

- `run_once()` skips slow discovery while a sampler is healthy;
- `RUN_PREFLIGHT` still forces discovery;
- active sampler uses cached selected device ID;
- backend `enumerate_devices()` is not called every tick while the sampler is healthy;
- tuning `LiveAxisSampleSource` skips JSON reads when embedded telemetry is fresh;
- JSON fallback is read when embedded telemetry becomes stale;
- Live Monitor skips synchronous JSON reads when embedded telemetry is fresh;
- telemetry publish writes JSON once;
- runtime truth remains conservative through existing HF-LRDC tests.

## Manual Windows/HOTAS Validation

Manual validation still needs to be run on the physical bench:

1. Plug in the Thrustmaster T-Flight HOTAS One.
2. Open HelmForge.
3. Open Live Monitor for at least 60 seconds.
4. Confirm active source remains `Embedded Bridge`.
5. Confirm the graph no longer pauses every four to five seconds.
6. Open Base Tuning, Filtering, and Combat Profile.
7. Confirm live dots/graphs do not pause periodically.
8. Check diagnostics for no periodic spikes in discovery, device enumeration, or JSON read timing.

## Runtime Truth Preservation

Embedded Bridge telemetry does not prove vJoy writes. Output intent is not output write proof. vJoy detection is not output verification. Simulation and JSON fallback remain available, but JSON fallback is lazy relative to fresh Embedded Bridge telemetry. No fake output verification, fake Full Live Runtime Ready, game injection, graphics hooking, cloud behavior, auto-save, or unsafe output enablement was added.
