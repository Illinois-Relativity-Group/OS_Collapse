"""Render the existing star/eta scene in parallel Blender batches, then encode.

Each Blender worker is pinned to a disjoint CPU set. Existing PNGs are
validated and resumed; the job settings are saved to prevent mixed renders.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def coord_time(index):
    with (ROOT/'data'/f'a_p_slice_9000_16_{index:08d}').open() as stream:
        for line in stream:
            match = re.search(r'coord time\s+([-+0-9.eE]+)', line)
            if match:
                return float(match.group(1))
    raise ValueError(f'No coordinate time for {index}')


def valid_png(path):
    if not path.is_file():
        return False
    from PIL import Image
    try:
        with Image.open(path) as image:
            image.verify()
        return True
    except (OSError, SyntaxError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--end', type=int, default=25000)
    parser.add_argument('--step', type=int, default=10)
    parser.add_argument('--workers', type=int, default=5)
    parser.add_argument('--threads', type=int, default=6)
    parser.add_argument('--output', default='output/eta_movie_2501')
    args = parser.parse_args()
    out = (ROOT/args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    frames = out/'frames'
    frames.mkdir(exist_ok=True)
    indices = list(range(args.start, args.end+1, args.step))
    settings = dict(indices=indices, workers=args.workers, threads=args.threads,
                    samples=16, percent=50, denoise=True, wave_scale=10000, mass=1.00071,
                    wave_file='data/Test_OS_collapse_magnetized.wave_extraction.4')
    settings_file=out/'render_settings.json'
    if settings_file.exists() and json.loads(settings_file.read_text()) != settings:
        raise ValueError('Output settings differ; choose a new output directory')
    settings_file.write_text(json.dumps(settings,indent=2)+'\n')
    cpus=sorted(os.sched_getaffinity(0))[:args.workers*args.threads]
    if len(cpus)!=args.workers*args.threads:
        raise ValueError('Insufficient CPUs in affinity mask')
    # Check all required assets before launching the expensive render.
    for index in indices:
        for file in [ROOT/'data'/f'a_p_slice_9000_16_{index:08d}',
                     ROOT/'output/fieldline_ply'/f'field_lines_{index:06d}.ply',
                     ROOT/'output/rho_movie'/f'rho_{index:08d}.png']:
            if not file.is_file():
                raise FileNotFoundError(file)
    times=[coord_time(index) for index in indices]
    if any(b<=a for a,b in zip(times,times[1:])):
        raise ValueError('Frame coordinate times must strictly increase')
    env=dict(os.environ,PYTHONPATH=str(ROOT/'blender_py311_packages'),
             OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
             RENDER_SAMPLES='16',RENDER_PERCENT='50',RENDER_DENOISE='true',
             WAVE_M_ADM='1.00071',WAVE_RESTART_POLICY='latest')
    with (out/'diagnostics.log').open('w') as log:
        subprocess.run([sys.executable,str(ROOT/'wave_eta.py'),'--input',str(ROOT/settings['wave_file']),
                        '--mass','1.00071','--output',str(out/'diagnostics')],
                       env={k:v for k,v in env.items() if k!='PYTHONPATH'},check=True,stdout=log,stderr=subprocess.STDOUT)
    # These renders have the same scene, scale, samples, resolution and eta input.
    clip=ROOT/'output/eta_clip_t42/frames'
    for index in indices:
        dst=frames/f'render_{index:08d}.png'
        src=clip/dst.name
        if not dst.exists() and valid_png(src):
            shutil.copy2(src,dst)
    remaining=[i for i in indices if not valid_png(frames/f'render_{i:08d}.png')]
    print(f'{len(indices)} target frames; {len(indices)-len(remaining)} reused; {len(remaining)} to render',flush=True)
    print(f'{args.workers} workers x {args.threads} CPUs: {cpus}',flush=True)
    started=time.monotonic()
    batch_script=ROOT/'render_eta_batch.py'
    blender='/data/shared/Blender/Blender_5.0/blender-5.0.0-linux-x64/blender'
    def run_worker(slot):
        batch=remaining[slot::args.workers]
        jobs=out/f'worker_{slot}.json'
        jobs.write_text(json.dumps(dict(root=str(ROOT),frames=str(frames),indices=batch,threads=args.threads)))
        affinity=','.join(map(str,cpus[slot*args.threads:(slot+1)*args.threads]))
        with (out/f'worker_{slot}.log').open('w') as log:
            subprocess.run(['taskset','-c',affinity,blender,'-b','--python-exit-code','1',
                            '--python-use-system-env','-t',str(args.threads),'-P',str(batch_script),'--',str(jobs)],
                           cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        print(f'Worker {slot} finished {len(batch)} frames',flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(run_worker,i) for i in range(args.workers)]
        for future in as_completed(futures):
            future.result()
    for index in indices:
        if not valid_png(frames/f'render_{index:08d}.png'):
            raise RuntimeError(f'Missing or invalid frame {index}')
    # Existing pipeline: each 0.0090925 code-time interval plays for 1/200 s.
    # Use actual headers to preserve the cadence change and rounding precisely.
    code_time_per_second=0.0090925*200
    concat=out/'frames.ffconcat'
    lines=['ffconcat version 1.0']
    for i,index in enumerate(indices):
        dt=times[i+1]-times[i] if i+1<len(times) else times[-1]-times[-2]
        lines += [f"file 'frames/render_{index:08d}.png'",f'duration {dt/code_time_per_second:.12f}']
    lines.append(f"file 'frames/render_{indices[-1]:08d}.png'")
    concat.write_text('\n'.join(lines)+'\n')
    movie=out/'os_collapse_with_eta_waves.mp4'
    print('All frames verified. Encoding movie.',flush=True)
    subprocess.run(['ffmpeg','-y','-v','warning','-threads','6','-f','concat','-safe','0','-i',str(concat),
                    '-vf','fps=200,format=yuv420p','-c:v','libx264','-threads','6','-preset','fast',
                    '-crf','19','-movflags','+faststart',str(movie)],check=True)
    subprocess.run(['ffmpeg','-v','error','-threads','2','-i',str(movie),'-f','null','-'],check=True)
    report=dict(settings,frame_count=len(indices),time_start=times[0],time_end=times[-1],
                cpus=cpus,movie=str(movie),elapsed_seconds=time.monotonic()-started,
                movie_fps=200,code_time_per_playback_second=code_time_per_second,status='complete')
    (out/'movie_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Complete: {len(indices)} frames and {movie}',flush=True)


if __name__=='__main__':
    main()
