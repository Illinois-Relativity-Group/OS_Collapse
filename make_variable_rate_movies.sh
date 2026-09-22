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
    local concat_file
    local name number_text index full_path last_path=""
    local count=0 early_count=0 late_count=0

    concat_file=$(mktemp --suffix=.ffconcat)
    printf 'ffconcat version 1.0\n' > "$concat_file"

    while IFS= read -r name; do
        number_text="${name#render_}"
        number_text="${number_text%.png}"
        [[ "$number_text" =~ ^[0-9]+$ ]] || continue
        index=$((10#$number_text))
        full_path="$image_dir/$name"

        printf "file '%s'\n" "$full_path" >> "$concat_file"
        if (( index < SWITCH_INDEX )); then
            printf 'duration %s\n' "$BEFORE_DURATION" >> "$concat_file"
            ((early_count += 1))
        else
            printf 'duration %s\n' "$AFTER_DURATION" >> "$concat_file"
            ((late_count += 1))
        fi
        last_path="$full_path"
        ((count += 1))
    done < <(find "$image_dir" -maxdepth 1 -type f -name 'render_*.png' -printf '%f\n' | sort -V)

    if [[ -z "$last_path" ]]; then
        rm -f "$concat_file"
        echo "No frames found in $image_dir" >&2
        return 1
    fi

    # The concat demuxer applies the last duration only when followed by another entry.
    printf "file '%s'\n" "$last_path" >> "$concat_file"

    echo "Creating $output_movie"
    echo "  Frames: $count ($early_count before, $late_count after excision)"
    ffmpeg -y -f concat -safe 0 -i "$concat_file" \
        -vf "fps=${OUTPUT_FPS},format=yuv420p" \
        -c:v libx264 -preset slow -crf 18 -movflags +faststart "$output_movie"
    rm -f "$concat_file"
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
