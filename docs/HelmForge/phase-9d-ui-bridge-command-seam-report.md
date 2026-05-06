# Phase 9D - UI Bridge Command Seam

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Scope: safe UI-to-Bridge command JSON requests only

## Summary

Phase 9D adds a safe UI-side command writer for the separate simulation-only `bridge_app` process. The UI can request status/config/preflight-style actions by writing a command JSON file, while the Bridge remains the owner of runtime processing and telemetry.

This phase does not add real HOTAS polling, vJoy writes, output verification, driver installation, installer launch, Windows Service installation, login auto-start, or automatic Bridge launching from the UI.

## Command Path

Default command path:

```text
%TEMP%\helmforge_bridge_command.json
```

The UI and Bridge now share this convention:

- UI writer: `v3_app/services/bridge_commands.py`
- Bridge reader/parser: `bridge_app/ipc.py`

Command writes are atomic where practical. A command file write means only "command requested." It is not a completion response.

## Allowed UI Commands

Phase 9D allows these commands from the UI:

- `Status`
- `RunPreflight`
- `ReloadConfig`
- `SwitchToSimulation`
- `ClearError`

## Rejected UI Commands

Phase 9D rejects these unsafe or out-of-scope commands from the UI:

- `StartBridge`
- `StopBridge`
- `RestartBridge`
- `SuspendBridge`
- `VerifyOutput`

The rejection is deliberate. Start/stop/service lifecycle work, output verification, and real runtime activation remain later phases.

## UI Surface

The Live Monitor `Live State` card now contains compact Bridge command request controls:

- Refresh Bridge Status
- Run Bridge Preflight
- Reload Bridge Config
- Switch to Simulation
- Clear Bridge Error

The UI status text says "command requested" and "awaiting Bridge telemetry." It does not claim a command completed just because the file was written.

## Screenshot Fidelity Notes

Inspected:

- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/09 Live Monitor/v2-live-monitor_final-raw-input-trace-graph.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/09 Live Monitor/v2-live-monitor_final-raw-vs-final-overlay-graph-view.png`
- `HOTAS Control Panel Forensic Spec Set/Recovered PNG Evidence/09 Live Monitor/v2-live-monitor_final-axis-levels-hotas-buttons-output-buttons.png`

Matched:

- Kept Monitor Controls compact.
- Preserved the recovered graph-first Live Monitor structure.
- Placed command controls in the existing Live State card so the top control row does not become crowded.

Intentional deviation:

- The recovered V2 screenshots did not include Bridge command buttons. Phase 9D adds them as a compact operational seam, with explicit request/pending wording. This is intentional and scoped to Bridge status/config/preflight requests.

Remaining visual gaps:

- Button spacing is functional and compact, not pixel-tuned. A later polish pass can refine exact screenshot spacing if needed.

## Command Request Semantics

Current semantics:

1. UI writes a JSON request file.
2. Bridge reads it on a later tick if running and pointed at the same command path.
3. Bridge telemetry remains the truth source.
4. UI must wait for fresh telemetry before implying the Bridge reflected a request.

No request/response IPC or per-command acknowledgement exists yet.

## Current Runtime Truth

Phase 9D precheck state:

- Thrustmaster driver/software detected: yes.
- HOTAS device detected: no.
- vJoy detected: yes.
- Runtime mode: `simulated`.
- Runtime truth: `blocked_missing_device`.
- Full Live Runtime Ready: false.
- Output writes verified: false.

## Tests Added

Added `tests/test_phase9d_ui_bridge_command_seam.py` covering:

- safe command JSON writes;
- unsafe command rejection;
- write failure handling;
- Bridge parsing of UI-written safe commands;
- Bridge once mode consuming a UI command while keeping `output_verified` false;
- Live Monitor command request buttons;
- request wording that does not claim completion;
- Bridge/shared-core dependency boundaries.

## Commands Run During Phase

Prechecks:

```powershell
git status --short
git remote -v
python -m pytest
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
python -m bridge_app.main --once
python -m bridge_app.main --run-for-ms 250
python -m bridge_app.main --status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
```

Focused verification:

```powershell
python -m pytest tests\test_phase9d_ui_bridge_command_seam.py
python -m pytest tests\test_phase9b_bridge_process_skeleton.py tests\test_phase9c_ui_bridge_telemetry_connection.py tests\test_phase9_live_monitor_page.py tests\test_phase9d_ui_bridge_command_seam.py
```

Final verification:

```powershell
python -m pytest
$env:QT_QPA_PLATFORM='offscreen'; python -m v3_app.main --smoke-exit-ms 250
python -m bridge_app.main --once
python -m bridge_app.main --run-for-ms 250
python -m bridge_app.main --status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\runtime_setup_check.ps1 -DryRun
```

Results:

- `python -m pytest`: 147 passed.
- UI smoke launch: passed.
- Bridge `--once`: passed.
- Bridge `--run-for-ms 250`: passed.
- Bridge `--status`: `lifecycle=Simulated`, `truth=blocked_missing_device`, `output_verified=False`.
- Runtime setup dry-run: HOTAS Not Connected, vJoy Detected, no installers launched.
- Manual command-file round trip: UI wrote `RunPreflight`, Bridge parsed it, telemetry stayed `output_verified=False`.

## Deferred

- Automatic Bridge launch from UI.
- Windows Service installation.
- Login auto-start.
- Bridge tray manager.
- Request/response IPC or acknowledgements.
- Real HOTAS polling.
- Real vJoy writes.
- Output verification.
- Full Live Runtime Ready.
