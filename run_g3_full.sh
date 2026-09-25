#!/bin/bash
# Full 566-frame render at the locked g3 look.
# 12 workers x 1 thread. Each worker gets its own IMAGE_SUBDIR because
# wave_eta.py writes gw_diagnostics/$IMAGE_SUBDIR/gw.clm -- sharing it across
# concurrent workers produced torn reads last time.
set -euo pipefail
cd "$(dirname "$0")"

NW=${NW:-12}
FINAL=${FINAL:-output/images_g3}
mkdir -p "$FINAL"

mapfile -t STEPS < <(ls data/a_p_slice_9000_16_* | sed 's/.*_//' | sed 's/^0*//;s/^$/0/' \
                     | awk '$1 % 100 == 0' | sort -n)
# MAX_STEP: stop after this step. 32900 is t = 299.509, the last frame at or
# below t/M = 300, which is where the movies are cut anyway -- and it is also
# below t = 565.66, past which inner radii fall off the eta record.
if [[ -n "${MAX_STEP:-}" ]]; then
    filtered=()
    for st in "${STEPS[@]}"; do (( st <= MAX_STEP )) && filtered+=("$st"); done
    STEPS=("${filtered[@]}")
fi
N=${#STEPS[@]}
echo "$N frames, $NW workers"

pids=()
for ((w=0; w<NW; w++)); do
    lo=$(( w * N / NW ))
    hi=$(( (w+1) * N / NW - 1 ))
    (( lo > hi )) && continue
    START=${STEPS[$lo]}; END=${STEPS[$hi]}
    sub="${PREFIX:-g3}_w$(printf '%02d' $w)"
    echo "worker $w: steps $START..$END -> $sub"
    env START="$START" END="$END" STEP=100 THREADS=1 \
        GENERATE_PLY=false GENERATE_RHO=false PLOT_WAVE=true \
        IMAGE_SUBDIR="$sub" \
        WAVE_HEIGHT_SCALE=500000 WAVE_M_ADM=1.0004 \
        ./run_pipeline.sh > "logs/$sub.log" 2>&1 &
    pids+=($!)
done

fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done

echo "merging into $FINAL"
for d in output/${PREFIX:-g3}_w*; do ln -f "$d"/render_*.png "$FINAL"/ 2>/dev/null || true; done
echo "frames in $FINAL: $(ls "$FINAL" | wc -l) (expected $N)"
[[ $fail -eq 0 ]] || echo "WARNING: at least one worker exited non-zero" >&2
