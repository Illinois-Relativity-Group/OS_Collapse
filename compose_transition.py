#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from wave_eta import MODES, calc_Ylm, load_eta, source_retarded_times, tortoise_radius

OUT = ROOT / 'output/cylinder_wall_wider_inset_movie_frames'
OUT.mkdir(parents=True, exist_ok=True)
FPS = 60
N_HOLD_NORMAL = 30
N_CUT = 60
N_BLACK = 30
N_SIDE = 240
N_AMPLIFY = 180
N_HOLD_FINAL = 60
N_TOTAL = 600


def smooth(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def load_frame(path: Path) -> Image.Image:
    return Image.open(path).convert('RGB').resize((960, 540), Image.Resampling.LANCZOS)


def coord_time(path: Path) -> float:
    for line in path.read_text().splitlines()[:8]:
        m = re.search(r'coord time\s+([-+0-9.eE]+)', line)
        if m:
            return float(m.group(1))
    raise ValueError(f'No coordinate time in {path}')

normal = load_frame(ROOT / 'output/images_levels_x20_amp100000_to35000/render_00034400.png')
normal_cut = load_frame(ROOT / 'output/cylinder_wall_wider_movie_raw/cut_white_label.png')
raw = ROOT / 'output/cylinder_wall_wider_movie_raw'
black_cut = load_frame(raw / 'frame_0000.png')

mass = 1.0
data = load_eta(ROOT / 'data/Test_OS_collapse_magnetized.wave_extraction.4', 'latest')
source_u = source_retarded_times(data, mass)
harmonics = np.array([calc_Ylm(ell, m, np.pi / 2, 0).real for ell, m in MODES])
hplus = (data.eta @ harmonics).real
observer_delay = float(tortoise_radius(np.array([10.0]), mass)[0])
current_u = coord_time(ROOT / 'data/a_p_slice_15000_16_00034400') - observer_delay
y_extent = 1.08 * float(np.max(np.abs(hplus)))
outer_y_extent = 1.20 * y_extent

fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=120)
fig.patch.set_alpha(0)
ax.set_facecolor((0, 0, 0, 0))
reference_line, = ax.plot([], [], color='white', linewidth=1.5, alpha=0.0)
line, = ax.plot([], [], color='white', linewidth=2.6)
zero_line, = ax.plot([], [], color='white', linewidth=1.4, alpha=0.9)
y_axis, = ax.plot([], [], color='white', linewidth=1.4, alpha=0.9)
ax.set_ylim(-outer_y_extent, outer_y_extent)
ax.set_xticks([]); ax.set_yticks([])
for spine in ax.spines.values():
    spine.set_visible(True); spine.set_color('white'); spine.set_linewidth(1.8)
h_label = ax.text(0, 0, r'$h_+$', color='white', fontsize=28, ha='right', va='center')
t_label = ax.text(0, 0, r'$t_{\rm ret}$', color='white', fontsize=28, ha='left', va='top')
scale_label = ax.text(0.88, 0.84, '', transform=ax.transAxes, color='red', fontsize=40, ha='right', va='top')
fig.subplots_adjust(left=0.15, right=0.985, bottom=0.11, top=0.985)

import os
for frame_index in range(int(os.environ.get('OVERLAY_WORKER', '0')), N_TOTAL, int(os.environ.get('OVERLAY_WORKERS', '1'))):
    # Cut reveal may dissolve, but all orbit/amplitude frames are real renders.
    if frame_index < 30:
        scene=normal.copy(); amp_progress=0.0
    elif frame_index < 90:
        scene=Image.blend(normal,normal_cut,smooth((frame_index-30)/59)); amp_progress=0.0
    elif frame_index < 120:
        scene=black_cut.copy(); amp_progress=0.0
    elif frame_index < 360:
        scene=load_frame(raw / f'frame_{frame_index-119:04d}.png'); amp_progress=0.0
    elif frame_index < 540:
        i=frame_index-119
        scene=load_frame(raw / f'frame_{i:04d}.png')
        x=(i-240)/180
        amp_progress=x*x*x*(10+x*(-15+6*x))
    else:
        scene=load_frame(raw / 'frame_0420.png'); amp_progress=1.0
    colour='black' if frame_index>=90 else 'white'
    for artist in [reference_line,line,zero_line,y_axis,h_label,t_label,*ax.spines.values()]:
        artist.set_color(colour)

    factor = 10.0 ** (2.0 * amp_progress)
    # Keep the complete nonnegative waveform interval visible.  The faint
    # reference trace preserves the unscaled waveform while the bright trace
    # grows with the same display factor used by the 3D surface.
    x_left = 0.0
    x_right = current_u
    x_span = x_right - x_left
    outer_x = (x_left - 0.14 * x_span, x_right + 0.14 * x_span)
    ax.set_xlim(*outer_x)
    zero_line.set_data((x_left, x_right), (0, 0))
    y_axis.set_data((x_left, x_left), (-y_extent, y_extent))
    visible = (source_u >= x_left) & (source_u <= current_u)
    reference_line.set_data(source_u[visible], 1.05 * hplus[visible])
    reference_line.set_alpha(0.35 * amp_progress)
    line.set_data(source_u[visible], 1.05 * factor * hplus[visible])
    h_label.set_position((x_left - 0.015 * x_span, y_extent))
    t_label.set_position((x_right + 0.015 * x_span, -0.03 * y_extent))
    scale_label.set_position((0.88, 0.84))
    scale_label.set_text(rf'$\times {factor:.1f}$' if factor < 10 else rf'$\times {factor:.0f}$')
    scale_label.set_alpha(amp_progress)

    fig.canvas.draw()
    inset = Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy(), 'RGBA')
    target_width = round(scene.width * 0.38 * 0.80)
    target_height = round(inset.height * target_width / inset.width)
    inset = inset.resize((target_width, target_height), Image.Resampling.LANCZOS)
    composite = scene.convert('RGBA')
    composite.alpha_composite(inset, (round(scene.width * 0.005), scene.height - target_height - round(scene.height * 0.035)))
    composite.convert('RGB').save(OUT / f'frame_{frame_index:04d}.png')
    if frame_index == 0 or (frame_index + 1) % 30 == 0 or frame_index + 1 == N_TOTAL:
        print(f'Completed {frame_index + 1}/{N_TOTAL}', flush=True)

plt.close(fig)
(OUT / 'transition_info.txt').write_text(
    f'frames={N_TOTAL}\nfps={FPS}\nendpoint_step=34400\nendpoint_t=299.699\n'
    f'endpoint_t_over_M={299.699/mass:.9f}\n3d_scale=100000..10000000\n'
    f'1d_scale=1..100\nfull_time_left=0\nfull_time_right={current_u:.9f}\n'
)
