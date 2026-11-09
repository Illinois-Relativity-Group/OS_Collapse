#!/usr/bin/env bash
#SBATCH --job-name=os_r400_no_legend
#SBATCH --account=mca99s008
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=14G
#SBATCH --time=00:30:00
#SBATCH --chdir=/anvil/scratch/x-xzhao14/os_collapse_B0004_spherical_with_gw
#SBATCH --output=logs/radius400_no_legend_%j.log
#SBATCH --error=logs/radius400_no_legend_%j.log
set -Eeuo pipefail
unset PYTHONPATH
export PATH="/apps/anvil/external/apps/conda/2024.02/bin:$PWD/bin:$PATH"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.cache/matplotlib" PYTHONUNBUFFERED=1
work="$PWD/output/extraction_r400/temporal_8_tM_to300"
exec 9>"$work/job.lock"
flock -n 9 || { echo 'Another movie job is active'; exit 1; }
trap 'echo FAILED_RECOMPOSITION > "$work/status"' ERR
movie="$work/os_collapse_B0004_spherical_with_gw_memory_8_tM_high_temporal.mp4"
backup="$work/movie_with_legend_backup.mp4"
if [[ -f "$movie" && ! -e "$backup" ]]; then cp "$movie" "$backup"; fi
echo RECOMPOSING_NO_LEGEND > "$work/status"
echo "$SLURM_JOB_ID" > "$work/slurm_job_id"
workers="${SLURM_CPUS_PER_TASK:-8}"
pids=()
for ((w=0;w<workers;w++)); do
    (
        python3 temporal_movie_worker.py --work "$work" --recompose-only --worker "$w" --workers "$workers"
        python3 composite_memory_movie.py --temporal --work "$work" --worker "$w" --workers "$workers"
    ) > "$work/logs/no_legend_$w.log" 2>&1 &
    pids+=("$!")
done
bad=0
for p in "${pids[@]}"; do wait "$p" || bad=1; done
[[ "$bad" == 0 ]]
python3 encode_temporal_movie.py --work "$work"
