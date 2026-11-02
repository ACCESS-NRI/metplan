"""Main module."""

import operator
import os
import shutil
import sys
import time
from collections.abc import Collection, Hashable
from typing import Any

import xarray as xr
from hpcpy import get_client

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


def get_derivable_var_list(dep_list, dataset: xr.Dataset) -> list:
    """Creates the list of variables needed by CABLE that are either in the input dataset or can be calculated from the available variables.

    Parameters
    ----------
    dep_list : list
        Dependency list
    dataset : xr.Dataset
        Dataset

    Returns
    -------
    list
        List of derivable variables.
    """
    var_list = list(map(operator.itemgetter(0), dep_list))
    variables = set(var_list).union(dataset.data_vars)
    param_map = mu.load_param_map(PARAM_MAP_FILE_NAME)
    return [
        var
        for var in variables
        if param_map.get(var, {}).get("type") in ("standard", "optional")
    ]

def preprocess_land_sea_mask(ds: xr.Dataset, threshold: float = 0.5) -> xr.Dataset:
    """
    Make the land-sea mask file compatible with the met forcing files,
    with respect to time.

    Parameters
    ----------
    ds : xr.Dataset
        metplan input dataset

    Returns
    -------
    xr.Dataset

    """
    param_map = mu.load_param_map(PARAM_MAP_FILE_NAME)
    lsm_names = param_map.get("landsea", {}).get("input_param")
    if lsm_names is None:
        raise ValueError("Land-Sea Mask variable not provided in param_map")

    for name in lsm_names:
        if name in ds:
            # Time has dimension length of 1 which is different 
            lsm = ds[name].isel(time=0, drop=True, missing_dims="ignore")
            ds[name] = xr.where(lsm.fillna(0) >= threshold, 0, 1).astype("int32")
            ds = ds.drop_vars("time", errors="ignore")
    return ds

def load_dataset(config: dict) -> xr.Dataset:
    """Load the dataset.

    Parameters
    ----------
    config : dict
        Configuration dictionary.

    Returns
    -------
    xr.Dataset
        Dataset
    """
    file_list = []
    for dir in config.get("directories"):
        logger.debug(f"Adding {dir}")
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
    logger.debug(dataset)
    logger.debug(dataset.chunks)
    return dataset


def _run_met(config: dict, var: str, dataset: xr.Dataset, dep_list: list) -> xr.Dataset:
    """Process a single variable instance.

    Parameters
    ----------
    config : dict
        Configuration
    var : str
        Variable name
    dataset : xr.Dataset
        Preloaded input dataset.
    dep_list : list
        Dependency list

    Returns
    -------
    xr.Dataset
        Processed dataset.
    """
    tic = time.perf_counter()

    # 2. Hourly accumulator
    for v in config.get("hourly_acc"):
        dataset[v] = daily_to_hourly_acc(dataset[v])

    # 3. Unit conversions
    ## List of all params for unit conversions
    param_map = mu.load_param_map(PARAM_MAP_FILE_NAME)
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


    output_filename = config.get("output_dir") + f"/{var}.nc"
    logger.debug(f"Saving var: {var}")
    # xarray on netcdf4 engine unpacks scale_factor/add_offset, but
    # keeps the attributes
    for key in ("scale_factor", "add_offset"):
        dataset[var].encoding.pop(key, None)
    dataset[var].encoding.update(config.get("encoding"))
    dataset[var].to_netcdf(output_filename, **config.get("to_netcdf"))

    logger.info("Saved dataset - Check log.txt for warnings")
    logger.info(f"Ouput Filepath = {output_filename}")

    toc = time.perf_counter()
    logger.debug(f"Completed in {toc - tic:0.4f} seconds")

    return dataset


def run_met(config: dict, var: str = None) -> xr.Dataset | None:
    """Wrapper for singular/multivariate processing.

    Parameters
    ----------
    config : dict
        Configuration.
    var : str, optional
        Variable to process, by default None (which loads from config)

    Returns
    -------
    xr.Dataset | None
        _description_
    """
    logger = get_logger()

    logger.debug("Loading param_map")
    param_map = mu.load_param_map(PARAM_MAP_FILE_NAME)

    logger.debug("Loading dataset.")
    dataset = load_dataset(config)

    # 1. Rename parameters
    logger.debug("Getting renaming param criteria")
    param_criteria = get_rename_param_criteria(list(dataset.keys()), param_map)
    dataset = dataset.rename(param_criteria)

    logger.debug("Generating dependency list")
    dep_list = generate_calculations(dataset, param_map)

    # Use case 1 - A single processing instance for a variable processed in this job
    if var:
        logger.debug(f"Single variable run ({var})")
        client, cluster = mu.start_dask_client(config)
        ds = _run_met(config, var, dataset, dep_list)
        mu.stop_dask_client(client, cluster)
        return ds

    # Use case 2 - All variables submitted and processed in their own jobs
    else:

        logger.debug("Preparing to submit all variables for processing")

        # Get an HPCpy client, path to exec etc.
        logger.debug("Getting HPCpy client")
        client = get_client()
        metplan_path = shutil.which(sys.argv[0])
        jobscript_path = mu.get_installed_root() / "data" / "pbs_jobscript.j2"

        logger.debug(f"metplan_path = {metplan_path}")
        logger.debug(f"jobscript_path = {jobscript_path}")

        for var in get_derivable_var_list(dep_list, dataset):

            metplan_path = shutil.which(sys.argv[0])
            job = client.submit(
                jobscript_path,
                render=True,
                metplan_path=metplan_path,
                metplan_var=var,
                project=config.get("project"),
                **config.get("job_pbs"),
                config_path=config["user_config"],
                directives=[f"-N {var}"],
            )

            logger.info(f"{var} = {job.id}")
            submit_cmd = client.history[0]
            logger.debug(submit_cmd)

        logger.info("All jobs submitted. Exiting.")
