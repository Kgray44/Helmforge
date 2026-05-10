# HF-LRDC-1D Bridge/UI Workspace Config Handshake Report

## Problem Summary

Before HF-LRDC-1D, Bridge telemetry showed runtime state but did not prove which workspace/config revision the Bridge had loaded. The UI could show one workspace while the Bridge processed an older file, a missing-file default, an invalid-file default, or a not-yet-reloaded config. That made Live Monitor debugging ambiguous.

## Workspace Identity Strategy

HF-LRDC-1D adds `shared_core/persistence/workspace_identity.py`.

The helper builds a deterministic SHA-256 hash from canonical workspace content:

- JSON keys are sorted.
- The hash is stable across key-order differences.
- Meaningful workspace content, schema version, profile, mappings, modes, tuning, filtering, combat, rules, profiles, and target metadata participate.
- Volatile/UI persistence fields such as workspace state and source-path notes are excluded.
- `workspace_revision` is the deterministic first 12 characters of the hash.
- `short_hash` is the first 8 characters for compact display.

## Bridge Telemetry Fields Added

Bridge telemetry now always includes:

```json
"bridge_workspace": {
  "config_path": "...",
  "config_status": "loaded|missing_default|invalid_default",
  "schema_version": "3.0.0",
  "product_name": "HelmForge",
  "active_profile": "...",
  "workspace_hash": "...",
  "workspace_revision": "...",
  "loaded_at": "...",
  "generated_at": "...",
  "using_default_workspace": false,
  "warnings": [],
  "errors": []
}
```

Missing configs report `missing_default` with `using_default_workspace: true`. Invalid configs report `invalid_default`, keep the parse/schema error visible, and use the default workspace honestly.

## Reload Command Handshake

UI reload requests may now include:

- `expected_workspace_hash`
- `expected_workspace_revision`
- `config_path`

When Bridge handles `ReloadConfig`, it loads the requested path, computes the loaded identity, compares expected vs loaded hash/revision when provided, and writes the result into `last_command`.

Command telemetry can include:

- `expected_workspace_hash`
- `expected_workspace_revision`
- `loaded_workspace_hash`
- `loaded_workspace_revision`
- `config_match`
- `mismatch_reason`
- `config_path`
- `config_status`

Mismatches are truthful but not fatal unless config loading itself fails into default/error behavior.

## UI/Live Monitor Labels

The Live Monitor now computes a UI-side workspace identity and displays compact config sync truth:

- `Config sync: match|mismatch|unknown | Bridge <hash> | UI <hash>`
- `Bridge config: <file> | loaded|missing_default|invalid_default`
- `Last reload: completed | expected hash matched`

If Bridge is using a missing or invalid default config, the label says `using default workspace`. If hashes differ, the label reports mismatch instead of claiming the Bridge is using unsaved or different UI state.

## Mismatch, Default, And Invalid States

- `match`: Bridge workspace hash equals the UI workspace hash.
- `mismatch`: Bridge hash differs from the UI hash.
- `missing_default`: Bridge did not find the requested config and is using defaults.
- `invalid_default`: Bridge found a config but could not parse/load it and is using defaults.
- `unknown`: telemetry lacks the optional `bridge_workspace` block.

Repeated or fresh telemetry does not imply config sync unless the hashes match.

## Tests Added

Added `tests/test_hf_lrdc_1d_workspace_config_handshake.py`, covering:

- deterministic workspace hashing;
- hash changes on meaningful config changes;
- Bridge loaded/missing/invalid config telemetry;
- reload expected-vs-loaded comparison;
- Bridge client pass-through;
- Live Monitor match/mismatch/default labels;
- runtime truth preservation.

## Deferred Work

HF-LRDC-1D intentionally does not implement persistent vJoy output ownership, output cadence/safety hardening, new telemetry transport, new physical input backends, mapping/tuning behavior changes, auto-save, game injection, graphics hooking, or cloud behavior.

Persistent vJoy output ownership remains intentionally deferred to HF-LRDC-2A.

## Runtime Truth Preservation

Config match does not prove physical input. Config match does not prove vJoy writes. Physical input does not mean Full Live Runtime Ready. vJoy detected is not output verification. Output intent is not output write proof. Fresh telemetry is not proof of vJoy writes. The readiness gate remains unchanged, and simulation fallback remains available.
