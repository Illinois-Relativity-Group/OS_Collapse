"""Render one full scene with the wave evaluated at the exact video time."""
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import plot_3d as renderer

args=sys.argv[sys.argv.index('--')+1:]
work=Path(args[0]).resolve();index=int(args[1])
plan=json.loads((work/'plan.json').read_text())
frame=plan['transition_state'] if index==len(plan['frames']) else plan['frames'][index]
os.environ.update(WAVE_M_ADM='1.0',GW_TIME_DECIMALS='0',GW_BACKDROP_ORIENT='floor',
                  RENDER_SAMPLES='16',RENDER_DENOISE='true',RENDER_PERCENT='50')
for name in ['WAVE_CAMERA','WAVE_SIDEVIEW_CUT','WAVE_HIDE_FIELD_LINES','GW_TIME_COLOR','GW_TIME_LABEL']:
    os.environ.pop(name,None)
original_label=renderer.create_time_label
renderer.create_time_label=lambda camera,time:original_label(camera,frame['label'])
renderer.read_time_from_fieldline=lambda path:frame['time']
step=frame['step']
target=work/'main_raw'/frame['file'];target.parent.mkdir(parents=True,exist_ok=True)
renderer.plot_3d(root_dir=str(ROOT),
    ply_path=str(ROOT/f'output/fieldline_ply/field_lines_{step:06d}.ply'),
    density_file=str(ROOT/f'output/rho_movie/rho_{step:08d}.png'),render_path=str(target),
    wave_file=plan.get('wave_source',{}).get('input',str(ROOT/'data/Test_OS_collapse_magnetized.wave_extraction.4')),
    field_line=str(ROOT/f'data/a_p_slice_15000_16_{step:08d}'),
    horizon_file=str(ROOT/'data/Test_OS_collapse_magnetized_15000_16.hor_surface'),
    plot_wave=True,hole_radius=plan['settings'].get('inner_radius',10.),height_scale=500000,r_max=220,NR=421,NPHI=320,radius=.04,value=2)
print(f'TEMPORAL_FRAME {index} wave_t={frame["time"]:.9f} source_t={frame["source_time"]:.9f}',flush=True)
