# Bambu preflight contract

## What can be proven

The bundled validator checks the parts that can be determined without guessing a printer setup.

| Input | Deterministic checks |
| --- | --- |
| STL | Parseability, finite coordinates, non-degenerate triangles, closed manifold edges, consistent orientation, positive signed volume, axis-aligned dimensions, and an optional build-volume limit |
| Core 3MF | Safe ZIP structure, CRC, bounded archive/XML size, required package parts, recognized model units, valid vertex indices, and per-object mesh topology |
| Bambu project 3MF | Core checks plus `Metadata/model_settings.config` and `Metadata/project_settings.config` |
| Sliced Bambu 3MF | Project checks plus slice metadata, matched plate JSON, and nontrivial per-plate G-code |

The validator does not currently prove self-intersection freedom, minimum wall thickness, feature resolution, fit/tolerance, balance, bed adhesion, overhang quality, support removability, material compatibility, or physical print success. It also does not evaluate 3MF build-item transforms against a build plate. Use Blender and Bambu Studio Preview for those checks.

## Commands

Resolve `<skill-dir>` from the location of `SKILL.md`.

Validate a raw STL, interpreting its numbers as millimeters:

```bash
python3 <skill-dir>/scripts/validate_model.py model.stl
```

Add an explicit X/Y/Z build-volume box when the printer is known:

```bash
python3 <skill-dir>/scripts/validate_model.py model.stl --max-dimensions 256 256 256 --json
```

Validate a Bambu Studio project file:

```bash
python3 <skill-dir>/scripts/validate_model.py project.3mf --require-bambu-settings --json
```

Validate a Bambu Studio sliced artifact:

```bash
python3 <skill-dir>/scripts/validate_model.py plate.gcode.3mf --require-sliced --json
```

Exit code `0` means no structural error; warnings may remain. Exit code `1` means the artifact failed preflight.

## STL-to-Bambu workflow

1. Record the source path and checksum when provenance matters. Copy the file into `.bambu-preflight/` before changing it.
2. Run the STL validator. Treat an assumed millimeter scale as an explicit warning because STL stores no unit.
3. If it fails, inspect a copy with Blender MCP. Check for holes, duplicated/internal faces, non-manifold edges, inverted normals, disconnected shells, zero-area faces, and obviously wrong scale. Make the smallest repair, export, and rerun the deterministic validator.
4. Collect the configuration needed to make “properly configured” concrete:

   - exact Bambu printer model and installed nozzle diameter;
   - build plate type;
   - filament vendor/type and AMS/extruder mapping;
   - layer-height/process preset;
   - intended strength, surface, or speed priority;
   - support policy and acceptable orientation;
   - quantity and whether multiple parts must retain alignment.

5. Import the validated STL into a known-good Bambu Studio `.3mf` template for that printer/nozzle/plate/filament combination. Prefer the offline `bambu_modeling` tools `get_stl_info`, `center_model`, `lay_flat`, `save_template`, `get_slice_settings`, `slice_with_template`, and `slice_stl` where appropriate.
6. Keep the source STL, template 3MF, configured project 3MF, and sliced `.gcode.3mf` as distinct artifacts. Never overwrite the source.
7. Validate the configured project and sliced output with the commands above.
8. Open the generated file in the Bambu Studio GUI and inspect Preview layer-by-layer. The GUI preview is a required acceptance gate for first prints, complex geometry, multiple materials, or supports.

## Result levels

- `PASS`: all requested automated gates passed and no validator warning remains. This is unusual for STL because its unit is inherently unstated.
- `WARN`: no structural failure, but assumptions or manual checks remain. Continue only after making those assumptions explicit.
- `FAIL`: malformed input, unsafe archive, bad topology/orientation, scale/build-volume violation, or missing required Bambu/slice parts. Repair or regenerate before import/printing.

Always distinguish “safe to import structurally” from “reviewed in Bambu Studio” and “physically test-printed.”
