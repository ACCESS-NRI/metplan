from metplan.utils.logger import get_logger
from metplan.metplan import run_met
from dask.distributed import LocalCluster, Client
from dask import delayed
from dask_jobqueue import PBSCluster
import os
import sys

logger = get_logger()

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

def main():

    try:
        if os.environ.get('PBS_JOBFS') is None:
            cluster = LocalCluster(n_workers=4, threads_per_worker=1, memory_limit="4GB")
            client = Client(cluster)
        else:
            # client, cluster = my_start_PBS_dask_cluster()
            logger.debug("Running on PBS")
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