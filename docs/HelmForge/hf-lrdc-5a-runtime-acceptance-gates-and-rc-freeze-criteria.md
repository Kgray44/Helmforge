# HF-LRDC-5A Runtime Acceptance Gates and RC Freeze Criteria

HF-LRDC acceptance is a deterministic report over existing runtime truth. It does not create runtime authority, enable output, overwrite config, or promote simulated/fake evidence into real hardware proof.

## Evidence Sources

Accepted evidence sources:

- Current Bridge telemetry JSON or a saved stream payload.
- HF-LRDC-4A runtime bench `summary.json`.
- HF-LRDC-4B manual validation `manual_validation.json`.
- Test-only synthetic evidence explicitly labeled fake or real.

Missing evidence is reported as unavailable or blocked depending on mode and requiredness. Evidence files may be partial; gates must fail closed instead of inventing proof.

## Proof Modes

`fake` mode:

- Uses fake bench/harness evidence.
- Does not require real HOTAS or vJoy.
- Can pass fake-path acceptance.
- Must not claim real Full Live Runtime Ready.

`real` mode:

- Requires real evidence when `--require-hotas`, `--require-vjoy`, `--require-real-output`, or `--require-manual-validation` are supplied.
- Blocks honestly when real HOTAS/vJoy/output/manual proof is missing.
- Can become an RC freeze candidate only when every required real proof gate passes.

## Required Gates

| Gate | Pass Criteria | Blocking Conditions |
| --- | --- | --- |
| Bridge fast loop health | `bridge_timing` exists, tick count is positive, last tick duration exists, slow discovery age/status is visible. | Missing timing/tick evidence. |
| Physical input fidelity | Backend choice/fidelity exists, sample age/read duration are available when active, mapping status is ok or warnings are surfaced. | Missing fidelity, or fake input evidence when real HOTAS is required. |
| Telemetry source truth | Source is labeled as stream, JSON fallback, or simulation; stale/invalid state is visible. | Stale/invalid telemetry or unlabeled source. |
| Frame dedupe/cadence | Accepted frame cadence or age exists, repeated frames are tracked, duplicates are not accepted as new samples. | Duplicate/repeated frames accepted as new. |
| Workspace config sync | Bridge workspace hash/revision exists; UI hash matches when UI context is supplied. | Missing Bridge hash or Bridge/UI mismatch. |
| Pipeline/output intent | Raw axes and final axes exist; runtime output intent is present or bench output changes are proven. | Missing raw/final axes or no output intent evidence. |
| vJoy/output verification truth | Real output verification is present only when actually proven; fake verification remains fake-path proof. | Real vJoy/output verification required but not proven. |
| Persistent output loop | `output_loop_runtime` exists with state and write/skip/failure counters. | Missing output-loop runtime telemetry. |
| Output cadence/safety | Target write rate, skip/failure counters, safety stop reason, and neutral restore status are visible. | Missing target write rate or active safety stop. |
| Bench harness proof | Bench summary exists and passes for the selected proof path. | Missing/failed bench, or fake bench used in real-required mode. |
| Manual validation proof | Manual report loads if supplied; it never overrides runtime proof gates. | Required manual validation missing or blocked/failed. |
| Full Live Runtime Ready | Mirrors the existing runtime readiness evaluator. Acceptance cannot force it. | This gate reports truth and does not convert output intent/telemetry/config/manual confirmation into readiness. |
| RC freeze | All required gates pass for the selected proof path. | Any required gate blocked. |

## Release Posture Vocabulary

- `blocked_runtime_truth`: runtime evidence is missing, stale, inconsistent, or blocked.
- `blocked_missing_hardware_proof`: real mode requires HOTAS/vJoy evidence that is not present.
- `blocked_output_verification`: real output verification or write proof is required but missing.
- `blocked_telemetry_transport`: telemetry source is stale, invalid, unlabeled, or duplicate-inflated.
- `fake_path_pass_real_path_unproven`: fake CI/runtime bench acceptance passed, but real hardware readiness is unproven.
- `real_path_candidate`: real evidence is present but not yet RC frozen.
- `rc_freeze_ready`: all required real-mode freeze gates pass.

## What Cannot Count As Proof

- Physical input working does not prove vJoy writes.
- Telemetry stream connected does not prove output writes.
- Fresh JSON/stream telemetry does not prove output verification.
- Config match does not prove vJoy writes.
- Manual operator confirmation does not override runtime proof gates.
- Output intent is not output write proof.
- vJoy detected is not output verification.
- Fake backend proof is fake-path proof only.

## RC Freeze Criteria

RC freeze is allowed only when:

- The selected proof mode is explicit.
- All required acceptance gates pass.
- Blocking warnings have been classified as non-blocking or resolved.
- Real-path freeze, when requested, includes real HOTAS proof, real vJoy/output verification proof, and safe output-loop write proof.
- Full Live Runtime Ready remains controlled by the existing runtime readiness evaluator.

Fake-path acceptance can be green for CI and regression confidence, but it is not real Full Live Runtime Ready.
