#!/usr/bin/env python3
"""Package the support-footprint cleanup STL with the validated P2S template."""

from __future__ import annotations

import struct
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (
    ROOT
    / "models/plate_cleanup/PETG_residue_lift_patch_50x50x1mm.3mf"
)
PLATE_CENTER_MM = (128.0, 128.0)
PROJECTS = [
    (
        ROOT
        / "models/plate_cleanup/PETG_support_footprint_lift_patch_100x140x1mm.stl",
        ROOT
        / "models/plate_cleanup/"
        "PETG_support_footprint_lift_patch_100x140x1mm.3mf",
        None,
    ),
    (
        ROOT / "models/plate_cleanup/PETG_remaining_support_islands_lift_patch_1mm.stl",
        ROOT
        / "models/plate_cleanup/"
        "PETG_remaining_support_islands_lift_patch_1mm.3mf",
        (0.0, 0.0, 100.0, 140.0),
    ),
]


def format_number(value: float) -> str:
    rounded = round(value, 6)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.6f}".rstrip("0").rstrip(".")


def read_binary_stl(path: Path) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"STL is too small: {path}")

    triangle_count = struct.unpack_from("<I", data, 80)[0]
    expected_size = 84 + triangle_count * 50
    if len(data) != expected_size:
        raise ValueError(f"Expected a binary STL of {expected_size} bytes, got {len(data)}")

    vertices: list[tuple[float, float, float]] = []
    vertex_ids: dict[tuple[float, float, float], int] = {}
    triangles: list[tuple[int, int, int]] = []
    offset = 84

    for _ in range(triangle_count):
        coordinates = struct.unpack_from("<12fH", data, offset)[3:12]
        face: list[int] = []
        for index in range(0, 9, 3):
            vertex = tuple(round(float(value), 6) for value in coordinates[index : index + 3])
            if vertex not in vertex_ids:
                vertex_ids[vertex] = len(vertices)
                vertices.append(vertex)
            face.append(vertex_ids[vertex])
        triangles.append(tuple(face))
        offset += 50

    return vertices, triangles


def build_model_xml(
    vertices: list[tuple[float, float, float]],
    triangles: list[tuple[int, int, int]],
    model_name: str,
    placement_bounds: tuple[float, float, float, float] | None = None,
) -> bytes:
    if placement_bounds is None:
        min_x = min(vertex[0] for vertex in vertices)
        min_y = min(vertex[1] for vertex in vertices)
        max_x = max(vertex[0] for vertex in vertices)
        max_y = max(vertex[1] for vertex in vertices)
    else:
        min_x, min_y, max_x, max_y = placement_bounds
    shift_x = PLATE_CENTER_MM[0] - (min_x + max_x) / 2
    shift_y = PLATE_CENTER_MM[1] - (min_y + max_y) / 2

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">',
        ' <metadata name="Application">BambuStudio-02.05.00.66</metadata>',
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
        f' <metadata name="Title">{model_name}</metadata>',
        " <resources>",
        f'  <object id="1" type="model" name="{model_name}">',
        "   <mesh>",
        "    <vertices>",
    ]
    for x, y, z in vertices:
        lines.append(
            f'     <vertex x="{format_number(x + shift_x)}" '
            f'y="{format_number(y + shift_y)}" z="{format_number(z)}"/>'
        )
    lines.extend(["    </vertices>", "    <triangles>"])
    for v1, v2, v3 in triangles:
        lines.append(f'     <triangle v1="{v1}" v2="{v2}" v3="{v3}"/>')
    lines.extend(
        [
            "    </triangles>",
            "   </mesh>",
            "  </object>",
            " </resources>",
            ' <build><item objectid="1" printable="1"/></build>',
            "</model>",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def build_model_settings(model_name: str, face_count: int) -> bytes:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<config>
 <object id="1">
  <metadata key="name" value="{model_name}"/>
  <metadata key="extruder" value="1"/>
  <metadata face_count="{face_count}"/>
  <part id="1" subtype="normal_part">
   <metadata key="name" value="{model_name}"/>
   <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
   <metadata key="source_file" value="{model_name}"/>
   <metadata key="source_object_id" value="0"/>
   <metadata key="source_volume_id" value="0"/>
   <mesh_stat face_count="{face_count}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
  </part>
 </object>
 <plate>
  <metadata key="plater_id" value="1"/>
  <metadata key="locked" value="false"/>
  <metadata key="filament_map_mode" value="Auto For Flush"/>
  <metadata key="filament_maps" value="1"/>
  <model_instance>
   <metadata key="object_id" value="1"/>
   <metadata key="instance_id" value="0"/>
  </model_instance>
 </plate>
</config>
'''.encode("utf-8")


def package_project(
    source: Path,
    output: Path,
    placement_bounds: tuple[float, float, float, float] | None,
) -> None:
    vertices, triangles = read_binary_stl(source)
    model_name = source.name
    replacements = {
        "3D/3dmodel.model": build_model_xml(
            vertices, triangles, model_name, placement_bounds
        ),
        "Metadata/model_settings.config": build_model_settings(
            model_name, len(triangles)
        ),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(TEMPLATE, "r") as source_archive, ZipFile(
        output, "w", compression=ZIP_DEFLATED, compresslevel=9
    ) as output_archive:
        for source_info in source_archive.infolist():
            payload = replacements.get(source_info.filename, source_archive.read(source_info))
            target_info = ZipInfo(source_info.filename, date_time=(1980, 1, 1, 0, 0, 0))
            target_info.compress_type = ZIP_DEFLATED
            target_info.external_attr = source_info.external_attr
            output_archive.writestr(target_info, payload)

    print(output)


def main() -> None:
    for source, output, placement_bounds in PROJECTS:
        package_project(source, output, placement_bounds)


if __name__ == "__main__":
    main()
