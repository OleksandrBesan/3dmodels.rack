from __future__ import annotations

import importlib.util
import json
import math
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "validate_model.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_model", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def tetrahedron(outward: bool = True):
    vertices = (
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    faces = ((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3))
    if not outward:
        faces = tuple((a, c, b) for a, b, c in faces)
    return vertices, faces


def write_binary_stl(path: Path, vertices, faces, *, declared_count=None):
    payload = bytearray(b"test mesh".ljust(80, b"\0"))
    count = len(faces) if declared_count is None else declared_count
    payload.extend(struct.pack("<I", count))
    for face in faces:
        payload.extend(struct.pack("<3f", 0.0, 0.0, 0.0))
        for index in face:
            payload.extend(struct.pack("<3f", *vertices[index]))
        payload.extend(struct.pack("<H", 0))
    path.write_bytes(payload)


def write_ascii_stl(path: Path, vertices, faces):
    lines = ["solid tetrahedron"]
    for face in faces:
        lines.extend(["  facet normal 0 0 0", "    outer loop"])
        lines.extend(
            f"      vertex {vertices[index][0]} {vertices[index][1]} {vertices[index][2]}"
            for index in face
        )
        lines.extend(["    endloop", "  endfacet"])
    lines.append("endsolid tetrahedron")
    path.write_text("\n".join(lines), encoding="ascii")


def model_xml(vertices, faces, *, unit="millimeter"):
    vertex_xml = "".join(
        f'<vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in vertices
    )
    triangle_xml = "".join(
        f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in faces
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<model unit="{unit}" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        '<resources><object id="1" type="model"><mesh>'
        f'<vertices>{vertex_xml}</vertices><triangles>{triangle_xml}</triangles>'
        '</mesh></object></resources><build><item objectid="1"/></build></model>'
    ).encode("utf-8")


def write_3mf(
    path: Path,
    vertices,
    faces,
    *,
    unit="millimeter",
    bambu=False,
    sliced=False,
    extra_entries=None,
):
    entries = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
            '</Types>'
        ).encode("utf-8"),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            '</Relationships>'
        ).encode("utf-8"),
        "3D/3dmodel.model": model_xml(vertices, faces, unit=unit),
    }
    if bambu:
        entries.update(
            {
                "Metadata/model_settings.config": b"<config/>",
                "Metadata/project_settings.config": b"{}",
            }
        )
    if sliced:
        entries.update(
            {
                "Metadata/slice_info.config": b"<config/>",
                "Metadata/plate_1.json": b"{}",
                "Metadata/plate_1.gcode": b"; generated test gcode\n" + b"G1 X1 Y1\n" * 160,
            }
        )
    if extra_entries:
        entries.update(extra_entries)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, contents in entries.items():
            archive.writestr(name, contents)


class ValidateModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_validator()

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.vertices, self.faces = tetrahedron()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_binary_stl_closed_outward_mesh_passes_with_unit_warning(self):
        path = self.root / "tetra.stl"
        write_binary_stl(path, self.vertices, self.faces)

        report = self.validator.validate_path(path)

        self.assertTrue(report["valid"])
        self.assertEqual(report["status"], "WARN")
        self.assertEqual(report["metrics"]["triangles"], 4)
        self.assertEqual(report["metrics"]["boundary_edges"], 0)
        self.assertAlmostEqual(report["metrics"]["signed_volume_mm3"], 1 / 6)
        self.assertTrue(any("unitless" in warning.lower() for warning in report["warnings"]))

    def test_ascii_stl_is_supported(self):
        path = self.root / "tetra-ascii.stl"
        write_ascii_stl(path, self.vertices, self.faces)

        report = self.validator.validate_path(path)

        self.assertTrue(report["valid"])
        self.assertEqual(report["metrics"]["encoding"], "ascii")

    def test_open_stl_fails_on_boundary_edges(self):
        path = self.root / "open.stl"
        write_binary_stl(path, self.vertices, self.faces[:-1])

        report = self.validator.validate_path(path)

        self.assertFalse(report["valid"])
        self.assertGreater(report["metrics"]["boundary_edges"], 0)
        self.assertTrue(any("boundary" in error.lower() for error in report["errors"]))

    def test_reversed_stl_fails_on_negative_signed_volume(self):
        path = self.root / "reversed.stl"
        vertices, faces = tetrahedron(outward=False)
        write_binary_stl(path, vertices, faces)

        report = self.validator.validate_path(path)

        self.assertFalse(report["valid"])
        self.assertLess(report["metrics"]["signed_volume_mm3"], 0)
        self.assertTrue(any("inward" in error.lower() for error in report["errors"]))

    def test_degenerate_triangle_fails(self):
        path = self.root / "degenerate.stl"
        vertices = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0))
        write_binary_stl(path, vertices, ((0, 1, 2),))

        report = self.validator.validate_path(path)

        self.assertFalse(report["valid"])
        self.assertEqual(report["metrics"]["degenerate_triangles"], 1)

    def test_truncated_binary_stl_is_rejected(self):
        path = self.root / "truncated.stl"
        write_binary_stl(path, self.vertices, self.faces[:1], declared_count=4)

        report = self.validator.validate_path(path)

        self.assertFalse(report["valid"])
        self.assertTrue(any("length" in error.lower() for error in report["errors"]))

    def test_build_volume_limit_is_enforced(self):
        path = self.root / "large.stl"
        vertices = tuple((x * 300.0, y, z) for x, y, z in self.vertices)
        write_binary_stl(path, vertices, self.faces)

        report = self.validator.validate_path(path, max_dimensions_mm=(256.0, 256.0, 256.0))

        self.assertFalse(report["valid"])
        self.assertTrue(any("build volume" in error.lower() for error in report["errors"]))

    def test_core_3mf_with_millimeter_manifold_mesh_passes(self):
        path = self.root / "model.3mf"
        write_3mf(path, self.vertices, self.faces)

        report = self.validator.validate_path(path)

        self.assertTrue(report["valid"])
        self.assertEqual(report["metrics"]["unit"], "millimeter")
        self.assertEqual(report["metrics"]["mesh_objects"], 1)

    def test_non_millimeter_3mf_fails_by_default(self):
        path = self.root / "inch.3mf"
        write_3mf(path, self.vertices, self.faces, unit="inch")

        report = self.validator.validate_path(path)

        self.assertFalse(report["valid"])
        self.assertTrue(any("millimeter" in error.lower() for error in report["errors"]))

    def test_bad_3mf_triangle_index_fails(self):
        path = self.root / "bad-index.3mf"
        faces = self.faces[:-1] + ((1, 2, 99),)
        write_3mf(path, self.vertices, faces)

        report = self.validator.validate_path(path)

        self.assertFalse(report["valid"])
        self.assertTrue(any("index" in error.lower() for error in report["errors"]))

    def test_bambu_project_and_sliced_requirements(self):
        project = self.root / "project.3mf"
        sliced = self.root / "sliced.gcode.3mf"
        write_3mf(project, self.vertices, self.faces, bambu=True)
        write_3mf(sliced, self.vertices, self.faces, bambu=True, sliced=True)

        project_report = self.validator.validate_path(project, require_bambu_settings=True)
        unsliced_report = self.validator.validate_path(project, require_sliced=True)
        sliced_report = self.validator.validate_path(sliced, require_sliced=True)

        self.assertTrue(project_report["valid"])
        self.assertFalse(unsliced_report["valid"])
        self.assertTrue(sliced_report["valid"])
        self.assertEqual(sliced_report["metrics"]["gcode_plates"], 1)

    def test_bambu_full_sparse_infill_density_fails(self):
        path = self.root / "invalid-full-density.3mf"
        settings = {
            "sparse_infill_density": "100%",
            "sparse_infill_pattern": "rectilinear",
        }
        write_3mf(
            path,
            self.vertices,
            self.faces,
            bambu=True,
            extra_entries={
                "Metadata/project_settings.config": json.dumps(settings).encode("utf-8")
            },
        )

        report = self.validator.validate_path(path, require_bambu_settings=True)

        self.assertFalse(report["valid"])
        self.assertTrue(any("100%" in error for error in report["errors"]))

    def test_bambu_zero_infill_with_solid_shell_layers_passes(self):
        path = self.root / "valid-solid-shells.3mf"
        settings = {
            "sparse_infill_density": "0%",
            "sparse_infill_pattern": "grid",
            "bottom_shell_layers": "5",
            "top_shell_layers": "5",
        }
        write_3mf(
            path,
            self.vertices,
            self.faces,
            bambu=True,
            extra_entries={
                "Metadata/project_settings.config": json.dumps(settings).encode("utf-8")
            },
        )

        report = self.validator.validate_path(path, require_bambu_settings=True)

        self.assertTrue(report["valid"])

    def test_3mf_archive_traversal_entry_is_rejected(self):
        path = self.root / "traversal.3mf"
        write_3mf(
            path,
            self.vertices,
            self.faces,
            extra_entries={"../outside.txt": b"should never be extracted"},
        )

        report = self.validator.validate_path(path)

        self.assertFalse(report["valid"])
        self.assertTrue(any("unsafe" in error.lower() for error in report["errors"]))

    def test_mesh_analysis_rejects_empty_nonfinite_and_bad_options(self):
        metrics, errors = self.validator.analyze_triangles([])
        self.assertEqual(metrics["triangles"], 0)
        self.assertTrue(any("no triangles" in error.lower() for error in errors))

        nonfinite = (((0.0, 0.0, 0.0), (math.inf, 0.0, 0.0), (0.0, 1.0, 0.0)),)
        metrics, errors = self.validator.analyze_triangles(nonfinite)
        self.assertEqual(metrics["nonfinite_triangles"], 1)
        self.assertTrue(any("non-finite" in error.lower() for error in errors))

        with self.assertRaises(ValueError):
            self.validator.analyze_triangles([], topology_keys=[(0, 1, 2)])
        with self.assertRaises(ValueError):
            self.validator.analyze_triangles([], weld_tolerance=0)

    def test_mesh_analysis_detects_orientation_and_nonmanifold_edges(self):
        same_direction = (
            ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, -1.0, 0.0)),
        )
        metrics, errors = self.validator.analyze_triangles(same_direction)
        self.assertEqual(metrics["orientation_conflicts"], 1)
        self.assertTrue(any("orientation" in error.lower() for error in errors))

        third_triangle = (
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
        )
        metrics, errors = self.validator.analyze_triangles(same_direction + (third_triangle,))
        self.assertEqual(metrics["nonmanifold_edges"], 1)
        self.assertTrue(any("more than two" in error.lower() for error in errors))

    def test_path_and_size_input_guards(self):
        missing = self.validator.validate_path(self.root / "missing.stl")
        unsupported_path = self.root / "model.obj"
        unsupported_path.write_text("not an obj parser", encoding="utf-8")
        unsupported = self.validator.validate_path(unsupported_path)

        good_path = self.root / "limited.stl"
        write_binary_stl(good_path, self.vertices, self.faces)
        too_large = self.validator.validate_path(good_path, max_file_mb=0.000001)
        bad_limit = self.validator.validate_path(good_path, max_file_mb=0)
        bad_dimensions = self.validator.validate_path(
            good_path, max_dimensions_mm=(256.0, -1.0, 256.0)
        )
        wrong_requirement = self.validator.validate_path(
            good_path, require_bambu_settings=True
        )

        self.assertFalse(missing["valid"])
        self.assertFalse(unsupported["valid"])
        self.assertFalse(too_large["valid"])
        self.assertFalse(bad_limit["valid"])
        self.assertFalse(bad_dimensions["valid"])
        self.assertFalse(wrong_requirement["valid"])

    def test_malformed_stl_variants_are_rejected(self):
        too_short = self.root / "short.stl"
        too_short.write_bytes(b"not an stl")
        invalid_ascii = self.root / "invalid-ascii.stl"
        invalid_ascii.write_text("solid empty\nendsolid empty", encoding="ascii")
        invalid_encoding = self.root / "invalid-encoding.stl"
        invalid_encoding.write_bytes(b"solid \xff\xfe")

        reports = [
            self.validator.validate_path(too_short),
            self.validator.validate_path(invalid_ascii),
            self.validator.validate_path(invalid_encoding),
        ]

        self.assertTrue(all(not report["valid"] for report in reports))

    def test_3mf_package_and_xml_guards(self):
        missing_parts = self.root / "missing-parts.3mf"
        with zipfile.ZipFile(missing_parts, "w") as archive:
            archive.writestr("unrelated.txt", b"x")

        malformed = self.root / "malformed.3mf"
        write_3mf(
            malformed,
            self.vertices,
            self.faces,
            extra_entries={"3D/3dmodel.model": b"<model>"},
        )
        forbidden_dtd = self.root / "dtd.3mf"
        write_3mf(
            forbidden_dtd,
            self.vertices,
            self.faces,
            extra_entries={
                "3D/3dmodel.model": b'<!DOCTYPE model [<!ENTITY x "bad">]><model>&x;</model>'
            },
        )

        reports = [
            self.validator.validate_path(missing_parts),
            self.validator.validate_path(malformed),
            self.validator.validate_path(forbidden_dtd),
        ]

        self.assertTrue(all(not report["valid"] for report in reports))
        self.assertTrue(any("required" in error.lower() for error in reports[0]["errors"]))
        self.assertTrue(any("malformed" in error.lower() for error in reports[1]["errors"]))
        self.assertTrue(any("forbidden" in error.lower() for error in reports[2]["errors"]))

    def test_3mf_units_components_and_build_limit_warning(self):
        inch_path = self.root / "inch-allowed.3mf"
        write_3mf(inch_path, self.vertices, self.faces, unit="inch")
        inch_report = self.validator.validate_path(
            inch_path,
            require_millimeter=False,
            max_dimensions_mm=(256.0, 256.0, 256.0),
        )

        component_only = self.root / "component-only.3mf"
        component_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
            '<resources><object id="1" type="model"><components/></object></resources>'
            '<build><item objectid="1"/></build></model>'
        ).encode("utf-8")
        write_3mf(
            component_only,
            self.vertices,
            self.faces,
            extra_entries={"3D/3dmodel.model": component_xml},
        )
        component_report = self.validator.validate_path(component_only)

        unknown_unit = self.root / "unknown-unit.3mf"
        write_3mf(unknown_unit, self.vertices, self.faces, unit="parsec")
        unknown_report = self.validator.validate_path(
            unknown_unit, require_millimeter=False
        )

        self.assertTrue(inch_report["valid"])
        self.assertAlmostEqual(inch_report["metrics"]["dimensions_mm"][0], 25.4)
        self.assertTrue(any("not applied" in warning.lower() for warning in inch_report["warnings"]))
        self.assertFalse(component_report["valid"])
        self.assertTrue(any("no mesh" in error.lower() for error in component_report["errors"]))
        self.assertFalse(unknown_report["valid"])
        self.assertTrue(any("unsupported unit" in error.lower() for error in unknown_report["errors"]))

    def test_cli_human_output(self):
        path = self.root / "human.stl"
        write_binary_stl(path, self.vertices, self.faces)

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), str(path)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("WARN:", result.stdout)
        self.assertIn("dimensions_mm", result.stdout)

    def test_cli_json_and_exit_codes(self):
        good_path = self.root / "good.stl"
        bad_path = self.root / "bad.stl"
        write_binary_stl(good_path, self.vertices, self.faces)
        write_binary_stl(bad_path, self.vertices, self.faces[:-1])

        good = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), str(good_path), "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        bad = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), str(bad_path), "--json"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(good.returncode, 0)
        self.assertTrue(json.loads(good.stdout)["valid"])
        self.assertEqual(bad.returncode, 1)
        self.assertFalse(json.loads(bad.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
