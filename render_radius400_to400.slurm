#!/usr/bin/env bash
#SBATCH --job-name=os_r400_t400
#SBATCH --account=mca99s008
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=112G
#SBATCH --time=04:00:00
#SBATCH --chdir=/anvil/scratch/x-xzhao14/os_collapse_B0004_spherical_with_gw
#SBATCH --output=logs/radius400_to400_%j.log
#SBATCH --error=logs/radius400_to400_%j.log
set -Eeuo pipefail
unset PYTHONPATH
export PATH="/apps/anvil/external/apps/conda/2024.02/bin:$PWD/bin:$PATH"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.cache/matplotlib" PYTHONUNBUFFERED=1
work="$PWD/output/extraction_r400/temporal_8_tM_to400"
exec 9>"$work/job.lock"
flock -n 9 || { echo 'Radius-400 endpoint-400 render already running'; exit 1; }
trap 'echo FAILED > "$work/status"' ERR
echo "$SLURM_JOB_ID" > "$work/slurm_job_id"
echo "job=$SLURM_JOB_ID node=$SLURMD_NODENAME CPUs=$SLURM_CPUS_PER_TASK"
workers=$((SLURM_CPUS_PER_TASK / 4))
((workers>=1)) || workers=1
python3 radius_pipeline.py run --work "$work" --workers "$workers" --threads 4
