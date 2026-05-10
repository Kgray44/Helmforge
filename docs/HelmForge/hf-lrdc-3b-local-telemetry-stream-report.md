# HF-LRDC-3B Local Telemetry Stream Report

Unique repair track: HF-LRDC, HelmForge Live Runtime Data Chain.

## Selected Transport Implemented

HF-LRDC-3B implements the HF-LRDC-3A recommendation: a localhost WebSocket telemetry stream bound to `127.0.0.1`.

The implementation is intentionally local-only and standard-library based. It does not add a remote control surface, cloud behavior, game injection, graphics hooks, admin requirements, or UI participation in the fast output path.

## Enable / Disable

Bridge CLI options:

- `--telemetry-stream` enables the local WebSocket telemetry stream.
- `--no-telemetry-stream` disables it.
- `--telemetry-host 127.0.0.1` selects the bind host. HF-LRDC-3B accepts only localhost.
- `--telemetry-port 8765` selects the bind port. Use `0` for an ephemeral local port in tests.
- `--telemetry-rate-hz 60` sets the maximum stream publish cadence.

The stream defaults to disabled for compatibility and packaging caution. JSON telemetry remains available either way.

Example:

```powershell
python -m bridge_app.main --run --telemetry-stream --telemetry-host 127.0.0.1 --telemetry-port 8765 --telemetry-rate-hz 60
```

## Stream Frame Schema

The stream sends full JSON frames using `helmforge.telemetry_frame.v1`.

Each frame includes:

- `schema_version`;
- `payload_version`;
- `transport.transport_name`;
- `transport.server_started_at`;
- `transport.sequence`;
- `transport.generated_at`;
- `transport.sent_at`;
- `transport.heartbeat`;
- `bridge.bridge_pid`;
- `bridge.bridge_started_at`;
- `bridge.lifecycle_state`;
- `bridge.runtime_truth`;
- `payload`, containing the existing Bridge telemetry payload;
- optional warnings and errors.

The payload preserves the legacy required fields plus `runtime_frame`, `bridge_timing`, `physical_input_fidelity`, `physical_input_backend_choice`, `bridge_workspace`, `output_loop_runtime`, `last_command`, `device_discovery`, warnings, and errors.

## Bridge Publisher Behavior

Added `bridge_app/telemetry_stream.py`.

The Bridge-side publisher:

- starts only when enabled;
- binds to `127.0.0.1`;
- accepts WebSocket clients in a background thread;
- tolerates no clients connected;
- sends full frames to connected clients;
- enforces a configured maximum publish cadence;
- tracks client count, frames sent, send errors, last send status, and last send time;
- exposes `telemetry_stream` status in JSON telemetry;
- shuts down cleanly through `BridgeService.shutdown()`.

The JSON snapshot write path remains intact and is still written as the diagnostic/fallback snapshot.

## UI Client Behavior

Added `v3_app/services/bridge_stream_client.py`.

The UI-side stream client:

- connects only to `127.0.0.1`;
- parses WebSocket text frames;
- validates `helmforge.telemetry_frame.v1`;
- parses the embedded payload through the existing Bridge telemetry parser;
- rejects malformed frames safely;
- reports reconnecting, invalid, stale, or connected states without crashing;
- exposes latest valid telemetry for source selection.

Live Monitor gained an optional stream client path. It is disabled by default for compatibility, but when enabled its source priority is stream, JSON, simulation.

## Source Priority And Fallback

Source priority:

1. Fresh valid Bridge Stream.
2. Fresh valid Bridge JSON Snapshot.
3. Simulation Fallback.

Rules preserved:

- Stream connected is not vJoy proof.
- Fresh stream telemetry is not output verification proof.
- JSON remains diagnostic/fallback.
- Simulation fallback remains available.
- HF-LRDC-1C frame dedupe still applies to whichever Bridge source is selected.
- Repeated frames are not appended as fake new history.

## Local-Only / Security Boundary

The stream binds only to `127.0.0.1` in this phase. Non-local bind hosts are rejected. This phase adds no cloud transport, no external network exposure, no unauthenticated remote control, no admin requirement, no game injection, and no graphics API hooking.

Localhost WebSocket may still be visible to firewall or endpoint tools in packaged environments. Windows packaging validation remains required before making the stream default-on for end users.

## Tests Added

Added `tests/test_hf_lrdc_3b_local_telemetry_stream.py`.

Coverage includes:

- stream frame schema;
- publisher start/stop;
- no-client publish safety;
- localhost WebSocket client receive path;
- malformed frame rejection;
- stream > JSON > simulation source priority;
- Bridge service stream status telemetry while preserving JSON;
- CLI stream options.

## Known Limitations

- The stream defaults off for compatibility and packaging caution.
- The UI stream path is optional and not yet globally enabled by the application shell.
- The server uses a small standard-library WebSocket implementation scoped to Bridge telemetry frames, not a general WebSocket framework.
- Authentication/token hardening is deferred.
- Packaged Windows firewall and endpoint-policy validation is still needed.
- The command file remains the command path; command streaming is not implemented.

## Deferred

Later phases may:

- decide when to enable the stream by default;
- add a same-user token or session token;
- add richer reconnect telemetry in UI-wide diagnostics;
- move command/control to a designed local channel;
- add named-pipe transport if packaging/firewall policy requires it;
- optimize to shared memory only if measured stream latency is insufficient.

## Runtime Truth Preservation

A stream connection is not proof of vJoy writes. Fresh stream telemetry is not proof of output verification. Config match is not proof of vJoy output. Physical input working does not prove vJoy writes. Output intent is not output write proof. Transport health does not weaken the Full Live Runtime Ready gate.

This phase adds no fake output verification, no fake Full Live Runtime Ready claim, no game injection, no graphics hooking, no cloud behavior, and no auto-save.
