"""Build top-loading blank for the V1 cable panel. Same dependencies as build_top_entry.py."""
from pathlib import Path
import importlib.util
import json
import zipfile
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'models/cable_passthrough'
STEM = 'PatchPanel_BLANKING_INSERT_V1'

def box(bounds):
    bounds = np.array(bounds)
    mesh = trimesh.creation.box(extents=bounds[1] - bounds[0])
    mesh.apply_translation(bounds.mean(axis=0))
    return mesh

panel = trimesh.load(OUT / 'PatchPanel_TOP_ENTRY_12MM_V1.stl', force='mesh')
panel.apply_translation([0, 0, -5])
panel.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2, [1,0,0]))
centers = json.loads((OUT / 'geometry_check.json').read_text())['hole_centers_x']
bottom, top = -13.8, 24.125
front = box([[-8.4,-6.9,bottom],[8.4,-5.3,top]])
stem = box([[-5.7,-5.31,-11.9],[5.7,5.31,top]])
# A 45-degree rear flange grows from the stem: no horizontal support ledge.
points = [[x,y,z] for y,w in [(5.3,5.7),(8.0,8.4)] for x in [-w,w] for z in [bottom,top]]
rear = trimesh.convex.convex_hull(points)
stop = box([[-8.4,-6.9,22.525],[8.4,8.0,top]])
insert = trimesh.boolean.union([front, stem, rear, stop], engine='manifold')
assert insert.is_volume and len(insert.split()) == 1
for center in centers:
    for lift in [0,2,5,10,20,40]:
        probe = insert.copy(); probe.apply_translation([center,0,lift])
        overlap = trimesh.boolean.intersection([panel,probe], engine='manifold')
        assert abs(overlap.volume) < 0.001, (center,lift,overlap.volume)

fig, axes = plt.subplots(2,1,figsize=(14,6),constrained_layout=True)
for ax in axes:
    ax.add_collection(PolyCollection(panel.triangles[:,:,[0,2]],facecolor='#dcae36',edgecolor='none'))
    ax.set(xlim=(-132,132),ylim=(-27,28),aspect='equal',xlabel='mm',facecolor='#303640')
for i in [0,1,4,7,8,9,11]:
    placed=insert.copy();placed.apply_translation([centers[i],0,0])
    axes[1].add_collection(PolyCollection(placed.triangles[:,:,[0,2]],facecolor='#80b9d9',edgecolor='none'))
axes[0].set_title('Existing panel')
axes[1].set_title('Example: seven removable blanks installed (blue)')
fig.savefig(ROOT / 'docs/previews/blanking_inserts.png',dpi=150)

insert.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]))
insert.apply_translation([0,0,-insert.bounds[0,2]])
insert.export(OUT / f'{STEM}.stl')
spec=importlib.util.spec_from_file_location('helper',ROOT/'tools/build_support_footprint_3mf.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
with zipfile.ZipFile(OUT / 'PatchPanel_TOP_ENTRY_12MM_V1.3mf') as archive:
    payloads={name:archive.read(name) for name in ['[Content_Types].xml','_rels/.rels','Metadata/project_settings.config']}
payloads['3D/3dmodel.model']=helper.build_model_xml(insert.vertices,insert.faces,STEM)
payloads['Metadata/model_settings.config']=helper.build_model_settings(STEM,len(insert.faces))
with zipfile.ZipFile(OUT/f'{STEM}.3mf','w',zipfile.ZIP_DEFLATED) as archive:
    for name,data in payloads.items():archive.writestr(name,data)
report={'single_connected_solid':True,'entry_stem_width_mm':11.4,'panel_channel_depth_mm':10.6,'cover_width_mm':16.8,'clearance_each_side_mm':0.3,'top_protrusion_mm':1.9,'collision_checks':72,'print_dimensions_mm':insert.extents.tolist(),'physically_tested':False}
(OUT/'blanking_geometry_check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
