from metplan.unit_conv import UnitConversion
from metplan.metplan import get_unit_conv_params
import pytest


@pytest.fixture(scope="module")
def unit_conv_params(param_map):
    return get_unit_conv_params(param_map)


@pytest.fixture(scope="module")
def param_conv(unit_conv_params):
    return UnitConversion(["t2m"])


def test_unit_conv(sample_xarray_data, param_conv):
    print(param_conv.convert_param(sample_xarray_data["t2m"], "kelvin"))