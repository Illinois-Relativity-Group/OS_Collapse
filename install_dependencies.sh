#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
python3 -m pip install -r "$ROOT/requirements.txt"
: "${BLENDER_PYTHON:?Set BLENDER_PYTHON to Blender 5.0 bundled Python executable}"
"$BLENDER_PYTHON" -m ensurepip
"$BLENDER_PYTHON" -m pip install --target "$ROOT/blender_packages" numpy scipy
