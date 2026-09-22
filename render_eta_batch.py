"""Blender worker: retain Python imports between frames, reset scene each time."""
import json
from pathlib import Path
import sys
import time

jobs=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
root=Path(jobs['root'])
sys.path.insert(0,str(root))
import bpy
import plot_3d

original_setup=plot_3d.setup_render
def setup_render(path,plot_wave=False):
    original_setup(path,plot_wave)
    bpy.context.scene.render.threads_mode='FIXED'
    bpy.context.scene.render.threads=jobs['threads']
plot_3d.setup_render=setup_render

for number,index in enumerate(jobs['indices'],1):
    start=time.monotonic()
    plot_3d.plot_3d(
        root_dir=str(root),
        ply_path=str(root/'output/fieldline_ply'/f'field_lines_{index:06d}.ply'),
        density_file=str(root/'output/rho_movie'/f'rho_{index:08d}.png'),
        render_path=str(Path(jobs['frames'])/f'render_{index:08d}.png'),
        wave_file=str(root/'data/Test_OS_collapse_magnetized.wave_extraction.4'),
        field_line=str(root/'data'/f'a_p_slice_9000_16_{index:08d}'),
        horizon_file=str(root/'data/Test_OS_collapse_magnetized_9000_16.hor_surface'),
        save_blender=False,radius=0.04,value=2,plot_wave=True,
        hole_radius=10,height_scale=10000,time_per_frame=1,r_max=220,NR=220,NPHI=160)
    print(f'FRAME_DONE {index} {number}/{len(jobs["indices"])} {time.monotonic()-start:.2f}s',flush=True)
