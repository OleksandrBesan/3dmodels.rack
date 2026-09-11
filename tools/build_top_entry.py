"""Local BY-NC-SA remix of Dawnchaser's MakerWorld 576762 blank panel.

Run: uv run --python 3.12 --with 'trimesh[easy]' --with manifold3d --with matplotlib tools/build_top_entry.py
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'models/cable_passthrough'
SOURCE = ROOT / 'tools/sources/cable_panel_blank.stl'
STEM = 'PatchPanel_TOP_ENTRY_12MM_V1'
NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

def main():
    # Preserved unnumbered source mesh; rebuilding needs no Downloads files.
    source = trimesh.load(SOURCE, force='mesh', process=True)
    assert source.is_watertight and source.is_volume
    section = source.section(plane_normal=[0, 1, 0], plane_origin=[0, -4, 0])
    holes = sorted([p for p in section.discrete if 14 < np.ptp(p[:, 0]) < 16], key=lambda p: p[:, 0].min())
    assert len(holes) == 12
    cutters = []
    centers = []
    for hole in holes:
        center = (hole[:, 0].min() + hole[:, 0].max()) / 2
        centers.append(float(center))
        cutter = trimesh.creation.box(extents=[12, 14, 35])
        cutter.apply_translation([center, 0, 7.5])  # z=-10..25: overlaps every original opening.
        cutters.append(cutter)
    result = trimesh.boolean.difference([source, *cutters], engine='manifold')
    assert result.is_volume and len(result.split()) == 1
    assert np.allclose(result.bounds, source.bounds, atol=1e-4)
    assert result.volume < source.volume
    # Verify clear 12mm entry channels and unchanged mounting-ear geometry.
    for cutter in cutters:
        assert trimesh.boolean.intersection([result, cutter], engine='manifold').volume < 1e-4
    for x in [-120, 120]:
        ear = trimesh.creation.box(extents=[20, 20, 60]); ear.apply_translation([x, 0, 0])
        before = trimesh.boolean.intersection([source, ear], engine='manifold')
        after = trimesh.boolean.intersection([result, ear], engine='manifold')
        assert abs(before.volume - after.volume) < 0.01
    fig, axes = plt.subplots(2, 1, figsize=(15, 6), constrained_layout=True)
    for ax, mesh, title in zip(axes, [source, result], ['Original keystone panel', '12 mm top entries — lower cable bodies in from above']):
        # Front projection of actual mesh faces, not a conceptual illustration.
        polygons = mesh.triangles[:, :, [0, 2]]
        ax.add_collection(PolyCollection(polygons, facecolor='#e9b83f', edgecolor='none'))
        ax.set(xlim=(-132,132), ylim=(-26,29), aspect='equal', title=title, xlabel='mm')
        ax.set_facecolor('#303640')
    fig.savefig(ROOT / 'docs/previews/cable_panel.png', dpi=160)
    # Broad original front face lies on the bed; rotate diagonally for clearance.
    result.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1,0,0]))
    result.apply_translation([0,0,-result.bounds[0,2]])
    result.export(OUT / f'{STEM}.stl')
    result.apply_transform(trimesh.transformations.rotation_matrix(np.pi/4, [0,0,1]))
    spec = importlib.util.spec_from_file_location('package_helper', ROOT / 'tools/build_support_footprint_3mf.py')
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    template = OUT / f'{STEM}.3mf'
    with zipfile.ZipFile(template) as archive:
        settings = json.loads(archive.read('Metadata/project_settings.config'))
        settings.update(enable_support='0', brim_type='no_brim', wall_loops='3')
        payloads = {n: archive.read(n) for n in ['[Content_Types].xml', '_rels/.rels']}
    payloads['3D/3dmodel.model'] = helper.build_model_xml(result.vertices, result.faces, STEM)
    payloads['Metadata/model_settings.config'] = helper.build_model_settings(STEM, len(result.faces))
    payloads['Metadata/project_settings.config'] = json.dumps(settings).encode()
    with zipfile.ZipFile(OUT / f'{STEM}.3mf', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in payloads.items(): archive.writestr(name, data)
    report = dict(source_stl_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), original_3mf_sha256='a531269ccd99ebe45387a693077d8090a4a7d785b61f998bcf618c4f568754a9', dimensions_mm=source.extents.tolist(), entry_width_mm=12, hole_centers_x=centers, connected_solids=1, mounting_ears_unchanged=True, original_volume=source.volume, modified_volume=result.volume, plate_extents_mm=result.extents.tolist())
    (OUT / 'geometry_check.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
