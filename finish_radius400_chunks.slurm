#!/usr/bin/env bash
#SBATCH --job-name=os_r400_finish
#SBATCH --account=mca99s008
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=14G
#SBATCH --time=00:30:00
#SBATCH --chdir=/anvil/scratch/x-xzhao14/os_collapse_B0004_spherical_with_gw
#SBATCH --output=logs/radius400_finish_%j.log
#SBATCH --error=logs/radius400_finish_%j.log
set -Eeuo pipefail
unset PYTHONPATH
export PATH="/apps/anvil/external/apps/conda/2024.02/bin:$PWD/bin:$PATH"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.cache/matplotlib" PYTHONUNBUFFERED=1
work="$PWD/output/extraction_r400/temporal_8_tM_to400"
exec 9>"$work/job.lock"
flock -n 9 || { echo 'Render jobs are still active';exit 1; }
trap 'echo FAILED_ASSEMBLY > "$work/status"' ERR
for ((i=0;i<64;i++));do
    printf -v chunk '%03d' "$i"
    [[ "$(cat "$work/chunks/$chunk/status")" == COMPLETE ]]
done
echo COMPOSITING_TRANSITION > "$work/status"
pids=()
for ((w=0;w<4;w++));do
    python3 composite_memory_movie.py --temporal --work "$work" --worker "$w" --workers 4 > "$work/logs/final_composite_$w.log" 2>&1 &
    pids+=("$!")
done
bad=0
for p in "${pids[@]}";do wait "$p" || bad=1;done
[[ "$bad" == 0 ]]
python3 encode_temporal_movie.py --work "$work"
