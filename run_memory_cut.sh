#!/bin/bash
# test-cut-memory.md reproduction, with our locked g3 mesh look instead of
# the document's teal/brick material and GW-MEM colour mask.
set -euo pipefail
cd "$(dirname "$0")"

export WAVE_COMPONENT="${WAVE_COMPONENT:-memory}"
export WAVE_REFERENCE_TIME="${WAVE_REFERENCE_TIME:-0}"
export WAVE_M_ADM="${WAVE_M_ADM:-1.0004}"   # our case; the doc's 1.00071 changes |dh| by 0.01%
export WAVE_RESTART_POLICY="${WAVE_RESTART_POLICY:-latest}"
export WAVE_MEMORY_TRANSITION_WIDTH="${WAVE_MEMORY_TRANSITION_WIDTH:-40}"

export WAVE_SIDEVIEW_CUT="${WAVE_SIDEVIEW_CUT:-true}"
export WAVE_CAMERA="${WAVE_CAMERA:-side_cut}"
export WAVE_SIDEVIEW_AZIMUTH="${WAVE_SIDEVIEW_AZIMUTH:--90}"
export WAVE_SIDEVIEW_ELEVATION="${WAVE_SIDEVIEW_ELEVATION:-0}"
export WAVE_SIDEVIEW_DISTANCE="${WAVE_SIDEVIEW_DISTANCE:-320.624}"
export WAVE_SIDEVIEW_TARGET_X="${WAVE_SIDEVIEW_TARGET_X:-0}"
export WAVE_SIDEVIEW_TARGET_Y="${WAVE_SIDEVIEW_TARGET_Y:-20}"
export WAVE_SIDEVIEW_TARGET_Z="${WAVE_SIDEVIEW_TARGET_Z:--2}"
export WAVE_SIDEVIEW_ORTHO_SCALE="${WAVE_SIDEVIEW_ORTHO_SCALE:-90}"

export WAVE_HIDE_FIELD_LINES="${WAVE_HIDE_FIELD_LINES:-true}"
export RENDER_SAMPLES="${RENDER_SAMPLES:-32}"
export RENDER_DENOISE="${RENDER_DENOISE:-true}"

STEP=${STEP:-00025000}
SUBDIR=${SUBDIR:-images_memory_cut}

PYTHONPATH="$PWD/blender_py311_packages" \
/data/shared/Blender/Blender_5.0/blender-5.0.0-linux-x64/blender \
  -b --python-exit-code 1 --python-use-system-env \
  -P plot_3d.py -t 8 -- \
  "data/a_p_slice_9000_16_$STEP" \
  "$PWD" "$PWD/output" \
  data/Test_OS_collapse_magnetized_9000_16.hor_surface \
  output/fieldline_ply \
  false 0.04 2 blend_files \
  "$SUBDIR" \
  "output/rho_movie/rho_$STEP.png" \
  data/Test_OS_collapse_magnetized.wave_extraction.4 \
  true 10 ${HEIGHT_SCALE:-10000000} 1 220 440 80
