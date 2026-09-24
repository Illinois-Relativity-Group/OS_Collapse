"""h+ against retarded time: full waveform, and the tail zoomed."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from wave_eta import prepare_wave, wave_height, tortoise_radius

WAVE = "data/Test_OS_collapse_magnetized.wave_extraction.4"
M_ADM = 1.0004
R_OBS = 10.0
TAIL_START = 250.0

data, source_u, clm = prepare_wave(WAVE, M_ADM, "latest")
rstar = tortoise_radius(np.array([R_OBS]), M_ADM)[0]

u = np.linspace(source_u.min(), source_u.max(), 4000)
hp = np.array([wave_height(WAVE, uu + rstar, np.array([R_OBS]), M_ADM, "latest")[0]
               for uu in u])
tail = u >= TAIL_START
print(f"tail mean {hp[tail].mean():+.4e}, range {hp[tail].min():+.4e} .. {hp[tail].max():+.4e}")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

ax1.plot(u, hp * 1e6, color="#2a78d6", linewidth=1.6)
ax1.axhline(0.0, color="#8a8985", linewidth=0.9, linestyle=(0, (4, 3)))
ax1.set_xlabel(r"$u = t - r_*$")
ax1.set_ylabel(r"$h_+$  [$10^{-6}$]")

ax2.plot(u[tail], hp[tail] * 1e8, color="#2a78d6", linewidth=1.6)
ax2.axhline(0.0, color="#8a8985", linewidth=0.9, linestyle=(0, (4, 3)))
ax2.set_ylim(bottom=0.0)
ax2.set_xlabel(r"$u = t - r_*$")
ax2.set_ylabel(r"$h_+$  [$10^{-8}$]")

for ax in (ax1, ax2):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(True, color="#8a8985", alpha=0.2, linewidth=0.6)
    ax.set_axisbelow(True)

fig.tight_layout()
fig.savefig("output/memory_sign.png", dpi=160)
print("wrote output/memory_sign.png")
