#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$ROOT_DIR/data"
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
END="${END:-25000}"
STEP="${STEP:-10}"
THREADS="${THREADS:-20}"
SAVE_BLENDER="${SAVE_BLENDER:-false}"
PLOT_WAVE="${PLOT_WAVE:-true}"
GENERATE_PLY="${GENERATE_PLY:-true}"
GENERATE_RHO="${GENERATE_RHO:-true}"
IMAGE_SUBDIR="${IMAGE_SUBDIR:-images}"
FORCE_RENDER="${FORCE_RENDER:-false}"

HORIZON_FILE="$DATA_DIR/Test_OS_collapse_magnetized_9000_16.hor_surface"
WAVE_FILE="$DATA_DIR/Test_OS_collapse_magnetized.wave_extraction.6"

mkdir -p "$OUTPUT_DIR/$IMAGE_SUBDIR" "$OUTPUT_DIR/blend_files" "$PLY_DIR" "$RHO_DIR"
cd "$ROOT_DIR"

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
        "$PLOT_WAVE" 10 2e7 1 220 220 160
done

echo "Finished. Images are in $OUTPUT_DIR/$IMAGE_SUBDIR"
