# Model tools and checks

Run from the repository root. Python 3.12 is used for the modeling checks.

```sh
python3 -m unittest discover -s .agents/skills/bambu-model-workflow/tests
uv run --python 3.12 --with 'trimesh[easy]' --with manifold3d --with matplotlib python -m unittest discover -s tools -p 'test_*.py'
python3 .agents/skills/bambu-model-workflow/scripts/validate_model.py models/cable_passthrough/PatchPanel_CABLE_INSERT_10MM_V1.3mf --require-bambu-settings
```

| Tool | Purpose |
| --- | --- |
| `build_top_entry.py` | Rebuild cable panel from preserved source geometry; requires upstream license compliance |
| `build_blanking_insert.py` | Rebuild solid insert and check its sliding fit |
| `build_cable_insert.py` | Build 8/10 mm cable caps into ignored draft output |
| `build_support_footprint_3mf.py` | Package cleanup meshes; shared 3MF helper |
| `test_cable_insert.py` | Cable-cap shape, fit, insertion and project checks |
| `test_public_layout.py` | Curated model boundary, documentation links and portable Codex defaults |

Dependencies are fetched by `uv`; they are not vendored. Existing geometry tests
do not need browser, Blender, Codex credentials or a printer connection.

```sh
uv run --python 3.12 --with 'trimesh[easy]' --with manifold3d --with matplotlib tools/build_cable_insert.py
```

The older `build_top_entry.py`, `build_blanking_insert.py` and packaging helper
write their current output files. Preserve copies under `.bambu-preflight/`
before running them, inspect the diff, and revalidate. No shelf/KWS construction
scripts or private geometry are included. The TP-Link strips are supplied as
validated exports; their full historical generator is not part of this repo.
