from pathlib import Path
import os
from importlib import resources
import yaml
import copy
from hpcpy.utilities import interpolate_string_template


def get_installed_root() -> Path:
    """Get the installed root of the package installation.

    Returns
    -------
    Path
        Path to the installed root.

    """
    return Path(resources.files("metplan"))


def deep_update(original_dict: dict, update_dict: dict) -> dict:
    """Deep-update a dict.

    Parameters
    ----------
    original_dict : dict
        The original dictionary
    update_dict : dict
        The dict containing updates

    Returns
    -------
    dict
        A new dict with the merge of the original and update dicts
    """
    # Create a copy to avoid updating the original
    new_dict = copy.deepcopy(original_dict)

    # Loop and recurse to update
    for key, value in update_dict.items():
        if isinstance(value, dict) and isinstance(new_dict.get(key), dict):
            new_dict[key] = deep_update(new_dict[key], value)
        else:
            new_dict[key] = copy.deepcopy(value)

    return new_dict


def load_config(user_config=None) -> dict:
    """Load default configuration, then overlay the user configuration.

    Parameters
    ----------
    user_config : Path-like, optional
        Path to the user-supplied configuration, by default None

    Returns
    -------
    dict
        Final configuation after all overrides.
    """

    # Load the default configuration
    config_paths = [get_installed_root() / "config" / "defaults.yml"]

    if user_config and Path(user_config).is_file():
        config_paths.append(Path(user_config))

    # Iteratively load the configuration in order
    config = dict()
    for cp in config_paths:

        # Only attempt load if it exists and is correct format
        if os.path.isfile(cp) and cp.suffix in [".yml", ".yaml"]:

            # Read the raw content
            raw = open(cp, "r").read()
            raw_env = interpolate_string_template(raw, **os.environ)

            # Parse the config, interpolating environment vars
            _config = yaml.safe_load(raw_env)
            config = deep_update(config, _config)

    return config