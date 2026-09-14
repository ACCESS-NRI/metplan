import json
import sys
from typing import Union

import xarray as xr

from metplan import __version__


def apply_provenance(
    xr_obj: Union[xr.Dataset, xr.DataArray],
    config: dict,
    command: str = " ".join(sys.argv[:]),
    era5land_version: str = None,
) -> xr.Dataset | xr.DataArray:
    """Apply provenence attributes to output files.

    Parameters
    ----------
    xr_obj : Union[xr.Dataset, xr.DataArray]
        xarray Dataset or DataArray object.
    config : dict
        Configuration for the current run.
    command : str
        Command used to run this instance of metplan.
    era5land_version : str, optional
        ERA5-Land version information, by default None

    Returns
    -------
    xr.Dataset | xr.DataArray
        Same type as first argument.
    """

    # Apply global attributes
    attrs = {
        "metplan_version": __version__,
        "metplan_command": command,
        "metplan_config": json.dumps(config),
        "era5land_version": era5land_version if era5land_version else "unknown",
    }

    # Update and return
    return xr_obj.assign_attrs(**attrs)
