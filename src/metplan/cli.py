"""Console script for metplan."""

import argparse
import metplan


def generate_parser(app) -> argparse.ArgumentParser:
    """Returns the instance of `argparse.ArgumentParser` used for `metplan`."""
    # parent parser that contains the help argument
    args_help = argparse.ArgumentParser(add_help=False)
    args_help.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )

    # parent parser that contains arguments common to all subcommands
    args_subcommand = argparse.ArgumentParser(add_help=False)
    args_subcommand.add_argument(
        "-c",
        "--config",
        dest="config_path",
        help="Config filename.",
        default="config.yaml",
    )
    args_subcommand.add_argument(
        "-v",
        "--verbose",
        help="Enable more detailed output in the command line.",
        action="store_true",
    )

    # main parser
    main_parser = argparse.ArgumentParser(
        description="metplan is a tool for preprocessing Meteorological Forcing Data.",
        parents=[args_help],
        add_help=False,
    )

    main_parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"metplan {metplan.__version__}",
        help="Show program's version number and exit.",
    )

    subparsers = main_parser.add_subparsers(metavar="command")

    # subcommand: 'benchcab run'
    parser_run = subparsers.add_parser(
        "run",
        parents=[
            args_help,
            args_subcommand,
        ],
        help="Run metplan.",
        description="""Runs metplan with config.yaml file assumed to be in the current folder.""",
        add_help=False,
    )
    parser_run.set_defaults(func=app)

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

    return main_parser