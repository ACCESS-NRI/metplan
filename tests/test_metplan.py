#!/usr/bin/env python

"""Tests for `metplan` package."""

import pytest
import xarray as xr
import numpy as np
from dask.distributed import LocalCluster, Client 

from metplan.metplan import run_met

# Receive consistent results with the test output file
seed_value = 42
rng = np.random.default_rng(seed=seed_value)

def test_sample_dataset():
    test_dataset = xr.open_dataset("tests/data/test_input.nc", engine="h5netcdf")
    expected_dataset = xr.open_dataset("tests/data/test_output.nc", engine="h5netcdf")
    cluster = LocalCluster(n_workers=4, threads_per_worker=1, memory_limit="4GB")
    client = Client(cluster)
    output_dataset = run_met(client, test_dataset)
    assert output_dataset.equals(expected_dataset)