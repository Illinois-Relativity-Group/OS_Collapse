"""Read an already projected r*eta(pi/2)/B0^2 waveform in retarded time."""
from dataclasses import dataclass
import hashlib
from pathlib import Path

import numpy as np


@dataclass
class EquatorialWave:
    u: np.ndarray
    radius_weighted_hp: np.ndarray
    report: dict

    def strain(self, time, radius, mass=1.):
        from wave_eta import tortoise_radius
        time, radius = np.broadcast_arrays(np.asarray(time, float), np.asarray(radius, float))
        if not np.isfinite(time).all() or not np.isfinite(radius).all():
            raise ValueError('Nonfinite observer time or radius')
        valid = radius > 2*mass
        u = np.full(time.shape, self.u[0]-1.)
        u[valid] = time[valid]-tortoise_radius(radius[valid], mass)
        if np.any(valid & (u > self.u[-1]+1.e-10)):
            raise ValueError(f'Supplied waveform ends at u={self.u[-1]:.9f}; '
                             f'observer needs u={u[valid].max():.9f}')
        # Tolerance above only covers roundoff when reconstructing sample times.
        u = np.where(np.abs(u-self.u[0]) <= 1.e-10, self.u[0], u)
        weighted = np.interp(np.minimum(u,self.u[-1]), self.u, self.radius_weighted_hp, left=0.)
        return np.divide(weighted, radius, out=np.zeros(time.shape), where=valid)


def is_equatorial_file(path):
    with Path(path).open() as stream:
        return 'r*eta(theta=pi/2)/B_0^2' in stream.readline()


def load_equatorial(path, b0=.004):
    path = Path(path)
    if not is_equatorial_file(path):
        raise ValueError('Expected t_ret and r*eta(theta=pi/2)/B_0^2 header')
    values = np.loadtxt(path, comments='#', ndmin=2)
    if values.shape[1] != 2 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError('Supplied waveform must contain two finite columns and at least two rows')
    if np.any(np.diff(values[:,0]) <= 0):
        raise ValueError('Supplied retarded times must strictly increase')
    if not np.isfinite(b0) or b0 <= 0:
        raise ValueError('B0 must be finite and positive')
    report = dict(input=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  format='equatorial_radius_weighted', input_rows=len(values), B0=b0,
                  source_extraction_radius=None,
                  source_retarded_time_start=float(values[0,0]),
                  source_retarded_time_end=float(values[-1,0]),
                  normalization='r*hplus_equator = supplied second column * B0^2; already angularly projected',
                  additional_wave_harmonic_factor=False, time_shift=0.)
    return EquatorialWave(values[:,0], values[:,1]*b0**2, report)
