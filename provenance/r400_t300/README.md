# Radius-400 gravitational-wave movie pipeline

Source snapshot for the completed B0=0.004 spherical-fluid collapse movie:
coordinate extraction radius **400**, final coordinate time **t/M=300**, evolution
at **8 t/M per second**, **60 fps**, **960 x 540**. The main evolution lasts
37.5 seconds; the camera orbit and amplitude zoom hold time at 300 for another
10 seconds. The validated output contains 2,850 frames and lasts 47.5 seconds.

The red memory curve is the supplied total-memory column times
`0.004**2 / 400 * 0.38627420202318946`. The harmonic is the equatorial spin-weight
-2, l=2, m=0 coefficient (standard polar angle pi/2). The wave reconstruction
uses eta modes l=2,4,6,8, m=0. Retarded-time propagation uses measured areal
radius, while memory division uses coordinate extraction radius. No fitted
amplitude or time shift is applied. The radius-weighted interpretation of the
supplied memory remains an assumption not established by its header alone.
The wave-sheet inner opening is 15; height scales are 500000 initially and
15000000 at the end of the zoom.

## Dependencies and inputs

Use Blender 5.0 with its bundled assets, NumPy/SciPy available to Blender,
FFmpeg with libx264, and host Python with `requirements.txt`. The completed
run used Anvil's `/apps/anvil/external/apps/conda/2024.02/bin/python` for host
processing. Clear the cluster module PYTHONPATH to avoid importing older NumPy.

Create these local links/directories in the checkout:

- `data`: the simulation directory `MHD_RK4_ICN_no_theta_surf_Nth16_B0.004_spherical_fluid`.
- `blender`: Blender's installation directory, containing `blender`.
- `blender_packages`: NumPy and SciPy installed for Blender's bundled Python;
  `install_dependencies.sh` accepts `BLENDER_PYTHON` for this step.
- `bin/ffmpeg`: the FFmpeg executable or a link to it.

Required simulation inputs include extraction `.14` (radius 400), extraction
`.4` (radius 112, used by comparison diagnostics), dense `a_p_slice_15000_16_*`
and `rho_0_slice_15000_16_*` snapshots through step 34420 and the next snapshot
needed to bracket t=300, and `Test_OS_collapse_magnetized_15000_16.hor_surface`.
The supplied `memory_data.dat` is included. Simulation dumps, rendered images,
software installations, caches, and the MP4 are external to this source snapshot.

## Reproduce from fresh inputs

From the checkout root, with the dependencies and links above configured:

```bash
mkdir -p logs .cache/matplotlib
unset PYTHONPATH
export MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.cache/matplotlib"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 radius_pipeline.py prepare \
  --work output/extraction_r400/temporal_8_tM_to300 \
  --wave-file data/Test_OS_collapse_magnetized.wave_extraction.14 \
  --coordinate-end 300 --inner-radius 15
python3 radius_pipeline.py run \
  --work output/extraction_r400/temporal_8_tM_to300 \
  --workers 4 --threads 2
```

Run the rendering command on allocated compute resources. Choose workers and
threads to fit the allocation; a fresh render takes longer than the cached
assembly job used for the completed movie. Preparation refuses to overwrite an
existing plan; resume with `run`. Generated plans contain absolute paths, so
prepare a new plan when moving to another checkout.

The output is
`output/extraction_r400/temporal_8_tM_to300/os_collapse_B0004_spherical_with_gw_memory_8_tM_high_temporal.mp4`.
Success is recorded by `status=COMPLETE` and a passing full-video decode in
`validation.json`. The endpoint first appears in the transition at video time
37.5 seconds; main frames cover t=0 through 299.8666667.

## Provenance of the finished movie

`provenance/r400_t300/` preserves the completed plan, validation, input hashes,
submission record, and reuse preflight. `source_sha256.json` records the copied
pipeline sources (time_bar.py retains the branch's equivalent whitespace). These records describe the existing completed run; they are
not instructions to reuse absolute paths on another machine.

The original production run first rendered radius-400 scenes through t=400
with `render_radius400_chunks.slurm` and `finish_radius400_chunks.slurm`.
The final t=300 correction reused the matching main-scene prefix via a
`main_raw` link to that run, rebuilt the insets and t=300 transition, and encoded
and validated using `finish_radius400_to300.slurm` (job 21873715).
That 30-minute launcher assumes those caches exist. The earlier chunk launchers
still target t=400 and are preserved as production provenance; use the explicit
t=300 commands above for a fresh reproduction. Slurm scripts retain the original
Anvil paths and account, which must be adjusted for another checkout/account.
`provenance/workspace_history.md` contains historical notes about other radii;
the configuration described here is the completed latest movie.
