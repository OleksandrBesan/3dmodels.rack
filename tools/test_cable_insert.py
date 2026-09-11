"""Check cable-cap geometry against the saved blank and actual panel."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
import json

import numpy as np
import trimesh
import build_cable_insert as build


class CableInsertTest(unittest.TestCase):
    def test_unchanged_outer_fit_and_connected_solid(self):
        source = build.load_blank()
        for width in (8, 10):
            cap = build.make_insert(width)
            self.assertTrue(cap.is_volume)
            self.assertEqual(len(cap.split()), 1)
            np.testing.assert_allclose(cap.bounds, source.bounds, atol=1e-5)
            self.assertLess(cap.volume, source.volume)
            # No material may be added outside the original sliding envelope.
            added = trimesh.boolean.difference([cap, source], engine='manifold')
            self.assertLess(abs(added.volume), .001)

    def test_open_notch_and_original_upper_body(self):
        for width in (8, 10):
            cap = build.make_insert(width)
            probe = trimesh.creation.box(extents=[width-.02, 18, 6])
            probe.apply_translation([0, 0, -11])
            self.assertLess(abs(trimesh.boolean.intersection([cap, probe], engine='manifold').volume), .001)
            upper = trimesh.creation.box(extents=[20, 20, 24])
            upper.apply_translation([0, 0, 12])
            before = trimesh.boolean.intersection([build.load_blank(), upper], engine='manifold')
            after = trimesh.boolean.intersection([cap, upper], engine='manifold')
            self.assertAlmostEqual(before.volume, after.volume, places=3)

    def test_all_slots_and_cables_during_insertion(self):
        for width in (8, 10):
            report = build.check_fit(build.make_insert(width), width)
            self.assertEqual(report['panel_checks'], 72)
            self.assertEqual(report['cable_checks'], 72)
            self.assertLess(report['max_overlap_mm3'], .001)

    def test_invalid_width(self):
        for width in (0, 6, 12, float('nan')):
            with self.assertRaises(ValueError):
                build.make_insert(width)

    def test_export_preserves_original_and_project_settings(self):
        before = hashlib.sha256(build.SOURCE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix='rack-cable-cap-') as tmp:
            build.generate(Path(tmp))
            for width in (8, 10):
                stem = build.stem(width)
                mesh = trimesh.load(Path(tmp)/f'{stem}.stl')
                self.assertTrue(mesh.is_volume)
                self.assertAlmostEqual(mesh.bounds[0, 2], 0)
                with ZipFile(Path(tmp)/f'{stem}.3mf') as archive:
                    self.assertNotIn('Metadata/slice_info.config', archive.namelist())
                    settings = json.loads(archive.read('Metadata/project_settings.config'))
                    self.assertEqual(settings['enable_support'], '0')
                    self.assertIn(b'unit="millimeter"', archive.read('3D/3dmodel.model'))
        self.assertEqual(hashlib.sha256(build.SOURCE.read_bytes()).hexdigest(), before)


if __name__ == '__main__':
    unittest.main()
