import yaml
import xarray as xr
from met_preprocessor.unit_conv import UnitConversion
from met_preprocessor.utils.files import list_nc_files
from met_preprocessor.utils.logger import get_logger
from met_preprocessor.accu import daily_to_hourly_acc
from met_preprocessor.dependency import generate_calculations
from dask.distributed import LocalCluster, Client
from dask import delayed
from dask_jobqueue import PBSCluster
import os
import sys

xr.set_options(keep_attrs=True)
logger = get_logger()

OUTPUT_FILE_FORMAT = "NETCDF4"
CONFIG_FILE_NAME = "config.yaml"
PARAM_MAP_FILE_NAME = "param_map.yaml"


def get_rename_param_criteria(params, param_map):
    """All input_param act as keys with the original key as value."""
    param_criteria = {}
    for param, param_info in param_map.items():
        for input_value in param_info.get("input_param", []):
            if input_value in params:
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


def run_met(client, dataset=None):
    """Run preprocessor for meteorological forcing dataset(s)."""

    client.amm.start()
    logger.info(f"Diagnostics: {client.dashboard_link}")

    with open(CONFIG_FILE_NAME) as file:
        config = yaml.safe_load(file)

    with open(PARAM_MAP_FILE_NAME) as file:
        param_map = yaml.safe_load(file)

    if dataset is None:

        ## REVIEW: Have validator like cerberus
        file_list = []
        for dir in config.get("directories"):
            file_list += list_nc_files(dir)

        ## TODO: Look more into parameter options for open_mfdataset
        logger.info("Loading combined dataset")
        dataset = xr.open_mfdataset(file_list, compat="override", coords="minimal", chunks={"latitude": 360})
        logger.info("Loaded combined dataset")

        # NOTE: Ideally remove after appropriate compression, otherwise can put in docs as WIP
        dataset = dataset.sel(time=slice("1950-01-01 00:00:00", "1950-01-10 23:59:59"), drop=True)
        logger.debug(dataset)
        logger.debug(dataset.chunks)

    # 1. Rename parameters
    param_criteria = get_rename_param_criteria(list(dataset.keys()), param_map)
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

    dataset = dataset.compute()

    # 4. Doing all possible calculations (Params)
    ## For strict ordering, resulting graph must be DAGs
    ## Can used memoisation + greedy approach
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
                lambda x: param_map.get(x, {}).get("type", "")
                not in ["standard", "optional"],
                list(dataset.keys()),
            )
        )
    )

    # Combine filtered params
    compression_dict = {"zlib": True, "complevel": 5, "shuffle": True}

    logger.info("Saving dataset")
    logger.debug(dataset)
    for var in dataset.data_vars:
        logger.debug(f"Saving var: {var}")
        dataset[var].encoding.update(compression_dict)
        dataset[var].to_netcdf(f"{config['output_file']}_{var}.nc", format="NETCDF4")

    logger.info("Saved dataset - Check log.txt for warnings")

    return dataset

def my_start_PBS_dask_cluster(  
    cores=8,
    memory="16GB",
    processes=8,
    walltime = '1:00:00',
    storages = "gdata/zz93+gdata/xp65+gdata/tm70"
):
    
    logger.debug("Starting Dask...\r", end="")
    
    cluster = PBSCluster(walltime=str(walltime), cores=cores, memory=str(memory), processes=processes,
                         job_extra_directives=['-q normalbw',
                                               '-l ncpus='+str(cores),
                                               '-l mem='+str(memory),
                                               '-l storage='+storages,
                                               '-l jobfs=16GB',
                                               '-P tm70'],
                         job_script_prologue=['module unload conda/analysis3-25.05'],
                         job_directives_skip=["select"],
                         python="/g/data/xp65/public/apps/med_conda_scripts/analysis3-25.05.d/bin/python",
                        )
    
    cluster.scale(jobs=10)  # Scale the resource to this many nodes
    logger.debug(cluster.job_script())
    client = Client(cluster)
    logger.info(f"Dask Client started. Dashboard URL: {client.dashboard_link}")
    return client, cluster

if __name__ == "__main__":

    try:
        if os.environ.get('PBS_JOBFS') is None:
            cluster = LocalCluster(n_workers=4, threads_per_worker=1, memory_limit="4GB")
            client = Client(cluster)
        else:
            # client, cluster = my_start_PBS_dask_cluster()
            print("Running on PBS")
            cluster = LocalCluster(n_workers=1, 
            processes=True, 
            memory_limit = int(os.environ['PBS_VMEM']), # / int(os.environ['PBS_NCPUS']), 
            local_directory = os.path.join(os.environ['PBS_JOBFS'], 'dask-worker-space'))
            client = Client(cluster)

        run_met(client)
    finally:
        cluster.close()
        client.close()

    # TODO: Check output result
    # TODO: Dask LocalCluster
    # TODO: Weather Generator
    # TODO: Temporal / Spatial resolution - Reference gridinfo - maximum types of datasets to support (3 is ideal). Warn if more than 2
    # TODO: CLI

# https://github.com/AusClimateService/axiom
