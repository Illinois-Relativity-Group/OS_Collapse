#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$ROOT_DIR/data/MHD_RK4_ICN_with_theta_surf_Nth16_B0.002_spherical"
OUTPUT_DIR="$ROOT_DIR/output"
PLY_DIR="$OUTPUT_DIR/fieldline_ply"
RHO_DIR="$OUTPUT_DIR/rho_movie"

BLENDER_BIN="/home/oscarzhao5/Blender_5.0/blender-5.0.0-linux-x64/blender"
if [[ ! -x "$BLENDER_BIN" ]]; then
    BLENDER_BIN="/data/shared/Blender/Blender_5.0/blender-5.0.0-linux-x64/blender"
fi
if [[ ! -x "$BLENDER_BIN" ]]; then
    echo "Blender executable not found." >&2
    exit 1
fi

BLENDER_PYTHONPATH="$ROOT_DIR/blender_py311_packages"

START="${START:-0}"
END=25000 #"${END:-1000}"
STEP="${STEP:-10}"
THREADS="${THREADS:-20}"
SAVE_BLENDER=true #"${SAVE_BLENDER:-false}"
PLOT_WAVE=false #"${PLOT_WAVE:-true}"
GENERATE_PLY=true #"${GENERATE_PLY:-false}"
GENERATE_RHO=true #"${GENERATE_RHO:-false}"




# Keep corrected eta frames separate so old h+_20 renders are not skipped/reused.
if [[ "$PLOT_WAVE" == "true" ]]; then
    IMAGE_SUBDIR="${IMAGE_SUBDIR:-images_eta}"
else
    IMAGE_SUBDIR="${IMAGE_SUBDIR:-images}"
fi
FORCE_RENDER="${FORCE_RENDER:-false}"

HORIZON_FILE="$DATA_DIR/Test_OS_collapse_magnetized_9000_16.hor_surface"
# Use the supplied extraction-4 eta modes; every radius can be selected explicitly.
WAVE_FILE="${WAVE_FILE:-$DATA_DIR/Test_OS_collapse_magnetized.wave_extraction.4}"
export WAVE_M_ADM="${WAVE_M_ADM:-1.00071}"  # initial ADM diagnostic for this B0.002 run
export WAVE_RESTART_POLICY="${WAVE_RESTART_POLICY:-latest}"
WAVE_HEIGHT_SCALE="${WAVE_HEIGHT_SCALE:-10000}"  # display exaggeration only
WAVE_HOLE_RADIUS="${WAVE_HOLE_RADIUS:-10}"
WAVE_R_MAX="${WAVE_R_MAX:-220}"
WAVE_NR="${WAVE_NR:-220}"
WAVE_NPHI="${WAVE_NPHI:-160}"

mkdir -p "$OUTPUT_DIR/$IMAGE_SUBDIR" "$OUTPUT_DIR/blend_files" "$PLY_DIR" "$RHO_DIR"
cd "$ROOT_DIR"

# Validate and plot eta before starting expensive Blender rendering.
if [[ "$PLOT_WAVE" == "true" ]]; then
    env -u PYTHONPATH python3 wave_eta.py --input "$WAVE_FILE" --mass "$WAVE_M_ADM" \
        --restart-policy "$WAVE_RESTART_POLICY" --output "$OUTPUT_DIR/gw_diagnostics/$IMAGE_SUBDIR"
fi

if [[ "$GENERATE_PLY" == "true" ]]; then
    env -u PYTHONPATH python3 generate_field_lines.py --a-dir "$DATA_DIR" --out-dir "$PLY_DIR" \
        --stride "$STEP" --start "$START" --end "$END"
fi

if [[ "$GENERATE_RHO" == "true" ]]; then
    env -u PYTHONPATH python3 plot_rho.py --rho-dir "$DATA_DIR" --out-dir "$RHO_DIR" \
        --stride "$STEP" --start "$START" --end "$END"
fi

for field in "$DATA_DIR"/a_p_slice_9000_16_*; do
    [[ -e "$field" ]] || continue
    raw_num="${field##*_}"
    num_int=$((10#$raw_num))
    (( num_int >= START && num_int <= END )) || continue
    (( num_int % STEP == 0 )) || continue

    ply_num=$(printf "%06d" "$num_int")
    if [[ ! -f "$PLY_DIR/field_lines_${ply_num}.ply" ]]; then
        echo "Missing PLY for timestep $num_int; skipping." >&2
        continue
    fi

    frame_num=$(printf "%08d" "$num_int")
    density="$RHO_DIR/rho_${frame_num}.png"
    if [[ ! -f "$density" ]]; then
        echo "Missing density PNG for timestep $num_int; skipping." >&2
        continue
    fi

    render="$OUTPUT_DIR/$IMAGE_SUBDIR/render_${frame_num}.png"
    if [[ -f "$render" && "$FORCE_RENDER" != "true" ]]; then
        echo "Render already exists for timestep $num_int; skipping."
        continue
    fi

    echo "Rendering timestep $num_int"
    PYTHONPATH="$BLENDER_PYTHONPATH" "$BLENDER_BIN" -b --python-use-system-env -P plot_3d.py -t "$THREADS" -- \
        "$field" "$ROOT_DIR" "$OUTPUT_DIR" "$HORIZON_FILE" "$PLY_DIR" \
        "$SAVE_BLENDER" 0.04 2 blend_files "$IMAGE_SUBDIR" "$density" "$WAVE_FILE" \
        "$PLOT_WAVE" "$WAVE_HOLE_RADIUS" "$WAVE_HEIGHT_SCALE" 1 "$WAVE_R_MAX" "$WAVE_NR" "$WAVE_NPHI"
done

echo "Finished. Images are in $OUTPUT_DIR/$IMAGE_SUBDIR"
