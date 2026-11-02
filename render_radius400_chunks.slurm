#!/usr/bin/env bash
#SBATCH --job-name=os_r400_chunks
#SBATCH --account=mca99s008
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=14G
#SBATCH --time=01:00:00
#SBATCH --array=0-63%8
#SBATCH --chdir=/anvil/scratch/x-xzhao14/os_collapse_B0004_spherical_with_gw
#SBATCH --output=logs/radius400_chunk_%A_%a.log
#SBATCH --error=logs/radius400_chunk_%A_%a.log
set -Eeuo pipefail
unset PYTHONPATH
export PATH="/apps/anvil/external/apps/conda/2024.02/bin:$PWD/bin:$PATH"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.cache/matplotlib" PYTHONUNBUFFERED=1
work="$PWD/output/extraction_r400/temporal_8_tM_to400"
mkdir -p "$work/chunks"
# Shared locks permit these disjoint chunks but exclude single-node runs.
exec 9>"$work/job.lock"
flock -s -n 9 || { echo 'A single-node pipeline is active';exit 1; }
exec 8>"$work/chunks/chunk_$SLURM_ARRAY_TASK_ID.lock"
flock -n 8 || { echo 'This chunk is already active';exit 1; }
echo "job=$SLURM_JOB_ID array=$SLURM_ARRAY_JOB_ID chunk=$SLURM_ARRAY_TASK_ID node=$SLURMD_NODENAME"
echo RENDERING_CHUNKS > "$work/status"
python3 render_movie_chunk.py --work "$work" --chunk "$SLURM_ARRAY_TASK_ID" --chunks 64
