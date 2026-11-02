"""Encode the newly computed temporal frames and retain the existing transition."""
import csv
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

from memory_alignment import MemoryComparison

ROOT=Path(__file__).resolve().parent
WORK=ROOT/'output/movie_amp500000_integer_time/temporal_8_tM'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=WORK)
    args=parser.parse_args()
    work=args.work.resolve()
    plan=json.loads((work/'plan.json').read_text())
    frames=plan['frames']
    if len(frames)!=plan['main_frames']:raise ValueError('Incorrect main frame count')
    if len({f['time'] for f in frames})<len(frames)-1:raise ValueError('Insufficient distinct wave times')
    for i,f in enumerate(frames):
        if f['frame']!=i or f['label']!=i*8//60:raise ValueError('Invalid time/counter plan')
        if abs(f['time']-i*plan['speed']/plan['fps'])>1e-9:
            raise ValueError('Simulation clock is not uniform in video time')
    if 'transition_state' in plan:
        endpoint=plan['transition_state']
        if abs(endpoint['time']-len(frames)*plan['speed']/plan['fps'])>1e-9:
            raise ValueError('Transition must begin exactly when the clock reaches the requested endpoint')
    model=MemoryComparison.from_work(work);model.save_comparison(work)
    with (work/'timeline.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(frames[0]))
        writer.writeheader();writer.writerows(frames)
    ffmpeg=str(ROOT/'bin/ffmpeg')
    threads=str(min(16,int(os.environ.get('SLURM_CPUS_PER_TASK','2'))))
    output=work/'os_collapse_B0004_spherical_with_gw_memory_8_tM_high_temporal.mp4'
    transition=(work/'transition_with_memory' if 'wave_source' in plan else
                ROOT/'output/movie_amp500000_integer_time/memory_8_tM/transition_with_memory')
    with tempfile.TemporaryDirectory(prefix='os_dense_movie_') as temp:
        sequence=Path(temp)
        paths=[work/'main_with_memory'/f['file'] for f in frames]
        paths += [transition/f'frame_{i:04d}.png' for i in range(600)]
        for i,path in enumerate(paths):
            with Image.open(path) as im:
                if im.size!=(960,540):raise ValueError(f'Incorrect image size: {path}')
                im.verify()
            (sequence/f'frame_{i:06d}.png').symlink_to(path)
        (work/'status').write_text('ENCODING\n')
        subprocess.run([ffmpeg,'-v','error','-y','-threads',threads,'-framerate','60',
                        '-i',str(sequence/'frame_%06d.png'),'-c:v','libx264','-threads',threads,
                        '-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],check=True)
    result=subprocess.run([ffmpeg,'-v','error','-threads',threads,'-i',str(output),
                           '-progress','pipe:1','-nostats','-f','null','-'],
                          capture_output=True,text=True,check=True)
    progress=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    if int(progress['frame'])!=plan['total_frames']:raise ValueError(f'Decode mismatch: {progress}')
    report={k:v for k,v in plan.items() if k!='frames'}
    report.update(decode_validation='passed',decoded_frames=int(progress['frame']),output=str(output),
                  memory_comparison=model.report,transition=('Recomputed at the last supported movie time'
                  if 'wave_source' in plan else 'Existing 600-frame fixed-time camera animation'))
    (work/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (work.parent/'latest_memory_movie.json').write_text(json.dumps(report,indent=2)+'\n')
    (work/'status').write_text('COMPLETE\n')
    print(f'COMPLETE: {output}',flush=True)


if __name__=='__main__':main()
