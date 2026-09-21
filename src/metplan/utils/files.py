import os
import netCDF4
import metplan.utils as mu


def list_nc_files(d):
    """Lists all .nc files in subdirectories, or as files themselves."""
    if os.path.isfile(d):
        return [d]

    files = []
    for r, d, f in os.walk(d):
        for file in f:
            if ".nc" in file:
                files.append(os.path.join(r, file))
    return files


def list_variables(paths: str | list) -> list:
    """List the variables in the provided NetCDF files.

    Parameters
    ----------
    paths : str | list
        List of paths, can supply a single path.

    Returns
    -------
    list
        Unique list of variable names.
    """
    # Ensure the paths variable is a list so we can send a single path
    paths = [paths] if isinstance(paths, list) == False else paths

    # Parse the variable names
    varnames = []
    for path in paths:    
        with netCDF4.Dataset(path) as nc:
            varnames += [v for v in nc.variables if v not in nc.dimensions]

    # Ensure unique, return
    return list(set(varnames))