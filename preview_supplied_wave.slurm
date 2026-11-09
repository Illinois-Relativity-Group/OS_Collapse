#!/usr/bin/env bash
#SBATCH --job-name=os_supplied_preview
#SBATCH --account=mca99s008
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=14G
#SBATCH --time=00:10:00
#SBATCH --chdir=/anvil/scratch/x-xzhao14/os_collapse_B0004_spherical_with_gw
#SBATCH --output=logs/supplied_preview_%j.log
#SBATCH --error=logs/supplied_preview_%j.log
set -Eeuo pipefail
unset PYTHONPATH
export PATH="/apps/anvil/external/apps/conda/2024.02/bin:$PWD/bin:$PATH"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.cache/matplotlib" PYTHONUNBUFFERED=1
export RENDER_THREADS=8 WAVE_ALLOW_OFF_RECORD=false
work="$PWD/output/supplied_equatorial_20261105/temporal_8_tM_to300"
export MOVIE_OUTPUT_DIR="$work"
exec 9>"$work/job.lock"
flock -n 9
trap 'echo FAILED_PREVIEW > "$work/status"' ERR
echo RENDERING_PREVIEW > "$work/status"
python3 temporal_movie_worker.py --work "$work" --only 450
python3 temporal_movie_worker.py --work "$work" --only 2250
PYTHONPATH="$PWD/blender_packages" TRANSITION_FRAMES=0,420 "$PWD/blender/blender" -b --python-exit-code 1 --python-use-system-env -t 8 -P render_transition.py -- 0 1
python3 composite_memory_movie.py --temporal --work "$work" --preview
echo PREVIEW_COMPLETE > "$work/status"
