#!/usr/bin/env python

"""Tests for `metplan` package."""

import math
import os
import tempfile

import numpy as np
import pandas as pd
import pytest
import xarray as xr

import metplan.utils as mu
from metplan.metplan import (
    PARAM_MAP_FILE_NAME,
    preprocess_land_sea_mask,
    run_met,
    standardise_grid,
)

# Receive consistent results with the test output file
seed_value = 42
rng = np.random.default_rng(seed=seed_value)


# https://github.com/CABLE-LSM/CABLE/blob/1701acb7c5dacb88df22d42a7f61d283cb285764/src/offline/cable_checks.F90#L60
# Constant ranges dict
ranges = {
    "SWdown": [0.0, 1360.0],  # W/m^2
    "LWdown": [0.0, 950.0],  # W/m^2
    "Rainf": [0.0, 0.1],  # mm/s
    "Snowf": [0.0, 0.1],  # mm/s
    "PSurf": [500.0, 1100.0],  # mbar/hPa
    "Tair": [200.0, 333.0],  # K
    "Qair": [0.0, 0.1],  # g/g
    "Tscrn": [-70.0, 70.0],  # oC
    "Qscrn": [0.0, 0.1],  # kg/kg
    "CO2air": [160.0, 2000.0],  # ppmv
    "Wind": [0.0, 75.0],  # m/s
    "Wind_N": [-75.0, 75.0],  # m/s
    "Wind_E": [-75.0, 75.0],  # m/s
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


# We use both types of input (Reading from NetCDF and existing fixture)
@pytest.fixture(
    scope="module",
    params=[
        ("tests/data/test_input.nc", "tests/data/test_output.nc"),
        # ("sample_xarray_data", None),
    ],
)
def met_run(request):
    """Run metplan for sample datasets."""
    input_path, expected_path = request.param

    os.environ["PROJECT"] = "TEST_PROJECT"
    os.environ["USER"] = "TEST_USER"
    config_path = "tests/data/test_config.yaml"
    config = mu.load_config(user_config=config_path)

    # Override the default with the test data
    config["directories"] = [input_path]
    expected_dataset = xr.open_dataset(expected_path)

    with tempfile.TemporaryDirectory() as td:
        # Write to the temp space
        config["output_dir"] = td

        # Start dask
        client, cluster = mu.start_dask_client(config)

        # Run
        output_dataset = run_met(config, var="SWdown")

        yield output_dataset, expected_dataset

        mu.stop_dask_client(client, cluster)


def test_sample_dataset(met_run):
    """Test dataset creation is within tolerances."""
    output_dataset, expected_dataset = met_run
    param_map = mu.load_param_map(PARAM_MAP_FILE_NAME)
    if expected_dataset is None:
        pytest.skip("No expected output for this input")
    for var in output_dataset.data_vars:
        # Check units
        assert output_dataset[var].attrs["units"] == param_map[var]["unit"], var
        # Check values upto tolerance
        xr.testing.assert_allclose(
            output_dataset[var], expected_dataset[var], rtol=tolerances[var]
        )


class TestStandardiseGrid:

    def test_preprocess_unwrapped_grid_data(self):
        """0-360 longitudes are wrapped to [-180, 180) and sorted ascending.
        Latitude is rounded but keeps its (north to south) order."""
        ds = xr.Dataset(
            {"t": (("lat", "lon"), [[0.0, 1.0, 2.0, 3.0], [4.0, 5.0, 6.0, 7.0]])},
            coords={
                "lon": [0.0, 90.0, 180.0, 270.0],
                "lat": [-40.0, -40.5],
            },
        )
        out = standardise_grid(ds)
        # Longitude gets wrapped
        np.testing.assert_array_equal(out["lon"], [-180.0, -90.0, 0.0, 90.0])
        # Latitude remains same
        np.testing.assert_array_equal(out["lat"], [-40.0, -40.5])
        # Data must move with its coordinate
        np.testing.assert_array_equal(
            out["t"], [[2.0, 3.0, 0.0, 1.0], [6.0, 7.0, 4.0, 5.0]]
        )


    def test_preprocess_wrapped_data(self):
        """Lat/lon already in range, so dataset should be preserved."""
        lon = [-99.0, -98.75, 143.5, 179.9]
        lat = [90.0, 0.0, -42.25, -90.0]
        ds = xr.Dataset(coords={"lon": lon, "lat": lat})
        out = standardise_grid(ds)
        np.testing.assert_allclose(out["lon"], lon)
        np.testing.assert_allclose(out["lat"], lat)


class TestPreprocessLandSeaMask:
    """Testing for preprocess_land_sea_mask."""
 
    @pytest.fixture
    def lsm_dataset(self):
        """ERA5-Land like landsea mask dataset with a length-1 time dimension."""
        frac = np.array([[[0.0, 0.49], [0.5, 1.0]]])  # (time, lat, lon)
        return xr.Dataset(
            {"lsm": (("time", "lat", "lon"), frac)},
            coords={
                "time": pd.to_datetime(["1950-01-01"]),
                "lat": [-42.0, -42.1],
                "lon": [147.0, 147.1],
            },
        )
 
    def test_preprocess_land_sea_mask(self, lsm_dataset):
        param_map = mu.load_param_map(PARAM_MAP_FILE_NAME)
        out = preprocess_land_sea_mask(lsm_dataset, param_map)
        # fraction >= 0.5 is land (0), otherwise sea (1).
        np.testing.assert_array_equal(out["lsm"].values, [[1, 1], [0, 0]])
        assert out["lsm"].dtype == np.int32
        # Time dimension is removed and only lat/lon remain
        assert "time" not in out["lsm"].dims
        assert out["lsm"].dims == ("lat", "lon")

@pytest.fixture(scope="module")
def cable_time_reference():
    """CABLE expects the time axis to be encoded relative to this reference."""
    return {
        "reference": pd.Timestamp("1900-01-01 01:00:00"),
        "units": "hours since 1900-01-01 01:00:00",
        "calendar": "proleptic_gregorian",
    }


def test_dataset_time_encoding(met_run, cable_time_reference):
    """Test the time encoding is correctly applied."""
    output_dataset, _ = met_run
    encoding = output_dataset["time"].encoding
    assert encoding["units"] == cable_time_reference["units"]
    assert encoding["calendar"] == cable_time_reference["calendar"]


def test_output_has_cable_lat_lon_dims(met_run):
    """Written variables use lat/lon dimensions with lat/lon coordinates."""
    output_dataset, _ = met_run
    for var in output_dataset.data_vars:
        assert {"lat", "lon"} <= set(output_dataset[var].dims)
    assert output_dataset["lat"].dims == ("lat",)
    assert output_dataset["lon"].dims == ("lon",)
