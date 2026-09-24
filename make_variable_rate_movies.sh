#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$ROOT_DIR/output"
WAVE_IMAGE_SUBDIR="${WAVE_IMAGE_SUBDIR:-images_eta}"

# Measured from adjacent a_p_slice headers.
SWITCH_INDEX=17600
BEFORE_DT=0.0090925
AFTER_DT=0.18525
BEFORE_SOURCE_FPS=300
OUTPUT_FPS=300

AFTER_SOURCE_FPS=$(awk -v fps="$BEFORE_SOURCE_FPS" -v before="$BEFORE_DT" -v after="$AFTER_DT" \
    'BEGIN {printf "%.12f", fps * before / after}')
BEFORE_DURATION=$(awk -v fps="$BEFORE_SOURCE_FPS" 'BEGIN {printf "%.12f", 1.0 / fps}')
AFTER_DURATION=$(awk -v fps="$AFTER_SOURCE_FPS" 'BEGIN {printf "%.12f", 1.0 / fps}')

make_movie() {
    local image_dir="$1"
    local output_movie="$2"
    local name number_text index full_path
    local count=0 early_count=0 late_count=0

    # The concat demuxer assumes 25 fps for image inputs and quantizes every
    # "duration" to 40 ms. BEFORE_DURATION is 1/300 s = 3.33 ms, so ~12
    # pre-excision frames used to collapse into one and ~92% of the infall was
    # lost; "-r" fixes the rate but then discards the durations entirely, which
    # kills the variable rate. So expand the repetition ourselves: build a
    # numbered symlink per OUTPUT frame and hand that to the image2 demuxer at
    # a constant OUTPUT_FPS. Exact, and no sub-quantum durations anywhere.
    #
    # Repeats per source frame = OUTPUT_FPS / source_fps, accumulated as a
    # running fraction so the rounding never drifts.
    local before_reps after_reps
    before_reps=$(awk -v o="$OUTPUT_FPS" -v s="$BEFORE_SOURCE_FPS" 'BEGIN{printf "%.12f", o/s}')
    after_reps=$(awk -v o="$OUTPUT_FPS" -v s="$AFTER_SOURCE_FPS" 'BEGIN{printf "%.12f", o/s}')

    local link_dir
    link_dir=$(mktemp -d)
    trap 'rm -rf "$link_dir"' RETURN

    local emitted=0 acc=0
    while IFS= read -r name; do
        number_text="${name#render_}"
        number_text="${number_text%.png}"
        [[ "$number_text" =~ ^[0-9]+$ ]] || continue
        index=$((10#$number_text))
        full_path="$image_dir/$name"

        local reps
        if (( index < SWITCH_INDEX )); then
            reps="$before_reps"; ((early_count += 1))
        else
            reps="$after_reps"; ((late_count += 1))
        fi
        # how many whole output frames this source frame gets
        local n
        read -r n acc < <(awk -v a="$acc" -v r="$reps" \
            'BEGIN{a+=r; n=int(a+1e-9); printf "%d %.12f\n", n, a-n}')
        local k
        for (( k = 0; k < n; k++ )); do
            ln -s "$full_path" "$(printf '%s/f%07d.png' "$link_dir" "$emitted")"
            ((emitted += 1))
        done
        ((count += 1))
    done < <(find "$image_dir" -maxdepth 1 -type f -name 'render_*.png' -printf '%f\n' | sort -V)

    if (( emitted == 0 )); then
        echo "No frames found in $image_dir" >&2
        return 1
    fi

    echo "Creating $output_movie"
    echo "  Frames: $count ($early_count before, $late_count after excision)"
    echo "  Output frames: $emitted at ${OUTPUT_FPS} fps"
    ffmpeg -y -framerate "$OUTPUT_FPS" -i "$link_dir/f%07d.png" \
        -vf "format=yuv420p" \
        -c:v libx264 -preset slow -crf 18 -movflags +faststart "$output_movie"
}

echo "Before-excision source rate: $BEFORE_SOURCE_FPS fps"
echo "After-excision source rate : $AFTER_SOURCE_FPS fps"
echo "Encoded output rate        : $OUTPUT_FPS fps"

case "${1:-both}" in
    with-wave)
        make_movie "$OUTPUT_DIR/$WAVE_IMAGE_SUBDIR" "$OUTPUT_DIR/magnetised_star_with_wave_eta_variable_rate.mp4"
        ;;
    no-wave)
        make_movie "$OUTPUT_DIR/images_no_wave" "$OUTPUT_DIR/magnetised_star_without_wave_variable_rate.mp4"
        ;;
    bh-test)
        make_movie "$OUTPUT_DIR/images_no_wave_bh_test_1000" "$OUTPUT_DIR/black_hole_test_1000frames.mp4"
        ;;
    both)
        make_movie "$OUTPUT_DIR/$WAVE_IMAGE_SUBDIR" "$OUTPUT_DIR/magnetised_star_with_wave_eta_variable_rate.mp4"
        make_movie "$OUTPUT_DIR/images_no_wave" "$OUTPUT_DIR/magnetised_star_without_wave_variable_rate.mp4"
        ;;
    *) echo "Usage: $0 [with-wave|no-wave|bh-test|both]" >&2; exit 2 ;;
esac
