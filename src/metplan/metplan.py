"""Main module."""

import os
import time
from collections.abc import Collection, Hashable
from typing import Any

import xarray as xr
import yaml
from hpcpy.utilities import interpolate_string_template

import metplan.utils as mu
from metplan.accu import daily_to_hourly_acc
from metplan.dependency import generate_calculations
from metplan.unit_conv import UnitConversion
from metplan.utils.files import list_nc_files
from metplan.utils.logger import get_logger

import numpy as np

xr.set_options(keep_attrs=True)
logger = get_logger()

OUTPUT_FILE_FORMAT = "NETCDF4"
CONFIG_FILE_NAME = "config.yaml"
PARAM_MAP_FILE_NAME = mu.get_installed_root() / "config" / "param_map.yaml"

def get_rename_param_criteria(params, param_map, coords=()) -> dict[Hashable, str]:
    """ Data variables are renamed by standard/optional/conversion entries,
    coordinates/dimensions by `coordinate` entries (eg. latitude -> lat) based
    on param_map.yaml

    Parameters
    ----------
    params : 
        Data variable names present in the input dataset.
    param_map : 
        Parameter map loaded from `param_map.yaml`.
    coords : 
        Coordinate and dimension names present in the input dataset,
        by default ().

    Returns
    -------
    dict[Hashable, str]
        Mapping of input name -> name in param_map
    """
    param_criteria: dict[Hashable, str] = {}
    for param, param_info in param_map.items():
        candidates = coords if param_info.get("type") == "coordinate" else params
        for input_value in param_info.get("input_param", []):
            if input_value in candidates:
                param_criteria[input_value] = param
    return param_criteria

def get_unit_conv_params(param_map):
    """Units conversions are to be done for all params having unit in mapping."""
    return [
        param
        for param, param_attrs in param_map.items()
        if param_attrs.get("unit") is not None
    ]


with open(PARAM_MAP_FILE_NAME) as file:
    param_map = yaml.safe_load(file)


def run_met(config, dataset=None):
    """Run preprocessor for meteorological forcing dataset(s)."""

    # Load the configuration
    # config = mu.load_config(config_path)

    with open(PARAM_MAP_FILE_NAME) as file:
        param_map = yaml.safe_load(file)

    if dataset is None:
        ## REVIEW: Have validator like cerberus
        file_list = []
        for dir in config.get("directories"):
            file_list += list_nc_files(dir)

        ## TODO: Look more into parameter options for open_mfdataset
        logger.info("Loading combined dataset")
        dataset = xr.open_mfdataset(
            file_list,
            compat="override",
            coords="minimal",
            chunks={"time": 24, "longitude": -1, "latitude": -1},
            engine="h5netcdf",
            parallel=True,
        )
        logger.info("Loaded combined dataset")

        # NOTE: Ideally remove after appropriate compression, otherwise can put in docs as WIP
        dataset = dataset.sel(
            time=slice("1950-01-01 00:00:00", "1950-01-02 23:59:59"), drop=True
        )
        logger.debug(dataset)
        logger.debug(dataset.chunks)

    tic = time.perf_counter()

    # 1. Rename parameters
    param_criteria = get_rename_param_criteria(
        list(dataset.data_vars),
        param_map,
        coords=list(set(dataset.coords) | set(dataset.dims)),
    )
    dataset = dataset.rename(param_criteria)

    # 1: Segregate by year/var
    # for var in dataset.data_vars:
    #     var_output_dir = f"{config.get('output_directory')}/{var}"
    #     try:
    #         shutil.rmtree(config.get("output_directory"))
    #     except OSError as e:
    #         print("Error: %s - %s." % (e.filename, e.strerror))
    #     os.mkdir(var_output_dir)

    #     for year in dataset.time.dt.year.unique:
    #         pass

    # TODO 2: Read year/year and do dask job queue
    # https://examples.dask.org/applications/embarrassingly-parallel.html

    # 2. Hourly accumulator
    for v in config.get("hourly_acc"):
        dataset[v] = daily_to_hourly_acc(dataset[v])

    # 3. Unit conversions
    ## List of all params for unit conversions
    params = get_unit_conv_params(param_map)
    param_conv = UnitConversion(params)

    for param in params:
        if dataset.get(param) is not None:
            dataset[param] = param_conv.convert_param(
                dataset[param], param_map[param]["unit"]
            )

        else:
            logger.info(f"Standard Stage: Skipping {param}")

    # 4. Doing all possible calculations (Params)
    ## For strict ordering, resulting graph must be DAGs
    ## Can use memoisation + greedy approach
    dep_list = generate_calculations(dataset, param_map)

    for param, deps, func in dep_list:
        if deps == []:
            dep_attrs = [dataset.coords, dataset.dims]
        else:
            dep_attrs = list(map(lambda x: dataset[x], deps))
        # TODO: Try just base unit conversion
        dataset[param] = func(*dep_attrs)
        dataset[param] = dataset[param].metpy.dequantify()
        # After convert to actual units needed
        dataset[param] = param_conv.convert_param(
            dataset[param], param_map[param]["unit"]
        )

    # sys.exit()
    # Only keep standard/optional variables (not including index variables)
    dataset = dataset.drop_vars(
        list(
            filter(
                lambda x: (
                    param_map.get(x, {}).get("type", "") not in ["standard", "optional"]
                ),
                list(dataset.keys()),
            )
        )
    )

    # NOTE: CABLE-specific settings

    # CABLE reads variables as Fortran (x, y, time), ie. netCDF (time, lat, lon)
    dataset = dataset.transpose("time", "lat", "lon", missing_dims="ignore")

    # CABLE time-steps
    dataset["time"].encoding["units"] = "hours since 1900-01-01 01:00:00"
    dataset["time"].encoding["calendar"] = "proleptic_gregorian"


    logger.info("Saving dataset")
    logger.debug(dataset)

    # Ensure that the output directory exists
    os.makedirs(config.get("output_dir"), exist_ok=True)

    for var in dataset.data_vars:
        output_filename = config.get("output_dir") + f"/{var}.nc"

        logger.debug(f"Saving var: {var}")
        dataset[var].encoding.update(config.get("encoding"))
        dataset[var].to_netcdf(output_filename, **config.get("to_netcdf"))

    logger.info("Saved dataset - Check log.txt for warnings")

    # Land-sea mask for CABLE GSWP3 mode (gswpfile%mask), on (lat, lon).
    # GSWP3 convention: 0 = land, 1 = sea (CABLE inverts it); all land for now
    landsea = xr.DataArray(
        np.zeros((dataset.sizes["lat"], dataset.sizes["lon"]), dtype=np.int32),
        coords={"lat": dataset["lat"], "lon": dataset["lon"]},
        name="landsea",
    )
    landsea.to_netcdf(config.get("output_dir") + "/landsea.nc", **config.get("to_netcdf"))

    toc = time.perf_counter()
    print(f"Completed in {toc - tic:0.4f} seconds")

    return dataset
