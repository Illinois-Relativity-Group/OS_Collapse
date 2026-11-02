"""Render an independent frame chunk on a small Slurm shared-node allocation."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image

ROOT=Path(__file__).resolve().parent


def valid_image(path):
    try:
        with Image.open(path) as im:
            if im.size!=(960,540):return False
            im.verify()
        return True
    except (OSError,ValueError):return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--chunk',type=int,required=True)
    parser.add_argument('--chunks',type=int,required=True)
    args=parser.parse_args()
    if not 0<=args.chunk<args.chunks:raise ValueError('Invalid chunk index')
    work=args.work.resolve();plan=json.loads((work/'plan.json').read_text())
    frames=plan['frames']+([plan['transition_state']] if 'transition_state' in plan else [])
    size=math.ceil(len(frames)/args.chunks)
    start=args.chunk*size;stop=min(start+size,len(frames))
    chunk_dir=work/'chunks'/f'{args.chunk:03d}';chunk_dir.mkdir(parents=True,exist_ok=True)
    status=chunk_dir/'status'
    source=Path(plan['wave_source']['input'])
    if hashlib.sha256(source.read_bytes()).hexdigest()!=plan['wave_source']['sha256']:
        raise ValueError('Extraction source changed')
    env=os.environ.copy();env.pop('PYTHONPATH',None)
    env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
               WAVE_ALLOW_OFF_RECORD='false',MOVIE_OUTPUT_DIR=str(work),GW_TIME_DECIMALS='0')
    threads=int(env.get('SLURM_CPUS_PER_TASK','2'))
    env['RENDER_THREADS']=str(threads)
    endpoint=plan.get('transition_state',plan['frames'][-1])
    steps=sorted({f['step'] for f in frames[start:stop]}|{endpoint['step']})
    def run(command):
        subprocess.run(command,cwd=ROOT,env=env,check=True)
    try:
        status.write_text('PREPARING\n')
        for script,flag,subdir,pattern in [
            ('generate_field_lines.py','--a-dir','fieldline_ply','field_lines_{:06d}.ply'),
            ('plot_rho.py','--rho-dir','rho_movie','rho_{:08d}.png')]:
            destination=ROOT/'output'/subdir
            missing=[s for s in steps if not (destination/pattern.format(s)).is_file()]
            if not missing:continue
            step_file=chunk_dir/f'{subdir}_steps.txt'
            step_file.write_text('\n'.join(map(str,missing))+'\n')
            staging=chunk_dir/subdir;staging.mkdir(exist_ok=True)
            # A timed-out chunk can leave an unfinished staged file. Never
            # publish or reuse it; shared caches are populated only atomically.
            for step in missing:
                (staging/pattern.format(step)).unlink(missing_ok=True)
            run([sys.executable,str(ROOT/script),flag,str(ROOT/'data'),
                 '--out-dir',str(staging),'--stride','10','--steps-file',str(step_file)])
            for step in missing:
                os.replace(staging/pattern.format(step),destination/pattern.format(step))
        status.write_text('RENDERING_MAIN\n')
        run([sys.executable,str(ROOT/'temporal_movie_worker.py'),'--work',str(work),
             '--frame-start',str(start),'--frame-stop',str(stop)])
        status.write_text('RENDERING_TRANSITION\n')
        raw=work/'cylinder_wall_wider_movie_raw';raw.mkdir(exist_ok=True)
        for i in range(args.chunk,421,args.chunks):
            path=raw/f'frame_{i:04d}.png'
            if path.exists() and not valid_image(path):path.unlink()
        if args.chunk==0 and not valid_image(raw/'cut_white_label.png'):
            (raw/'frame_0000.png').unlink(missing_ok=True)
        env['PYTHONPATH']=str(ROOT/'blender_packages')
        run([str(ROOT/'blender/blender'),'-b','--python-exit-code','1',
             '--python-use-system-env','-t',str(threads),'-P',str(ROOT/'render_transition.py'),
             '--',str(args.chunk),str(args.chunks)])
        for frame in frames[start:stop]:
            if not valid_image(work/'main_with_memory'/frame['file']):
                raise RuntimeError(f'Invalid completed frame: {frame["file"]}')
        for i in range(args.chunk,421,args.chunks):
            if not valid_image(raw/f'frame_{i:04d}.png'):raise RuntimeError(f'Invalid transition {i}')
        status.write_text('COMPLETE\n')
        print(f'CHUNK COMPLETE {args.chunk}/{args.chunks}; frames {start}..{stop-1}',flush=True)
    except BaseException:
        status.write_text('FAILED\n')
        raise


if __name__=='__main__':main()
