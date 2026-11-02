"""Render fresh scenes, then apply the user's memory inset at each video time."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from PIL import Image

from memory_alignment import MemoryComparison, MemoryInset
from wave_eta import tortoise_radius

ROOT=Path(__file__).resolve().parent


def valid(path):
    try:
        with Image.open(path) as im:
            if im.size != (960,540):return False
            im.verify()
        return True
    except (OSError,ValueError):return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=ROOT/'output/movie_amp500000_integer_time/temporal_8_tM')
    parser.add_argument('--worker',type=int,default=0)
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--only',type=int,help='render a single planned frame for validation')
    parser.add_argument('--recompose-only',action='store_true',help='Replace insets using existing raw frames; never render 3D')
    parser.add_argument('--frame-start',type=int,default=0)
    parser.add_argument('--frame-stop',type=int,help='Exclusive end of a contiguous frame range')
    args=parser.parse_args();work=args.work.resolve()
    plan=json.loads((work/'plan.json').read_text())
    if not 0<=args.worker<args.workers:raise ValueError('Invalid worker')
    all_frames=plan['frames']+([plan['transition_state']] if 'transition_state' in plan else [])
    selected=all_frames[args.frame_start:args.frame_stop]
    tasks=selected[args.worker::args.workers] if args.only is None else [all_frames[args.only]]
    raw=work/'main_raw';raw.mkdir(exist_ok=True)
    out=work/'main_with_memory';out.mkdir(exist_ok=True)
    logs=work/'logs';logs.mkdir(exist_ok=True)
    model=MemoryComparison.from_work(work);inset=MemoryInset(model)
    delay=float(tortoise_radius(plan['settings'].get('inner_radius',10.),1.))
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'blender_packages')
    threads=os.environ.get('RENDER_THREADS','2')
    for frame in tasks:
        target=out/frame['file']
        if valid(target) and not args.recompose_only:continue
        source=raw/frame['file']
        if args.recompose_only and not valid(source):
            raise FileNotFoundError(f'Missing or invalid raw frame: {source}')
        if not valid(source):
            for path in [ROOT/f'output/fieldline_ply/field_lines_{frame["step"]:06d}.ply',
                         ROOT/f'output/rho_movie/rho_{frame["step"]:08d}.png']:
                if not path.is_file():raise FileNotFoundError(path)
            with (logs/f'render_{args.worker}.log').open('a') as stream:
                subprocess.run([str(ROOT/'blender/blender'),'-b','--python-exit-code','1',
                                '--python-use-system-env','-t',threads,'-P',str(ROOT/'render_temporal_frame.py'),
                                '--',str(work),str(frame['frame'])],cwd=ROOT,env=env,
                               stdout=stream,stderr=subprocess.STDOUT,check=True)
        if not valid(source):raise RuntimeError(f'Invalid render: {source}')
        with Image.open(source) as im:scene=im.convert('RGBA')
        overlay=inset.draw(frame['time']-delay,width=365)
        scene.alpha_composite(overlay,(5,540-overlay.height-19))
        scene.convert('RGB').save(target)
        print(f'COMPLETED {frame["frame"]}/{len(all_frames)-1} t={frame["time"]:.6f}',flush=True)
    inset.close()


if __name__=='__main__':main()
