"""OS eta strain for this folder's Blender pipeline.

eta columns 28:32 are h+ modes (2,0), (4,0), (6,0), (8,0), not Psi4.
Parser, spin -2 harmonics and propagation reused from the ABID eta route.
This module is self-contained and does not read or generate VTK files.
"""
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import os
import numpy as np
from scipy.special import factorial as fact

MODES = ((2, 0), (4, 0), (6, 0), (8, 0))
ETA_COLUMNS = (28, 29, 30, 31)
HEADER = ['coord_time', 'proper_time', 'r_ext', 'r_areal']
for suffix in ('', '_qk'):
    for ell, _ in MODES:
        HEADER += [f'Re(psi4{suffix}_{ell}0)', f'h+dot{suffix}_{ell}0', f'h+{suffix}_{ell}0']
HEADER += [f'eta_{ell}0' for ell, _ in MODES]
HEADER += ['GW_luminosity', 'GW_energy', 'GW_luminosity_qk', 'GW_energy_qk']

def calc_l_d_ms(l, m, theta, s=-2):
    sint = np.sin(theta / 2); cost = np.cos(theta / 2)
    k_i = np.maximum(0, m - s); k_f = np.minimum(l + m, l - s)
    pt1 = np.sqrt(fact(l + m) * fact(l - m) * fact(l + s) * fact(l - s))
    pt2 = 0.0
    for k in range(k_i, k_f + 1, 1):
        num = ((-1) ** k) * (sint ** (2 * k + s - m)) * (cost ** (2 * l + m - s - 2 * k))
        den = fact(k) * fact(l + m - k) * fact(l - s - k) * fact(s - m + k)
        pt2 += num / den
    return pt1 * pt2


def calc_Ylm(l, m, theta, phi, s=-2):
    coeff = ((-1) ** s) * np.sqrt((2 * l + 1) / (4 * np.pi)) * calc_l_d_ms(l, m, theta)
    return coeff * np.cos(m * phi) + coeff * np.sin(m * phi) * 1j


def tortoise_radius(radius, mass):
    """ABID's r* = r + 2 M log(r/(2 M) - 1), in input code units."""
    radius = np.asarray(radius, dtype=float)
    if not np.isfinite(mass) or mass <= 0:
        raise ValueError("M_ADM must be finite and positive")
    if np.any(~np.isfinite(radius)) or np.any(radius <= 2 * mass):
        raise ValueError("Tortoise radius requires finite r > 2 M_ADM")
    return radius + 2 * mass * np.log(radius / (2 * mass) - 1)


def retarded_time(time, travel_radius, extraction_radius_star=0.0):
    """Shared outgoing-wave shift; all arguments use the same code units."""
    return time - (travel_radius - extraction_radius_star)


def sample_eta_clm(time, radius, source_u, clm, mass):
    """Evaluate eta coefficients at u=t-r*(r), with zero outside the record.

    source_u = coordinate_time - r*(r_areal(coordinate_time)). Thus the
    propagation delay vanishes at each source sample's extraction radius.
    Only interpolation is performed; eta is never integrated.
    """
    radius = np.asarray(radius, dtype=float)
    query_time, radius = np.broadcast_arrays(time, radius)
    valid = radius > 2 * mass
    query_u = np.full(radius.shape, source_u[0] - 1.0)
    query_u[valid] = retarded_time(query_time[valid], tortoise_radius(radius[valid], mass))
    # Off the end of the record np.interp would return 0, which renders as a
    # flat sheet indistinguishable from "the wave decayed". That silently put a
    # growing dead zone into the late frames of every movie -- at t = 736.7 only
    # r >= 175 of a 10..220 mesh still had data -- and it is what made a late
    # sample read as "no memory". Refuse instead of inventing zeros.
    # WAVE_ALLOW_OFF_RECORD=true restores the old zero-fill.
    off = valid & ((query_u < source_u[0]) | (query_u > source_u[-1]))
    if off.any() and os.environ.get("WAVE_ALLOW_OFF_RECORD", "false").lower() != "true":
        bad_r = np.asarray(radius)[off]
        bad_u = query_u[off]
        raise ValueError(
            f"{off.sum()} of {valid.sum()} sampled radii fall outside the eta "
            f"record u=[{source_u[0]:.3f}, {source_u[-1]:.3f}]: "
            f"r={bad_r.min():.3f}..{bad_r.max():.3f} need "
            f"u={bad_u.min():.3f}..{bad_u.max():.3f}. "
            f"Use an earlier time, a smaller r_max, or set "
            f"WAVE_ALLOW_OFF_RECORD=true to zero-fill them.")

    sampled = np.zeros(radius.shape + (clm.shape[1],), dtype=complex)
    for mode in range(clm.shape[1]):
        sampled[..., mode] = np.interp(query_u, source_u, clm[:, mode].real, left=0, right=0)
        sampled[..., mode] += 1j * np.interp(query_u, source_u, clm[:, mode].imag, left=0, right=0)
    sampled[~valid] = 0
    return sampled


def eta_strain(time, radius, ylm, source_u, clm, mass):
    """Unscaled h+, h_cross using ABID's 2 Re(clm Y/r), -2 Im(clm Y/r)."""
    sampled = sample_eta_clm(time, radius, source_u, clm, mass)
    field = np.sum(ylm * sampled, axis=-1)
    field = np.divide(field, radius, out=np.zeros_like(field), where=np.asarray(radius) > 2 * mass)
    return 2 * field.real, -2 * field.imag


@dataclass
class EtaData:
    time: np.ndarray
    radius: np.ndarray
    eta: np.ndarray
    report: dict

    @property
    def clm(self):
        # ABID divides by the observer radius, then multiplies Re(...) by 2.
        # Multiplication by THIS sample's areal radius cancels that 1/r exactly
        # at extraction. There is deliberately no division by M_ADM.
        return (0.5 * self.radius[:, None] * self.eta).astype(complex)


def load_eta(path, restart_policy='error'):
    """Validate the named 36-column layout; preserve nonuniform sample times.

    With explicit 'latest', a new timestamp <= the previous timestamp starts
    a replacement history: discard all earlier rows at/after the restart time.
    Merely sorting and deduplicating would mix abandoned and restarted runs.
    """
    if restart_policy not in ('error', 'latest'):
        raise ValueError('restart_policy must be error or latest')
    path = Path(path)
    header_count = 0
    with path.open() as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.lstrip().startswith('#'):
                continue
            if 'eta_20' in line or ('coord time' in line and 'r_areal' in line):
                fields = line.lstrip()[1:].strip().replace('coord time', 'coord_time').replace('proper time', 'proper_time').split()
                if fields != HEADER:
                    raise ValueError(f'{path}:{line_no}: unexpected 36-column wave-extraction header')
                header_count += 1
    if not header_count:
        raise ValueError(f'{path}: missing named wave-extraction header; cannot verify eta columns')
    values = np.loadtxt(path, comments='#', ndmin=2)
    if values.shape[1] != 36 or len(values) < 2:
        raise ValueError(f'{path}: expected at least two rows of 36 numbers, got {values.shape}')
    if not np.isfinite(values).all():
        raise ValueError(f'{path}: nonfinite numerical data')
    if np.any(values[:, 2:4] <= 0):
        raise ValueError(f'{path}: extraction radii must be positive')
    if not np.allclose(values[:, 2], values[0, 2], rtol=1e-10, atol=0):
        raise ValueError(f'{path}: r_ext changes; supply a single extraction worldtube')
    restarts = np.flatnonzero(np.diff(values[:, 0]) <= 0) + 1
    if len(restarts) and restart_policy == 'error':
        raise ValueError(f'{path}: {len(restarts)} non-increasing time boundaries; inspect the file or explicitly select --restart-policy latest')
    keep, times = [], []
    for row, t in enumerate(values[:, 0]):
        if times and t <= times[-1]:
            first = bisect_left(times, t)
            del times[first:]
            del keep[first:]
        keep.append(row)
        times.append(t)
    cleaned = values[keep]
    if len(cleaned) < 2:
        raise ValueError('Fewer than two samples remain after restart reconciliation')
    report = {
        'input': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'input_rows': len(values), 'retained_rows': len(cleaned),
        'restart_policy': restart_policy, 'restart_boundaries': len(restarts),
        'discarded_rows': len(values) - len(cleaned),
        'restart_coordinate_times': values[restarts, 0].tolist(),
        'r_ext': float(cleaned[0, 2]),
        'r_areal_min': float(cleaned[:, 3].min()), 'r_areal_max': float(cleaned[:, 3].max()),
        'coordinate_time_start': float(cleaned[0, 0]), 'coordinate_time_end': float(cleaned[-1, 0]),
        'sample_dt_min': float(np.diff(cleaned[:, 0]).min()),
        'sample_dt_max': float(np.diff(cleaned[:, 0]).max()),
    }
    return EtaData(cleaned[:, 0], cleaned[:, 3], cleaned[:, ETA_COLUMNS], report)


def source_retarded_times(data, mass):
    source_u = data.time - tortoise_radius(data.radius, mass)
    if np.any(np.diff(source_u) <= 0):
        raise ValueError('t-r*(r_areal(t)) must increase; extraction history is not suitable for interpolation')
    return source_u


def diagnostics(data, mass, output):
    """Run all checks before rendering, using the actual Blender strain evaluator."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    source_u = source_retarded_times(data, mass)
    # Serialize and reload the actual representation used to displace the Blender mesh.
    np.savetxt(output / 'gw.clm', data.clm, fmt='%.18e',
               header='OS eta: columns (2,0) (4,0) (6,0) (8,0); clm = r_areal * eta / 2; no mass rescaling')
    clm = np.loadtxt(output / 'gw.clm', dtype=complex, ndmin=2)
    sampled = sample_eta_clm(data.time, data.radius, source_u, clm, mass)
    recovered = 2 * sampled.real / data.radius[:, None]
    errors = np.max(np.abs(recovered - data.eta), axis=0)
    peaks = np.max(np.abs(data.eta), axis=0)
    relative = np.divide(errors, peaks, out=np.zeros_like(errors), where=peaks != 0)
    np.testing.assert_allclose(recovered, data.eta, rtol=1e-12, atol=1e-30)
    harmonics = np.array([calc_Ylm(ell, m, np.pi / 2, 0) for ell, m in MODES])
    direct = (data.eta @ harmonics).real
    hp, hc = eta_strain(data.time, data.radius, harmonics, source_u, clm, mass)
    np.testing.assert_allclose(hp, direct, rtol=1e-12, atol=max(1e-30, np.max(np.abs(direct)) * 1e-14))
    np.testing.assert_allclose(hc, 0, rtol=0, atol=1e-30)
    # Also evaluate away from the equator and at multiple azimuths.
    theta = np.linspace(0, np.pi, 31)[:, None]
    phi = np.linspace(-np.pi, np.pi, 17)[None, :]
    angular = np.stack([calc_Ylm(ell, m, theta, phi) for ell, m in MODES], axis=-1)
    np.testing.assert_allclose(angular.imag, 0, atol=1e-30)
    np.testing.assert_allclose(angular, np.broadcast_to(angular[:, :1, :], angular.shape), atol=1e-30)
    report = dict(data.report, modes=MODES, eta_columns_zero_based=ETA_COLUMNS,
                  normalization='clm_l0(t) = r_areal(t) * eta_l0(t) / 2; h+ = 2 Re(sum(clm Y)/r)',
                  mass=mass, time_column='coordinate time (0), code units',
                  propagation='u_source = t_source - r*(r_areal(t_source)); u_query = t_observer - r*(r)',
                  interpolation='linear in source retarded time; zero outside recorded interval',
                  origin_and_horizon='zero at r <= 2 M_ADM',
                  equatorial_spin_minus_2_Y_l0=harmonics.real.tolist(),
                  mode_max_absolute_error=errors.tolist(), mode_max_relative_to_peak_error=relative.tolist(),
                  hcross_max_absolute=float(np.max(np.abs(hc))), diagnostics_passed=True)
    (output / 'eta_diagnostics.json').write_text(json.dumps(report, indent=2) + '\n')
    np.savetxt(output / 'eta_modes.dat', np.column_stack((data.time, data.radius, data.eta)),
               header='coordinate_time r_areal eta_20 eta_40 eta_60 eta_80')
    np.savetxt(output / 'eta_equator.dat', np.column_stack((data.time, source_u, hp, hc)),
               header='coordinate_time source_retarded_time hplus_equator hcross_equator (unscaled)')
    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True, constrained_layout=True)
    for i, ax in enumerate(axes):
        ax.plot(data.time, data.eta[:, i], lw=0.9)
        ax.set_ylabel(rf'$\eta_{{{MODES[i][0]}0}}$')
        ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 0))
        ax.grid(alpha=0.25)
    axes[0].set_title('OS collapse: supplied strain modes at the extraction radius')
    axes[-1].set_xlabel('Coordinate time (code units)')
    fig.savefig(output / 'eta_modes.png', dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4), constrained_layout=True)
    ax.plot(data.time, hp, lw=1, label=r'$h_+(\theta=\pi/2)$')
    ax.plot(data.time, hc, lw=0.8, label=r'$h_\times$')
    ax.set(xlabel='Coordinate time (code units)', ylabel='Strain at extraction (unscaled)',
           title='Spin weight −2 reconstruction from (2,0), (4,0), (6,0), (8,0)')
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(output / 'eta_equator.png', dpi=160)
    plt.close(fig)
    print(f'Diagnostics passed: max mode error={errors.max():.3e}, max |h_cross|={np.max(np.abs(hc)):.3e}', flush=True)
    return source_u, clm, report


@lru_cache(maxsize=4)
def _prepare(path, mtime_ns, size, mass, restart_policy):
    data = load_eta(path, restart_policy)
    return data, source_retarded_times(data, mass), data.clm


def prepare_wave(path, mass=1.00071, restart_policy='latest'):
    path = Path(path).resolve()
    stat = path.stat()
    return _prepare(str(path), stat.st_mtime_ns, stat.st_size, mass, restart_policy)


def wave_height(path, current_time, radii, mass=1.00071, restart_policy='latest'):
    """Unscaled equatorial h+ at observer radii, already including 1/r.

    2*Re(clm)/r with clm=r_areal*eta/2 cancels the factor two. Thus
    h+ at extraction equals sum(eta_l0 * spin_minus_2_Y_l0).
    """
    data, source_u, clm = prepare_wave(path, mass, restart_policy)
    ylm = np.array([calc_Ylm(ell, m, np.pi/2, 0) for ell, m in MODES])
    hp, hc = eta_strain(current_time, np.asarray(radii), ylm, source_u, clm, mass)
    if not np.isfinite(hp).all() or np.any(hc != 0):
        raise ValueError('Invalid axisymmetric eta strain')
    return hp


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--mass', type=float, default=1.00071)
    parser.add_argument('--restart-policy', choices=('error', 'latest'), default='latest')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data = load_eta(args.input, args.restart_policy)
    diagnostics(data, args.mass, args.output)
