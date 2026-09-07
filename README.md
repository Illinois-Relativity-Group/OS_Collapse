# Magnetised star collapse visualization pipeline

Code-only extraction of `magnetised_star_collapse_3d_2ddata_2026-09-02_B0.002`.
All eight source scripts are copied unchanged, preserving executable permissions.
No simulation data, generated outputs, logs, PID files, Python caches, bundled
third-party packages, or `.orig` backups are included.

## Pipeline

1. `generate_field_lines.py`: converts vector-potential slices to field-line PLY files.
2. `plot_rho.py`: renders density slices to transparent PNG images.
3. `plot_3d.py`: renders the scene in Blender using `geo_node.py` and `plot_density.py`.
4. `make_variable_rate_movies.sh`: assembles rendered frames into MP4 movies with FFmpeg.

`run_pipeline.sh` runs steps 1–3. `start_background.sh` launches it in the background.

## Setup

- Python 3 with NumPy, SciPy, and Matplotlib for preprocessing.
- Blender with its bundled `bpy` and `mathutils`, plus compatible NumPy and SciPy.
  The scripts were configured for Blender 5.0; `geo_node.py` uses Blender's bundled
  geometry-node assets.
- FFmpeg with libx264, Bash, and the command-line utilities used by the shell scripts.
- Update the hard-coded Blender executable paths in `run_pipeline.sh` for your machine.
  Its `BLENDER_PYTHONPATH` points to a local `blender_py311_packages` directory that
  is deliberately omitted here. Supply packages compatible with your Blender Python,
  or adjust that setting to your installed environment.
- Supply your own `data/` directory containing `a_p_slice_9000_16_*`,
  `rho_0_slice_9000_16_*`, `Test_OS_collapse_magnetized_9000_16.hor_surface`,
  and `Test_OS_collapse_magnetized.wave_extraction.6` when plotting waves.
  Data and output directories have not been created in this extraction.

## Run after setup

From this folder:

```bash
START=0 END=25000 STEP=10 THREADS=20 ./run_pipeline.sh
./make_variable_rate_movies.sh with-wave
```

To render without the wave overlay:

```bash
PLOT_WAVE=false IMAGE_SUBDIR=images_no_wave ./run_pipeline.sh
./make_variable_rate_movies.sh no-wave
```

Use `./start_background.sh` for a background run; it creates `logs/` and a PID file.
The pipeline creates its own `output/` subdirectories.

The scripts retain the original run-specific settings, including physical/render
parameters, movie timing, and some historical absolute defaults. In particular,
pass explicit `--a-dir` and `--out-dir` if running `generate_field_lines.py` directly;
`run_pipeline.sh` already supplies those arguments.

## Verification

Copied scripts were checked for byte-for-byte equality with the source. Python
syntax and Bash syntax were checked without running the data processing or rendering.
An end-to-end run requires the omitted data and configured dependencies.
