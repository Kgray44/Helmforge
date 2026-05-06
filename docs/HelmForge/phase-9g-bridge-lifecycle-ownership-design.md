# Phase 9G - Bridge Lifecycle Ownership Design

Product: HelmForge  
Technical subtitle: HOTAS Control Panel V3  
Scope: design and decision record only

## Design-Only Boundary

Phase 9G does not implement lifecycle behavior. It adds no process spawning, no automatic Bridge launch, no Windows Service, no login auto-start task, no tray/background manager, no real HOTAS polling, no vJoy writes, no output verification, and no real runtime activation.

The purpose of this document is to decide ownership and safety rules before any future phase changes how the Bridge starts, stops, wakes, idles, or reports process presence.

## Current Lifecycle State

Current runtime truth after Phases 9C-9F:

- HOTAS is not connected.
- vJoy is detected.
- Runtime truth is `blocked_missing_device`.
- `output_verified` is false.
- Full Live Runtime Ready is false.
- Bridge telemetry can be `Connected`, `Missing`, `Stale`, `Invalid`, or `Error`.
- Missing, stale, invalid, and error telemetry use simulation fallback.
- Stale telemetry is not treated as live Bridge truth.

Allowed current lifecycle posture:

- manual simulation Bridge runs through `python -m bridge_app.main`;
- UI reads telemetry when present and fresh;
- UI requests safe commands through the command file;
- Bridge acknowledges consumed command requests through telemetry;
- UI never claims runtime readiness without fresh telemetry and output verification proof.

## Current Bridge Startup Model

The Bridge startup model is manual development launch.

Supported commands:

```powershell
python -m bridge_app.main --once
python -m bridge_app.main --run-for-ms 250
python -m bridge_app.main --status
```

The UI does not spawn the Bridge process. The Bridge is not installed as a service. The Bridge is not registered as a login startup task. The Bridge is not managed by a tray/background manager.

This is intentional until lifecycle truth, command acknowledgement, crash handling, and user control rules are settled.

## Current UI Responsibility

The UI owns configuration, visualization, diagnostics, and user interaction.

Current UI responsibilities:

- save and edit the V3 workspace/configuration;
- display telemetry freshness and runtime truth;
- display simulation fallback when Bridge telemetry is missing, stale, invalid, or unreadable;
- write safe Bridge command requests for `Status`, `RunPreflight`, `ReloadConfig`, `SwitchToSimulation`, and `ClearError`;
- show command request status only when matching telemetry confirms the request ID;
- avoid fake live/output claims.

The UI currently does not own Bridge process lifecycle.

## Current Bridge Responsibility

The Bridge owns the future real-time runtime boundary, but current implementation is simulation-only.

Current Bridge responsibilities:

- load the V3 workspace or use default fallback safely;
- run bounded simulation ticks;
- process simulation values through shared-core logic;
- publish telemetry JSON;
- parse safe command requests;
- report the most recently consumed command through `last_command`;
- keep `output_verified` false.

The Bridge currently does not poll real HOTAS hardware and does not write vJoy.

## Current Telemetry Responsibility

Telemetry is the only runtime truth surface.

Telemetry responsibility:

- Bridge publishes lifecycle, runtime truth, input/output status, output verification status, axes, buttons, hats, active modes, rule summary, warnings, errors, and `last_command`;
- UI reads telemetry and validates freshness;
- UI treats stale, missing, invalid, and error telemetry as simulation fallback;
- UI does not infer process state from command-file writes.

## Current Command Responsibility

Command-file writes are requests, not success responses.

Command responsibility:

- UI writes safe command JSON with `schema_version`, `request_id`, `command`, `created_at`, and `source`;
- Bridge consumes command files during its own ticks;
- Bridge ignores stale commands older than the configured threshold;
- Bridge avoids re-executing the same request ID while running;
- Bridge reports command status through telemetry `last_command`;
- UI only treats `last_command` as relevant when the request ID matches the latest UI request.

## Why the UI Does Not Yet Start, Stop, or Restart the Bridge

The UI does not yet start, stop, or restart the Bridge because process lifecycle ownership is riskier than command-file ownership.

Reasons:

- process launch can look like runtime readiness even when telemetry is stale or output is unverified;
- process termination can interrupt a future real-time control path;
- child-process management needs crash handling, log capture, cleanup, and user-visible truth;
- Windows process/session behavior differs between development shells, packaged apps, elevated contexts, and login startup;
- current Bridge telemetry already supports read-only manual development without making the UI responsible for runtime authority.

## Why Output Verification Remains Deferred

Output verification remains deferred because vJoy detected is not the same as confirmed vJoy writes.

Output verification requires a future phase to prove:

- a virtual output backend is selected;
- writes are sent safely;
- write results are read back or otherwise verified;
- failure states are explicit and recoverable;
- user consent and safety behavior are defined.

Until then, `output_verified` remains false and Full Live Runtime Ready remains false.

## Why Real HOTAS/vJoy Runtime Work Remains Deferred

Real HOTAS polling and vJoy writes remain deferred because lifecycle and truth semantics must be stable first.

Reasons:

- the Bridge must be the runtime owner, not the UI;
- missing/unplugged HOTAS behavior must safe-idle without fake live claims;
- output writes need separate verification and failure handling;
- hardware access may require driver, permission, and device-state handling;
- unsafe startup or stale command handling would be harder to correct after real output writes exist.

## Lifecycle Ownership Options

### Option A: Manual Bridge Launch During Development

Description:

Developer or user starts the Bridge manually from a shell.

Advantages:

- lowest implementation complexity;
- easiest to inspect stdout, telemetry, and command files;
- avoids hidden background behavior;
- safest while real hardware/output writes do not exist.

Risks:

- user must know whether the Bridge is running;
- no automatic recovery after crash;
- inconvenient for non-developer use.

Implementation complexity:

- low.

User experience impact:

- acceptable for current development;
- not ideal for finished product.

Debugging impact:

- best current debugging posture because process identity and logs are visible.

Safety/truth implications:

- safest current option;
- UI can truthfully show Bridge telemetry missing, stale, or connected without owning lifecycle.

Appropriateness:

- appropriate now.

### Option B: UI-Launched Bridge Child Process

Description:

The PySide6 UI launches `bridge_app` as a child process and monitors telemetry.

Advantages:

- convenient for users opening the UI;
- can keep development install simple;
- avoids Windows Service complexity.

Risks:

- UI close may kill or orphan the Bridge depending implementation;
- child-process launch can be mistaken for runtime readiness;
- packaged app path/elevation/environment handling can be fragile;
- crash and restart semantics must be explicit.

Implementation complexity:

- medium.

User experience impact:

- better than manual launch if done carefully;
- confusing if the UI cannot clearly explain starting, running, stale, blocked, and failed states.

Debugging impact:

- harder than manual launch unless logs and process identity are surfaced.

Safety/truth implications:

- not safe until the UI has read-only process presence hints, log location, crash state, and telemetry freshness checks.

Appropriateness:

- later, after a read-only presence phase.

### Option C: Tray/Background Bridge Manager

Description:

A small user-session manager owns Bridge lifecycle, status, safe-idle, logs, and user controls.

Advantages:

- clearer ownership than UI child process;
- can keep Bridge alive when UI closes;
- can present user-controlled start/stop/safe-idle;
- can host future notifications and log access.

Risks:

- additional process and UX surface;
- needs robust crash handling and update behavior;
- must avoid fake "ready" states.

Implementation complexity:

- medium to high.

User experience impact:

- likely best long-term non-service desktop model;
- visible and user-controlled.

Debugging impact:

- good if tray exposes logs, telemetry age, lifecycle state, and command status.

Safety/truth implications:

- strong option if it remains telemetry-driven and conservative.

Appropriateness:

- recommended later, after manual Bridge and read-only presence semantics are proven.

### Option D: Windows Service

Description:

Bridge runs as a Windows Service outside the normal UI process/session.

Advantages:

- can start before UI;
- can recover independently;
- suitable for always-on background runtime if needed.

Risks:

- service/session/device-access complexity;
- driver and HID/vJoy access can behave differently under service accounts;
- harder installation, permissions, updates, logs, and support;
- can feel opaque to users.

Implementation complexity:

- high.

User experience impact:

- potentially smooth once mature;
- poor if users cannot understand or control it.

Debugging impact:

- harder than manual, child process, or tray unless substantial diagnostics exist.

Safety/truth implications:

- risky before real runtime stability and output verification are proven.

Appropriateness:

- defer until there is a strong reason.

### Option E: Login Auto-Start Task

Description:

Bridge or a Bridge manager starts when the user logs in.

Advantages:

- convenient;
- supports ready monitoring before the UI opens;
- can reduce user setup friction later.

Risks:

- background behavior can surprise users;
- stale or failed runtime can persist unnoticed;
- startup ordering with drivers/devices can be tricky;
- needs opt-in, disable, logs, and clear status.

Implementation complexity:

- medium.

User experience impact:

- useful only after the Bridge is stable and user-controlled.

Debugging impact:

- can be difficult if startup logs and failure causes are not surfaced.

Safety/truth implications:

- unsafe before user control and verified runtime states exist.

Appropriateness:

- later, opt-in only.

## Recommended Staged Lifecycle Path

Recommended conservative path:

1. Keep manual Bridge launch for now.
2. Add read-only process presence hints if needed.
3. Add a tray/background Bridge manager after process presence and logs are reliable.
4. Defer UI-launched child process until it can avoid fake readiness and orphaned processes.
5. Defer Windows Service until there is a strong reason.
6. Defer login auto-start until the Bridge is stable, user-controlled, and opt-in.
7. Never allow UI to imply runtime readiness without fresh telemetry and output verification.

## Bridge Lifecycle Truth States

Proposed lifecycle truth states:

- `not_configured`: Bridge path/config is not known.
- `not_running`: process presence check says Bridge is not running.
- `starting`: Bridge launch has begun but fresh telemetry has not confirmed readiness.
- `running_simulated`: Bridge is running in simulation mode.
- `running_blocked_missing_device`: Bridge is running but physical HOTAS is missing.
- `running_read_only`: Bridge is running without output authority.
- `running_live_unverified`: physical input/output path is partially detected but output writes are not verified.
- `running_live_verified`: input and output writes are verified.
- `stopping`: Bridge shutdown is in progress.
- `crashed`: a previously known Bridge process exited unexpectedly.
- `stale`: telemetry exists but is stale.
- `unknown`: UI cannot determine process or telemetry truth.

Allowed before real hardware work exists:

- `not_configured`
- `not_running`
- `starting`
- `running_simulated`
- `running_blocked_missing_device`
- `running_read_only`
- `stopping`
- `crashed`
- `stale`
- `unknown`

Not allowed before real hardware/output verification work exists:

- `running_live_unverified`
- `running_live_verified`

`running_live_verified` is allowed only after a future output verification phase proves real output writes.

## Future UI Wording Rules

The UI must distinguish:

- Bridge telemetry missing;
- Bridge not known to be running;
- Bridge stale;
- Bridge simulated;
- Bridge blocked by missing HOTAS;
- Bridge output unverified;
- Full Live Runtime Ready false.

The UI must not say these words as state claims unless corresponding telemetry/runtime proof exists:

- live;
- active;
- output verified;
- ready;
- connected to HOTAS;
- writing to vJoy.

Safe wording examples:

- "Bridge telemetry missing."
- "Bridge telemetry stale; simulation fallback active."
- "Bridge simulated."
- "Bridge blocked: HOTAS not connected."
- "Output verified: false."
- "Full Live Runtime Ready: false."

## Safety Gates

Before UI can launch Bridge:

- process path resolution is tested;
- logs and stderr are captured;
- stale telemetry cannot be mistaken for running state;
- crash state is visible;
- UI wording distinguishes requested, starting, running, stale, and failed.

Before tray manager can be added:

- Bridge process presence can be read safely;
- user can stop/safe-idle intentionally;
- logs are accessible;
- telemetry freshness and command acknowledgement are stable.

Before login auto-start can be added:

- startup is opt-in;
- user can disable it;
- startup failures are visible;
- safe-idle behavior is proven with missing HOTAS;
- output writes remain gated by verification.

Before Windows Service can be added:

- there is a strong reason not solved by tray/user-session manager;
- device access in service context is proven;
- install/uninstall/update flows are designed;
- admin permission and logs are clear.

Before real HOTAS polling can be added:

- device discovery truth is stable;
- unplug/replug behavior is designed;
- no UI code owns polling;
- Bridge safe-idle behavior is tested.

Before vJoy writes can be added:

- output backend selection is explicit;
- no writes occur without user-visible status;
- failure handling is typed;
- output writes are separated from output verification.

Before output verification can be claimed:

- write path exists;
- verification/readback or equivalent proof exists;
- failures are reported truthfully;
- Full Live Runtime Ready remains false until both input and output are verified.

## Phase 9G Decision

Decision:

- keep manual Bridge launch for now;
- do not implement UI process spawning;
- do not implement tray/background manager yet;
- do not implement Windows Service;
- do not implement login auto-start;
- keep all lifecycle status telemetry-driven;
- use Phase 9G as the governing decision record before any lifecycle implementation.
