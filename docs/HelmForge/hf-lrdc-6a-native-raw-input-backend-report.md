# HF-LRDC-6A Native Raw Input Backend Report

## Problem Summary

HF-LRDC-1B left Windows Raw Input as a guarded candidate seam because real Raw Input needs native window registration and WM_INPUT message ownership. HF-LRDC-6A adds that ownership boundary while preserving the existing WinMM fallback and all runtime truth gates.

## Raw Input Architecture

The new `WindowsRawInputBackend` is a physical input backend with backend kind `windows_raw_input`. It wraps a `WindowsRawInputProvider` that owns the Windows-only boundary:

- enumerates Raw Input HID devices with `GetRawInputDeviceList`;
- queries device names with `GetRawInputDeviceInfoW`;
- matches the Thrustmaster T-Flight HOTAS One by VID/PID `044F:B68D` and supported names;
- starts a dedicated daemon thread for a hidden native window;
- registers joystick/gamepad usage pages with `RegisterRawInputDevices`;
- receives `WM_INPUT` in the hidden window procedure;
- reads HID payloads with `GetRawInputData`;
- stores the latest report in a thread-safe cache;
- exposes snapshots through the existing `PhysicalInputBackend.read_current_state()` contract.

The Bridge fast loop does not own the Windows message pump and does not block on WM_INPUT delivery.

## Device Identity Strategy

Raw Input device records include:

- `device_id`;
- display name;
- vendor ID;
- product ID;
- native handle;
- report size when known.

The supported HOTAS is recognized by VID/PID `044F:B68D`; matching records are converted to `PhysicalInputDeviceInfo` with six expected axes, fifteen buttons, and one hat/POV.

## Report Decoding Status

HF-LRDC-6A adds a bounded decoder for the supported HOTAS report shape:

- six unsigned 16-bit axis channels mapped to Roll, Pitch, Throttle, Yaw, Aux 1, and Aux 2;
- a 15-bit button mask mapped to B1-B15;
- one hat byte mapped to centered/cardinal/diagonal directions.

Unknown or short reports are not padded into fake logical channels. Missing axes/buttons/hats are reported through fidelity warnings and `mapping_status=missing_expected_channels`.

Real HID report layouts can vary by firmware/driver path, so `scripts/run_raw_input_probe.py` captures bounded evidence for report-size and channel behavior without writing vJoy.

## Backend Selection And Fallback

Backend priority is now:

1. `windows_raw_input` when available and sampling-active;
2. guarded `windows_raw_input_candidate` test seam;
3. `windows_winmm_joystick`;
4. missing backend / simulation fallback.

The Bridge starts with the highest-priority backend. If Raw Input starts but does not produce an initial `WM_INPUT` sample, the Bridge falls back to WinMM for continuous state reads and records:

- `fallback_used=true`;
- `fallback_reason=windows_raw_input produced no sample after message-loop start`;
- candidate backend list including Raw Input and WinMM.

This keeps the Live Monitor usable with the known WinMM path while making Raw Input ownership and probe diagnostics available.

## Telemetry

Existing `physical_input_fidelity` telemetry is reused. For Raw Input it reports:

- `backend_name=windows_raw_input`;
- `backend_kind=windows_raw_input`;
- device identity;
- sequence;
- sample age;
- read duration;
- estimated sample rate when enough events exist;
- raw and normalized axes;
- buttons;
- hats;
- mapping status;
- warnings/errors.

`physical_input_backend_choice` reports selected backend, candidate backends, fallback state, and fallback reason.

## Probe

Run:

```powershell
python scripts/run_raw_input_probe.py --duration-ms 10000 --output .artifacts/hf-lrdc/raw-input-probe/live
```

The probe writes:

- `summary.json`;
- `summary.md`;
- `frames.jsonl`.

The probe is physical-input-only. It does not write vJoy, verify vJoy output, or prove Full Live Runtime Ready.

## Tests Added

`tests/test_hf_lrdc_6a_native_raw_input_backend.py` covers:

- missing provider safety;
- VID/PID device mapping;
- fake Raw Input report decoding;
- selector preference/fallback;
- Bridge telemetry identity;
- missing logical channels reported instead of faked.

## Limitations

- Raw Input ownership and message-loop registration are implemented, but real HOTAS report decoding still needs live probe evidence across the actual Windows driver path.
- On the current live smoke run, Raw Input enumerated the HOTAS at `raw:\\?\HID#VID_044F&PID_B68D...`, started the message loop, and wrote artifacts under `.artifacts/hf-lrdc/raw-input-probe/live`, but captured `0` active samples over 10 seconds. The Bridge therefore fell back to WinMM for continuous-state reads.
- Full native Raw Input event fidelity should be validated with physical axis/button/hat movement using the probe.
- Raw Input physical input does not prove vJoy output writes.

## Runtime Truth Preservation

HF-LRDC-6A does not change vJoy output behavior, mapping/tuning behavior, telemetry transport, or readiness gates. Raw Input working does not prove output writes, vJoy verification, or Full Live Runtime Ready. WinMM and simulation fallback remain available. No fake output verification, fake Full Live Runtime Ready, game injection, graphics hooking, cloud behavior, or auto-save was added.
