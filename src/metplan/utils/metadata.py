import json
import re
import sys

import xarray as xr

import metplan.utils as mu
from metplan import __version__


def get_era5land_doi(ds: xr.Dataset) -> str:
    """Get the DOI out of the ERA5-Land input datasets.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset

    Returns
    -------
    str
        ERA5-Land DOI or unknown if unable to parse
    """
    try:
        summary = ds.attrs.get("summary")
        match = re.search(r"https?://[^\s]+?(?=[.,;:!?)]*(?:\s|$))", summary)
        return match.group(0) if match else "unknown"
    except:
        return "unknown"


def apply_provenance(
    xr_obj: xr.Dataset | xr.DataArray,
    config: dict,
    command: str = " ".join(sys.argv[:]),
) -> xr.Dataset | xr.DataArray:
    """Apply provenance attributes to output files.

    Parameters
    ----------
    xr_obj : Union[xr.Dataset, xr.DataArray]
        xarray Dataset or DataArray object.
    config : dict
        Configuration for the current run.
    command : str
        Command used to run this instance of metplan.

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
    }

    # Get user-supplied provenance from config
    provenance = config.get("provenance", {})

    # Ensure dict and has data
    if isinstance(provenance, dict) and len(provenance):
        attrs.update(**provenance)
    else:
        mu.get_logger().warning(
            "Provenance metadata is not configured. Data will lack provenance."
        )

    # Check if ERA5-Land, add the DOI
    if attrs.get("source", None) == "ERA5-Land" and not attrs.get("source_url"):
        attrs["source_url"] = get_era5land_doi(xr_obj)

    # Update and return
    return xr_obj.assign_attrs(**attrs)
