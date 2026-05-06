# Phase 2A Local Driver Installation and Runtime Verification

Status: Phase 2A setup tooling and documentation implemented. Local installer launch is permitted only with explicit user/admin approval.

## Product Identity

- Product name: HelmForge
- Technical subtitle: HOTAS Control Panel V3
- V3 workspace/config name: `hotas_bridge_config_v3.json`
- Known physical HOTAS target: Thrustmaster T-Flight HOTAS One / Thrustmaster T.Flight Hotas One

The recovered documents may refer to HOTAS Control Panel V2 because they came from the lost app. Phase 2A keeps V2 references as recovery evidence only.

## Driver Roles

Thrustmaster driver/software is for physical HOTAS input. It lets Windows and the Thrustmaster Control Panel see and test the Thrustmaster T-Flight HOTAS One.

vJoy is for virtual joystick output. A later HelmForge runtime phase may write processed axis/button/hat output to vJoy or another verified output backend.

These are separate pieces of software. Installing the Thrustmaster package does not install vJoy, and installing vJoy does not install the Thrustmaster HOTAS driver/control panel.

## Simulation Mode

HelmForge remains usable in Simulation Mode without the Thrustmaster driver, without the physical HOTAS connected, and without vJoy installed. Missing driver/device/backend status is non-fatal and should be visible to the app/user.

Phase 2A does not implement real HOTAS polling and does not implement real vJoy writes. Do not treat device presence as proof of full live output. Full Live Runtime Ready is only valid when physical input and output writes are both verified in a later runtime phase.

## Official and Verified Sources

Use the official Thrustmaster support page for T.Flight Hotas One:

`https://support.thrustmaster.com/en/product/t-flight-hotas-one-en/`

On May 5, 2026, the official page listed `Drivers - Package 2025_TFHT_5 + Firmware` for Windows 10/11 and noted that the PC USB sliding switch on the base must be set to the PC position. Always re-check the official page before installing because driver packages can change.

For vJoy, use a verified current Windows-compatible release source only. The selected Phase 2A source is:

`https://github.com/BrunnerInnovation/vJoy/releases`

On May 5, 2026, the latest release API reported `v2.2.2.0` with asset `vJoySetup_v2.2.2.0_Win10_Win11.exe`, and the release notes stated the driver/installer are signed and work on Windows 10/11. Re-check compatibility before installing.

Do not use random driver mirrors, bundled archives, SEO download sites, or third-party driver pages.

## Installation Cautions

- Installation may require administrator permission or a UAC prompt.
- HelmForge tooling does not silently elevate.
- The Thrustmaster package may require unplug/replug or reboot.
- The official Thrustmaster instructions say not to connect the device before the installer prompts for it.
- For PC use, set the T.Flight Hotas One base switch to PC if applicable.
- The Thrustmaster package may uninstall an older package on the first run and require a second run to install the new package.
- vJoy installation may also require reboot before a virtual device/backend is visible.

## Local Checklist Script

Dry run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/runtime_setup_check.ps1 -DryRun
```

Open official/verified setup pages:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/runtime_setup_check.ps1 -OpenPages
```

Request installer launch with explicit paths:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/runtime_setup_check.ps1 -LaunchInstallers -ThrustmasterInstaller "C:\Path\2025_TFHT_5.exe" -VJoyInstaller "C:\Path\vJoySetup_v2.2.2.0_Win10_Win11.exe"
```

The script still requires the confirmation text `LAUNCH INSTALLERS` before launching the supplied paths. It does not download installers. It does not mark installation successful. Run the setup check again after installer completion, unplug/replug, or reboot.

## App Status Labels

The minimal app can show these Phase 2A setup/runtime labels:

- Thrustmaster Driver Unknown
- HOTAS Not Connected
- T-Flight HOTAS One Detected
- vJoy Missing
- vJoy Detected
- Simulation Mode Active
- Full Live Runtime Ready only when physical input and verified output writes are both true

On this Windows machine after the Thrustmaster installer ran, the device appeared with generic HID-friendly names but a Thrustmaster USB identifier:

- `HID-compliant game controller ... VID_044F&PID_B68D`
- `USB Input Device ... VID_044F&PID_B68D`

Phase 2A detection treats that USB signature as a likely T.Flight HOTAS One presence signal, while still keeping live runtime output unverified.

## Local Verification Results

Installer sources used after explicit user approval:

- Thrustmaster official package: `https://ts.thrustmaster.com/download/pub/webupdate/TFlightHotas/2025_TFHT_5.exe`
- vJoy verified release source: `https://github.com/BrunnerInnovation/vJoy/releases`
- vJoy release used: `v2.2.2.0`
- vJoy installer asset: `vJoySetup_v2.2.2.0_Win10_Win11.exe`

Downloaded installer hashes:

- `2025_TFHT_5.exe`: `AAFAED56EAA78725192D18C73900A5DA529091289B066DD9AB27E30AEDA8DBFA`
- `vJoySetup_v2.2.2.0_Win10_Win11.exe`: `EF569A3105CD301B89580F18F60C66B339E95296ACF2C0DFCAF4B4BBF8AB68FE`

Post-install Windows registry detection:

- `T.Flight Hotas drivers` version `5.TFHT.2025`, publisher `Thrustmaster`
- `vJoy Device Driver 2.2.2.0` version `2.2.2.0`

Post-install device detection:

- HOTAS detected by Thrustmaster USB signature `VID_044F&PID_B68D`
- vJoy detected as `vJoy Driver`, `vJoy Device`, and `C:\Program Files\vJoy\x64\vJoyInterface.dll`

Current runtime truth after install:

- Mode: `simulated`
- Truth: `detected_unverified`
- Input: `detected`
- Output: `vjoy_detected`
- Live output writes verified: `false`

This is the expected Phase 2A ceiling. Installation and detection are working, but HelmForge still does not perform real HOTAS polling or vJoy writes in this phase.

## Implementation Notes

Created:

- `shared_core/runtime/driver_setup.py`
- `scripts/runtime_setup_check.ps1`
- `tests/test_phase2a_driver_setup.py`
- `docs/HelmForge/phase-2a-local-driver-installation-and-runtime-verification.md`

Changed:

- `shared_core/runtime/setup_guidance.py`
- `v3_app/main.py`
- `README.md`

Intentionally deferred:

- Real HOTAS polling.
- Real vJoy writes.
- Driver download automation.
- Silent installation.
- Any claim that live runtime support is working before post-install verification proves it.
