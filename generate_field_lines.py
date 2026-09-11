from pathlib import Path
import argparse
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scipy.interpolate import RectBivariateSpline


# ============================================================
# Helper functions
# ============================================================
def clean_contour_segments(segments, r_hide=7.0, min_points=20, min_length=0.5):
    """
    Remove only the parts of field lines inside the star/center.
    Keep the outer parts of the same field line.

    r_hide controls how much of the center/star to cut away.
    """
    clean = []

    for seg in segments:
        seg = np.asarray(seg)

        if len(seg) < min_points:
            continue

        x = seg[:, 0]
        y = seg[:, 1]
        r = np.sqrt(x**2 + y**2)

        keep = r > r_hide

        current = []

        for p, ok in zip(seg, keep):
            if ok:
                current.append(p)
            else:
                if len(current) >= min_points:
                    current = np.asarray(current)

                    dxy = np.diff(current[:, :2], axis=0)
                    length = np.sum(np.sqrt(np.sum(dxy**2, axis=1)))

                    if length > min_length:
                        clean.append(current)

                current = []

        if len(current) >= min_points:
            current = np.asarray(current)

            dxy = np.diff(current[:, :2], axis=0)
            length = np.sum(np.sqrt(np.sum(dxy**2, axis=1)))

            if length > min_length:
                clean.append(current)

    return clean

def chaikin(points, n_iter=2):
    """
    Smooth a polyline visually. This does not change the physics data;
    it only makes the rendered curve less polygonal.
    """
    pts = np.asarray(points, dtype=float)

    if len(pts) < 3:
        return pts

    closed = np.linalg.norm(pts[0] - pts[-1]) < 1e-8

    if closed:
        pts = pts[:-1]

    for _ in range(n_iter):
        new_pts = []

        if not closed:
            new_pts.append(pts[0])

        n = len(pts)
        last = n if closed else n - 1

        for i in range(last):
            p = pts[i]
            q = pts[(i + 1) % n]

            Q = 0.75 * p + 0.25 * q
            R = 0.25 * p + 0.75 * q

            new_pts.append(Q)
            new_pts.append(R)

        if not closed:
            new_pts.append(pts[-1])

        pts = np.asarray(new_pts)

    if closed:
        pts = np.vstack([pts, pts[0]])

    return pts


def extract_contour_segments(cs, ds=0.01):
    segments = []

    for level_segs in cs.allsegs:
        for seg in level_segs:

            if len(seg) < 2:
                continue

            x = seg[:, 0]
            y = seg[:, 1]

            dx = np.diff(x)
            dy = np.diff(y)

            s = np.concatenate(
                ([0.0], np.cumsum(np.sqrt(dx**2 + dy**2)))
            )

            length = s[-1]

            if length < ds:
                continue

            s_new = np.arange(0.0, length, ds)

            if len(s_new) == 0 or s_new[-1] < length:
                s_new = np.append(s_new, length)

            x_new = np.interp(s_new, s, x)
            y_new = np.interp(s_new, s, y)
            z_new = np.zeros_like(x_new)

            pts = np.column_stack([x_new, y_new, z_new])

            if len(pts) >= 2:
                pts = chaikin(pts, n_iter=2)
                segments.append(pts)

    return segments


def add_segments_to_ply(vertices, edges, segments, point_spacing):
    for pts in segments:

        pts = np.asarray(pts)

        offset = len(vertices)
        vertices.extend([tuple(p) for p in pts])

        for i in range(len(pts) - 1):
            edges.append((offset + i, offset + i + 1))

        # Close contour if it is basically closed already.
        p0 = np.array(pts[0])
        p1 = np.array(pts[-1])

        if np.linalg.norm(p1 - p0) < 2.5 * point_spacing:
            edges.append((offset + len(pts) - 1, offset))


# ============================================================
# USER INPUT
# ============================================================

parser = argparse.ArgumentParser(description="Convert a_p slice files to field-line PLY files")
parser.add_argument("--a-dir", type=Path,
    default=Path("/data/oscarzhao5/magnetised_star_collapse_3d_2ddata_0706/Test_OS_collapse_magnetized_MHD_RK4_ICN_no_theta_surf_B0.005_Kinnersley/a_p_slice"),
    help="directory containing a_p_slice_9000_16_* files")
parser.add_argument("--out-dir", type=Path,
    default=Path("/data/oscarzhao5/magnetised_star_collapse_3d_2ddata_0706/fieldline_ply"),
    help="output directory for field_lines_*.ply")
parser.add_argument("--stride", type=int, default=10,
    help="keep timesteps divisible by this value")
parser.add_argument("--start", type=int, default=None, help="first timestep to process")
parser.add_argument("--end", type=int, default=None, help="last timestep to process (inclusive)")
args = parser.parse_args()

A_DIR = args.a_dir.expanduser().resolve()
OUT_DIR = args.out_dir.expanduser().resolve()

OUT_DIR.mkdir(parents=True, exist_ok=True)

# Same number of field-line levels as the picture
levels = [ 0.00012, 0.0012, 0.0036, 0.0074, 0.0125, 0.0191, 0.0274, 0.0377, 0.0501, 0.0653]
# A_phi scales linearly with the initial field strength, so the level array
# scales with B_0. The shipped 0.25 factor was tuned for the B_0 = 0.002 run
# (magnetised_star_collapse_3d_2ddata_2026-09-02_B0.002). This case is
# B_0 = 0.0001 (see OS_Input_Mag), i.e. 20x weaker, so 0.25 * (0.0001/0.002).
levels = [x * 0.0125 for x in levels]

# Smaller = smoother PLY curves, but larger files
point_spacing = 0.02

# Fine interpolation grid
nr_fine = 2000
nt_fine = 1500

# Process every N frames. Use 1 if you want every available a_p file.
FRAME_STRIDE = args.stride

# Remove central glitch. Try 0.5 if it removes too much; try 2.0 if glitch remains.

MIN_POINTS = 20


# ============================================================
# Find files
# ============================================================

a_files = sorted(A_DIR.glob("a_p_slice_9000_16_*"))

print(f"Found {len(a_files)} files in {A_DIR}")

if len(a_files) == 0:
    raise RuntimeError(f"No a_p files found in {A_DIR}")


# ============================================================
# Main loop
# ============================================================

for a_file in a_files:

    frame = a_file.name.split("_")[-1]

    try:
        frame_number = int(frame)
    except ValueError:
        continue

    if frame_number % FRAME_STRIDE != 0:
        continue
    if args.start is not None and frame_number < args.start:
        continue
    if args.end is not None and frame_number > args.end:
        continue

    frame_padded = f"{frame_number:06d}"
    outfile = OUT_DIR / f"field_lines_{frame_padded}.ply"
    if outfile.exists():
        print(f"  Already exists; skipping {outfile}")
        continue

    print(f"Processing {a_file.name}")

    data = np.loadtxt(a_file, comments="#")

    if data.size == 0:
        print(f"  Empty file: {a_file.name}")
        continue

    r = data[:, 0]
    theta = data[:, 1]
    a_p = data[:, 2]

    r_unique = np.unique(r)
    theta_unique = np.unique(theta)

    nr = len(r_unique)
    nt = len(theta_unique)

    order = np.lexsort((theta, r))
    ap_sorted = a_p[order]

    try:
        AP = ap_sorted.reshape(nr, nt)
    except ValueError:
        print(f"  Cannot reshape {a_file.name}")
        continue

    # Add theta symmetry boundaries if missing.
    theta_grid = theta_unique.copy()
    AP_grid = AP.copy()

    if theta_grid[0] > 1e-12:
        theta_grid = np.insert(theta_grid, 0, 0.0)
        AP_grid = np.hstack([AP_grid[:, 0:1], AP_grid])

    if theta_grid[-1] < np.pi / 2 - 1e-12:
        theta_grid = np.append(theta_grid, np.pi / 2)
        AP_grid = np.hstack([AP_grid, AP_grid[:, -1:]])

    kx = min(3, len(r_unique) - 1)
    ky = min(3, len(theta_grid) - 1)

    spline = RectBivariateSpline(
        r_unique,
        theta_grid,
        AP_grid,
        kx=kx,
        ky=ky
    )

    r_fine = np.linspace(r_unique.min(), r_unique.max(), nr_fine)
    theta_fine = np.linspace(0.0, np.pi / 2, nt_fine)

    R_fine, TH_fine = np.meshgrid(
        r_fine,
        theta_fine,
        indexing="ij"
    )

    AP_fine = spline(r_fine, theta_fine)

    # Flux function. Field lines are contours of A_phi.
    Aphi_fine = AP_fine * R_fine * np.sin(TH_fine)**2

    X_fine = R_fine * np.sin(TH_fine)
    Y_fine = R_fine * np.cos(TH_fine)

    fig, ax = plt.subplots()
    ax.set_aspect("equal")

    vertices = []
    edges = []

    # Reflect the quadrant into all 4 meridional quadrants
    for sx, sy in [
        (1, 1),
        (-1, 1),
        (1, -1),
        (-1, -1),
    ]:

        cs = ax.contour(
            sx * X_fine,
            sy * Y_fine,
            Aphi_fine,
            levels=levels,
            colors="white"
        )

        segments = extract_contour_segments(
            cs,
            ds=point_spacing
        )


        # THIS is the important added line:
        segments = clean_contour_segments(
        segments,
        r_hide=0,
         min_points=MIN_POINTS,
        min_length=0.5
        )

        add_segments_to_ply(
            vertices,
            edges,
            segments,
            point_spacing
        )

    plt.close(fig)

    with open(outfile, "w") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")

        f.write(f"element vertex {len(vertices)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")

        f.write(f"element edge {len(edges)}\n")
        f.write("property int vertex1\n")
        f.write("property int vertex2\n")

        f.write("end_header\n")

        for x, y, z in vertices:
            f.write(f"{x} {y} {z}\n")

        for i, j in edges:
            f.write(f"{i} {j}\n")

    print(f"  Saved {outfile}")
    print(f"  Vertices = {len(vertices)}")
    print(f"  Edges    = {len(edges)}")

print("Done.")
