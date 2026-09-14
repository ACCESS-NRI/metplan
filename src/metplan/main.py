import os
import sys

import metplan.cli as mc
import metplan.utils as mu
from metplan.metplan import run_met
from metplan.utils.logger import get_logger


def main():

    logger = get_logger()

    # Parse intially to get the optional user config path
    args = mc.parse_args(mc.get_parser(run_met))

    # Load the default config
    config = mu.load_config(user_config=args.config)

    try:

        # Start the client and cluster
        client, cluster = mu.start_dask_client(config)

        # Dispatch to command
        mc.dispatch(args)

    finally:

        # Stop the client and cluster
        mu.stop_dask_client(client, cluster)

    # TODO: Check output result
    # TODO: Dask LocalCluster
    # TODO: Weather Generator
    # TODO: Temporal / Spatial resolution - Reference gridinfo - maximum types of datasets to support (3 is ideal). Warn if more than 2


# https://github.com/AusClimateService/axiom
