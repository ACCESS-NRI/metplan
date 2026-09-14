import json

import xarray as xr

import metplan.utils.metadata as mum
from metplan import __version__


def test_apply_provenance():
    """Test apply_provenance on the dataset"""

    dummy_config = {"test_key": "test_value"}
    dummy_command = "metplan run"
    ds = mum.apply_provenance(
        xr.Dataset(), config=dummy_config, command=dummy_command, era5land_version=None
    )

    assert ds.attrs["metplan_version"] == __version__
    assert ds.attrs["metplan_command"] == dummy_command
    assert ds.attrs["metplan_config"] == json.dumps(dummy_config)
    assert ds.attrs["era5land_version"] == "unknown"
