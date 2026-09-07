#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/logs"
PID_FILE="$ROOT_DIR/pipeline.pid"
LOG_FILE="$LOG_DIR/pipeline.log"

mkdir -p "$LOG_DIR"

if [[ -f "$PID_FILE" ]]; then
    old_pid="$(cat "$PID_FILE")"
    if kill -0 "$old_pid" 2>/dev/null; then
        echo "Pipeline is already running with PID $old_pid"
        echo "Log: $LOG_FILE"
        exit 0
    fi
fi

cd "$ROOT_DIR"
nohup setsid env \
    START="${START:-0}" \
    END="${END:-25000}" \
    STEP="${STEP:-10}" \
    SAVE_BLENDER="${SAVE_BLENDER:-false}" \
    PLOT_WAVE="${PLOT_WAVE:-true}" \
    GENERATE_PLY="${GENERATE_PLY:-true}" \
    GENERATE_RHO="${GENERATE_RHO:-true}" \
    ./run_pipeline.sh >>"$LOG_FILE" 2>&1 </dev/null &

pid=$!
echo "$pid" >"$PID_FILE"
echo "Pipeline started in the background with PID $pid"
echo "Log: $LOG_FILE"
