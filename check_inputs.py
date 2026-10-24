"""Read-only preflight for the frozen B0.002, t~300 movie inputs."""
from pathlib import Path
import sys
import numpy, scipy, matplotlib, PIL
root=Path(sys.argv[1]).expanduser().resolve()
required=['Test_OS_collapse_magnetized.wave_extraction.4','Test_OS_collapse_magnetized_15000_16.hor_surface']
for i in range(0,34401,100):
 required += [f'a_p_slice_15000_16_{i:08d}',f'rho_0_slice_15000_16_{i:08d}']
missing=[n for n in required if not (root/n).is_file()]
if missing:
 raise SystemExit(f'Missing {len(missing)} input files in {root}:\n'+ '\n'.join(missing[:20]))
print(f'Input check passed: {len(required)} files in {root}')
