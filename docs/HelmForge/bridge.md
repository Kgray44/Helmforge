# HelmForge Bridge

The Bridge is the runtime side of HelmForge. It connects physical HOTAS input to the configured signal pipeline, publishes telemetry for the UI, and writes verified final output to vJoy.

The UI is the control room. The Bridge is the runtime engine.

## Responsibilities

### Bridge

The Bridge owns work that must stay close to hardware and output timing:

- Detect the supported HOTAS.
- Sample physical axes, buttons, and hats.
- Load the active HelmForge workspace.
- Apply mapping, tuning, filtering, modes, and conditional rules.
- Build final virtual output intent.
- Verify and write output through the real vJoy provider.
- Publish telemetry that describes what actually happened.
- Stop or safe-idle the output path when input or output proof is lost.

### UI

The UI owns human interaction:

- Edit mappings and tuning values.
- Save workspace configuration.
- Display live graphs, tuning dots, diagnostics, and runtime truth.
- Show Bridge telemetry in the Mapping, Live Monitor, Effective Response Stack, Help / Docs, and Perf / Diagnostics surfaces.
- Keep simulation fallback visible when the Bridge cannot prove live hardware/output.

The UI should not fake live success. It displays the Bridge state it receives.

## How The Bridge Starts

There are two supported startup paths.

### App Startup

When `python -m v3_app.main` opens the app window, HelmForge creates an embedded Bridge runtime worker.

Important behavior:

- The Bridge worker starts when the window is shown.
- It runs on a worker thread, not the Qt UI thread.
- It ticks at the live refresh cadence.
- It publishes telemetry for the UI to consume.
- It stops when the app window closes.

This keeps the app responsive while the Bridge performs physical sampling and vJoy output work.

### Command Line

The Bridge can also be run directly:

```powershell
python -m bridge_app.main --status
```

Useful forms:

```powershell
python -m bridge_app.main --once
python -m bridge_app.main --run-for-ms 250
python -m bridge_app.main --status
```

The command-line Bridge writes the same telemetry shape used by the UI.

## How The Bridge Stops

When the embedded Bridge belongs to the app window:

1. The user closes the app.
2. The app stops the embedded Bridge worker.
3. The output loop stops.
4. The vJoy output path attempts to restore neutral output after writes.

When HOTAS input disappears while the Bridge is running:

1. Device selection no longer has an active supported input.
2. Physical sampling closes or reports inactive.
3. Runtime input falls back to simulation or a blocked state.
4. The output loop is disabled instead of continuing to write stale physical input.
5. Telemetry reports the blocked or fallback state.

When vJoy output verification is lost or output writing fails:

1. The write result is recorded.
2. The output loop safety state is updated.
3. Neutral restore is attempted where applicable.
4. Telemetry reports the failure instead of reporting live readiness.

## Data Flow

The full live data path is:

```text
Physical HOTAS
  -> Windows joystick backend
  -> PhysicalInputSampler
  -> RuntimeOrchestrator
  -> WorkspaceSignalPipeline
  -> VirtualOutputIntent
  -> RealVJoyOutputBackend
  -> vJoy device
```

The UI observes this path through Bridge telemetry:

```text
Bridge runtime frame
  -> telemetry JSON
  -> BridgeTelemetryClient
  -> UI pages and status chips
```

## Physical Input

The physical input backend reads Windows joystick state and normalizes supported controls into HelmForge axis names:

- Roll
- Pitch
- Throttle
- Yaw
- Aux 1
- Aux 2

Buttons are reported as `B1` through `B15` where available. Hat/POV input is reported as a normalized direction such as `Centered`, `North`, `South`, or a diagonal direction.

The Bridge treats physical input as live only when a fresh supported sample exists.

## Signal Pipeline

Each frame passes through the shared workspace pipeline:

1. Mapping
2. Base tuning
3. Filtering
4. Mode modifiers
5. Conditional rules
6. Final output limits
7. Virtual output intent

The Runtime Orchestrator records proof for the input source, pipeline state, output verification, output-loop state, and readiness result.

## vJoy Output

The real vJoy provider uses the vJoy interface DLL when available. The output path is guarded:

- vJoy must be detected.
- A vJoy device must be available.
- The backend must acquire the device.
- A bounded verification write must succeed.
- Neutral restore must succeed.
- The output loop must be enabled and running before final output is considered live.

Axis values are converted from HelmForge normalized values into vJoy axis range values. Buttons are written as pressed/released states. Hat directions are written as continuous POV values or centered.

## Telemetry

Telemetry is the UI truth surface. It includes:

- Runtime truth.
- Lifecycle state.
- Input status.
- Output status.
- Output verified flag.
- Raw axes.
- Final axes.
- Buttons and hats.
- Active modes.
- Rule summary.
- Runtime frame proof.
- Output loop state.
- Last output write status.
- Warnings and errors.

Default telemetry path:

```text
%TEMP%\helmforge_bridge_telemetry.json
```

The UI treats missing, stale, invalid, or error telemetry as a fallback state.

## UI Interaction

The UI consumes Bridge truth in several places:

- Header status chip.
- Mapping status chips and runtime setup rows.
- Tuning page live dots.
- Live Monitor graphs and rolling history.
- Effective Response Stack live values.
- Perf / Diagnostics runtime and telemetry cards.
- Help / Docs runtime setup guidance.

The tuning and live graphs update at a 60 Hz target. The Bridge worker runs away from the UI thread so graph refreshes, scrolling, and page switching remain usable.

## Readiness Rules

Full live readiness is reported only when all required proof exists:

- Fresh physical HOTAS input.
- Successful signal pipeline frame.
- Real vJoy output verification.
- Running output loop.
- Fresh telemetry.
- No safety stop.
- No blocking runtime error.

The Bridge does not infer readiness from a single signal. HOTAS detection alone, vJoy detection alone, or output intent alone is not enough.

## Failure Behavior

The Bridge fails safe:

- Missing HOTAS keeps simulation or blocked runtime state visible.
- Missing vJoy keeps output unverified.
- Stale telemetry is not treated as live.
- Output write failure safety-stops the output path.
- Neutral restore failure is surfaced in telemetry.
- The UI displays the failure rather than replacing it with a generic success message.
