"""Render actual camera-orbit and displacement frames; run inside Blender."""
from pathlib import Path
import os, sys, math
import bpy
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from process_label import set_render_label
set_render_label()
worker, workers = map(int,sys.argv[sys.argv.index('--')+1:])
OUT=ROOT/'output/cylinder_wall_wider_movie_raw'
OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(WAVE_M_ADM='1.0',WAVE_SIDEVIEW_CUT='false',WAVE_HIDE_FIELD_LINES='true',WAVE_CAMERA='',GW_TIME_COLOR='0,0,0',RENDER_SAMPLES='16',RENDER_DENOISE='true',GW_BACKDROP_ORIENT='floor')
# Build the existing renderer's scene once, without its immediate still render.
source=(ROOT/'plot_3d.py').read_text()
source=source.replace('    bpy.ops.render.render(write_still=True)','    pass # Render each animated frame below')
ns={'__name__':'transition_scene','__file__':str(ROOT/'plot_3d.py')}
exec(compile(source,str(ROOT/'plot_3d.py'),'exec'),ns)
ns['plot_3d'](root_dir=str(ROOT),ply_path=str(ROOT/'output/fieldline_ply/field_lines_034400.ply'),density_file=str(ROOT/'output/rho_movie/rho_00034400.png'),render_path=str(OUT/'init.png'),wave_file=str(ROOT/'data/Test_OS_collapse_magnetized.wave_extraction.4'),field_line=str(ROOT/'data/a_p_slice_15000_16_00034400'),horizon_file=str(ROOT/'data/Test_OS_collapse_magnetized_15000_16.hor_surface'),plot_wave=True,hole_radius=10,height_scale=100000,r_max=220,NR=421,NPHI=320,radius=.04,value=2)
# Match the approved sample: original radius-10 opening plus one half-plane cut.
import bmesh
cut_mesh=bpy.data.objects['GWPlane'].data
bm=bmesh.new(); bm.from_mesh(cut_mesh)
faces=[f for f in bm.faces if f.calc_center_median().y<0]
bmesh.ops.delete(bm,geom=faces,context='FACES')
bm.to_mesh(cut_mesh); bm.free(); cut_mesh.update()
# Stationary reference at unperturbed wave height: z = 0.
# The cut and reference are rotated together to expose x=0 toward -x.
curve=bpy.data.curves.new('HZeroDashes', 'CURVE')
curve.dimensions='3D'
curve.bevel_depth=0.07
curve.bevel_resolution=2
for x in np.arange(-220.,220.,3.0):
 spline=curve.splines.new('POLY'); spline.points.add(1)
 spline.points[0].co=(float(x),-0.2,0.,1.)
 spline.points[1].co=(float(min(x+1.8,220.)),-0.2,0.,1.)
reference=bpy.data.objects.new('h=0 reference',curve)
bpy.context.collection.objects.link(reference)
reference.visible_shadow=False
mat=bpy.data.materials.new('HZeroWhite'); mat.use_nodes=True
mat.node_tree.nodes.clear()
emission=mat.node_tree.nodes.new('ShaderNodeEmission')
emission.inputs['Color'].default_value=(1.,1.,1.,1.)
output=mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
mat.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
curve.materials.append(mat)
# Rotate the half-plane y>=0 to x>=0, leaving a cut in the y-z plane.
bpy.data.objects['GWPlane'].rotation_euler.z=-math.pi/2
reference.rotation_euler.z=-math.pi/2

scene=bpy.context.scene
scene.render.resolution_x=960; scene.render.resolution_y=540
scene.render.resolution_percentage=100
scene.render.threads_mode='FIXED'; scene.render.threads=1
scene.cycles.seed=42
cam=scene.camera
loc0=cam.location.copy(); q0=cam.rotation_euler.to_quaternion()
distance0=100.
target0=loc0 + q0 @ Vector((0,0,-distance0))
offset0=loc0-target0
az0=math.atan2(offset0.y,offset0.x); el0=math.asin(offset0.z/distance0)
target1=Vector((20,0,0))
# Keep perspective throughout, avoiding a perspective/orthographic projection jump.
distance1=1.50*90*cam.data.lens/cam.data.sensor_width
mesh=bpy.data.objects['GWPlane'].data
coords=np.empty(len(mesh.vertices)*3,dtype=np.float32)
mesh.vertices.foreach_get('co',coords); coords=coords.reshape(-1,3)
base_z=coords[:,2].copy()
# Inner display wall matches the approved cylindrical-cut sample.
inner_indices=sorted([v.index for v in mesh.vertices if abs(math.hypot(v.co.x,v.co.y)-10)<0.001],key=lambda j: math.atan2(coords[j,1],coords[j,0]))
assert len(inner_indices)>100
wall_coords=np.zeros((2*len(inner_indices),3),dtype=np.float32)
wall_coords[0::2]=coords[inner_indices]
wall_coords[1::2]=coords[inner_indices]
wall_coords[1::2,2]=0.
wall_mesh=bpy.data.meshes.new('InnerCylinderWall')
wall_mesh.from_pydata(wall_coords.tolist(),[],[(2*j,2*j+1,2*j+3,2*j+2) for j in range(len(inner_indices)-1)])
wall_mesh.update()
wall=bpy.data.objects.new('Inner cylindrical display wall',wall_mesh)
bpy.context.collection.objects.link(wall)
wall.rotation_euler=bpy.data.objects['GWPlane'].rotation_euler.copy()
wall.data.materials.append(bpy.data.materials['GWBackdropMaterial'])
wall.visible_shadow=False
back=bpy.data.objects.get('GWBackdrop')
def ease(x):
 x=min(1.,max(0.,x)); return x*x*x*(10+x*(-15+6*x))
for i in range(worker,421,workers):
 path=OUT/f'frame_{i:04d}.png'
 if path.exists(): continue
 p=ease(min(i,240)/240)
 a=az0+(-math.pi-az0)*p; e=el0*(1-p)
 target=target0.lerp(target1,p); dist=distance0+(distance1-distance0)*p
 cam.location=target+Vector((dist*math.cos(e)*math.cos(a),dist*math.cos(e)*math.sin(a),dist*math.sin(e)))
 if i>=240:
  cam.location=Vector((20-distance1,0.,0.))
  target=target1.copy()
  assert cam.location.y == 0. and cam.location.z == 0.
 cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 amp=ease((i-240)/180)
 coords[:,2]=base_z*10**(2*amp)
 mesh.vertices.foreach_set('co',coords.ravel()); mesh.update()
 # Follow the changing wave height exactly while keeping the other edge at z=0.
 wall_coords[0::2,2]=coords[inner_indices,2]
 wall_mesh.vertices.foreach_set('co',wall_coords.ravel());wall_mesh.update()
 if back:
  # Keep the background behind all visible geometry and the camera label.
  # A rotating 6000-unit floor/wall previously intersected the viewing volume.
  direction=(target-cam.location).normalized()
  back.location=cam.location+1000*direction
  back.rotation_euler=cam.rotation_euler.copy()
  assert (back.location-cam.location).dot(direction)>900
 if i==0:
  # Matching cut-reveal still with the previous white time label.
  label=bpy.data.materials['TimeLabelMaterial']
  emit=next(n for n in label.node_tree.nodes if n.type=='EMISSION')
  emit.inputs['Color'].default_value=(0.573,0.585,0.665,1.)
  scene.render.filepath=str(OUT/'cut_white_label.png')
  bpy.ops.render.render(write_still=True)
  emit.inputs['Color'].default_value=(0.,0.,0.,1.)
 set_render_label()
 scene.render.filepath=str(path)
 bpy.ops.render.render(write_still=True)
 print(f'ORBIT_FRAME {i}/420 gain={10**(2*amp):.6f}',flush=True)
