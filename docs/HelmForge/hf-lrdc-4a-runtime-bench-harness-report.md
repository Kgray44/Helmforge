# HF-LRDC-4A Runtime Bench Harness Report

Unique repair track: HF-LRDC, HelmForge Live Runtime Data Chain.

## Problem Summary

HF-LRDC now has fast-loop separation, physical input fidelity diagnostics, Live Monitor frame dedupe, workspace config identity, persistent output-loop ownership, output cadence/safety telemetry, and a local telemetry stream. HF-LRDC-4A adds a repeatable bench harness so those seams can be measured with deterministic fake backends in CI and, later, with real HOTAS/vJoy on a Windows bench machine.

## Harness Architecture

Added `bridge_app/runtime_bench.py` and `scripts/run_hf_lrdc_runtime_bench.py`.

The harness runs without launching the full UI. Fake mode builds deterministic HOTAS sample frames, injects them through `FakePhysicalInputBackend`, runs `BridgeService` for bounded ticks, observes JSON telemetry output, and writes bounded artifacts. Real mode is opt-in and currently reports bench-only truth unless real hardware requirements are explicitly requested and future real bench support is expanded.

The harness does not bypass Bridge readiness gates and does not turn fake proof into real proof.

## Fake Scenarios

Fake input scenarios:

- `axis_sweep_roll`: Roll sweeps from -1.0 to +1.0 and back.
- `axis_step_pitch`: Pitch steps through 0.0, +1.0, -1.0, 0.0.
- `throttle_ramp`: Throttle ramps smoothly across its normalized range.
- `buttons_hat`: B1, B2, B15 and hat/POV directions are exercised.
- `multi_axis_mixed`: Roll, Pitch, Throttle, and Yaw change together.

Fake output validation scenarios:

- `fake_output_success`: fake writes succeed and write counts increase.
- `fake_output_rate_limited`: output ticks exceed write cadence and rate-limited skips are counted.
- `fake_output_failure`: a harness-owned fake backend injects write failure and safety stop truth is reported.
- `fake_output_unverified`: output loop remains unwritten and runtime truth stays blocked.

## Artifact Outputs

Each run writes a timestamped directory under the requested output root:

```text
.artifacts/hf-lrdc/runtime-bench/<timestamp>-<mode>-<scenario>/
  summary.md
  summary.json
  frames.jsonl
  timings.csv
```

The logs are bounded by duration/tick count and do not store unbounded histories.

## Pass / Fail Criteria

Fake mode pass criteria include:

- the Bridge runs bounded ticks for the requested duration;
- fake input samples are produced;
- pipeline output changes are observed;
- telemetry frames are produced;
- duplicate/repeated frame count remains truthful;
- fake output success records writes when configured;
- fake output rate-limited records skipped writes separately;
- fake output failure reports failure and safety stop;
- fake output unverified does not claim write proof;
- Full Live Runtime Ready remains false in fake-only mode.

Real mode is conservative:

- real HOTAS/vJoy proof is not faked;
- real mode can be used as a bench placeholder without failing CI when hardware is not required;
- `--require-hotas` or `--require-vjoy` turns missing real proof into failure;
- real output writes are not enabled unless future real bench expansion explicitly uses existing safe gates and `--allow-real-output-writes`.

## Safety Rules

- Fake backend proof is fake-path proof only.
- Physical input working does not prove vJoy writes.
- Telemetry stream/JSON freshness does not prove output writes.
- Output intent is not output write proof.
- vJoy detected is not output verification.
- Full Live Runtime Ready remains gated by real input proof, pipeline proof, real output verification, output loop running, and real write proof.
- No unsafe live output enablement was added.

## Tests Added

Added `tests/test_hf_lrdc_4a_runtime_bench_harness.py`.

Coverage includes fake scenario generation, fake bench artifacts, fake output success/rate-limit/failure/unverified cases, real-mode missing hardware honesty, CLI parsing/smoke run, and frame/timing artifact content.

## Verification Commands

Required command targets:

```powershell
python -m pytest tests/test_hf_lrdc_4a_runtime_bench_harness.py
python scripts/run_hf_lrdc_runtime_bench.py --mode fake --scenario axis_sweep_roll --duration-ms 1000
python scripts/run_hf_lrdc_runtime_bench.py --mode fake --scenario fake_output_failure --duration-ms 1000
```

## Known Limitations

- Real Windows/HOTAS/vJoy validation remains manual/bench-only.
- Fake mode currently observes JSON telemetry; local stream observation can be expanded in a later measurement pass.
- Real mode does not write vJoy in this phase.
- The harness is bounded for CI and not a long-duration soak test.

## Runtime Truth Preservation

HF-LRDC-4A adds measurement, not authority. It adds no fake output verification, no fake Full Live Runtime Ready claim, no game injection, no graphics hooking, no cloud behavior, and no auto-save.
