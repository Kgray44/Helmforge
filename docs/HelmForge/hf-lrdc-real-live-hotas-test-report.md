# HF-LRDC Real Live HOTAS Test Report

Date/time: 2026-05-10, live test run from the Windows development machine.

Machine/environment:

- Machine: `LIMITNOTFOUND`
- OS: Microsoft Windows 11 Home, version 10.0.26200
- Repo: `C:\Users\kkids\Documents\HOTAS-Control-Panel`
- Test scope: live validation only; no new runtime behavior or unsafe output enablement added.

## Summary

The Thrustmaster T-Flight HOTAS One is present at the Windows PnP layer and Bridge telemetry reports active physical sampling through the WinMM fallback backend. vJoy is present and Bridge telemetry reports real guarded vJoy verification plus real output writes through the persistent output loop.

However, the HF-LRDC real bench harness still reports `blocked_real_bench_not_exercised` in real mode, and the live frame-history capture did not record axis/button/hat movement during the capture window. Therefore real-path acceptance remains blocked by bench/manual evidence, even though direct Bridge telemetry currently shows `full_live_runtime_ready=true`.

## Hardware Detection

PnP detection:

- HOTAS connected: yes.
- HOTAS device: `HID-compliant game controller`, `VID_044F&PID_B68D`.
- vJoy installed/detected: yes.
- vJoy devices: `vJoy Driver`, `vJoy Device`.

Bridge status:

- Command: `python -m bridge_app.main --status`
- Result: `lifecycle=LiveVerified truth=live_verified output_verified=True`
- Telemetry path: `C:\Users\kkids\AppData\Local\Temp\helmforge_bridge_telemetry.json`

Truth note: PnP presence is not output proof by itself. In this run, Bridge telemetry also reported real guarded vJoy verification and real write success.

## JSON Telemetry Run

Command:

```powershell
python -m bridge_app.main --run-for-ms 5000
```

Captured telemetry:

- `runtime_truth`: `live_verified`
- `input_status`: `detected`
- `output_status`: `output_verified`
- `output_verified`: `true`
- `runtime_frame.full_live_runtime_ready`: `true`
- `runtime_frame.fake_or_real_path`: `real`
- `runtime_frame.input_source`: `physical`
- `runtime_frame.output_verification_status`: `real_verified`
- `runtime_frame.last_output_write_status`: `real_write_succeeded`

Bridge timing:

- Target tick interval: 16 ms
- Last tick duration: about 12.397 ms
- Last input read duration: about 3.104 ms
- Last pipeline duration: about 2.09 ms
- Last output loop/write duration: about 0.683 ms
- Last telemetry publish duration: about 9.15 ms
- Slow lane status: `cached`

Physical input backend:

- Selected backend: `windows_winmm_joystick`
- Backend kind: `windows_winmm`
- Raw Input candidate: unavailable
- Fallback used: yes
- Device name: `Microsoft PC-joystick driver`
- Mapping status: `ok`
- Axis count: 6
- Button count: 15
- Hat count: 1
- Sample age: 0 ms in the captured frame
- Read duration: about 3.104 ms
- Estimated sample rate: unavailable in the final snapshot
- Axis resolution hint: `16-bit-ish`

Workspace/config:

- `bridge_workspace.config_status`: `missing_default`
- `using_default_workspace`: `true`
- Config path: `hotas_bridge_config_v3.json`
- Warning: workspace config missing, default workspace used.

This means the Bridge was not proving it was using a saved UI workspace config during this live run.

Output loop:

- Backend: `Real vJoy`
- Selected device: `vJoy Device 1`
- Verification status: `real_verified`
- Verification real: `true`
- Loop state: `running`
- Last write status: `real_write_succeeded`
- Write successes: 68 in the JSON run snapshot
- Write failures: 0
- Rate-limited skips: 16
- Safety stop reason: `None`
- Neutral restore status: `not_attempted`

One stale wording issue remains in `output_loop_runtime.warnings`: it includes `Full Live Runtime Ready remains false until Phase 16 end-to-end conditions are proven.` while the runtime frame in this live run reports `full_live_runtime_ready=true`. Treat that warning as stale wording to clean up in a follow-up, not as the authoritative readiness value.

## Telemetry Stream Run

Command:

```powershell
python -m bridge_app.main --run-for-ms 5000 --telemetry-stream --telemetry-host 127.0.0.1 --telemetry-port 8765 --telemetry-rate-hz 60
```

Stream status:

- Enabled: true
- Transport: `local_websocket`
- Host: `127.0.0.1`
- Port: `8765`
- Client count: 0
- Frames sent: 0
- Last send status: `no_clients`
- Errors: none

Result: stream server started successfully and did not block Bridge operation. No UI stream client was connected during this CLI run, so no stream frames were sent.

Source priority remains: Bridge Stream > Bridge JSON Snapshot > Simulation Fallback.

## Live Frame-History Capture

Second movement capture artifact:

`.artifacts/hf-lrdc/live-capture/real-live-hotas-movement-20260510T140847`

Files:

- `telemetry_frames.jsonl`
- `capture_summary.json`
- `latest_bridge_telemetry.json`
- `bridge_stdout.txt`
- `bridge_stderr.txt`

Second capture summary:

- Captured frames: 126
- Runtime truth values: `live_verified`
- Output verified values: `True`
- Buttons seen pressed: `B1`, `B2`
- Button transitions: `B1=10`, `B2=4`
- Hats seen: `Centered`

Axis observations from the second capture:

| Axis | Min | Max | Delta | Distinct Values |
| --- | ---: | ---: | ---: | ---: |
| Roll | -1.0 | 0.217670 | 1.217670 | 29 |
| Pitch | -1.0 | 0.290211 | 1.290211 | 56 |
| Throttle | 0.0 | 0.599207 | 0.599207 | 54 |
| Yaw | -0.000015 | -0.000015 | 0.0 | 1 |
| Aux 1 | -0.000015 | -0.000015 | 0.0 | 1 |
| Aux 2 | -0.000015 | 1.0 | 1.000015 | 2 |

Result: the second capture proves real physical movement telemetry for Roll, Pitch, Throttle, Aux 2, B1, and B2 through the current WinMM backend. Yaw, Aux 1, B15, and hat movement were not captured and remain unproven by these artifacts.

HAT-specific capture artifact:

`.artifacts/hf-lrdc/live-capture/real-live-hotas-hat-20260510T141012`

Files:

- `hat_frames.jsonl`
- `hat_capture_summary.json`
- `latest_bridge_telemetry.json`
- `bridge_stdout.txt`
- `bridge_stderr.txt`

HAT capture summary:

- Captured frames: 333
- Runtime truth values: `live_verified`
- Output verified values: `True`
- Top-level `HOTAS Hat` transitions: 125
- Top-level `Output Hat` transitions: 125
- Physical fidelity `Hat 1` transitions: 125
- Top-level HAT values seen: `Centered`, `North`, `East`, `South`, `West`, `North East`, `North West`, `South East`
- Physical fidelity HAT values seen: `Centered`, `North`, `East`, `South`, `West`, `North East`, `North West`, `South East`

Result: the HAT/POV is now proven active through both top-level Bridge telemetry and `physical_input_fidelity.hats`. The capture saw cardinal directions plus diagonals and centered state. `South West` was not observed in this specific capture.

First capture artifact:

Artifact directory:

`.artifacts/hf-lrdc/live-capture/real-live-hotas-20260510T140615`

Files:

- `telemetry_frames.jsonl`
- `capture_summary.json`
- `latest_bridge_telemetry.json`
- `bridge_stdout.txt`
- `bridge_stderr.txt`

Capture summary:

- Captured frames: 120
- Runtime truth values: `live_verified`
- Output verified values: `True`
- Buttons seen pressed: none
- Hats seen: `Centered`

Axis observations from the capture:

| Axis | Min | Max | Delta |
| --- | ---: | ---: | ---: |
| Roll | -0.000015 | -0.000015 | 0.0 |
| Pitch | -0.000015 | -0.000015 | 0.0 |
| Throttle | 0.499992 | 0.499992 | 0.0 |
| Yaw | -0.000015 | -0.000015 | 0.0 |
| Aux 1 | -0.000015 | -0.000015 | 0.0 |
| Aux 2 | -0.000015 | -0.000015 | 0.0 |

Result: the first live telemetry capture confirmed stable physical telemetry frames, but it did not capture operator movement. The second capture above supersedes it for movement evidence.

## Real Bench Harness

Command:

```powershell
python scripts/run_hf_lrdc_runtime_bench.py --mode real --duration-ms 5000 --require-hotas --require-vjoy --output .artifacts/hf-lrdc/runtime-bench/real-live-hotas
```

Artifact:

`.artifacts/hf-lrdc/runtime-bench/real-live-hotas/20260510T180512Z-real-axis_sweep_roll`

Result:

- Pass: false
- Runtime truth: `blocked_real_bench_not_exercised`
- Full Live Runtime Ready: false in the bench summary
- Real output verified: false in the bench summary
- Error: `required real hardware was not exercised`

Input-only rerun:

```powershell
python scripts/run_hf_lrdc_runtime_bench.py --mode real --duration-ms 5000 --require-hotas --output .artifacts/hf-lrdc/runtime-bench/real-live-hotas-input-only
```

Artifact:

`.artifacts/hf-lrdc/runtime-bench/real-live-hotas-input-only/20260510T180518Z-real-axis_sweep_roll`

Result: also false, with the same `blocked_real_bench_not_exercised` limitation.

Conclusion: the current real bench harness is still a placeholder for real hardware mode. It cannot yet provide the required bench evidence even though direct Bridge telemetry can see the physical HOTAS and vJoy path.

## Manual Validation

Manual validation UI was not completed/exported during this pass. No manual validation artifact exists under:

`.artifacts/hf-lrdc/manual-validation/real-live-hotas`

Real operator checklist evidence remains missing.

## Acceptance

Acceptance using the real bench artifact only:

```powershell
python scripts/run_hf_lrdc_acceptance.py --mode real --require-hotas --require-vjoy --bench-artifact .artifacts/hf-lrdc/runtime-bench/real-live-hotas/20260510T180512Z-real-axis_sweep_roll/summary.json --output .artifacts/hf-lrdc/acceptance/real-live-hotas
```

Artifact:

`.artifacts/hf-lrdc/acceptance/real-live-hotas/20260510T180532Z-real`

Result:

- Overall status: blocked
- Ready for RC: false
- Proof kind: real
- Blocked gate count: 8

Acceptance using live telemetry plus the real bench artifact:

```powershell
python scripts/run_hf_lrdc_acceptance.py --mode real --require-hotas --require-vjoy --telemetry-json C:\Users\kkids\AppData\Local\Temp\helmforge_bridge_telemetry.json --bench-artifact .artifacts/hf-lrdc/runtime-bench/real-live-hotas/20260510T180512Z-real-axis_sweep_roll/summary.json --output .artifacts/hf-lrdc/acceptance/real-live-hotas-with-telemetry
```

Artifact:

`.artifacts/hf-lrdc/acceptance/real-live-hotas-with-telemetry/20260510T180659Z-real`

Result:

- Overall status: blocked
- Ready for RC: false
- Proof kind: real
- Blocked gate count: 2
- Warning count: 3
- Top blocker: bench harness did not pass.

Conclusion: live telemetry improves acceptance evidence, but RC acceptance remains blocked because the real bench harness did not exercise hardware and no manual validation artifact was supplied.

## Final Live Result

HOTAS connected: yes.

vJoy installed/detected: yes.

vJoy verified by Bridge telemetry: yes, `real_verified`.

Physical input backend selected: `windows_winmm_joystick`.

Backend kind: `windows_winmm`.

Physical samples active: yes in Bridge telemetry.

Axis movement quality/resolution: partially proven. Roll, Pitch, Throttle, and Aux 2 changed in the second capture; Roll/Pitch/Throttle showed multiple distinct values through WinMM. Yaw and Aux 1 did not change.

Button/hat detection: B1 and B2 transitions were captured. HAT/POV movement was captured in a dedicated HAT run with 125 transitions. B15 was not captured.

Bridge telemetry source:

- JSON snapshot works.
- Telemetry stream server starts when enabled.
- No UI stream client was connected, so stream delivery to UI was not proven in this pass.

Config sync:

- Not proven. Bridge used missing/default workspace config.

Output-loop state:

- Running in direct Bridge telemetry.
- Real vJoy guarded verification true.
- Real write successes reported.
- No safety stop.
- Neutral restore not attempted.

Full Live Runtime Ready:

- Direct Bridge telemetry: true.
- Acceptance posture: still blocked because required real bench/manual proof is incomplete.

## Real-Path Blockers

1. The HF-LRDC real bench harness currently does not exercise real hardware and reports `blocked_real_bench_not_exercised`.
2. Operator movement proof is incomplete: Roll, Pitch, Throttle, Aux 2, B1, B2, and HAT were captured, but Yaw, Aux 1, and B15 remain unproven.
3. Manual validation checklist was not completed/exported.
4. Bridge used a missing/default workspace config, so UI/Bridge config sync was not proven.
5. Raw Input event-loop ownership remains incomplete; current live input path is WinMM fallback.
6. Stream server starts, but UI stream consumption was not proven because no client was connected.

## Next Fixes

1. Implement or repair real mode in `scripts/run_hf_lrdc_runtime_bench.py` so it drives the actual Bridge/physical backend instead of returning the placeholder real summary.
2. Rerun live capture specifically targeting Yaw, Aux 1, and B15, then confirm nonzero deltas/transitions.
3. Load or create the intended `hotas_bridge_config_v3.json` so `bridge_workspace.config_status` is `loaded` and UI/Bridge hashes can match.
4. Complete and export the HF-LRDC-4B manual validation checklist.
5. Connect Live Monitor to the telemetry stream and verify stream frames are consumed by the UI.
6. Continue Raw Input event-loop ownership work if WinMM latency/resolution remains visibly chunky under movement.

## Runtime Truth Preservation

This pass did not fake output verification, fake Full Live Runtime Ready, game injection, graphics hooking, cloud behavior, or auto-save.

Output intent is not output write proof. vJoy detected is not output verification. Manual operator confirmation does not override runtime proof gates. Fake-path proof remains fake-path only.
