#!/usr/bin/env bash
#SBATCH --job-name=os_r400_t300
#SBATCH --account=mca99s008
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=14G
#SBATCH --time=00:30:00
#SBATCH --chdir=/anvil/scratch/x-xzhao14/os_collapse_B0004_spherical_with_gw
#SBATCH --output=logs/radius400_to300_%j.log
#SBATCH --error=logs/radius400_to300_%j.log
set -Eeuo pipefail
unset PYTHONPATH
export PATH="/apps/anvil/external/apps/conda/2024.02/bin:$PWD/bin:$PATH"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.cache/matplotlib" PYTHONUNBUFFERED=1
work="$PWD/output/extraction_r400/temporal_8_tM_to300"
exec 9>"$work/job.lock"
flock -n 9 || { echo 'Endpoint correction already running';exit 1; }
trap 'echo FAILED > "$work/status"' ERR
echo "$SLURM_JOB_ID" > "$work/slurm_job_id"
echo "job=$SLURM_JOB_ID node=$SLURMD_NODENAME"
# main_raw points to the already rendered radius-400 scenes. Only the inset,
# endpoint-300 camera transition, and final encode need to be rebuilt.
python3 radius_pipeline.py run --work "$work" --workers 4 --threads 2
