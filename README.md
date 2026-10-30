## How to Run

Start by using find_time_switch.py to identify the index where the time step changes.
You will need to edit line 194 of `generate_field_lines.py` to correctly scale to your magnetic field strength. This code is set up for a a field of 0.002. The code reads `levels = [x * 0.25 for x in levels]`. If for example, you have a field strength of 0.001, change this line to `levels = [x * 0.25 * 0.5 for x in levels]`. This will be updated to be less janky in the future.
My data had files named like `a_p_slice_15000_16_*`. Your data may be named like `a_p_slice_9000_16_*`. Paths in many files are set up for "15000", if yours differs, you will need to go through each file an update this.
Use `run_pipeline.sh` from 0 to the time-switch-index using 200-index steps. Then use `run_pipeline.sh` again from the time-switch-index + 10 to whatever index is at t/M=300 using 10-index steps. When you run these make sure that GW waves are turned off. 
Run `make_variable_rate_movies.sh`. Check you are using the correct image directory name. The frame rate is set to have a continuous 8 t/M per second assuming 200-index steps prior to time-step-change and 10-index steps after. If you change the index step rate, you must scale this accordingly. Do not use a frame rate that is less than 20, this will be visibly jerky. If you encounter this issue, you need to decrease your step size to allow for a frame rate of >20 for the entire movie. The 8 t/M per second is the standard. Check that your final movie is 37.5 seconds.

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
#This is the movie frame generation setting that I suggest
Before: START=0 END=25000 STEP=200 THREADS=20
After: START=0 END=25000 STEP=10 THREADS=20
START=0 END=25000 STEP=200 THREADS=20 ./run_pipeline.sh
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

./make_variable_rate_movies.sh now take 
SWITCH_INDEX=16480
BEFORE_SOURCE_FPS=45.8666666667
AFTER_SOURCE_FPS=46.7242232611
Please refer to the following for customized movie
# Reference: suggested simulation dt per 10-index step.
# Reconsider these reference intervals if the index step changes.
# BEFORE_DT=0.0090925
# AFTER_DT=0.18525
You can use find_time_switch.py to find switch index




## Verification

Copied scripts were checked for byte-for-byte equality with the source. Python
syntax and Bash syntax were checked without running the data processing or rendering.
An end-to-end run requires the omitted data and configured dependencies.

## Oliver's Changes

The frame rate has been updated to match 8 t/M per second. This assumes a 200-index step before extraction and a 10-index switch after extraction.
