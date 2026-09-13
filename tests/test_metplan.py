#!/usr/bin/env python

"""Tests for `metplan` package."""

import tempfile
import os
import xarray as xr
import math
import numpy as np
from dask.distributed import LocalCluster, Client

from metplan.metplan import run_met
import metplan.utils as mu
from metplan.utils.logger import get_logger

# Receive consistent results with the test output file
seed_value = 42
rng = np.random.default_rng(seed=seed_value)


# https://github.com/CABLE-LSM/CABLE/blob/1701acb7c5dacb88df22d42a7f61d283cb285764/src/offline/cable_checks.F90#L60
# Constant ranges dict
ranges = {
    'SWDown':  [0.0, 1360.0],    # W/m^2
    'LWDown':  [0.0, 950.0],     # W/m^2
    'Rainf':   [0.0, 0.1],       # mm/s
    'Snowf':   [0.0, 0.1],       # mm/s
    'PSurf':   [500.0, 1100.0],  # mbar/hPa
    'Tair':    [200.0, 333.0],   # K
    'Qair':    [0.0, 0.1],       # g/g
    'Tscrn':   [-70.0, 70.0],    # oC
    'Qscrn':   [0.0, 0.1],       # kg/kg
    'CO2air':  [160.0, 2000.0],  # ppmv
    'Wind':    [0.0, 75.0],      # m/s
    'Wind_N':  [-75.0, 75.0],    # m/s
    'Wind_E':  [-75.0, 75.0],    # m/s
}

def round_to_power_of_ten(value):
    """Return the nearest power of ten to `value`, expressed as 1e-n."""
    if value <= 0:
        return 0.0
    n = round(-math.log10(value))
    return float(f"1e-{n}")

# Raw tolerance = (max - min) / 1e6, then rounded to nearest 1e-n
tolerances = {
    key: round_to_power_of_ten((vmax - vmin) / 1e6)
    for key, (vmin, vmax) in ranges.items()
}


def test_sample_dataset():
    
    os.environ['PROJECT'] = "TEST_PROJECT"
    os.environ['USER'] = "TEST_USER"
    config = mu.load_config("config.yaml")

    with tempfile.TemporaryDirectory() as td:

        config['output_dir'] = td

        test_dataset = xr.open_dataset("tests/data/test_input.nc", engine="h5netcdf")
        expected_dataset = xr.open_dataset("tests/data/test_output.nc", engine="h5netcdf")
        cluster = LocalCluster(n_workers=4, threads_per_worker=1, memory_limit="4GB")
        client = Client(cluster)
        output_dataset = run_met(config, test_dataset)
        for var in output_dataset.data_vars: 
            xr.testing.assert_allclose(output_dataset[var], expected_dataset[var], rtol=tolerances[var])