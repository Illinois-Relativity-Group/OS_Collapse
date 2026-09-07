import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import re
import argparse

from scipy.interpolate import griddata
from matplotlib.colors import LinearSegmentedColormap

# ============================================================
# User Inputs
# ============================================================

parser = argparse.ArgumentParser(description="Render density slices as transparent PNG files")
parser.add_argument("--rho-dir", type=Path, required=True)
parser.add_argument("--out-dir", type=Path, required=True)
parser.add_argument("--stride", type=int, default=10)
parser.add_argument("--start", type=int, default=None)
parser.add_argument("--end", type=int, default=None)
args = parser.parse_args()

RHO_DIR = args.rho_dir.expanduser().resolve()
OUTPUT_DIR = args.out_dir.expanduser().resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RHO_CUT = 1e-7        # physical cutoff (IMPORTANT)
RHO_MAX = 0.00373     # normalization reference

VMIN = 0.0
VMAX = 1.5

XY_LIMIT = 3

# ============================================================
# Files
# ============================================================

rho_files = sorted(RHO_DIR.glob("rho_0_slice_9000_16_*"))
print(f"Found {len(rho_files)} files")

# ============================================================
# Colormap (your style)
# ============================================================

# ============================================================
# Warm orange-red colormap
# ============================================================

dark_red   = (35/255,   0/255,   5/255)
deep_red   = (120/255,  5/255,  10/255)
red        = (220/255, 25/255,  10/255)
orange_red = (1.0,     0.22,    0.02)
orange     = (1.0,     0.55,    0.03)
yellow     = (1.0,     0.90,    0.30)

cmap = LinearSegmentedColormap.from_list(
    "orange_red_density",
    [
        (0.00, dark_red),
        (0.15, deep_red),
        (0.40, red),
        (0.65, orange_red),
        (0.85, orange),
        (1.00, yellow),
    ],
    N=256
)

# Masked low-density regions remain transparent
cmap.set_bad(color=(0.0, 0.0, 0.0, 0.0))
# ============================================================
# Loop
# ============================================================

for filename in rho_files:

    try:
        frame_number = int(filename.name.split("_")[-1])
    except ValueError:
        continue

    if frame_number % args.stride != 0:
        continue
    if args.start is not None and frame_number < args.start:
        continue
    if args.end is not None and frame_number > args.end:
        continue

    output_file = OUTPUT_DIR / f"rho_{frame_number:08d}.png"
    if output_file.exists():
        print(f"Already exists; skipping {output_file}")
        continue

    print(f"Processing {filename.name}")

    data = []

    # --------------------------------------------------------
    # Read file
    # --------------------------------------------------------
    with open(filename, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue

            vals = line.split()
            if len(vals) != 3:
                continue

            data.append([float(v) for v in vals])

    if len(data) == 0:
        continue

    data = np.array(data)

    r     = data[:, 0]
    theta = data[:, 1]
    rho   = data[:, 2]

    # --------------------------------------------------------
    # reshape
    # --------------------------------------------------------
    nr = len(np.unique(r))
    nt = len(np.unique(theta))

    try:
        R   = r.reshape(nr, nt)
        TH  = theta.reshape(nr, nt)
        RHO = rho.reshape(nr, nt)
    except ValueError:
        print("Cannot reshape:", filename.name)
        continue

    # --------------------------------------------------------
    # APPLY PHYSICAL CUT (IMPORTANT)
    # --------------------------------------------------------
    RHO = np.where(RHO < RHO_CUT, np.nan, RHO)

    # normalize AFTER masking
    RHO = RHO / RHO_MAX

    # convert to masked array for matplotlib transparency
    RHO = np.ma.masked_invalid(RHO)

    # --------------------------------------------------------
    # symmetry extension
    # --------------------------------------------------------
    TH_left  = np.zeros((nr, 1))
    TH_right = np.full((nr, 1), np.pi / 2)

    R_left  = R[:, 0:1]
    R_right = R[:, -1:]

    R   = np.hstack([R_left, R, R_right])
    TH  = np.hstack([TH_left, TH, TH_right])
    RHO = np.hstack([RHO[:, 0:1], RHO, RHO[:, -1:]])

    # --------------------------------------------------------
    # Cartesian transform
    # --------------------------------------------------------
    X = R * np.sin(TH)
    Y = R * np.cos(TH)

    # ============================================================
    # Plot
    # ============================================================

    fig, ax = plt.subplots(figsize=(8, 8))

    # fully transparent background
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    # quadrants
    ax.pcolormesh(X,  Y, RHO, shading="auto", cmap=cmap, vmin=VMIN, vmax=VMAX)
    ax.pcolormesh(-X, Y, RHO, shading="auto", cmap=cmap, vmin=VMIN, vmax=VMAX)
    ax.pcolormesh(X, -Y, RHO, shading="auto", cmap=cmap, vmin=VMIN, vmax=VMAX)
    ax.pcolormesh(-X, -Y, RHO, shading="auto", cmap=cmap, vmin=VMIN, vmax=VMAX)

    # --------------------------------------------------------
    # clean layout
    # --------------------------------------------------------
    ax.set_xlim(-XY_LIMIT, XY_LIMIT)
    ax.set_ylim(-XY_LIMIT, XY_LIMIT)
    ax.set_aspect("equal")

    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # --------------------------------------------------------
    # save transparent PNG
    # --------------------------------------------------------
    plt.savefig(
        output_file,
        dpi=200,
        bbox_inches="tight",
        pad_inches=0,
        transparent=True
    )

    plt.close()

    print(f"Saved {output_file}")

print("Done.")
