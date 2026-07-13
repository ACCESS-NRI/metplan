import logging
import sys


def get_logger(name="metplan", level="debug"):
    """Get a logger instance.

    Parameters
    ----------
    name : str, optional
        Name, by default 'metplan'
    level : str, optional
        Level, by default 'debug'

    Returns
    -------
    logging.Logger
        A logger instance guaranteed to be singleton if called with the same params.

    """
    # Get or create a logger
    logger = logging.getLogger(name)

    # Workaround for native singleton property.
    # NOTE: This will ignore the provided level and give you whatever was first set.
    if logger.level != logging.NOTSET:
        return logger

    # Set the level
    level = getattr(logging, level.upper())
    logger.setLevel(level)

    # Create the formatter
    log_format = (
        "%(asctime)s - %(levelname)s - %(module)s.%(filename)s:%(lineno)s - %(message)s"
    )
    formatter = logging.Formatter(log_format)

    # Create/set the handler to point to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def is_verbose():
    """Return True if verbose output is enabled, False otherwise."""
    return get_logger().getEffectiveLevel() == logging.DEBUG
