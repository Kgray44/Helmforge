# HF-LRDC-3A Low-Latency Telemetry Transport Report

Unique repair track: HF-LRDC, HelmForge Live Runtime Data Chain.

## Problem Summary

The Bridge still publishes live UI telemetry primarily through `%TEMP%/helmforge_bridge_telemetry.json`. That JSON snapshot remains valuable for diagnostics, crash recovery, and human inspection, but it should not remain the primary high-rate live telemetry bus. File polling can add latency, jitter, repeated-frame reads, and confusing UI cadence unless it is treated as fallback/diagnostic truth rather than the live stream.

## Transport Options Compared

The design document compares:

- current JSON snapshot file;
- localhost WebSocket;
- localhost TCP socket;
- Windows named pipe;
- memory-mapped file / shared memory ring buffer;
- hybrid stream primary + JSON diagnostic fallback.

The comparison covers latency, jitter, implementation complexity, packaging impact, dependency impact, Windows compatibility, cross-platform potential, local-only safety, firewall behavior, multiple UI client support, Bridge restart handling, UI reconnect behavior, schema evolution, testability, human-debuggability, failure modes, suitability for 30 Hz / 60 Hz / 120 Hz telemetry, command/control suitability, and whether the channel should carry latest frames or large history buffers.

## Final Recommendation

Final recommended transport: localhost WebSocket stream primary.

JSON fallback role: JSON snapshot remains the diagnostic and fallback snapshot. The existing command file remains separate for HF-LRDC-3B unless a later phase designs a command stream.

This choice gives HelmForge a specific implementation path for HF-LRDC-3B with push-based low-latency telemetry, natural multiple-client support, versioned full-frame JSON messages, reasonable Windows packaging, cross-platform potential, and lower complexity than a custom TCP framing layer or shared memory ring buffer.

## Message Schema Summary

The proposed schema is `helmforge.telemetry_frame.v1`.

The stream envelope includes:

- schema and payload versions;
- transport name, server start time, stream sequence, generated time, sent time, and heartbeat flag;
- Bridge PID, Bridge start time, lifecycle state, and runtime truth;
- a `payload` object carrying the existing telemetry payload;
- optional warnings and errors.

The first implementation should send full frames, not deltas. Full frames make reconnect, testing, and JSON fallback compatibility simpler. Delta frames remain a later optimization only after measured need.

## Source Priority

Source priority:

1. Fresh valid Bridge stream frame.
2. Fresh valid Bridge JSON snapshot.
3. Simulation fallback.

Stream frames must be valid and fresh to win. JSON frames must be valid and fresh to serve as fallback. Simulation remains available when both Bridge sources are missing, stale, or invalid.

## Cadence Policy

Telemetry cadence is separate from the Bridge fast loop and output write loop.

- The fast loop can continue at its configured target.
- The output write loop keeps its own cadence and safety gates.
- The stream should start with configurable 60 Hz telemetry when sustainable, with 30 Hz as a safe fallback and 120 Hz as a measured future target.
- The UI must keep HF-LRDC-1C frame dedupe and append graph samples only for accepted new source frames.
- The UI must report source cadence from accepted stream/JSON frames, not UI timer ticks.

## Security And Local-Only Boundary

HF-LRDC-3B should bind the stream only to `127.0.0.1` by default. It must not add cloud behavior, external network exposure, game injection, graphics API hooking, admin requirements, or UI-owned fast output writes.

If localhost WebSocket packaging or firewall behavior becomes a blocker, Windows named pipe can be implemented later behind the same schema with same-user access control expectations.

## Code, Docs, And Tests Changed

Added:

- `shared_core/runtime/telemetry_transport.py`
- `tests/test_hf_lrdc_3a_telemetry_transport_design.py`
- `docs/HelmForge/hf-lrdc-3a-low-latency-telemetry-transport-design.md`
- `docs/HelmForge/hf-lrdc-3a-low-latency-telemetry-transport-report.md`

Updated:

- `docs/HelmForge/bridge-service-design.md`
- `docs/HelmForge/bridge-ui-architecture.md`

The code seam is intentionally small: transport/source enums, a source candidate model, and source priority selection. It does not implement a server, client, socket, pipe, or shared memory transport.

## HF-LRDC-3B Test Strategy

The next implementation phase should cover:

- server startup without connected clients;
- client connect and receive full frames;
- sequence increment;
- producer identity across Bridge restart;
- reconnect backoff;
- malformed frame rejection;
- stale stream fallback to JSON;
- JSON fallback to simulation;
- frame dedupe preservation;
- runtime truth gates not weakened;
- no real HOTAS or vJoy required in CI.

## Deferred To HF-LRDC-3B

HF-LRDC-3A intentionally defers the actual transport implementation to HF-LRDC-3B:

- no WebSocket server/client;
- no named pipe server/client;
- no TCP stream;
- no shared memory ring buffer;
- no command stream migration.

## Runtime Truth Preservation

runtime truth preservation: a telemetry stream connection is not proof of vJoy writes, fresh telemetry is not proof of output verification, config match is not proof of vJoy output, physical input working does not prove vJoy writes, output intent is not output write proof, and transport health must not weaken readiness gates.

This phase adds no fake output verification, no fake Full Live Runtime Ready claim, no game injection, no graphics hooking, no cloud behavior, and no auto-save.
