# B0.004 spherical fluid with gravitational waves

For high temporal resolution at the same 8 t/M per second, run
`python3 plan_temporal_movie.py` followed by `sbatch render_temporal_movie.slurm`.
This produces a fresh 60-fps scene sequence: the eta wave is evaluated at every
video time (0.133333 t/M spacing), while matter and magnetic field lines use the
nearest available step-10 snapshot (about 0.177 t/M spacing after excision).
The original camera, 500000 height multiplier, pixel dimensions and memory
formula are preserved. Dense preparations are cached and incomplete jobs can
resume. Results, plan, worker logs, status and validation are stored in
`output/movie_amp500000_integer_time/temporal_8_tM/`.

To update the latest original-clock movie with the direct memory comparison at
8 t/M per real second, run `bash run_memory_movie.sh`. This reuses the existing
3D renders and Blender clock patches. The supplied total-memory column is
multiplied by `0.004**2 / 112 * spin_minus_2_Y20(pi/2, 0)`, exactly as in
`plot_memory_h+.py`; no empirical fit or time shift is applied. Both inset
curves share the existing display amplification during the transition.
The new movie and validation are in
`output/movie_amp500000_integer_time/memory_8_tM/`. The main sequence lasts
37.5 seconds and the fixed-time camera transition lasts 10 seconds, at 60 fps.

On Anvil, `run_local.sh` uses the workspace Blender 5.0 installation and its
Python 3.11 NumPy/SciPy packages through local `blender/` and
`blender_packages/` symlinks. Keep the corresponding installation in
`../os_collapse_1015/`. Host plotting uses Anaconda Python 3.11, and `bin/ffmpeg`
provides H.264 encoding. The default input is the sibling
`MHD_RK4_ICN_no_theta_surf_Nth16_B0.004_spherical_fluid` directory.

```bash
cd /anvil/scratch/x-xzhao14/os_collapse_B0004_spherical_with_gw
bash run_local.sh check
bash run_local.sh all
```

`check` validates inputs and dependencies without starting movie rendering.

Latest cylinder-wall/wider-inset template applied to the 15000_16 dataset.
No-wave movie is preserved separately. Endpoint step 34400, t=299.699, M=1
from OS_Input_Mag. Extraction .4, no memory color overlay.
Main height multiplier 500000, final transition multiplier 15000000;
matching 1D amplification 1 to 30, red 40pt label inset at (0.88,0.84).
The 30-fold transition gain keeps the late flattened waveform inside the inset;
the earlier large peaks clip during this amplitude zoom.
Radius-10 gray inner wall, smooth orbit to equatorial view, latest wide camera.
Variable movie timing uses switch 18300 and measured source intervals
0.08699 / 1.772, retaining the template's early slowdown and 60 fps output.
Prepared field/density images reused from the same B0.004 no-wave dataset.
Field level factor 0.50. All 3D and 1D images rendered anew.
See output/pipeline.status and logs/pipeline.log.
Run via run_local.sh; CPU capacity accounts for both affinity and cgroup quota.
The login session exposes 32 logical CPUs but is limited to two CPU equivalents
and 12 GiB RAM. For the full render use `sbatch render_movie.slurm`: one 128-core
compute node, 192 GiB RAM, 64 two-thread Blender workers, two-hour wall limit.
The job resumes valid completed frames and retains the approved render quality.
The approved movie uses the original perspective camera, the complete wave
surface, 421 radial by 320 angular samples, 16 render samples with denoising,
and 960 by 540 output, matching the approved t/M=60.4324 preview.
Outputs and worker logs are isolated in `output/movie_amp500000/`.
`pipeline.status`, `settings.json`, and `validation.json` record the run there;
the root `output/pipeline.status` also follows the active stage.

Render-process label: exe_TOV_peos. The default worker count equals the available
CPU capacity, with one thread per Blender worker unless RENDER_THREADS is set.
FFmpeg encoding uses the available CPU count. Set NW to reduce concurrency.
Scheduler logs are in `logs/slurm_movie_JOBID.log`; the submitted job ID is
recorded in `output/movie_amp500000/slurm_job_id`.
The original Blender executable path remains visible in full command lines.
The transition retains separate wave and memory panels; memory uses B0=0.004.
Their relative scientific normalization is unresolved, so no fitted amplitude
or time shift is applied to force agreement.
# Radius-500 rerun

Latest endpoint correction: retain extraction radius 400 but end at t/M=300.
The prepared run is `output/extraction_r400/temporal_8_tM_to300`, launched with
`finish_radius400_to300.slurm`. It reuses the matching radius-400 raw scenes,
rebuilds the insets and camera transition at t=300, and validates the final
2,850-frame movie: 37.5 seconds of evolution plus 10 seconds of fixed-time zoom.
The completed endpoint-400 movie is preserved in its original directory.

The current requested replacement uses extraction radius 400 and ends at
t/M=400. Its prepared plan is `output/extraction_r400/temporal_8_tM_to400/plan.json`.
To fit available shared-node capacity it now uses `render_radius400_chunks.slurm`:
64 independent one-hour chunks, at most eight concurrent, each with 8 CPUs and
14 GiB. The `finish_radius400_chunks.slurm` job must depend on successful
completion of the entire render array (`--dependency=afterok:ARRAY_JOB_ID`).
It composes the transition, encodes the MP4, and validates every decoded frame.
The active render and assembly IDs are in `submission.json` inside that work
directory; per-chunk progress is in `chunks/NNN/status`. Generated preprocessing
files are published atomically, so chunks can safely share completed caches.
An alternative single-node launcher is `render_radius400_to400.slurm`; do not
run it concurrently with the chunk array. It reaches 400 at
exactly 50 seconds (8 t/M per second), then holds time fixed for the 10-second
final zoom: 60 seconds total at 60 fps. It retains the central wave-sheet
opening of 15, which is required for valid late-time coverage, and the red
memory overlay scaled by B0²/400 and the equatorial spin-weight −2 Y20 factor.
The pending radius-500 endpoint-300 job was canceled when this replacement was
requested. Earlier completed movies are preserved.

The endpoint-300 variant is in `output/extraction_r500/temporal_8_tM_to300`:

```bash
env -u PYTHONPATH /apps/anvil/external/apps/conda/2024.02/bin/python radius_pipeline.py prepare --work output/extraction_r500/temporal_8_tM_to300 --coordinate-end 300 --inner-radius 15
sbatch render_radius500_to300.slurm
```

Its plan is already prepared. It reaches coordinate time t/M=300 at exactly
37.5 video seconds, followed by a 10-second fixed-time transition (47.5 seconds
total, 60 fps). The wave sheet's central opening is 15 rather than 10: this keeps
every displayed radius within the radius-500 source's retarded-time coverage at
t=300. The extraction radius, 8 t/M per second speed, red memory overlay,
coordinate-radius memory division, harmonic factor, and display gains are kept.
The main sequence has 2,250 frames; a separate t=300 endpoint scene supplies the
first transition frame so an extra main frame does not shift the timing.

The isolated radius-500 pipeline uses `data/Test_OS_collapse_magnetized.wave_extraction.15`
from the same B0=0.004 spherical-fluid simulation. It recomputes the eta modes,
equatorial strain CSV, diagnostics, waveform/memory/difference plots, every 3D
movie wave surface, the memory inset, and the final camera transition. Existing
radius-112 outputs are preserved. Density and field-line caches can be reused
because their simulation source is unchanged.

```bash
env -u PYTHONPATH /apps/anvil/external/apps/conda/2024.02/bin/python radius_pipeline.py prepare
sbatch render_radius500.slurm
```

Preparation is already complete for `output/extraction_r500/temporal_8_tM`.
To resume that run, submit the Slurm script without repeating preparation.
The job records its ID in `slurm_job_id`, progress in `status` and `logs/`, and
successful full-movie decode checks in `validation.json`. It retains 960×540,
60 fps, 8 t/M per second, and the existing display gains. It evaluates 2,196
distinct main-frame wave times and recomputes a 600-frame transition.

The source record ends at retarded time 281.3097. The movie therefore ends at
coordinate time 292.6667 (inner-edge retarded time 279.8941), followed by the
fixed-time transition. No upper-end extrapolation or zero filling is used.
Propagation uses the measured areal radius and M=1. The memory comparison uses
the supplied total memory × 0.004² / 500 × spin-weight −2 Y20(π/2,0), with no
fitted time shift or amplitude. This retains the radius-weighted-memory
normalization assumption; the supplied memory header alone does not verify it.

The new `hplus_1d.csv`, `memory_comparison.png`, `memory_differences.png`,
`differences.csv`, `radius_comparison.png`, and final MP4 live inside the new
output directory. The top-level `hplus_1d.csv` remains the old radius-112 export.

