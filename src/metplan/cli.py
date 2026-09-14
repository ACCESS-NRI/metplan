"""Console script for metplan."""

import argparse
import sys

import metplan


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

    # Assign default
    parser_run.set_defaults(func=default_app)
    return parser


def parse_args(parser: argparse.ArgumentParser) -> argparse.Namespace:
    """Parse the arguments for the given parser, displaying help and exiting if no args.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parser object.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    # Check if no args, print help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args()


def dispatch(parsed_args: argparse.ArgumentParser):
    """Dispatch the parsed arguments to the nominated function.

    Parameters
    ----------
    parsed_args : argparse.ArgumentParser
        Parsed arguments.
    """
    func = parsed_args.pop("func")
    func(**parsed_args)
