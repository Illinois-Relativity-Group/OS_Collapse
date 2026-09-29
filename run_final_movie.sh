#!/usr/bin/env bash
#
# Reproduce the reviewed movie end to end: render the frames, then encode.
#
#   ./run_final_movie.sh
#
# The LOOK and the TIMING are baked in below -- they were settled by review and
# should not be changed casually. Everything that depends on WHICH RUN you are
# visualising is in the CASE SETTINGS block and must be supplied.
#
# For the MHD_RK4_ICN_with_theta_surf_Nth16_B0.0001 case this repo is pointed
# at, that is:
#
#   WAVE_M_ADM=1.0004 WAVE_HEIGHT_SCALE=500000 ./run_final_movie.sh
#
set -Eeuo pipefail
cd "$(dirname "$0")"

# ======================================================================
# CASE SETTINGS -- fill these in for your run
# ======================================================================

# ADM mass of YOUR run, from its initial diagnostics. Sets the retarded time
# r* = r + 2M ln(r/2M - 1) and the t/M label, so a wrong value is wrong
# physics, not just a wrong picture. No default on purpose.
: "${WAVE_M_ADM:?set WAVE_M_ADM -- the ADM mass of your run (this case: 1.0004)}"

# Vertical exaggeration of the wave mesh. Pure display: pick it so the mesh
# reads without clipping. Scale it inversely with your peak |h+| -- this case
# peaks at 2.7e-5 and uses 5e5. No default on purpose.
: "${WAVE_HEIGHT_SCALE:?set WAVE_HEIGHT_SCALE -- display exaggeration (this case: 500000)}"

# Stride between rendered timesteps, matching how your slices were dumped.
STEP="${STEP:-100}"

# Stop the movie at this t/M. The step is found from the slice headers below,
# so you do not have to work it out. Keep it under the point where the wave
# record runs out, or the render will (correctly) refuse -- see the
# WAVE_ALLOW_OFF_RECORD note in wave_eta.py.
TM_LIMIT="${TM_LIMIT:-300}"

# Parallel render workers, one core each. Check the machine first.
NW="${NW:-12}"

FRAME_DIR="${FRAME_DIR:-output/images_final}"
PREFIX="${PREFIX:-final}"
MOVIE="${MOVIE:-output/magnetised_star_final.mp4}"

# ======================================================================
# LOCKED LOOK -- reviewed, do not change casually
# ======================================================================
export GW_ALPHA=0.75                       # mesh opacity
export GW_BACKDROP=true                    # plane under the mesh
export GW_BACKDROP_COLOR=0.35,0.38,0.42    # grey; it is emissive, so it is also fill light
export GW_UNDERLIGHT=true                  # lifts the field lines beneath the mesh
export GW_UNDERLIGHT_ENERGY=400000
export GW_UNDERLIGHT_Z=-30
export GW_UNDERLIGHT_SIZE=60
# GW_EMISSION=0, GW_SUN_ENERGY=4, GW_SUN2_ENERGY=0.3, GW_GRID_SCALE=0.125,
# GW_COLOR_MODE=gradient and GW_TIME_LABEL=true are already the committed
# defaults in plot_3d.py and need no setting here.

# ======================================================================
# LOCKED TIMING
# ======================================================================
BEFORE_SLOWDOWN=5   # infall stretch. 5 is the minimum that keeps the infall's
                    # source rate at or below OUTPUT_FPS; at 4 a 60 fps encode
                    # silently drops 20% of it.
OUTPUT_FPS=60       # a display can show this. 300 forces the player to drop
                    # 4 of every 5 frames, unevenly, and it reads as the movie
                    # speeding up and slowing down.

# ======================================================================

# Last step at or below TM_LIMIT, read from the slice headers.
MAX_STEP=$(for f in data/a_p_slice_9000_16_*; do
        st=${f##*_}
        t=$(head -5 "$f" | grep -o 'coord time [0-9.]*' | awk '{print $3}')
        [[ -n "$t" ]] && echo "$((10#$st)) $t"
    done | sort -n | awk -v lim="$TM_LIMIT" -v m="$WAVE_M_ADM" \
        '$2/m <= lim {last=$1} END {print last}')
[[ -n "$MAX_STEP" ]] || { echo "No frame found at or below t/M = $TM_LIMIT" >&2; exit 1; }

echo "=============================================================="
echo " M_ADM          : $WAVE_M_ADM"
echo " height scale   : $WAVE_HEIGHT_SCALE"
echo " stride         : $STEP"
echo " t/M limit      : $TM_LIMIT  -> last step $MAX_STEP"
echo " workers        : $NW"
echo " look           : alpha $GW_ALPHA, grey plane, under-light on"
echo " timing         : infall ${BEFORE_SLOWDOWN}x, ${OUTPUT_FPS} fps"
echo " frames -> $FRAME_DIR"
echo " movie  -> $MOVIE"
echo "=============================================================="

mkdir -p "$FRAME_DIR"
NW="$NW" MAX_STEP="$MAX_STEP" PREFIX="$PREFIX" FINAL="$FRAME_DIR" \
    STEP="$STEP" ./run_g3_full.sh

BEFORE_SLOWDOWN="$BEFORE_SLOWDOWN" OUTPUT_FPS="$OUTPUT_FPS" MAX_INDEX="$MAX_STEP" \
    WAVE_IMAGE_SUBDIR="$(basename "$FRAME_DIR")" ./make_variable_rate_movies.sh with-wave
mv output/magnetised_star_with_wave_eta_variable_rate.mp4 "$MOVIE"
echo "Done: $MOVIE"
