# HF-LRDC-1B Physical Input Fidelity Report

## Current Backend Summary

Before HF-LRDC-1B, HelmForge had a Windows WinMM joystick backend using `joyGetNumDevs`, `joyGetDevCapsW`, and `joyGetPosEx`. That backend remains available as the Windows fallback path. It is read-only and does not prove vJoy writes.

## Fidelity Instrumentation Added

Physical input now has UI-independent fidelity models:

- `PhysicalInputAxisDiagnostics`
- `PhysicalInputFidelitySnapshot`
- `PhysicalInputBackendChoice`

Bridge telemetry now includes:

- `physical_input_fidelity`
- `physical_input_backend_choice`

The fidelity payload exposes backend identity, backend kind, device identity, sample timestamp, sequence, sample age, read duration, estimated sample rate when available, axis/button/hat counts, logical axis diagnostics, mapping status, warnings, and errors.

## WinMM Instrumentation

The WinMM backend now records `read_duration_ms` for the `joyGetPosEx` path and keeps raw axis values, normalized values, raw min/max/center, one-sided axis assumptions, buttons, hats, sample timestamp, and sequence in the shared snapshot/fidelity model.

Resolution hints are derived from the raw axis range. For example, a `0..65535` range reports `16-bit-ish`.

## Backend Selection Behavior

The Bridge now uses a physical input backend selection result when no backend is explicitly supplied.

Selection priority:

1. Guarded Windows Raw Input candidate, when a provider is available.
2. WinMM joystick backend on Windows.
3. Missing backend with simulation fallback.

If a backend is injected explicitly for tests or app embedding, Bridge records that explicit backend as the selected backend and does not invent fallback authority.

## Candidate Backend Implemented

HF-LRDC-1B adds `WindowsRawInputCandidateBackend` as a guarded higher-fidelity candidate seam.

What works now:

- It is constructible without crashing when unavailable.
- It reports clean unavailable status without a provider.
- It exposes capability metadata including `requires_message_loop=true`.
- It can enumerate/open/read through an injected provider in deterministic tests.
- It returns normal `PhysicalInputSnapshot` shape when provider data is available.

Blocker for full real Raw Input implementation now:

Real Windows Raw Input requires registering a window/message loop and parsing HID reports from `WM_INPUT`. Adding that correctly would cross into a larger runtime ownership and event-loop design pass. HF-LRDC-1B therefore lands the guarded candidate seam and deterministic provider path, while leaving full native Raw Input event-loop ownership for a later refinement.

## Telemetry Fields Added

`physical_input_fidelity` includes:

- `backend_name`
- `backend_kind`
- `device_id`
- `device_name`
- `sampled_at`
- `sequence`
- `sample_age_ms`
- `read_duration_ms`
- `estimated_sample_rate_hz`
- `axis_count`
- `button_count`
- `hat_count`
- `axes`
- `buttons`
- `hats`
- `mapping_status`
- `warnings`
- `errors`

`physical_input_backend_choice` includes:

- `selected_backend_name`
- `selected_backend_kind`
- `selection_reason`
- `fallback_used`
- `fallback_reason`
- `candidate_backends`
- `warnings`
- `errors`

The Bridge client passes both blocks through. The Live Monitor adds a compact truth-focused diagnostic line for backend, sample age, read duration, sample rate, mapping status, and fallback use.

## Known Limitations

- Full real Raw Input/HID/DirectInput sampling is not claimed complete in this phase.
- Real HOTAS sample-rate and axis-resolution proof still requires validation on Windows with the physical Thrustmaster T-Flight HOTAS One connected.
- `estimated_sample_rate_hz` is exposed but remains unavailable unless a backend supplies or later derives it from bounded read history.
- Live Monitor frame dedupe is intentionally not implemented here; it remains HF-LRDC-1C.

## Runtime Truth Preservation

Physical input fidelity does not mean Full Live Runtime Ready. Physical input working does not prove vJoy writes. vJoy detection is not output verification. Output intent is not output write proof. Simulation fallback remains available, and readiness gates remain unchanged.

HF-LRDC-1B added no fake output verification, fake Full Live Runtime Ready, game injection, graphics API hooking, cloud behavior, or auto-save.
