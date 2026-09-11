# 3dmodels.rack

Selected rack accessories and print utilities, with STL files, editable Bambu
Studio projects, and an optional Codex-assisted modeling workflow.

This is a clean-history collection, not a copy of the private development
repository. Restricted-source shelves, KWS parts, old revisions, browser
sessions, and personal machine configuration are not included.

Review [licensing](LICENSE.md) and [excluded models](docs/excluded-models.md).
The [release checklist](docs/release-checklist.md) records passed checks and
remaining uncertainties, including the unverified upstream cable-license version.
Original models: **CC BY-NC-SA 4.0**. Code/docs/Codex setup: **MIT**.
Upstream cable-panel geometry retains its own terms; see [license scope](LICENSE.md).

## Models

| Collection | Current files | Notes |
| --- | --- | --- |
| [Cable passthrough and inserts](models/cable_passthrough/README.md) | V1 top-entry panel, solid blank, 8/10 mm cable caps | Twelve top-entry openings; caps fit over installed cable bodies |
| [TP-Link front/back strip panels](models/tplink_panels/README.md) | V10 plain, lettered, vented | 268 × 30 × 2 mm; 238.5 mm mounting-column span |
| [PETG cleanup patches](models/plate_cleanup/README.md) | Three distinct residue-lifting shapes | Experimental utilities; read plate-damage warning |

These are different accessories, not one interchangeable panel standard.
The cable passthrough is 254 mm wide with round mounting holes; the TP-Link
strips use a separate custom rounded-square mounting layout.

Projects retain the Bambu P2S / 0.4 mm / Generic PETG / 0.20 mm / Textured PEI
setup. Confirm the actual printer, material and settings before slicing.
Validation does not prove physical fit or print success. Test one part first.

## Codex and development

- [Codex setup](docs/codex.md): optional Blender, browser and offline Bambu MCP.
- [Repository instructions](AGENTS.md): geometry, provenance and safety rules.
- [Bambu workflow skill](.agents/skills/bambu-model-workflow/SKILL.md): STL/3MF checks.
- [Tools and tests](tools/README.md): reproducible commands and limitations.
- [Sources and attribution](docs/sources.md): copied geometry versus compatibility references.

No credentials, personal email addresses, printer access codes, browser state,
or upstream restricted meshes belong here. Temporary work goes into ignored
`.bambu-preflight/` or `.work/`.
