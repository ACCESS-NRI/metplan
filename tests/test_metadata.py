import json

import xarray as xr

import metplan.utils as mu
import metplan.utils.metadata as mum
from metplan import __version__


def test_apply_provenance():
    """Test apply_provenance on the dataset"""
    config = mu.load_config(user_config="tests/data/test_config.yaml")

    dummy_command = "metplan run"
    ds = mum.apply_provenance(xr.Dataset(), config=config, command=dummy_command)

    assert ds.attrs["metplan_version"] == __version__
    assert ds.attrs["metplan_command"] == dummy_command
    assert ds.attrs["metplan_config"] == json.dumps(config)
    assert ds.attrs["source"] == "ERA5-Land"
    assert ds.attrs["source_url"] == "unknown"
    assert ds.attrs["license"] == "CC-BY-4.0"


def test_get_era5land_version():
    """Get the ERA5-Land version (doi) out of the dataset"""

    doi = "http://dx.doi.org/10.25914/5f48874388857"

    ds = xr.Dataset()

    # Check unparseable
    assert mum.get_era5land_doi(ds) == "unknown"

    # Check legitimate attribute
    ds.attrs["summary"] = f"ERA5 ... please see {doi}"
    assert doi == mum.get_era5land_doi(ds)
