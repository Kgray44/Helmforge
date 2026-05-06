# Phase 9E - Bridge Command Acknowledgement

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Scope: command acknowledgement/status refinement only

## Summary

Phase 9E refines the Phase 9D command-file seam so a UI command request can be matched to later Bridge telemetry by `request_id`.

The key rule remains: writing the command file means only "command requested." Bridge telemetry remains the only source of truth for acknowledgement, completion, failure, rejection, or ignored-stale status.

No real HOTAS polling, vJoy writes, output verification, automatic Bridge launch, service installation, login auto-start, installer launch, tray manager work, or real runtime activation was added.

## Command Request Shape

UI command writes now include:

- `schema_version`: `helmforge.bridge_command.v1`
- `request_id`
- `command`
- `created_at`
- `source`: `v3_app`

`v3_app/services/bridge_commands.py` supports injectable request ID and clock providers for deterministic tests.

## Bridge Acknowledgement Telemetry

Bridge telemetry now includes `last_command`.

When present, `last_command` includes:

- `schema_version`: `helmforge.bridge_command_status.v1`
- `request_id`
- `command`
- `status`
- `received_at`
- `completed_at`
- `updated_at`
- `message`
- `error`

Implemented statuses in Phase 9E:

- `completed`
- `failed`
- `ignored_stale`

The simulation-only Bridge completes safe skeleton commands during the same tick. There is no request/response IPC yet.

## Stale Command Protection

The Bridge ignores command requests older than 30 seconds based on `created_at`.

Ignored stale commands are not executed and are reported through telemetry as:

```text
last_command.status = ignored_stale
```

This prevents old command files discovered at Bridge startup from triggering actions.

## Duplicate Request Protection

The Bridge remembers consumed request IDs in memory for this phase.

If the same command file remains present across ticks, the Bridge does not execute the same `request_id` again. The most recent command status remains available in telemetry.

## Live Monitor Behavior

The Live Monitor command status label now distinguishes:

- command requested;
- awaiting Bridge telemetry;
- completed by Bridge;
- failed/rejected/ignored by Bridge.

The UI only treats telemetry as acknowledgement/completion when:

```text
telemetry.last_command.request_id == latest UI-written request_id
```

Unrelated or stale telemetry does not complete the current UI request.

## Runtime Truth During Implementation

Precheck state:

- Thrustmaster driver/software detected: yes.
- HOTAS device detected: no.
- vJoy detected: yes.
- Runtime truth: `blocked_missing_device`.
- Full Live Runtime Ready: false.
- Output writes verified: false.

## Tests Added

Added `tests/test_phase9e_bridge_command_acknowledgement.py` covering:

- command JSON includes schema/request ID/timestamp/source;
- unsafe command rejection remains intact;
- Bridge consumes a safe command and echoes `request_id`/status in telemetry;
- stale commands are ignored;
- duplicate request IDs are not re-executed every tick;
- UI waits for matching telemetry;
- UI ignores unrelated `last_command` telemetry;
- UI shows completion only for matching `request_id`;
- output remains unverified;
- Bridge/shared-core dependency boundaries remain UI-free.

## Verification Commands

Required final verification:

```powershell
python -m pytest
python -m pytest tests\test_phase9d_ui_bridge_command_seam.py
python -m pytest tests\test_phase9c_ui_bridge_telemetry_connection.py tests\test_phase9d_ui_bridge_command_seam.py
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
python -m bridge_app.main --once
python -m bridge_app.main --run-for-ms 250
python -m bridge_app.main --status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
git diff --check
```

Results:

- `python -m pytest`: 156 passed.
- `python -m pytest tests\test_phase9d_ui_bridge_command_seam.py`: 8 passed.
- `python -m pytest tests\test_phase9c_ui_bridge_telemetry_connection.py tests\test_phase9d_ui_bridge_command_seam.py`: 17 passed.
- UI smoke launch with `QT_QPA_PLATFORM=offscreen`: passed.
- `python -m bridge_app.main --once`: passed.
- `python -m bridge_app.main --run-for-ms 250`: passed.
- `python -m bridge_app.main --status`: `lifecycle=Simulated`, `truth=blocked_missing_device`, `output_verified=False`.
- Runtime setup dry-run: HOTAS Not Connected, vJoy Detected, no installers launched.
- `git diff --check`: passed.
- Manual command acknowledgement sample: UI wrote `RunPreflight` with `request_id=cmd-manual-9e`; Bridge telemetry reported `last_command.status=completed` and `output_verified=False`.

## Deferred

- Full command response/ack IPC.
- Automatic Bridge launch from UI.
- Windows Service installation.
- Login auto-start.
- Tray/background manager.
- Real HOTAS polling.
- Real vJoy writes.
- Output verification.
- Full Live Runtime Ready.
