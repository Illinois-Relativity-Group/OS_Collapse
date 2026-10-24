# B0.004 spherical fluid with gravitational waves

Latest cylinder-wall/wider-inset template applied to the 15000_16 dataset.
No-wave movie is preserved separately. Endpoint step 34400, t=299.699, M=1
from OS_Input_Mag. Extraction .4, no memory color overlay.
Main height multiplier 100000, final transition multiplier 10000000;
matching 1D amplification 1 to 100, red 40pt label inset at (0.88,0.84).
Radius-10 gray inner wall, smooth orbit to equatorial view, latest wide camera.
Variable movie timing uses switch 18300 and measured source intervals
0.08699 / 1.772, retaining the template's early slowdown and 60 fps output.
Prepared field/density images reused from the same B0.004 no-wave dataset.
Field level factor 0.50. All 3D and 1D images rendered anew.
See output/pipeline.status and logs/pipeline.log.
Run via run_local.sh; it enforces a five-CPU affinity limit.

Render-process label: exe_TOV_peos. Five shared logical CPUs maximum,
five single-threaded Blender workers, and FFmpeg encoding limited to five threads.
The original Blender executable path remains visible in full command lines.
