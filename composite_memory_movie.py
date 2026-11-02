"""Recompose the latest original-view movie with a labeled memory comparison."""
import argparse
import json
from pathlib import Path

from PIL import Image

from memory_alignment import MemoryComparison, MemoryInset
from overlay_wave_1d_full_movie import coordinate_time
from wave_eta import tortoise_radius

ROOT = Path(__file__).resolve().parent


def smooth(x):
    x = max(0., min(1., x))
    return x*x*(3-2*x)


def ease(x):
    x = max(0., min(1., x))
    return x*x*x*(10+x*(-15+6*x))


def load(path):
    with Image.open(path) as im:
        return im.convert('RGBA').resize((960,540),Image.Resampling.LANCZOS)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,default=ROOT/'output/movie_amp500000_integer_time')
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--alignment',choices=['physical'],default='physical')
    parser.add_argument('--worker',type=int,default=0)
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--preview',action='store_true')
    parser.add_argument('--temporal',action='store_true',help='Compose only a fresh temporal run transition')
    args=parser.parse_args()
    if not 0<=args.worker<args.workers: raise ValueError('Invalid worker')
    base,work=args.base.resolve(),args.work.resolve()
    model=MemoryComparison.from_work(work) if args.temporal else MemoryComparison()
    inset=MemoryInset(model,args.alignment)
    main_out=work/'main_with_memory';main_out.mkdir(parents=True,exist_ok=True)
    trans_out=work/'transition_with_memory';trans_out.mkdir(exist_ok=True)
    delay=float(tortoise_radius(10.,1.))
    steps=[20900,34400] if args.preview else list(range(0,34401,100))
    if args.temporal:steps=[]
    for step in steps[args.worker::args.workers]:
        scene=load(base/'images'/f'render_{step:08d}.png')
        current=coordinate_time(ROOT/'data'/f'a_p_slice_15000_16_{step:08d}')-delay
        overlay=inset.draw(current,width=365)
        scene.alpha_composite(overlay,(5,540-overlay.height-19))
        scene.convert('RGB').save(main_out/f'render_{step:08d}.png')
        print(f'MAIN {step}',flush=True)
    if args.temporal:
        plan=json.loads((work/'plan.json').read_text())
        last=plan.get('transition_state',plan['frames'][-1])
        normal=load(work/'main_raw'/last['file'])
        raw=work/'cylinder_wall_wider_movie_raw'
    else:
        normal=load(base/'images/render_00034400.png')
        raw=base/'cylinder_wall_wider_movie_raw'
    cut_white=load(raw/'cut_white_label.png')
    cut_black=load(raw/'frame_0000.png')
    indices=[599] if args.preview else list(range(600))
    cache={}
    for i in indices[args.worker::args.workers]:
        gain=1.
        if i<30: scene=normal.copy()
        elif i<90: scene=Image.blend(normal,cut_white,smooth((i-30)/59))
        elif i<120: scene=cut_black.copy()
        else:
            raw_index=min(i-119,420)
            scene=load(raw/f'frame_{raw_index:04d}.png')
            gain=30**ease((raw_index-240)/180)
        colour='white' if i<90 else 'black'
        key=(colour,round(gain,12))
        if key not in cache:
            cache[key]=inset.draw(model.endpoint,gain=gain,colour=colour,width=365)
        overlay=cache[key]
        scene.alpha_composite(overlay,(5,540-overlay.height-19))
        scene.convert('RGB').save(trans_out/f'frame_{i:04d}.png')
        if i%30==0 or i==599:print(f'TRANSITION {i}',flush=True)
    inset.close()


if __name__=='__main__':
    main()
