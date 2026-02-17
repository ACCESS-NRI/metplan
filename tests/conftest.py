import pytest
import pandas as pd
import xarray as xr
import numpy as np
import yaml
from met_preprocessor.met_preprocessing import run_met

TEST_PARAM_MAP_FILE = "tests/data/test_param_map.yaml"

# Receive consistent results with the test output file
seed_value = 42
rng = np.random.default_rng(seed=seed_value)


@pytest.fixture(scope="module")
def param_map():
    with open(TEST_PARAM_MAP_FILE) as file:
        param_map = yaml.safe_load(file)
    return param_map


# TODO: Similar for leap year
# TODO: Trusted short script for vpd / calc

@pytest.fixture(scope="module")
def sample_xarray_data():
    lon = [-99, -98.75]
    lat = [42.25, 42.5]
    time = pd.date_range("2024-09-06 00:00:00", periods=24, freq="h")

    # Data Variables
    temperature = 15 + 8 * np.random.randn(2, 2, 24)
    rain = np.tile(np.arange(1, 25), (2, 2, 1))
    shortwave_rad = np.tile(np.arange(1e5, 25e5, 1e5), (2, 2, 1))
    longwave_rad = np.tile(np.arange(1e5, 25e5, 1e5), (2, 2, 1))
    wind_u = np.full((2, 2, 24), 3)
    wind_v = np.full((2, 2, 24), 4)
    rain = np.tile(np.arange(1, 25), (2, 2, 1))
    surf_pressure = 150 + 8 * np.random.randn(2, 2, 24)

    reference_time = pd.Timestamp("2014-09-05")
    ds = xr.Dataset(
        data_vars=dict(
            ssrd=(["lon", "lat", "time"], shortwave_rad, {"units": "J m**-2"}), #SWDown
            strd=(["lon", "lat", "time"], longwave_rad, {"units": "J m**-2"}), #LWDown
            t2m=(["lon", "lat", "time"], temperature, {"units": "K"}), #Tair
            tp=(["lon", "lat", "time"], rain, {"units": "mm"}), #Rainf
            u10=(["lon", "lat", "time"], wind_u, {"units": "m s**-1"}), #Wind
            v10=(["lon", "lat", "time"], wind_v, {"units": "m s**-1"}), #Wind
            sp=(["lon", "lat", "time"], surf_pressure, {"units": "Pa"}), #PSurf
        ),
        coords=dict(
            lon=lon,
            lat=lat,
            time=time,
            reference_time=reference_time,
        ),
        attrs=dict(description="Test dataset."),
    )
    return ds

def test_sample_dataset():
    test_dataset = xr.open_dataset("tests/data/test_input.nc")
    expected_dataset = xr.open_dataset("tests/data/test_output.nc")
    assert run_met(test_dataset).equals(expected_dataset)