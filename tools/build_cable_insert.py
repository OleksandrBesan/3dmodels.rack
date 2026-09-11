"""Cable-friendly derivatives of the saved V1 blank; original files untouched.

Assembly axes: X across opening, Y through panel, Z vertical. Bottom-open
rounded slots allow the cap to slide down around an already installed cable.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
import trimesh
import build_support_footprint_3mf as package

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'models/cable_passthrough'
SOURCE = MODELS / 'PatchPanel_BLANKING_INSERT_V1.stl'
TEMPLATE = MODELS / 'PatchPanel_BLANKING_INSERT_V1.3mf'
CABLE_Z = -7.5


def stem(width):
    return f'PatchPanel_CABLE_INSERT_{width}MM_V1'


def load_blank():
    mesh = trimesh.load(SOURCE, force='mesh')
    mesh.apply_translation([0, 0, -6.9])
    mesh.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2, [1, 0, 0]))
    return mesh


def cable_probe(diameter, x=0):
    mesh = trimesh.creation.cylinder(radius=diameter/2, height=24, sections=96)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
    mesh.apply_translation([x, 0, CABLE_Z])
    return mesh


def make_insert(width):
    if width not in (8, 10):
        raise ValueError('Supported slot widths: 8 or 10 mm')
    blank = load_blank()
    # Rectangle extends below the cap and meets the semicircular crown.
    lower = blank.bounds[0, 2]-1
    entry = trimesh.creation.box(extents=[width, 24, CABLE_Z-lower])
    entry.apply_translation([0, 0, (CABLE_Z+lower)/2])
    cutter = trimesh.boolean.union([entry, cable_probe(width)], engine='manifold')
    result = trimesh.boolean.difference([blank, cutter], engine='manifold')
    if not result.is_volume or len(result.split()) != 1:
        raise ValueError('Cable cap must remain one closed solid')
    return result


def check_fit(cap, width):
    panel = trimesh.load(MODELS/'PatchPanel_TOP_ENTRY_12MM_V1.stl', force='mesh')
    panel.apply_translation([0, 0, -5])
    panel.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2, [1, 0, 0]))
    centers = json.loads((MODELS/'geometry_check.json').read_text())['hole_centers_x']
    maximum, panel_checks, cable_checks = 0.0, 0, 0
    # 1 mm diametral allowance. Tests prove clearance, not real cable flexibility.
    for center in centers:
        cable = cable_probe(width-1, center)
        overlap = abs(trimesh.boolean.intersection([panel, cable], engine='manifold').volume)
        maximum = max(maximum, overlap)
        for lift in (0, 2, 5, 10, 20, 40):
            placed = cap.copy()
            placed.apply_translation([center, 0, lift])
            for obstacle in (panel, cable):
                overlap = abs(trimesh.boolean.intersection([placed, obstacle], engine='manifold').volume)
                maximum = max(maximum, overlap)
            panel_checks += 1
            cable_checks += 1
    if maximum >= .001:
        raise ValueError(f'Insertion interference: {maximum} mm3')
    return dict(panel_checks=panel_checks, cable_checks=cable_checks,
                max_overlap_mm3=maximum, checked_cable_diameter_mm=width-1)


def project(mesh, path, name):
    with ZipFile(TEMPLATE) as archive:
        entries = {n: archive.read(n) for n in
                   ('[Content_Types].xml', '_rels/.rels', 'Metadata/project_settings.config')}
    entries['3D/3dmodel.model'] = package.build_model_xml(mesh.vertices, mesh.faces, name)
    entries['Metadata/model_settings.config'] = package.build_model_settings(name, len(mesh.faces))
    with ZipFile(path, 'w', ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


def preview(caps, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Circle
    fig, axes = plt.subplots(1, 3, figsize=(10, 6), constrained_layout=True)
    for ax, (title, cap, width) in zip(axes, [('Original solid blank', load_blank(), None),
                                          *[(f'{w} mm bottom-open slot', caps[w], w) for w in (8, 10)]]):
        ax.add_collection(PolyCollection(cap.triangles[:, :, [0, 2]], facecolor='#e9b83f', edgecolor='none'))
        if width:
            ax.add_patch(Circle((0, CABLE_Z), (width-1)/2, color='#424953'))
        ax.set(xlim=(-10, 10), ylim=(-16, 26), aspect='equal', title=title,
               xlabel='Width (mm)', ylabel='Height (mm)', facecolor='#eff2f5')
    fig.suptitle('Actual mesh front projections — cable cross-sections shown in grey\nSlide cap downward over cable; connector stays outside')
    fig.savefig(path, dpi=160)
    plt.close(fig)


def generate(output):
    output.mkdir(parents=True, exist_ok=True)
    caps, reports = {}, {}
    for width in (8, 10):
        cap = make_insert(width)
        caps[width] = cap
        report = check_fit(cap, width)
        mesh = cap.copy()
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
        mesh.apply_translation([0, 0, -mesh.bounds[0, 2]])
        mesh.export(output/f'{stem(width)}.stl')
        project(mesh, output/f'{stem(width)}.3mf', stem(width))
        report.update(slot_width_mm=width, print_dimensions_mm=mesh.extents.tolist(),
                      physically_tested=False, source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        reports[str(width)] = report
    (output/'cable_insert_geometry_check.json').write_text(json.dumps(reports, indent=2)+'\n')
    preview(caps, output/'cable_inserts.png')
    print(json.dumps(reports, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'.bambu-preflight/cable_insert/draft')
    generate(parser.parse_args().output)


if __name__ == '__main__':
    main()
