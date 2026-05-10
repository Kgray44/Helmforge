# HF-LRDC-3A Low-Latency Telemetry Transport Design

Unique repair track: HF-LRDC, HelmForge Live Runtime Data Chain.

Status: design complete for HF-LRDC-3A. Do not implement the actual WebSocket server/client in HF-LRDC-3A. Actual stream implementation is intentionally HF-LRDC-3B.

## Problem Summary

The current Bridge-to-UI live telemetry path is the local JSON snapshot file at `%TEMP%/helmforge_bridge_telemetry.json`. That file is valuable because it is simple, crash-resistant, human-debuggable, and useful when a Bridge process exits. It is not the right primary live bus for high-rate HOTAS monitoring because the UI must poll it, file updates can jitter, repeated file reads can re-read the same Bridge frame, and file I/O should not define the perceived cadence of physical input or output-loop state.

HF-LRDC-1A through HF-LRDC-2B made the data itself more truthful: Bridge timing, physical input fidelity, frame dedupe, workspace identity, persistent output-loop ownership, and output write cadence/safety telemetry now exist. HF-LRDC-3A defines how those truthful frames should move to the UI with lower latency while preserving JSON fallback and all runtime gates.

## Transport Comparison

| Option | Latency | jitter | implementation complexity | packaging impact | dependency impact | Windows compatibility | cross-platform potential | local-only safety | firewall / network surface | multiple UI client support | Bridge restart handling | UI reconnect behavior | schema evolution | testability | human-debuggability | failure modes | 30 Hz / 60 Hz / 120 Hz suitability | command/control suitability | large history or latest frames |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| JSON snapshot file | Medium to high because the UI polls and waits for filesystem visibility | Medium to high under filesystem and antivirus pressure | Low, already implemented | Very low | None | Excellent | Excellent | Local path only | None | Many readers can read, but all poll the same file | Good because last snapshot remains after crash | Polling resumes automatically | Easy because JSON object is self-describing | Excellent with temp files and fake payloads | Excellent | stale file, invalid JSON, partial writes if atomicity fails, repeated reads | Fine for 30 Hz diagnostics, weak at 60 Hz live, poor at 120 Hz | Poor for commands beyond the existing safe command file | Latest snapshot only; should not carry large history |
| localhost WebSocket | Low because frames are pushed | Low when bound locally and frame size is compact | Medium | Medium because packaged app needs a small async or threaded server | Can use stdlib plus a small dependency later, or Qt client support if selected | Good | Good | Bind to 127.0.0.1 only | Possible firewall prompt depending implementation and packaging | Natural fan-out to multiple UI clients | Good if server restarts and clients reconnect | Natural reconnect with backoff | Good with versioned JSON frames | Good with fake in-process server in HF-LRDC-3B tests | Good enough when JSON fallback remains | server unavailable, port conflict, malformed frame, stale stream, client disconnect | Good for 30 Hz and 60 Hz, acceptable for 120 Hz with compact frames | Acceptable later, but 3B should keep commands separate | Full latest frame per publish; no large history in stream |
| localhost TCP socket | Low | Low | Medium to high because framing, reconnect, and fan-out must be hand-built | Medium | None if stdlib sockets are used | Good | Good | Bind to 127.0.0.1 only | Possible firewall prompt | Requires extra server logic for many clients | Good with explicit reconnect | Must implement backoff and framing recovery | Good if framed JSON is versioned | Good but framing tests are more custom | Moderate because raw stream is less friendly | port conflict, half-open socket, frame boundary corruption, stale stream | Good for 30 Hz, 60 Hz, 120 Hz if framed well | Possible later, but separate command channel remains safer | Full latest frame per publish; no large history |
| Windows named pipe | Very low | Low | Medium to high, especially robust async and multi-client behavior | Medium | Windows APIs or pywin32/ctypes | Excellent on Windows | Poor without an alternate transport | Strong same-machine boundary, can use ACLs | No firewall prompt, no TCP port | Possible but more complex | Good if pipe server recreates after Bridge restart | Client reconnect must handle pipe disappearance | Good with versioned JSON frames | Good with fake pipe wrapper, harder in CI off Windows | Moderate, not as visible as JSON | pipe unavailable, broken pipe, ACL mistakes, Windows-only test gaps | Excellent for 30 Hz, 60 Hz, 120 Hz | Good for local command/control later with ACL care | Full latest frame per publish; no large history |
| memory-mapped file / shared memory ring buffer | Very low | Very low when implemented carefully | High because ring indices, locks, stale detection, and schema ownership must be precise | High | Usually none, but platform code is substantial | Good with Windows APIs | Medium with separate implementations | Local-only if scoped correctly | None | Multiple readers possible with careful ring design | Complex because readers must detect new producer identity | Reattach logic is explicit and fragile | Harder because binary or structured memory needs versioning | Harder; fake clocks help but race tests are tricky | Poor unless mirrored to JSON | corrupt ring state, stale producer, reader overrun, lock contention | Excellent for 60 Hz and 120 Hz | Poor for commands; should remain read-only | Latest frame plus bounded ring only; never unbounded history |
| hybrid stream primary + JSON diagnostic fallback | Low live latency with stream, durable snapshot fallback | Low for stream, JSON jitter isolated to fallback/diagnostics | Medium because two paths remain | Medium | Depends on selected stream | Good | Good if stream choice is cross-platform | Local-only stream plus local JSON file | Same as selected stream | Same as selected stream | Best because JSON remains after crash and stream reconnects | Best because UI can step down to JSON then simulation | Best because full frames can be shared across both | Excellent if common parser validates both paths | Excellent because JSON remains inspectable | stream unavailable, JSON stale, both invalid, simulation fallback | Best overall for 30 Hz and 60 Hz; 120 Hz possible later with compact stream | Keep command/control separate initially | Stream carries latest full frames; JSON carries latest diagnostic snapshot |

## Recommendation

Recommended path for HF-LRDC-3B: localhost WebSocket stream primary, JSON snapshot remains the diagnostic and fallback snapshot, and the existing command file remains separate for the first stream implementation.

Why localhost WebSocket:

- It is specific enough to implement next without inventing a custom framing protocol.
- It supports multiple UI observers naturally, which helps Live Monitor, Perf / Diagnostics, overlay, and future recorder surfaces.
- It works on Windows and keeps a cross-platform path open.
- It can carry versioned JSON frames matching the current telemetry shape.
- It is easy to test with fake Bridge frames and a client reconnect loop.
- It preserves a human-debuggable JSON snapshot without forcing high-rate UI polling.

Why not Windows named pipe first:

- Named pipes are attractive for Windows-only local IPC and avoid firewall prompts, but they increase platform-specific complexity now.
- HelmForge already has a PySide6 UI and Python Bridge path where a localhost WebSocket can be tested and packaged with less OS-specific code.
- A named-pipe adapter can remain a later transport implementation behind the same schema if firewall or endpoint policy makes it preferable.

Why not raw TCP first:

- Raw TCP is viable, but WebSocket gives message framing and a well-known client model. Avoiding custom stream framing lowers the risk of malformed frame and reconnect bugs.

Why not shared memory first:

- Shared memory is the lowest-latency option, but it is too much complexity for the next step. It should be reserved for a later optimization if 60 Hz or 120 Hz JSON-frame streaming proves insufficient.

What this replaces:

- The UI should prefer the stream over polling `%TEMP%/helmforge_bridge_telemetry.json` as the live source.

What this does not replace yet:

- The JSON snapshot file remains diagnostic/fallback.
- The command file remains the safe command path in HF-LRDC-3B unless a later phase designs a command stream.
- The stream does not own vJoy writes, runtime authority, mapping changes, or output verification.

## Stream Responsibilities

The future stream should:

- publish Bridge telemetry frames to the UI with lower latency than file polling;
- preserve runtime frame identity, including `runtime_frame.sequence`, `runtime_frame.frame_id`, `runtime_frame.generated_at`, telemetry `timestamp`, and `bridge_timing.tick_count`;
- include a transport sequence that increments for every streamed frame;
- include Bridge process identity and Bridge start time so UI reconnect can distinguish restarts;
- allow no-client operation without blocking the Bridge fast loop;
- allow UI reconnect with backoff;
- preserve JSON snapshot fallback;
- keep older `BridgeTelemetryClient` JSON behavior possible during migration;
- keep frame dedupe from HF-LRDC-1C active on stream frames.

The stream should not:

- bypass runtime truth gates;
- perform vJoy writes;
- let the UI become part of the fast output path;
- expose network surface beyond the local machine;
- require admin;
- silently claim output verification;
- carry giant unbounded histories.

The UI is not in the fast output path. The Bridge owns physical input sampling, workspace pipeline processing, output intent generation, output-loop ownership, and vJoy write attempts. The UI observes telemetry and sends safe commands through the existing command boundary.

## Message Schema

Schema name: `helmforge.telemetry_frame.v1`.

Initial stream frames should be full telemetry frames, not deltas. Full frames simplify reconnect, testing, compatibility, and human reasoning. Delta frames can be considered later only after full-frame latency is measured.

Example top-level frame:

```json
{
  "schema_version": "helmforge.telemetry_frame.v1",
  "payload_version": "helmforge.bridge_telemetry.v1",
  "transport": {
    "transport_name": "local_websocket",
    "connection_id": "ui-client-optional-id",
    "server_started_at": "2026-05-10T12:00:00+00:00",
    "sequence": 123,
    "generated_at": "2026-05-10T12:00:01.234000+00:00",
    "sent_at": "2026-05-10T12:00:01.235000+00:00",
    "heartbeat": false
  },
  "bridge": {
    "bridge_pid": 1234,
    "bridge_started_at": "2026-05-10T11:59:58+00:00",
    "lifecycle_state": "LiveUnverified",
    "runtime_truth": "blocked_unverified_output"
  },
  "payload": {
    "timestamp": "2026-05-10T12:00:01.234000+00:00",
    "runtime_frame": {},
    "bridge_timing": {},
    "physical_input_fidelity": {},
    "physical_input_backend_choice": {},
    "bridge_workspace": {},
    "output_loop_runtime": {}
  },
  "warnings": [],
  "errors": []
}
```

Required stream envelope fields:

- `schema_version`;
- `payload_version`;
- `transport.transport_name`;
- `transport.server_started_at`;
- `transport.sequence`;
- `transport.generated_at`;
- `transport.sent_at` when the stream layer can provide it;
- `transport.heartbeat`;
- `bridge.bridge_pid`;
- `bridge.bridge_started_at`;
- `bridge.lifecycle_state`;
- `bridge.runtime_truth`;
- `payload`;
- optional `warnings` and `errors`.

Payload blocks to preserve:

- legacy required telemetry fields: `timestamp`, `lifecycle_state`, `runtime_truth`, `input_status`, `output_status`, `output_verified`, `active_profile`, `raw_axes`, `final_axes`, `buttons`, `hats`, `active_modes`, `rule_summary`;
- `runtime_frame`;
- `bridge_timing`;
- `physical_input_fidelity`;
- `physical_input_backend_choice`;
- `bridge_workspace`;
- `output_loop_runtime`;
- `last_command`;
- `device_discovery`;
- `warnings`;
- `errors`.

Heartbeat frames:

- Heartbeat frames may use the same envelope with `heartbeat: true` and either the last known payload or a compact status payload.
- A heartbeat is transport health only. A telemetry stream connection is not proof of vJoy writes. Fresh telemetry is not proof of output verification.

## Connection Lifecycle

Bridge side:

1. Bridge starts its telemetry publisher during startup after core options and config identity are known.
2. The publisher binds only to `127.0.0.1` by default.
3. The Bridge continues normally if no UI clients are connected.
4. After each accepted telemetry publish event, the Bridge sends a full `helmforge.telemetry_frame.v1` frame to connected clients.
5. The Bridge keeps writing the JSON diagnostic snapshot. Initial HF-LRDC-3B may write JSON every frame for compatibility; later phases may reduce JSON cadence if measured file cost matters.
6. Client connect/disconnect must not block the fast loop.
7. Shutdown sends a final stopping/stopped frame when the existing architecture can do so safely, then closes the publisher.

UI side:

1. UI attempts stream connection first when stream telemetry is enabled.
2. UI falls back to fresh JSON snapshot if stream is unavailable, reconnecting, stale, or invalid.
3. UI falls back to simulation if both Bridge sources are missing, stale, or invalid.
4. UI reconnects with bounded backoff.
5. UI displays source truth:
   - Bridge Stream
   - Bridge Stream Reconnecting
   - Bridge JSON Snapshot
   - Simulation Fallback
   - Bridge Missing
   - Bridge Stale
   - Bridge Invalid
6. UI keeps HF-LRDC-1C frame dedupe. The UI never treats a UI timer tick as a new Bridge frame.

Bridge restart handling:

- The frame envelope includes `bridge_pid`, `bridge_started_at`, `transport.server_started_at`, and `transport.sequence`.
- If those identities change, the UI treats it as a new producer and resets stream connection state without clearing runtime truth incorrectly.
- JSON fallback remains available during reconnect if fresh.

## Source Priority And Fallback

Source priority:

1. Fresh valid Bridge stream frame.
2. Fresh valid Bridge JSON snapshot.
3. Simulation fallback.

Rules:

- A stream frame wins only if it is valid and fresh.
- A JSON snapshot wins only if stream is unavailable, reconnecting, stale, or invalid and JSON is fresh.
- Simulation fallback activates if neither Bridge source is usable.
- Source changes must be visible in the Live Monitor.
- Source changes must not reset output verification or readiness proof.
- Stale stream frames must not be shown as live.
- Repeated stream frames must not be appended as new history samples.

The source-priority helper in `shared_core/runtime/telemetry_transport.py` defines this order without implementing a server or client.

## Cadence Policy

Output/control loop cadence and telemetry publish cadence are separate.

- The Bridge fast loop continues at its configured target.
- The output write loop continues to enforce its own output write cadence and safety policy.
- The telemetry stream should publish at a configurable rate, initially 60 Hz if the Bridge can sustain it, with 30 Hz as a safe fallback and 120 Hz as a measured future target.
- The UI graph renders accepted source frames only; it never reports UI timer cadence as Bridge cadence.
- Telemetry frames include `bridge_timing.tick_count`, transport `sequence`, runtime frame identity, `bridge_timing.last_tick_duration_ms`, physical input sample timing, and output-loop timing/cadence fields.
- The stream should carry latest full frames, not large history buffers.

## Security And Local-Only Boundary

The recommended WebSocket path is local-only:

- bind only to `127.0.0.1` by default;
- no cloud;
- no external network exposure;
- no game injection;
- no graphics hooks;
- no admin requirement;
- no unauthenticated remote access;
- no UI fast-path output writes.

Firewall considerations:

- Localhost TCP/WebSocket may still trigger security-product or firewall prompts in some packaging contexts.
- HF-LRDC-3B should document the exact bind address and port behavior.
- A future same-user token or random local session token may be added if needed, but this phase does not implement auth.

Named-pipe consideration:

- If localhost firewall prompts or endpoint policy become a blocking packaging issue, a Windows named-pipe implementation can be added behind the same `helmforge.telemetry_frame.v1` schema. Named-pipe ACLs should be same-user scoped.

## HF-LRDC-3B Test Strategy

HF-LRDC-3B should test:

- telemetry server starts without requiring UI clients;
- UI client connects to localhost stream;
- client receives full frames;
- stream sequence increments;
- runtime frame identity is preserved;
- Bridge restart changes producer identity and reconnect works;
- client reconnect backoff works;
- malformed frames are rejected safely;
- stale stream falls back to JSON;
- missing stream falls back to JSON;
- stale/missing/invalid JSON falls back to simulation;
- frame dedupe still prevents duplicate history appends;
- no runtime truth gates are weakened;
- stream connection does not prove vJoy writes;
- fresh stream telemetry does not prove output verification;
- no real HOTAS or vJoy is required in CI.

## Deferred

HF-LRDC-3A intentionally does not implement:

- WebSocket server or client;
- named pipe server or client;
- TCP stream;
- shared memory ring buffer;
- command stream;
- physical input backend changes;
- vJoy output behavior changes;
- mapping/tuning behavior changes;
- UI redesign;
- auto-save;
- game injection;
- graphics API hooking;
- cloud behavior;
- fake output verification;
- fake Full Live Runtime Ready claims.
