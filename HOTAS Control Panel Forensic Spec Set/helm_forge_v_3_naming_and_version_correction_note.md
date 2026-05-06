# HelmForge V3 Naming and Version Correction Note

## Purpose

This note explains the naming/version correction for the rebuild prompt book and repository work.

The original recovered project was called **HOTAS Control Panel V2**, but the new rebuild is now officially being treated as a new product/version:

# **HelmForge**
## **HOTAS Control Panel V3**

This means the recovered V2 documents remain the historical source material, but the rebuilt application should use **HelmForge** as the user-facing product name and **HOTAS Control Panel V3** as the technical subtitle/version lineage.

---

## Naming Decision

### User-facing product name

Use:

```text
HelmForge
```

This should appear in:

- README title and description
- app window title
- user-facing documentation
- installer/package naming later
- app branding
- future shortcuts/start menu entries
- phase reports

### Technical subtitle / lineage name

Use:

```text
HOTAS Control Panel V3
```

This should appear as the technical descriptor, especially when explaining that the project is a rebuild of the lost HOTAS Control Panel V2 work.

### Preferred full branding

Use:

```text
HelmForge — HOTAS Control Panel V3
```

Examples:

- Window title: `HelmForge — HOTAS Control Panel V3`
- README heading: `HelmForge — HOTAS Control Panel V3`
- Project description: `HelmForge is the V3 rebuild of the lost HOTAS Control Panel project.`

---

## Relationship to the Recovered V2 Material

The recovered forensic documents still refer heavily to **HOTAS Control Panel V2** because they were created from old ChatGPT conversations and screenshots of the previous near-complete app.

That is expected and should not be treated as a contradiction.

The correct interpretation is:

```text
Recovered source material: HOTAS Control Panel V2
New rebuilt app/product: HelmForge — HOTAS Control Panel V3
```

Codex should use the V2 notes as design/architecture evidence, but implement the new repository/app as **HelmForge / V3**.

---

## Repository / Package Naming Guidance

Prefer V3 names in new code and folders:

```text
v3_app/
shared_core/
docs/HelmForge/
hotas_bridge_config_v3.json
HelmForge
HelmForge — HOTAS Control Panel V3
```

Avoid creating new V2-specific package names unless referring to recovered documentation or legacy compatibility.

The old prompt book still contains many V2 references. These should be corrected gradually as the prompt book is updated, but current Codex phase prompts should explicitly override them when needed.

---

## Config Naming Guidance

Recovered V2 config name:

```text
hotas_bridge_config_v2.json
```

Preferred V3 config name:

```text
hotas_bridge_config_v3.json
```

Codex should use `hotas_bridge_config_v3.json` for new V3 workspace/config files, while preserving notes that the recovered V2 app used `hotas_bridge_config_v2.json`.

If backward compatibility/import logic is later added, it may support importing V2 configs, but Phase 2 should primarily define the V3 schema.

---

## Prompt Book Correction Needed

The current prompt book still has older language such as:

- `HOTAS Control Panel V2`
- `V2 app`
- `v2_app/`
- `hotas_bridge_config_v2.json`
- installer paths using `HOTAS Control Panel V2`

These should be treated as historical/recovered wording unless the specific phase prompt has already been updated.

When creating new prompts, prefer:

- `HelmForge`
- `HOTAS Control Panel V3`
- `v3_app/`
- `hotas_bridge_config_v3.json`
- `docs/HelmForge/`
- `HelmForge — HOTAS Control Panel V3`

---

## Codex Instruction Patch

Use this short instruction at the top of future Codex prompts when there is any V2/V3 ambiguity:

```text
Naming/version correction:
The recovered documents refer to HOTAS Control Panel V2 because they came from the lost previous app. The new rebuild is named HelmForge, with the technical subtitle HOTAS Control Panel V3.

Use HelmForge as the user-facing product name.
Use HOTAS Control Panel V3 as the technical subtitle/version lineage.
Use v3_app for the new PySide6 application package.
Use hotas_bridge_config_v3.json for the new V3 workspace/config schema unless explicitly implementing V2 import compatibility.
Do not create new V2-branded code paths except when preserving or referencing recovered evidence.
```

---

## Phase 2 Specific Correction

For Phase 2, Codex should use:

```text
Product name: HelmForge
Technical subtitle: HOTAS Control Panel V3
Application package: v3_app
Preferred config filename: hotas_bridge_config_v3.json
Recovered historical config filename: hotas_bridge_config_v2.json
Known target hardware: Thrustmaster T-Flight HOTAS One / Thrustmaster T.Flight HOTAS One
```

Phase 2 should create V3 data models and schema. It should not create new V2-branded schema unless needed for import notes.

---

## Bottom Line

The new app is not simply “V2 again.”

It is:

# **HelmForge — HOTAS Control Panel V3**

The V2 forensic notes are the blueprint. HelmForge V3 is the rebuild.

Tiny naming goblin contained. Carry on.

