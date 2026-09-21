"""Console script for metplan."""

import argparse
import os
import sys

import metplan
import metplan.utils as mu
from metplan.metplan import run_met
from metplan.utils.logger import get_logger


def get_parser(default_app: callable) -> argparse.ArgumentParser:
    """Get the parser for metplan

    Parameters
    ----------
    default_app : callable
        Default method to call.

    Returns
    -------
    argparse.ArgumentParser
        Parser object
    """
    # Base parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"metplan {metplan.__version__}",
        help="Show program's version number and exit.",
    )

    # Shared arguments
    args_shared = argparse.ArgumentParser(add_help=False)

    # Add Config
    args_shared.add_argument(
        "-c",
        "--config",
        help="Path to user config",
        default=None,
        type=str,
        required=False,
    )

    # Add verbosity
    args_shared.add_argument(
        "-v",
        "--verbose",
        help="Enable more detailed output",
        default=False,
        action="store_true",
    )

    # Set up subparsers
    subparsers = parser.add_subparsers(help="Sub command")

    # Add the subparser for running metplan
    parser_run = subparsers.add_parser(
        "run", help="Run metplan", description="Runs metplan.", parents=[args_shared]
    )

    # Require either a single variable or --all, but not both.
    group_run = parser_run.add_mutually_exclusive_group(required=True)
    group_run.add_argument(
        "var",
        nargs="?",
        default=None,
        help="Name of the variable to process.",
    )
    group_run.add_argument(
        "--all",
        dest="all",
        action="store_true",
        help="Process all variables instead of specifying one.",
    )

    # Assign default
    parser_run.set_defaults(func=default_app)
    return parser


def parse_args(parser: argparse.ArgumentParser) -> dict:
    """Parse the arguments for the given parser, displaying help and exiting if no args.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parser object.

    Returns
    -------
    dict
        Parsed arguments.
    """
    # Check if no args, print help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # Ensure that there is no var set if all is set
    args = vars(parser.parse_args())
    args["var"] = None if args.pop("all") else args["var"]

    # Attach the user config (needs to absolute for submission)
    args["config"] = mu.load_config(user_config=os.path.abspath(args["config"]))

    return args


def dispatch(parsed_args: argparse.ArgumentParser):
    """Dispatch the parsed arguments to the nominated function.

    Parameters
    ----------
    parsed_args : argparse.ArgumentParser
        Parsed arguments.
    """
    func = parsed_args.pop("func")
    func(**parsed_args)


def cli():
    """CLI entrypoint for the system."""

    # Parse intially to get the optional user config path
    args = parse_args(get_parser(run_met))

    # Set up the logger, remove verbosity
    log_level = "debug" if args.pop("verbose") else "info"
    logger = get_logger(level=log_level)

    # Dispatch to command
    logger.debug("Dispatching")
    dispatch(args)

#     # TODO: Check output result
#     # TODO: Dask LocalCluster
#     # TODO: Weather Generator
#     # TODO: Temporal / Spatial resolution - Reference gridinfo - maximum types of datasets to support (3 is ideal). Warn if more than 2


# # https://github.com/AusClimateService/axiom
