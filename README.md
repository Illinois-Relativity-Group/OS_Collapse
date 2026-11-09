# Supplied-waveform collapse movie pipeline

This is the pipeline for the completed November 5, 2026 movie. The supplied
`inputs/equatorial_wave_supplied_20261105.dat` drives both the 3D surface and
the black 1D waveform. Matter and field lines come from the **B0=0.004
spherical-fluid collapse** simulation.

The movie runs at **8 t/M per second**, **60 fps**, **960 x 540**, through
**t/M=300** at video time 37.5 seconds. A 10-second camera orbit and 30x amplitude
zoom then hold physical time fixed. The output is **47.5 seconds / 2,850 frames**;
all frames passed the completed run's decode validation. The red memory curve
and the h+ and retarded-time axis labels remain; the two curve legends are removed.

## Wave and memory normalization

The new file has two columns: supplied retarded time and
`r*eta(theta=pi/2)/B_0^2`. Its equatorial angular projection is already included.

- 3D surface: interpolate the second column at `u = t - r*(r)`, then multiply
  by `0.004**2 / r`, using each displayed observer radius.
- Black 1D curve: second column times `0.004**2 / 400`, with no additional
  spherical-harmonic factor and no fitted time shift.
- Red memory: the last column of `memory_data.dat` times
  `0.004**2 / 400 * 0.38627420202318946`. This harmonic is spin weight -2,
  l=2, m=0, at standard polar angle pi/2.

Here **400 is the chosen comparison radius**. The supplied waveform's header
does not identify its original extraction radius. The radius-weighted
interpretation of the memory column remains an assumption not established
by its header alone.

The wave-sheet opening is 15.25. At t=300, its latest required retarded time is
280.9682992563, within the supplied record ending at 281.0236697. Upper-end
extrapolation is rejected. The initial surface height multiplier is 500000;
the final multiplier is 15000000. The code also retains the earlier 36-column
eta-mode input route for old runs.

## Dependencies and inputs

Use Blender 5.0 with its bundled assets, NumPy/SciPy for Blender, FFmpeg with
libx264, and host Python with `requirements.txt`. The completed run used
`/apps/anvil/external/apps/conda/2024.02/bin/python` for host processing on Anvil.
Clear the module PYTHONPATH to avoid importing the cluster's older NumPy.

Configure these local paths in the checkout:

- `data`: link to `MHD_RK4_ICN_no_theta_surf_Nth16_B0.004_spherical_fluid`.
- `blender`: Blender installation directory, containing the executable `blender`.
- `blender_packages`: NumPy and SciPy installed for Blender's bundled Python.
  `install_dependencies.sh` accepts `BLENDER_PYTHON` for this setup.
- `bin/ffmpeg`: executable or link to an FFmpeg installation.

Required external simulation files are dense `a_p_slice_15000_16_*` and
`rho_0_slice_15000_16_*` snapshots covering t=0 through at least 301,
`Test_OS_collapse_magnetized_15000_16.hor_surface`, and extraction file
`Test_OS_collapse_magnetized.wave_extraction.4` for the old/new comparison
plot. The supplied waveform and `memory_data.dat` are included in Git.
Simulation dumps, software installations, caches, rendered frames, and MP4s
are external to this source repository.

## Reproduce from fresh inputs

From the configured checkout root:

```bash
mkdir -p logs .cache/matplotlib
unset PYTHONPATH
export MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.cache/matplotlib"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 radius_pipeline.py prepare \
  --work output/supplied_equatorial_20261105/temporal_8_tM_to300 \
  --wave-file inputs/equatorial_wave_supplied_20261105.dat \
  --coordinate-end 300 --inner-radius 15.25 --comparison-radius 400
```

On allocated compute resources, run the full pipeline (including missing
matter preprocessing, all 3D frames, overlays, encoding, and decode checks):

```bash
python3 radius_pipeline.py run \
  --work output/supplied_equatorial_20261105/temporal_8_tM_to300 \
  --workers 4 --threads 2
```

Choose workers/threads to fit the allocation. `prepare` refuses to overwrite
an existing plan; `run` resumes completed stages. Generate a new plan when
moving the checkout because plans record absolute paths.

## Production Slurm scripts

The completed movie used **`render_supplied_wave_chunks.slurm`**, followed by
**`finish_supplied_wave_chunks.slurm`**. The render array has 64 chunks with up
to eight simultaneous jobs, each requesting 8 CPUs and 14 GiB. The preview
script requires existing matter preprocessing for its two selected snapshots;
it does not prepare those caches. With those caches and the plan already ready:

```bash
preview_job=$(sbatch --parsable preview_supplied_wave.slurm)
render_job=$(sbatch --parsable --dependency=afterok:"$preview_job" render_supplied_wave_chunks.slurm)
sbatch --dependency=afterok:"$render_job" finish_supplied_wave_chunks.slurm
```

These scripts retain the exact production Anvil account and working paths.
Adjust their account, chdir, and work-directory settings for another checkout.
Do not run the array and the single-allocation `radius_pipeline.py run` against
the same work directory concurrently. The older `finish_radius400_to300.slurm`
is for the previous eta-source movie, not this supplied-waveform movie.

The output filename is
`output/supplied_equatorial_20261105/temporal_8_tM_to300/os_collapse_B0004_spherical_with_gw_memory_8_tM_high_temporal.mp4`.
Progress is recorded in `status` and `chunks/NNN/status`; successful completion
writes `COMPLETE` and a passing `validation.json`.

## Validation and provenance

```bash
python3 -m unittest test_supplied_equatorial -v
```

The tests cover direct B0^2/r scaling without a second harmonic factor,
retarded-time propagation, record bounds, and invalid inputs.
`provenance/supplied_equatorial_20261105/` preserves the finished run's plan,
source hashes, preflight, diagnostics, job IDs, and full-movie validation.
The production render array was 21983413 and assembly job was 21983414.
These are historical records with original absolute paths, not portable plans.
The preceding eta-source movie is documented in `provenance/r400_t300/README.md`.
