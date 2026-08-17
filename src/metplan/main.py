from metplan.cli import generate_parser
from metplan.utils.logger import get_logger
import metplan.utils as mu
from metplan.metplan import run_met
from dask.distributed import LocalCluster, Client
from dask_jobqueue import PBSCluster
import os
import sys

logger = get_logger()


def my_start_PBS_dask_cluster(
    cores=8,
    memory="16GB",
    processes=8,
    walltime="1:00:00",
    storages="gdata/zz93+gdata/xp65+gdata/tm70",
):

    logger.debug("Starting Dask...\r", end="")

    cluster = PBSCluster(
        walltime=str(walltime),
        cores=cores,
        memory=str(memory),
        processes=processes,
        job_extra_directives=[
            "-q normalbw",
            "-l ncpus=" + str(cores),
            "-l mem=" + str(memory),
            "-l storage=" + storages,
            "-l jobfs=16GB",
            "-P tm70",
        ],
        job_script_prologue=["module unload conda/analysis3"],
        job_directives_skip=["select"],
        python="/g/data/xp65/public/apps/med_conda_scripts/analysis3-26.05.d/bin/python",
    )

    cluster.scale(jobs=10)  # Scale the resource to this many nodes
    logger.debug(cluster.job_script())
    client = Client(cluster)
    logger.info(f"Dask Client started. Dashboard URL: {client.dashboard_link}")
    return client, cluster


def parse_and_dispatch(parser, app):
    """Parse arguments for the script and dispatch to the correct function.

    Args:
    ----
    parser : argparse.ArgumentParser
        Parser object.
    app : metplan
        metplan application instance.

    """
    args = vars(parser.parse_args(sys.argv[1:] if sys.argv[1:] else ["-h"]))

    _ = args.pop("verbose")
    _ = args.pop("all")

    func = args.pop("func")
    func(**args)


def main():

    # Load the default config
    config = mu.load_config()

    try:

        # Local cluster
        if os.environ.get("PBS_JOBFS") is None:
            cluster = LocalCluster(**config.get("cluster_local"))
            client = Client(cluster)

        # PBS / Gadi Cluster (still of LocalCluster class, but running on HPC)
        else:

            logger.debug("Running on PBS")

            cluster = LocalCluster(
                memory_limit=int(os.environ["PBS_VMEM"]),
                local_directory=os.path.join(
                    os.environ["PBS_JOBFS"], "dask-worker-space"
                ),
                **config.get("cluster_pbs"),
            )

            client = Client(cluster)

        parser = generate_parser(run_met)

        client.amm.start()
        logger.info(f"Diagnostics: {client.dashboard_link}")

        parse_and_dispatch(parser, run_met)
        # run_met()
    finally:
        cluster.close()
        client.close()

    # TODO: Check output result
    # TODO: Dask LocalCluster
    # TODO: Weather Generator
    # TODO: Temporal / Spatial resolution - Reference gridinfo - maximum types of datasets to support (3 is ideal). Warn if more than 2
    # TODO: CLI


# https://github.com/AusClimateService/axiom
