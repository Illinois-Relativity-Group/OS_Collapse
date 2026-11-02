"""Prepare and run a complete, isolated movie from another GW extraction sphere."""
import argparse
import bisect
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

from memory_alignment import MemoryComparison
from overlay_wave_1d_full_movie import coordinate_time
from wave_eta import MODES, calc_Ylm, diagnostics, load_eta, source_retarded_times, tortoise_radius, wave_height

ROOT = Path(__file__).resolve().parent
DEFAULT_WORK = ROOT/'output/extraction_r500/temporal_8_tM'


def prepare(work, wave_file, retarded_end, coordinate_end=None, inner_radius=10.):
    work.mkdir(parents=True, exist_ok=True)
    if (work/'plan.json').exists():
        raise FileExistsError('Plan already exists; use run to resume or choose a new work directory')
    data = load_eta(wave_file, 'latest')
    source_u = source_retarded_times(data, 1.)
    delay = float(tortoise_radius(inner_radius, 1.))
    if coordinate_end is not None and coordinate_end-delay > source_u[-1]:
        raise ValueError(f't={coordinate_end:g} at inner radius {inner_radius:g} needs '
                         f'u={coordinate_end-delay:.6f}; source ends at {source_u[-1]:.6f}')
    samples = []
    for path in sorted((ROOT/'data').glob('a_p_slice_15000_16_*')):
        step = int(path.name.split('_')[-1])
        if coordinate_end is None and step > 34400:
            continue
        snapshot_time = coordinate_time(path)
        if coordinate_end is not None and snapshot_time > coordinate_end+1:
            break
        if not (ROOT/'data'/f'rho_0_slice_15000_16_{step:08d}').is_file():
            raise FileNotFoundError(f'Density snapshot {step}')
        samples.append((snapshot_time, step))
    times = [item[0] for item in samples]
    if not times or np.any(np.diff(times) <= 0):
        raise ValueError('Snapshot times must strictly increase')
    endpoint = (min(times[-1], source_u[-1]+delay, retarded_end+delay)
                if coordinate_end is None else coordinate_end)
    if endpoint > times[-1]:
        raise ValueError('Coordinate endpoint exceeds the available matter snapshots')
    if coordinate_end is not None and not math.isclose(endpoint*60/8, round(endpoint*60/8), abs_tol=1e-9):
        raise ValueError('Coordinate endpoint must coincide with a video frame at 8 t/M per second')
    frames = []
    for i in range(math.floor(endpoint*60/8)+1):
        target = i*8/60
        right = bisect.bisect_left(times, target)
        j = min({max(0,right-1),min(len(times)-1,right)}, key=lambda k:(abs(times[k]-target),k))
        source_time, step = samples[j]
        frames.append(dict(frame=i,time=target,label=i*8//60,step=step,source_time=source_time,
                           source_time_error=source_time-target,file=f'frame_{i:06d}.png'))
    endpoint_frame = frames[-1] if coordinate_end is not None else None
    last_u = frames[-1]['time']-delay
    # Test every main-frame time at the inner mesh edge (largest queried u).
    # The outer edge and angular samples are checked by the renderer as well.
    wave_height(wave_file, np.array([f['time'] for f in frames]), np.full(len(frames),inner_radius))
    diagnostics(data, 1., work/'gw_diagnostics')
    y = np.array([calc_Ylm(l,m,np.pi/2,0).real for l,m in MODES])
    hp = data.eta@y
    np.savetxt(work/'hplus_1d.csv',np.column_stack((data.time,source_u,hp,1.05*hp)),delimiter=',',
               header='coordinate_time,source_retarded_time,hplus_unscaled,hplus_displayed',comments='')
    needed = sorted({f['step'] for f in frames})
    distinct_wave_times = len(frames)
    coordinate_endpoint = frames[-1]['time']
    if endpoint_frame is not None:
        # t=300 first appears at video time 37.5 s, as the first held-time
        # transition frame. Do not add an extra main frame and alter duration.
        frames = frames[:-1]
    plan = dict(speed=8,fps=60,main_frames=len(frames),main_seconds=len(frames)/60,
                transition_frames=600,total_frames=len(frames)+600,total_seconds=len(frames)/60+10,
                source_endpoint=times[-1],movie_coordinate_endpoint=coordinate_endpoint,
                comparison_endpoint=last_u,source_retarded_time_start=float(source_u[0]),
                source_retarded_time_end=float(source_u[-1]),wave_source=data.report,
                distinct_source_snapshots=len(needed),distinct_wave_times=distinct_wave_times,
                max_nearest_source_time_error=max(abs(f['source_time_error']) for f in frames),
                wave_time_spacing=8/60,source_step_stride=10,
                source_fields='Nearest dense simulation snapshot; cached field and density preprocessing',
                gravitational_wave='Fresh eta reconstruction at every video time, all l=2,4,6,8 m=0',
                memory_formula=f'Given total memory * B0^2 / {data.report["r_ext"]:g} * spin(-2)Y20(pi/2,0)',
                radius_convention='Memory divided by coordinate extraction radius; propagation uses time-dependent areal radius',
                counter='Original Blender label, floor(8 * video_seconds)',
                settings=dict(height_scale=500000,NR=421,NPHI=320,samples=16,width=960,height=540,
                              inner_radius=inner_radius),frames=frames)
    if endpoint_frame is not None:
        plan['transition_state'] = endpoint_frame
    (work/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (work/'needed_steps.txt').write_text('\n'.join(map(str,needed))+'\n')
    comparison_plots(work, plan)
    (work/'status').write_text('PREPARED\n')
    print(json.dumps({k:v for k,v in plan.items() if k!='frames'},indent=2),flush=True)


def comparison_plots(work, plan):
    import matplotlib.pyplot as plt
    model = MemoryComparison.from_work(work)
    model.save_comparison(work)
    u = np.linspace(0, model.endpoint, 3000)
    wave = np.interp(u, model.u, model.hp)
    memory = model.memory_at(u)
    diff = wave-memory
    relative = np.divide(np.abs(diff),np.abs(memory),out=np.full_like(u,np.nan),
                         where=np.abs(memory)>1e-6*np.max(np.abs(memory)))
    np.savetxt(work/'differences.csv',np.column_stack((u,wave,memory,diff,np.abs(diff),relative)),
               delimiter=',',header='t_ret,hplus,memory,hplus_minus_memory,absolute_difference,absolute_difference_over_abs_memory',comments='')
    fig,axs = plt.subplots(2,2,figsize=(12,7),layout='constrained')
    for column,lo in enumerate((0,180)):
        axs[0,column].plot(u,np.abs(diff));axs[1,column].plot(u,100*relative)
        for ax in axs[:,column]:ax.set_xlim(lo,model.endpoint);ax.grid(alpha=.2);ax.set_xlabel('Retarded time')
    axs[0,0].set_ylabel('Absolute strain difference')
    axs[1,0].set_ylabel('Difference / |memory| (%)')
    axs[0,0].set_title('Full history');axs[0,1].set_title('Late time')
    fig.savefig(work/'memory_differences.png',dpi=180);plt.close(fig)
    # Compare radius-weighted curves: raw strains at different radii differ as 1/r.
    old = load_eta(ROOT/'data/Test_OS_collapse_magnetized.wave_extraction.4','latest')
    old_u = source_retarded_times(old,1.)
    y = np.array([calc_Ylm(l,m,np.pi/2,0).real for l,m in MODES])
    old_hp = np.interp(u,old_u,old.eta@y)
    new_r = plan['wave_source']['r_ext']
    weighted_memory = memory*new_r
    fig,ax = plt.subplots(figsize=(10,5),layout='constrained')
    ax.plot(u,112*old_hp,label='Extraction radius 112')
    ax.plot(u,new_r*wave,label=f'Extraction radius {new_r:g}')
    ax.plot(u,weighted_memory,label='Given total memory × B0² × Y20',color='black',ls='--')
    mask = u>=180
    values = np.r_[112*old_hp[mask],new_r*wave[mask],weighted_memory[mask]]
    pad = .1*np.ptp(values)
    ax.set(xlim=(180,model.endpoint),ylim=(values.min()-pad,values.max()+pad),
           xlabel='Retarded time',ylabel='Coordinate extraction radius × strain',title='Same retarded time; no fitted shift or amplitude')
    ax.grid(alpha=.2);ax.legend();fig.savefig(work/'radius_comparison.png',dpi=180);plt.close(fig)
    report = dict(interval=[180,model.endpoint],normalization='Coordinate radius × hplus; relative RMS denominator is RMS memory',
                  source_112=old.report,source_new=plan['wave_source'])
    for label,values in [('r112',112*old_hp),('new_radius',new_r*wave)]:
        report[label]=dict(relative_rms_difference=float(np.linalg.norm((values-weighted_memory)[mask])/np.linalg.norm(weighted_memory[mask])),
                           endpoint_wave_over_memory=float(values[-1]/weighted_memory[-1]))
    (work/'radius_comparison.json').write_text(json.dumps(report,indent=2)+'\n')


def run(work, workers, threads):
    plan = json.loads((work/'plan.json').read_text())
    source = Path(plan['wave_source']['input'])
    if hashlib.sha256(source.read_bytes()).hexdigest()!=plan['wave_source']['sha256']:
        raise ValueError('Extraction source changed after preparation')
    env = os.environ.copy()
    env.update(RENDER_THREADS=str(threads),MOVIE_OUTPUT_DIR=str(work),GW_TIME_DECIMALS='0',
               OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',MPLBACKEND='Agg',
               WAVE_ALLOW_OFF_RECORD='false')
    env.pop('PYTHONPATH',None)
    (work/'logs').mkdir(exist_ok=True)
    python = sys.executable

    def execute(stage, commands):
        (work/'status').write_text(stage.upper()+'\n')
        print(stage.upper(),flush=True)
        def worker(item):
            index,command = item
            with (work/'logs'/f'{stage}_{index}.log').open('a') as stream:
                subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(worker,enumerate(commands)))

    try:
        for script,out,flag in [('generate_field_lines.py','fieldline_ply','--a-dir'),('plot_rho.py','rho_movie','--rho-dir')]:
            execute(Path(script).stem,[[python,str(ROOT/script),flag,str(ROOT/'data'),'--out-dir',str(ROOT/'output'/out),
                     '--stride','10','--start','0','--end',str(max(map(int,(work/'needed_steps.txt').read_text().split()))),
                     '--steps-file',str(work/'needed_steps.txt'),
                     '--worker',str(w),'--workers',str(workers)] for w in range(workers)])
        execute('main',[[python,str(ROOT/'temporal_movie_worker.py'),'--work',str(work),
                        '--worker',str(w),'--workers',str(workers)] for w in range(workers)])
        # Both transition geometry and inset must use this run, never old radius-112 frames.
        env['PYTHONPATH']=str(ROOT/'blender_packages')
        execute('transition_render',[[str(ROOT/'blender/blender'),'-b','--python-exit-code','1',
                '--python-use-system-env','-t',str(threads),'-P',str(ROOT/'render_transition.py'),'--',str(w),str(workers)]
                for w in range(workers)])
        env.pop('PYTHONPATH',None)
        execute('transition_composite',[[python,str(ROOT/'composite_memory_movie.py'),'--temporal','--work',str(work),
                '--worker',str(w),'--workers',str(workers)] for w in range(workers)])
        execute('encoding',[[python,str(ROOT/'encode_temporal_movie.py'),'--work',str(work)]])
    except BaseException:
        (work/'status').write_text('FAILED\n')
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','run'])
    parser.add_argument('--work',type=Path,default=DEFAULT_WORK)
    parser.add_argument('--wave-file',type=Path,default=ROOT/'data/Test_OS_collapse_magnetized.wave_extraction.15')
    parser.add_argument('--retarded-end',type=float,default=280.)
    parser.add_argument('--coordinate-end',type=float,help='Exact final coordinate time; reject unsupported wave coverage')
    parser.add_argument('--inner-radius',type=float,default=10.)
    parser.add_argument('--workers',type=int,default=32)
    parser.add_argument('--threads',type=int,default=4)
    args=parser.parse_args()
    if args.stage=='prepare':prepare(args.work.resolve(),args.wave_file.resolve(),args.retarded_end,
                                    args.coordinate_end,args.inner_radius)
    else:run(args.work.resolve(),args.workers,args.threads)


if __name__=='__main__':main()
