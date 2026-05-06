# Runtime Setup: Thrustmaster T-Flight HOTAS One

HelmForge targets the **Thrustmaster T-Flight HOTAS One**, also written as **Thrustmaster T.Flight Hotas One**, as the primary physical HOTAS input device.

## Open Official Thrustmaster Support Page

Use the official Thrustmaster support site only:

https://support.thrustmaster.com/en/product/t-flight-hotas-one-en/

Do not install drivers from third-party driver sites, mirrors, bundled archives, or unofficial downloads.

## Driver Setup Guidance

1. Open the official Thrustmaster support site.
2. Select **Joysticks**.
3. Select **T.Flight Hotas One**.
4. Open **Drivers**.
5. Download and install the official Windows 10/11 driver package listed there.
6. The current package name may resemble `Drivers - Package 2025_TFHT_5 + Firmware`, but the official support page should be checked for the newest package before installing.
7. After installing, connect or reconnect the HOTAS by USB.
8. Open the Thrustmaster Control Panel if installed and verify that axes/buttons respond there.
9. Return to HelmForge and run Preflight Check.

## Thrustmaster Driver vs vJoy

Thrustmaster driver/software and vJoy are separate:

- Thrustmaster driver/software handles the physical HOTAS input and control panel.
- vJoy or a future virtual output backend creates the virtual joystick output that HelmForge may write to in a later phase.

Both may be needed for full live runtime. Installing one does not prove the other is installed or working.

## Phase 1A Boundaries

Phase 1A does not:

- silently install Thrustmaster drivers,
- silently install vJoy,
- download driver installers,
- bundle driver installers,
- write real vJoy output,
- claim live HOTAS input without Windows/device enumeration,
- claim vJoy output without detected and verified output writes.

If the HOTAS is missing, HelmForge should report `HOTAS Not Connected`. If vJoy is missing, HelmForge should report `vJoy Missing`. Simulation mode remains available.

