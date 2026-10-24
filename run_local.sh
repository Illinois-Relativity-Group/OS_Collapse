#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
export BLENDER_BIN=/data/shared/Blender/Blender_5.0/blender-5.0.0-linux-x64/blender
export BLENDER_PYTHONPATH=/data/oscarzhao5/magnetised_star_collapse_3d_2ddata_2026-09-02_B0.002/yguo_latest_ecd7339/blender_py311_packages
export NW=5 PYTHONUNBUFFERED=1
cpus=$(python3 -c 'import os;print(",".join(map(str,sorted(os.sched_getaffinity(0))[:5])))')
exec taskset -c "$cpus" bash run_all.sh "${1:-all}"
