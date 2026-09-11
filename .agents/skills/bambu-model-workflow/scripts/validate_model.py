#!/usr/bin/env python3
"""Deterministic structural preflight for STL and Bambu-flavoured 3MF files.

This intentionally uses only Python's standard library.  It validates file
structure and mesh topology; it does not claim that a model will print well.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Hashable, Iterable, Sequence
from xml.etree import ElementTree


DEFAULT_MAX_FILE_MB = 512.0
MAX_ARCHIVE_ENTRIES = 10_000
MAX_MODEL_XML_BYTES = 128 * 1024 * 1024
MAX_SETTINGS_JSON_BYTES = 16 * 1024 * 1024
THREE_MF_UNITS_TO_MM = {
    "micron": 0.001,
    "millimeter": 1.0,
    "centimeter": 10.0,
    "inch": 25.4,
    "foot": 304.8,
    "meter": 1000.0,
}
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
ASCII_VERTEX = re.compile(
    rf"^\s*vertex\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s*$",
    re.IGNORECASE | re.MULTILINE,
)

Point = tuple[float, float, float]
Triangle = tuple[Point, Point, Point]


class ValidationInputError(ValueError):
    """Raised for a malformed, unsupported, or unsafe input file."""


def _new_report(path: Path, file_format: str) -> dict:
    return {
        "path": str(path),
        "format": file_format,
        "valid": False,
        "status": "FAIL",
        "errors": [],
        "warnings": [],
        "metrics": {},
    }


def _finish(report: dict) -> dict:
    report["valid"] = not report["errors"]
    if report["errors"]:
        report["status"] = "FAIL"
    elif report["warnings"]:
        report["status"] = "WARN"
    else:
        report["status"] = "PASS"
    return report


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _cross(a: Point, b: Point) -> Point:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _subtract(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _quantize(point: Point, tolerance: float) -> tuple[int, int, int]:
    return tuple(round(value / tolerance) for value in point)  # type: ignore[return-value]


def analyze_triangles(
    triangles: Sequence[Triangle],
    *,
    topology_keys: Sequence[tuple[Hashable, Hashable, Hashable]] | None = None,
    weld_tolerance: float = 1e-6,
) -> tuple[dict, list[str]]:
    """Return mesh metrics and structural errors for a triangle surface."""
    if topology_keys is not None and len(topology_keys) != len(triangles):
        raise ValueError("topology_keys must match triangle count")
    if weld_tolerance <= 0 or not math.isfinite(weld_tolerance):
        raise ValueError("weld_tolerance must be a positive finite number")

    errors: list[str] = []
    finite_points = [
        point
        for triangle in triangles
        for point in triangle
        if all(math.isfinite(value) for value in point)
    ]
    nonfinite_triangles = sum(
        not all(math.isfinite(value) for point in triangle for value in point)
        for triangle in triangles
    )

    if finite_points:
        minimum = [min(point[axis] for point in finite_points) for axis in range(3)]
        maximum = [max(point[axis] for point in finite_points) for axis in range(3)]
        dimensions = [maximum[axis] - minimum[axis] for axis in range(3)]
    else:
        minimum = maximum = dimensions = [0.0, 0.0, 0.0]

    diagonal = math.sqrt(sum(dimension * dimension for dimension in dimensions))
    cross_epsilon = max(diagonal * diagonal * 1e-12, 1e-18)
    volume_epsilon = max(diagonal * diagonal * diagonal * 1e-12, 1e-18)

    edge_uses: dict[tuple[Hashable, Hashable], list[int]] = defaultdict(list)
    degenerate_triangles = 0
    signed_volume = 0.0
    unique_vertices: set[Hashable] = set()

    for triangle_index, triangle in enumerate(triangles):
        if not all(math.isfinite(value) for point in triangle for value in point):
            continue
        a, b, c = triangle
        twice_area = _cross(_subtract(b, a), _subtract(c, a))
        twice_area_length = math.sqrt(_dot(twice_area, twice_area))
        if twice_area_length <= cross_epsilon:
            degenerate_triangles += 1
            continue

        signed_volume += _dot(a, _cross(b, c)) / 6.0
        if topology_keys is None:
            keys = tuple(_quantize(point, weld_tolerance) for point in triangle)
        else:
            keys = topology_keys[triangle_index]
        unique_vertices.update(keys)
        for start, end in ((keys[0], keys[1]), (keys[1], keys[2]), (keys[2], keys[0])):
            if start == end:
                degenerate_triangles += 1
                continue
            edge = tuple(sorted((start, end), key=repr))
            direction = 1 if start == edge[0] else -1
            edge_uses[edge].append(direction)

    boundary_edges = sum(len(uses) == 1 for uses in edge_uses.values())
    nonmanifold_edges = sum(len(uses) > 2 for uses in edge_uses.values())
    orientation_conflicts = sum(
        len(uses) == 2 and uses[0] == uses[1] for uses in edge_uses.values()
    )

    if not triangles:
        errors.append("Mesh has no triangles.")
    if nonfinite_triangles:
        errors.append(f"Mesh has {nonfinite_triangles} triangle(s) with non-finite coordinates.")
    if degenerate_triangles:
        errors.append(f"Mesh has {degenerate_triangles} degenerate triangle(s).")
    if boundary_edges:
        errors.append(f"Mesh has {boundary_edges} boundary edge(s); it is not watertight.")
    if nonmanifold_edges:
        errors.append(f"Mesh has {nonmanifold_edges} edge(s) used by more than two triangles.")
    if orientation_conflicts:
        errors.append(
            f"Mesh has {orientation_conflicts} shared edge(s) with inconsistent triangle orientation."
        )
    closed_surface = bool(edge_uses) and not boundary_edges and not nonmanifold_edges
    if closed_surface and not orientation_conflicts:
        if signed_volume < -volume_epsilon:
            errors.append("Closed mesh has negative signed volume; faces appear inward-oriented.")
        elif abs(signed_volume) <= volume_epsilon:
            errors.append("Closed mesh has near-zero signed volume.")

    metrics = {
        "triangles": len(triangles),
        "vertices": len(unique_vertices),
        "bounds_mm": {"min": minimum, "max": maximum},
        "dimensions_mm": dimensions,
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "orientation_conflicts": orientation_conflicts,
        "degenerate_triangles": degenerate_triangles,
        "nonfinite_triangles": nonfinite_triangles,
        "signed_volume_mm3": signed_volume,
    }
    return metrics, errors


def _parse_binary_stl(data: bytes) -> list[Triangle]:
    if len(data) < 84:
        raise ValidationInputError("STL is too short to contain a binary header.")
    declared_count = struct.unpack_from("<I", data, 80)[0]
    expected_length = 84 + declared_count * 50
    if expected_length != len(data):
        raise ValidationInputError(
            "Binary STL length mismatch: "
            f"header declares {declared_count} triangle(s), requiring {expected_length} bytes, "
            f"but file has {len(data)} bytes."
        )
    triangles: list[Triangle] = []
    for index in range(declared_count):
        offset = 84 + index * 50 + 12
        coordinates = struct.unpack_from("<9f", data, offset)
        triangles.append(
            (
                tuple(coordinates[0:3]),  # type: ignore[arg-type]
                tuple(coordinates[3:6]),  # type: ignore[arg-type]
                tuple(coordinates[6:9]),  # type: ignore[arg-type]
            )
        )
    return triangles


def _parse_ascii_stl(data: bytes) -> list[Triangle]:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValidationInputError("STL is neither a valid binary STL nor ASCII STL.") from error
    if not text.lstrip().lower().startswith("solid"):
        raise ValidationInputError("ASCII STL must start with 'solid'.")
    vertices = [tuple(float(value) for value in match) for match in ASCII_VERTEX.findall(text)]
    if not vertices or len(vertices) % 3:
        raise ValidationInputError(
            "ASCII STL must contain three parseable vertex lines per triangle."
        )
    return [
        (vertices[index], vertices[index + 1], vertices[index + 2])  # type: ignore[list-item]
        for index in range(0, len(vertices), 3)
    ]


def parse_stl(path: Path, *, max_file_bytes: int) -> tuple[list[Triangle], str]:
    size = path.stat().st_size
    if size > max_file_bytes:
        raise ValidationInputError(
            f"File is {size} bytes, exceeding the configured {max_file_bytes}-byte limit."
        )
    data = path.read_bytes()
    if len(data) >= 84:
        declared_count = struct.unpack_from("<I", data, 80)[0]
        if 84 + declared_count * 50 == len(data):
            return _parse_binary_stl(data), "binary"
    if data.lstrip().lower().startswith(b"solid"):
        return _parse_ascii_stl(data), "ascii"
    return _parse_binary_stl(data), "binary"


def validate_stl(
    path: Path,
    *,
    max_dimensions_mm: tuple[float, float, float] | None,
    max_file_bytes: int,
) -> dict:
    report = _new_report(path, "stl")
    triangles, encoding = parse_stl(path, max_file_bytes=max_file_bytes)
    metrics, mesh_errors = analyze_triangles(triangles)
    metrics["encoding"] = encoding
    report["metrics"] = metrics
    report["errors"].extend(mesh_errors)
    report["warnings"].append(
        "STL is unitless; coordinates were interpreted as millimeters. Confirm scale in Bambu Studio."
    )
    report["warnings"].append(
        "This structural check does not prove self-intersection freedom, minimum wall thickness, "
        "clearances, support needs, material suitability, or print success."
    )
    if max_dimensions_mm is not None:
        dimensions = metrics["dimensions_mm"]
        exceeded = [
            axis
            for axis in range(3)
            if dimensions[axis] > max_dimensions_mm[axis] + 1e-9
        ]
        if exceeded:
            report["errors"].append(
                "Model dimensions "
                f"{dimensions} mm exceed configured build volume {list(max_dimensions_mm)} mm."
            )
    return _finish(report)


def _safe_archive_name(name: str) -> bool:
    if not name or "\\" in name or name.startswith("/"):
        return False
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def _read_xml(archive: zipfile.ZipFile, name: str, *, max_bytes: int) -> ElementTree.Element:
    info = archive.getinfo(name)
    if info.file_size > max_bytes:
        raise ValidationInputError(f"XML part {name!r} exceeds the {max_bytes}-byte limit.")
    data = archive.read(name)
    uppercase_prefix = data[:4096].upper()
    if b"<!DOCTYPE" in uppercase_prefix or b"<!ENTITY" in uppercase_prefix:
        raise ValidationInputError(f"XML part {name!r} contains a forbidden DTD/entity declaration.")
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise ValidationInputError(f"XML part {name!r} is malformed: {error}.") from error


def _read_json_object(archive: zipfile.ZipFile, name: str, *, max_bytes: int) -> dict:
    info = archive.getinfo(name)
    if info.file_size > max_bytes:
        raise ValidationInputError(f"JSON part {name!r} exceeds the {max_bytes}-byte limit.")
    try:
        payload = json.loads(archive.read(name))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationInputError(f"JSON part {name!r} is malformed: {error}.") from error
    if not isinstance(payload, dict):
        raise ValidationInputError(f"JSON part {name!r} must contain an object.")
    return payload


def _mesh_from_object(element: ElementTree.Element) -> tuple[list[Point], list[tuple[int, int, int]]] | None:
    mesh = next((child for child in element if _local_name(child.tag) == "mesh"), None)
    if mesh is None:
        return None
    vertices_element = next(
        (child for child in mesh if _local_name(child.tag) == "vertices"), None
    )
    triangles_element = next(
        (child for child in mesh if _local_name(child.tag) == "triangles"), None
    )
    if vertices_element is None or triangles_element is None:
        raise ValidationInputError("3MF mesh must contain vertices and triangles elements.")

    vertices: list[Point] = []
    for vertex in vertices_element:
        if _local_name(vertex.tag) != "vertex":
            continue
        try:
            point = tuple(float(vertex.attrib[name]) for name in ("x", "y", "z"))
        except (KeyError, ValueError) as error:
            raise ValidationInputError("3MF vertex has missing or non-numeric coordinates.") from error
        vertices.append(point)  # type: ignore[arg-type]

    faces: list[tuple[int, int, int]] = []
    for triangle in triangles_element:
        if _local_name(triangle.tag) != "triangle":
            continue
        try:
            face = tuple(int(triangle.attrib[name]) for name in ("v1", "v2", "v3"))
        except (KeyError, ValueError) as error:
            raise ValidationInputError("3MF triangle has missing or non-integer indices.") from error
        if len(set(face)) != 3:
            raise ValidationInputError("3MF triangle must reference three distinct vertex indices.")
        if any(index < 0 or index >= len(vertices) for index in face):
            raise ValidationInputError(
                f"3MF triangle index is outside the vertex range 0..{max(len(vertices) - 1, 0)}."
            )
        faces.append(face)  # type: ignore[arg-type]
    return vertices, faces


def validate_3mf(
    path: Path,
    *,
    require_millimeter: bool,
    require_bambu_settings: bool,
    require_sliced: bool,
    max_file_bytes: int,
) -> dict:
    report = _new_report(path, "3mf")
    if path.stat().st_size > max_file_bytes:
        raise ValidationInputError(
            f"File exceeds the configured {max_file_bytes}-byte compressed-size limit."
        )

    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_ENTRIES:
            raise ValidationInputError(
                f"3MF contains {len(infos)} entries, exceeding the {MAX_ARCHIVE_ENTRIES}-entry limit."
            )
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise ValidationInputError("3MF contains duplicate archive entry names.")
        unsafe_names = [name for name in names if not _safe_archive_name(name)]
        if unsafe_names:
            raise ValidationInputError(
                f"3MF contains unsafe archive path(s): {unsafe_names[:3]}."
            )
        encrypted = [info.filename for info in infos if info.flag_bits & 0x1]
        if encrypted:
            raise ValidationInputError("Encrypted 3MF archive entries are not supported.")
        total_uncompressed = sum(info.file_size for info in infos)
        if total_uncompressed > max_file_bytes:
            raise ValidationInputError(
                "3MF uncompressed content exceeds the configured "
                f"{max_file_bytes}-byte limit."
            )
        bad_crc = archive.testzip()
        if bad_crc is not None:
            raise ValidationInputError(f"3MF archive CRC check failed for {bad_crc!r}.")

        required_parts = {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
        missing_parts = sorted(required_parts.difference(names))
        if missing_parts:
            raise ValidationInputError(f"3MF is missing required package part(s): {missing_parts}.")
        _read_xml(archive, "[Content_Types].xml", max_bytes=4 * 1024 * 1024)
        _read_xml(archive, "_rels/.rels", max_bytes=4 * 1024 * 1024)
        model = _read_xml(archive, "3D/3dmodel.model", max_bytes=MAX_MODEL_XML_BYTES)

        unit = model.attrib.get("unit", "millimeter").lower()
        if unit not in THREE_MF_UNITS_TO_MM:
            report["errors"].append(f"3MF declares unsupported unit {unit!r}.")
            unit_scale = 1.0
        else:
            unit_scale = THREE_MF_UNITS_TO_MM[unit]
        if require_millimeter and unit != "millimeter":
            report["errors"].append(
                f"3MF unit is {unit!r}; this Bambu preflight requires explicit millimeter units."
            )

        object_reports: list[dict] = []
        all_points_mm: list[Point] = []
        for element in model.iter():
            if _local_name(element.tag) != "object":
                continue
            parsed = _mesh_from_object(element)
            if parsed is None:
                continue
            vertices, faces = parsed
            triangles = [
                (vertices[face[0]], vertices[face[1]], vertices[face[2]]) for face in faces
            ]
            metrics, errors = analyze_triangles(triangles, topology_keys=faces)
            object_id = element.attrib.get("id", "unknown")
            report["errors"].extend(f"Object {object_id}: {error}" for error in errors)
            metrics["object_id"] = object_id
            object_reports.append(metrics)
            all_points_mm.extend(
                tuple(value * unit_scale for value in point)  # type: ignore[arg-type]
                for point in vertices
            )

        if not object_reports:
            report["errors"].append("3MF contains no mesh objects.")

        if all_points_mm:
            minimum = [min(point[axis] for point in all_points_mm) for axis in range(3)]
            maximum = [max(point[axis] for point in all_points_mm) for axis in range(3)]
            dimensions = [maximum[axis] - minimum[axis] for axis in range(3)]
        else:
            minimum = maximum = dimensions = [0.0, 0.0, 0.0]

        required_bambu = {
            "Metadata/model_settings.config",
            "Metadata/project_settings.config",
        }
        has_bambu_settings = required_bambu.issubset(names)
        if require_bambu_settings or require_sliced:
            missing_bambu = sorted(required_bambu.difference(names))
            if missing_bambu:
                report["errors"].append(
                    f"3MF is missing Bambu project setting part(s): {missing_bambu}."
                )
        if "Metadata/project_settings.config" in names:
            project_settings = _read_json_object(
                archive,
                "Metadata/project_settings.config",
                max_bytes=MAX_SETTINGS_JSON_BYTES,
            )
            density_value = project_settings.get("sparse_infill_density")
            if density_value is not None:
                try:
                    density = float(str(density_value).strip().removesuffix("%"))
                except ValueError:
                    report["errors"].append(
                        "Bambu sparse_infill_density must be a numeric percentage."
                    )
                else:
                    if not 0.0 <= density <= 100.0:
                        report["errors"].append(
                            "Bambu sparse_infill_density must be between 0% and 100%."
                        )
                    if density == 100.0:
                        report["errors"].append(
                            "Bambu 100% sparse infill is not portable across Studio versions; "
                            "use solid top/bottom shell layers instead."
                        )

        gcode_pattern = re.compile(r"^Metadata/plate_(\d+)\.gcode$")
        json_pattern = re.compile(r"^Metadata/plate_(\d+)\.json$")
        gcode_plates = {
            match.group(1): name
            for name in names
            if (match := gcode_pattern.match(name)) is not None
        }
        json_plates = {
            match.group(1)
            for name in names
            if (match := json_pattern.match(name)) is not None
        }
        if require_sliced:
            if "Metadata/slice_info.config" not in names:
                report["errors"].append("Sliced 3MF is missing Metadata/slice_info.config.")
            if not gcode_plates:
                report["errors"].append("Sliced 3MF has no Metadata/plate_N.gcode part.")
            for plate, gcode_name in gcode_plates.items():
                if plate not in json_plates:
                    report["errors"].append(
                        f"Sliced plate {plate} has G-code but no matching plate_{plate}.json."
                    )
                if archive.getinfo(gcode_name).file_size < 1024:
                    report["errors"].append(
                        f"Sliced plate {plate} G-code is unexpectedly small (<1024 bytes)."
                    )

        report["metrics"] = {
            "unit": unit,
            "mesh_objects": len(object_reports),
            "triangles": sum(item["triangles"] for item in object_reports),
            "vertices": sum(item["vertices"] for item in object_reports),
            "bounds_mm": {"min": minimum, "max": maximum},
            "dimensions_mm": dimensions,
            "boundary_edges": sum(item["boundary_edges"] for item in object_reports),
            "nonmanifold_edges": sum(item["nonmanifold_edges"] for item in object_reports),
            "orientation_conflicts": sum(
                item["orientation_conflicts"] for item in object_reports
            ),
            "degenerate_triangles": sum(
                item["degenerate_triangles"] for item in object_reports
            ),
            "signed_volume_mm3": sum(
                item["signed_volume_mm3"] * unit_scale**3 for item in object_reports
            ),
            "has_bambu_settings": has_bambu_settings,
            "gcode_plates": len(gcode_plates),
            "archive_entries": len(infos),
            "uncompressed_bytes": total_uncompressed,
        }

    report["warnings"].append(
        "Structural/package validation does not replace Bambu Studio Preview: inspect layers, "
        "first-layer contact, thin walls, supports, seams, bridges, material mapping, and collisions."
    )
    return _finish(report)


def validate_path(
    path: str | Path,
    *,
    max_dimensions_mm: tuple[float, float, float] | None = None,
    require_millimeter: bool = True,
    require_bambu_settings: bool = False,
    require_sliced: bool = False,
    max_file_mb: float = DEFAULT_MAX_FILE_MB,
) -> dict:
    input_path = Path(path)
    suffix = input_path.suffix.lower()
    file_format = "3mf" if suffix == ".3mf" else "stl" if suffix == ".stl" else "unknown"
    report = _new_report(input_path, file_format)
    try:
        if not math.isfinite(max_file_mb) or max_file_mb <= 0:
            raise ValidationInputError("max_file_mb must be a positive finite number.")
        if max_dimensions_mm is not None and (
            len(max_dimensions_mm) != 3
            or any(not math.isfinite(value) or value <= 0 for value in max_dimensions_mm)
        ):
            raise ValidationInputError(
                "max_dimensions_mm must contain three positive finite millimeter values."
            )
        if not input_path.is_file():
            raise ValidationInputError("Input path is not a readable file.")
        max_file_bytes = int(max_file_mb * 1024 * 1024)
        if suffix == ".stl":
            if require_bambu_settings or require_sliced:
                raise ValidationInputError(
                    "Bambu settings and sliced-output requirements apply only to 3MF files."
                )
            return validate_stl(
                input_path,
                max_dimensions_mm=max_dimensions_mm,
                max_file_bytes=max_file_bytes,
            )
        if suffix == ".3mf":
            if max_dimensions_mm is not None:
                report["warnings"].append(
                    "Build-volume limits are not applied to 3MF because build-item transforms "
                    "are outside this validator's structural scope."
                )
            result = validate_3mf(
                input_path,
                require_millimeter=require_millimeter,
                require_bambu_settings=require_bambu_settings,
                require_sliced=require_sliced,
                max_file_bytes=max_file_bytes,
            )
            result["warnings"] = report["warnings"] + result["warnings"]
            return _finish(result)
        raise ValidationInputError("Supported file extensions are .stl and .3mf.")
    except (OSError, ValidationInputError, zipfile.BadZipFile, struct.error) as error:
        report["errors"].append(str(error))
        return _finish(report)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate STL/3MF structure before a reviewed Bambu Studio workflow."
    )
    parser.add_argument("model", type=Path, help="Path to an .stl or .3mf file")
    parser.add_argument(
        "--max-dimensions",
        nargs=3,
        type=float,
        metavar=("X_MM", "Y_MM", "Z_MM"),
        help="Fail an STL whose axis-aligned dimensions exceed these millimeter limits",
    )
    parser.add_argument(
        "--allow-non-millimeter",
        action="store_true",
        help="Allow a 3MF with an explicit supported unit other than millimeter",
    )
    parser.add_argument(
        "--require-bambu-settings",
        action="store_true",
        help="Require Bambu model and project settings in a 3MF",
    )
    parser.add_argument(
        "--require-sliced",
        action="store_true",
        help="Require Bambu settings, slice metadata, and nontrivial per-plate G-code",
    )
    parser.add_argument(
        "--max-file-mb",
        type=float,
        default=DEFAULT_MAX_FILE_MB,
        help=f"Maximum input and uncompressed archive size (default: {DEFAULT_MAX_FILE_MB:g} MiB)",
    )
    parser.add_argument("--json", action="store_true", help="Print the complete JSON report")
    return parser


def _print_human(report: dict) -> None:
    print(f"{report['status']}: {report['path']} ({report['format']})")
    metrics = report.get("metrics", {})
    if metrics:
        for key in (
            "dimensions_mm",
            "triangles",
            "vertices",
            "boundary_edges",
            "nonmanifold_edges",
            "orientation_conflicts",
            "degenerate_triangles",
            "has_bambu_settings",
            "gcode_plates",
        ):
            if key in metrics:
                print(f"  {key}: {metrics[key]}")
    for error in report["errors"]:
        print(f"  ERROR: {error}")
    for warning in report["warnings"]:
        print(f"  WARN: {warning}")


def main(argv: Iterable[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    dimensions = tuple(args.max_dimensions) if args.max_dimensions else None
    report = validate_path(
        args.model,
        max_dimensions_mm=dimensions,
        require_millimeter=not args.allow_non_millimeter,
        require_bambu_settings=args.require_bambu_settings,
        require_sliced=args.require_sliced,
        max_file_mb=args.max_file_mb,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
