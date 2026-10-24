"""Overlay a fixed boxed h+ trace on a complete directory of 3D frames."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from wave_eta import MODES, calc_Ylm, load_eta, source_retarded_times, tortoise_radius


def coordinate_time(path: Path) -> float:
    with path.open() as stream:
        for line in stream:
            match = re.search(r"coord time\s+([-+0-9.eE]+)", line)
            if match:
                return float(match.group(1))
    raise ValueError(f"No coordinate time in {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--field-dir", type=Path, required=True)
    parser.add_argument("--wave-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mass", type=float, default=1.0)
    parser.add_argument("--inner-radius", type=float, default=10.0)
    parser.add_argument("--restart-policy", choices=("error", "latest"), default="latest")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=25000)
    parser.add_argument("--step", type=int, default=10)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    data = load_eta(args.wave_file, args.restart_policy)
    source_u = source_retarded_times(data, args.mass)
    harmonics = np.array([
        calc_Ylm(ell, m, np.pi / 2, 0).real for ell, m in MODES
    ])
    hplus = (data.eta @ harmonics).real

    # Show the complete retarded-time interval covered by this movie.  The old
    # significant-signal crop hid the quiet beginning and post-wave evolution.
    observer_delay = float(tortoise_radius(np.array([args.inner_radius]), args.mass)[0])
    first_field = args.field_dir / f"a_p_slice_15000_16_{args.start:08d}"
    last_field = args.field_dir / f"a_p_slice_15000_16_{args.end:08d}"
    x_limits = (
        max(0.0, coordinate_time(first_field) - observer_delay),
        max(0.0, coordinate_time(last_field) - observer_delay),
    )
    if x_limits[1] <= x_limits[0]:
        raise ValueError(f"Invalid movie retarded-time range: {x_limits}")
    y_extent = 1.08 * float(np.max(np.abs(hplus)))

    figure, axis = plt.subplots(figsize=(7.2, 3.8), dpi=120)
    figure.patch.set_alpha(0)
    axis.set_facecolor((0, 0, 0, 0))
    line, = axis.plot([], [], color="white", linewidth=2.6)
    x_span = x_limits[1] - x_limits[0]
    outer_x_limits = (x_limits[0] - 0.14 * x_span, x_limits[1] + 0.14 * x_span)
    outer_y_extent = 1.20 * y_extent
    axis.set_xlim(*outer_x_limits)
    axis.set_ylim(-outer_y_extent, outer_y_extent)
    axis.plot(x_limits, (0, 0), color="white", linewidth=1.4, alpha=0.9)
    axis.plot((x_limits[0], x_limits[0]), (-y_extent, y_extent),
              color="white", linewidth=1.4, alpha=0.9)
    axis.set_xticks([])
    axis.set_yticks([])
    for side in ("left", "right", "top", "bottom"):
        axis.spines[side].set_visible(True)
        axis.spines[side].set_color("white")
        axis.spines[side].set_linewidth(1.8)
    axis.annotate(r"$h_+$", xy=(x_limits[0], y_extent), xytext=(-5, 0),
                  textcoords="offset points", color="white", fontsize=28,
                  ha="right", va="center")
    axis.annotate(r"$t_{\rm ret}$", xy=(x_limits[1], 0), xytext=(5, -3),
                  textcoords="offset points", color="white", fontsize=28,
                  ha="left", va="top")
    figure.subplots_adjust(left=0.15, right=0.985, bottom=0.11, top=0.985)

    completed = 0
    expected = ((args.end - args.start) // args.step) + 1
    for timestep in range(args.start, args.end + 1, args.step):
        name = f"render_{timestep:08d}.png"
        source = args.image_dir / name
        field = args.field_dir / f"a_p_slice_15000_16_{timestep:08d}"
        destination = args.output_dir / name
        if destination.exists() and not args.force:
            completed += 1
            continue
        if not source.exists() or not field.exists():
            raise FileNotFoundError(f"Missing source pair for timestep {timestep}")

        current_u = coordinate_time(field) - observer_delay
        revealed = (source_u >= x_limits[0]) & (source_u <= current_u)
        line.set_data(source_u[revealed], 1.05 * hplus[revealed])
        figure.canvas.draw()
        inset = Image.fromarray(np.asarray(figure.canvas.buffer_rgba()).copy(), "RGBA")

        with Image.open(source) as frame_image:
            frame = frame_image.convert("RGBA")
            if frame.size != (args.width, args.height):
                frame = frame.resize((args.width, args.height), Image.Resampling.LANCZOS)
            target_width = round(frame.width * 0.38 * 0.80)
            target_height = round(inset.height * target_width / inset.width)
            scaled_inset = inset.resize((target_width, target_height), Image.Resampling.LANCZOS)
            edge_x = round(frame.width * 0.005)
            edge_y = round(frame.height * 0.035)
            frame.alpha_composite(
                scaled_inset,
                (edge_x, frame.height - target_height - edge_y),
            )
            frame.convert("RGB").save(destination, optimize=False)

        completed += 1
        if completed == 1 or completed % 50 == 0 or completed == expected:
            print(f"Completed {completed}/{expected}: {destination.name}", flush=True)

    plt.close(figure)


if __name__ == "__main__":
    main()
