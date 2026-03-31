import yaml
import xarray as xr
from met_preprocessor.unit_conv import UnitConversion
from met_preprocessor.utils import list_nc_files
from met_preprocessor.accu import daily_to_hourly_acc
from met_preprocessor.dependency import generate_calculations

xr.set_options(keep_attrs=True)

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


def run_met(dataset=None):
    """Run preprocessor for meteorological forcing dataset(s)."""

    with open(CONFIG_FILE_NAME) as file:
        config = yaml.safe_load(file)

    with open(PARAM_MAP_FILE_NAME) as file:
        param_map = yaml.safe_load(file)

    if dataset is None:

        ## REVIEW: Have validator like cerberus
        file_list = []
        for dir in config.get("directories"):
            file_list += list_nc_files(dir)

        ## TODO: Have to differentiate output out by variables
        ## TODO: Look more into parameter options for open_mfdataset
        print("Loading combined dataset")
        dataset = xr.open_mfdataset(file_list, compat="override", coords="minimal")
        print("Loaded combined dataset")

        # NOTE: Ideally remove after appropriate compression, otherwise can put in docs as WIP
        dataset = dataset.sel(time=slice("1950-01-01 00:00:00", "1950-01-01 23:59:59"))
        print(dataset)

    # 1. Rename parameters
    param_criteria = get_rename_param_criteria(list(dataset.keys()), param_map)
    dataset = dataset.rename(param_criteria)

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
            print(f"Standard Stage: Skipping {param}")

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

    print("Saving dataset")

    # Combine filtered params
    compression_dict = {"zlib": True, "complevel": 5, "shuffle": True}

    print("Saving dataset")
    print(dataset["time"])
    for var in dataset.data_vars:
        print(f"Saving var: {var}")
        dataset[var].encoding.update(compression_dict)
        dataset[var].to_netcdf(f"{config['output_file']}_{var}.nc", format="NETCDF4")

    print("Saved dataset - Check log.txt for warnings")

    return dataset


if __name__ == "__main__":
    run_met()

# https://github.com/AusClimateService/axiom
