"""Checks for direct, already projected waveform propagation and normalization."""
from pathlib import Path
import tempfile
import unittest

import numpy as np

from supplied_equatorial import load_equatorial
from wave_eta import wave_height, tortoise_radius


class SuppliedEquatorialTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'wave.dat'
        self.path.write_text('# t_ret r*eta(theta=pi/2)/B_0^2\n-2 1\n0 3\n2 2\n')

    def test_no_second_harmonic_and_observer_delay(self):
        radii = np.array([15.25, 60., 220., 400.])
        for u, value in [(-2.,1.), (-1.,2.), (0.,3.), (1.,2.5), (2.,2.)]:
            actual = wave_height(self.path, u+tortoise_radius(radii,1.), radii)
            np.testing.assert_allclose(actual, value*.004**2/radii, rtol=1.e-12)

    def test_out_of_record_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'ends at'):
            wave_height(self.path, 2.1+tortoise_radius(15.25,1.), 15.25)

    def test_before_start_and_inside_horizon(self):
        np.testing.assert_array_equal(wave_height(self.path, -3.+tortoise_radius(15.25,1.),15.25),0.)
        np.testing.assert_array_equal(wave_height(self.path, 0., np.array([0.,1.,2.])),0.)

    def test_nonmonotonic_and_nonfinite_rejected(self):
        for rows in ['0 1\n0 2\n', '0 1\n1 nan\n']:
            self.path.write_text('# t_ret r*eta(theta=pi/2)/B_0^2\n'+rows)
            with self.assertRaises(ValueError):
                load_equatorial(self.path)


if __name__ == '__main__':
    unittest.main()
