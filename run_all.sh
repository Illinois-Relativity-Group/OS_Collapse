#!/usr/bin/env bash
# Complete latest visualization: simulation -> 3D+1D -> cylindrical cut transition.
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$ROOT"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg
export BLENDER_BIN="${BLENDER_BIN:-$(command -v blender || true)}"
export BLENDER_PYTHONPATH="${BLENDER_PYTHONPATH:-$ROOT/blender_packages}"
DATA_DIR="${DATA_DIR:-$ROOT/data}"
NW="${NW:-5}"
((NW<=5)) || NW=5
[[ "$NW" =~ ^[1-9][0-9]*$ ]] || { echo 'NW must be a positive integer' >&2; exit 1; }
stage="${1:-all}"
case "$stage" in all|check|prepare|main|transition|assemble) ;; *) echo 'Usage: bash run_all.sh [check|prepare|main|transition|assemble|all]' >&2; exit 2;; esac
python3 check_inputs.py "$DATA_DIR"
[[ -x "$BLENDER_BIN" ]] || { echo 'Set BLENDER_BIN to a Blender 5.0 executable.' >&2; exit 1; }
command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
PYTHONPATH="$BLENDER_PYTHONPATH" "$BLENDER_BIN" -b --python-exit-code 1 --python-use-system-env --python-expr 'import bpy, scipy, numpy; assert bpy.app.version[:2] == (5,0), "Use Blender 5.0 for this snapshot"; print("Blender scientific dependencies OK")' > /tmp/os_collapse_1015_blender_check_$$.log 2>&1 || { cat /tmp/os_collapse_1015_blender_check_$$.log; exit 1; }
rm /tmp/os_collapse_1015_blender_check_$$.log
[[ "$stage" != check ]] || { echo 'Preflight passed'; exit 0; }
if [[ ! -e "$ROOT/data" ]]; then ln -s "$(realpath "$DATA_DIR")" "$ROOT/data"; fi
[[ "$(realpath "$DATA_DIR")" == "$(realpath "$ROOT/data")" ]] || { echo 'data already points to different inputs; use a fresh output folder/package for a different dataset.' >&2; exit 1; }
mkdir -p output logs
status="$ROOT/output/pipeline.status"
trap 'echo "FAILED at line $LINENO" > "$status"' ERR
wait_workers() {
 local bad=0 p
 for p in "${pids[@]}"; do wait "$p" || bad=1; done
 [[ "$bad" == 0 ]]
}
prepare() {
 echo PREPARING > "$status"
 python3 generate_field_lines.py --a-dir data --out-dir output/fieldline_ply --stride 100 --start 0 --end 34400
 python3 plot_rho.py --rho-dir data --out-dir output/rho_movie --stride 100 --start 0 --end 34400
}
main() {
 echo RENDERING_MAIN > "$status"
 local w pids=()
 for ((w=0;w<NW;w++)); do
  # Interleave source steps, preserving all 330 frames; separate diagnostics per worker.
  START=$((w*100)) END=34400 STEP=100 THREADS=1 \
   GENERATE_PLY=false GENERATE_RHO=false IMAGE_SUBDIR="main_worker_$w" \
   WORKER_INDEX="$w" WORKER_COUNT="$NW" WAVE_HEIGHT_SCALE=100000 WAVE_M_ADM=1.0 \
   bash render_main_batch.sh > "logs/main_$w.log" 2>&1 &
  pids+=("$!")
 done
 wait_workers
 python3 - <<'PY'
from pathlib import Path
import shutil
out=Path('output/images_levels_x20_amp100000_to35000');out.mkdir(exist_ok=True)
for i in range(0,34401,100):
 matches=list(Path('output').glob(f'main_worker_*/render_{i:08d}.png'))
 if len(matches)!=1: raise RuntimeError(f'Expected one frame for {i}, got {matches}')
 shutil.copy2(matches[0],out/matches[0].name)
PY
 echo OVERLAYING_MAIN > "$status"
 python3 overlay_wave_1d_full_movie.py --image-dir output/images_levels_x20_amp100000_to35000 --field-dir data --wave-file data/Test_OS_collapse_magnetized.wave_extraction.4 --output-dir output/main_with_1d --start 0 --end 34400 --step 100 --force
 BEFORE_SLOWDOWN=5 OUTPUT_FPS=60 MAX_INDEX=34400 WAVE_IMAGE_SUBDIR=main_with_1d bash make_variable_rate_movies.sh with-wave
 mv output/magnetised_star_with_wave_eta_variable_rate.mp4 output/main_to_t300_levels_x20_amp100000_with_1d.mp4
}
transition() {
 echo RENDERING_TRANSITION > "$status"
 local w pids=()
 for ((w=0;w<NW;w++)); do
  PYTHONPATH="$BLENDER_PYTHONPATH" "$BLENDER_BIN" -b --python-exit-code 1 --python-use-system-env -t 1 -P render_transition.py -- "$w" "$NW" > "logs/transition_$w.log" 2>&1 &
  pids+=("$!")
 done
 wait_workers
}
assemble() {
 echo COMPOSITING > "$status"
 python3 - <<'PY'
from pathlib import Path
from PIL import Image
r=Path('output/cylinder_wall_wider_movie_raw')
for p in [r/'cut_white_label.png',*(r/f'frame_{i:04d}.png' for i in range(421))]:
 with Image.open(p) as im: im.verify()
PY
 local w pids=() overlays=4
 ((NW>=4)) || overlays="$NW"
 for ((w=0;w<overlays;w++)); do
  OVERLAY_WORKER="$w" OVERLAY_WORKERS="$overlays" python3 compose_transition.py > "logs/overlay_$w.log" 2>&1 &
  pids+=("$!")
 done
 wait_workers
 echo ENCODING > "$status"
 ffmpeg -v error -y -framerate 60 -i output/cylinder_wall_wider_inset_movie_frames/frame_%04d.png -c:v libx264 -threads "$NW" -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart output/transition.mp4
 ffmpeg -v error -y -i output/main_to_t300_levels_x20_amp100000_with_1d.mp4 -i output/transition.mp4 -filter_complex '[0:v][1:v]concat=n=2:v=1:a=0[v]' -map '[v]' -c:v libx264 -threads "$NW" -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart output/os_collapse_B0004_spherical_with_gw.mp4
 ffmpeg -v error -i output/os_collapse_B0004_spherical_with_gw.mp4 -f null -
 ffprobe -v error -show_entries format=duration:stream=nb_frames,width,height,r_frame_rate -of json output/os_collapse_B0004_spherical_with_gw.mp4 > output/validation.json
 echo COMPLETE > "$status"
 echo "Movie: $ROOT/output/os_collapse_B0004_spherical_with_gw.mp4"
}
if [[ "$stage" == all ]]; then prepare; main; transition; assemble; else "$stage"; fi
