# HelmForge

HelmForge is a Windows desktop app for configuring, tuning, monitoring, and recording a HOTAS control setup.

The app is focused on the Thrustmaster T-Flight / T.Flight HOTAS One and a vJoy virtual output device. It provides a visual control panel for mapping physical controls, shaping axis response, inspecting live input/output behavior, and keeping runtime state visible without hiding hardware or driver problems.

## What The App Does

- Maps physical HOTAS axes, buttons, and hats to virtual output intent.
- Tunes axis response with base tuning, filtering, combat profile modifiers, modes, and conditional rules.
- Shows live raw and processed axis values in tuning pages and Live Monitor.
- Displays a live response stack so you can see how each stage changes the selected axis.
- Provides a detached Live Overlay for compact telemetry display.
- Includes Flight Recorder surfaces for telemetry-backed review/export workflows.
- Provides Help / Docs and Perf / Diagnostics pages inside the app.
- Uses a Bridge runtime path to sample physical HOTAS input and write verified output to vJoy.

## Runtime Model

HelmForge has two major parts:

- **UI app**: the PySide6 desktop interface used for editing, monitoring, diagnostics, and user interaction.
- **Bridge runtime**: the runtime path that samples the HOTAS, applies the workspace pipeline, publishes telemetry, and writes to vJoy when the real output path is verified.

When the app window opens, HelmForge starts an embedded Bridge runtime worker. The worker runs away from the UI thread so page switching, scrolling, and graph rendering remain responsive.

The UI reads Bridge telemetry and displays the current truth:

- HOTAS connected or missing.
- Runtime simulated, detected but unverified, or live verified.
- vJoy missing, detected, or output verified.
- Output loop running, disabled, or safety-stopped.
- Full live readiness state and any blocking reason.

## Hardware And Output Flow

The live path is:

```text
Thrustmaster HOTAS
  -> Windows joystick input
  -> HelmForge Bridge sampler
  -> workspace signal pipeline
  -> final virtual output intent
  -> guarded vJoy provider
  -> vJoy device
```

The Bridge keeps these states separate:

- Seeing a HOTAS is not the same as sampling it.
- Seeing vJoy is not the same as verifying output writes.
- A final output intent is not proof that vJoy accepted a write.
- Full live readiness requires physical input, pipeline success, verified real vJoy output, a running output loop, fresh telemetry, and no safety stop.

## Main Pages

- **Mapping**: routes physical HOTAS controls to virtual output intent.
- **Modes**: configures mode buttons and mode behavior.
- **Base Tuning**: shapes raw axis response.
- **Filtering**: smooths, slews, and stabilizes axis output.
- **Combat Profile**: applies combat-focused modifiers.
- **Profiles**: manages workspace/profile context.
- **Conditional Rules**: adds rule-driven changes to the signal path.
- **Effective Response Stack**: shows the selected axis through every processing stage.
- **Live Monitor**: shows live raw/final axes, buttons, hats, telemetry, and rolling graphs.
- **Flight Recorder**: reviews telemetry-backed recorder artifacts.
- **Help / Docs**: provides built-in app documentation.
- **Perf / Diagnostics**: shows runtime truth, telemetry health, and UI timing.

## Running From Source

Install dependencies:

```powershell
python -m pip install -e .
```

Launch the app:

```powershell
python -m v3_app.main
```

Run an offscreen smoke launch:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m v3_app.main --smoke-exit-ms 250
Remove-Item Env:\QT_QPA_PLATFORM
```

Check the Bridge directly:

```powershell
python -m bridge_app.main --status
```

Run tests:

```powershell
python -m pytest
```

## Packaging

The packaged app target is:

```text
packaging/dist/HelmForge/HelmForge.exe
```

Packaged smoke command:

```powershell
packaging/dist/HelmForge/HelmForge.exe --smoke-exit-ms 250
```

Installer metadata lives in:

```text
packaging/inno/helmforge.iss
```

## Important Files

```text
v3_app/                    Desktop UI.
bridge_app/                Bridge runtime entry point and service loop.
shared_core/               Runtime models, pipeline, rules, HOTAS input, and vJoy output.
docs/HelmForge/bridge.md   Bridge runtime and UI interaction guide.
packaging/                 Build and installer packaging assets.
tests/                     Regression and contract tests.
```

## Safety Notes

- The app keeps simulation fallback available when hardware or vJoy is missing.
- Hardware and output status are shown as explicit runtime truth, not generic success text.
- vJoy writes are guarded and verified before the runtime reports live output readiness.
- The Bridge attempts neutral restore behavior when stopping output after writes.
