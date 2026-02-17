import pytest
from met_preprocessor.met_preprocessing import (
    get_rename_param_criteria,
    get_unit_conv_params,
)
from met_preprocessor.dependency import (
    process_dependencies,
    order_load_dep,
    cycle_check,
)
from met_preprocessor.opt_param import calc_lwdown_swinbank
from met_preprocessor.standard_param import vpd_tair_sh


class TestGetRenameParamCriteria:
    """Test cases for get_rename_param_criteria function."""

    def test_get_rename_param_criteria_empty(self):
        """Test with empty parameters list."""
        params = []
        param_map = {
            "Tair": {"input_param": ["tavg", "temp"]},
        }

        result = get_rename_param_criteria(params, param_map)

        assert result == {}

    def test_get_rename_param_criteria_single_match(self):
        """Test with single parameter match."""
        params = ["tavg"]
        param_map = {
            "Tair": {"input_param": ["tavg", "temp"]},
        }

        result = get_rename_param_criteria(params, param_map)

        assert result == {"tavg": "Tair"}

    def test_get_rename_param_criteria_multiple_matches(self):
        """Test with multiple parameter matches."""
        params = ["tavg", "rain", "srad"]
        param_map = {
            "Tair": {"input_param": ["tavg", "temp"]},
            "Rainf": {"input_param": ["rain", "precip"]},
            "SWDown": {"input_param": ["srad"]},
        }

        result = get_rename_param_criteria(params, param_map)

        assert result == {
            "tavg": "Tair",
            "rain": "Rainf",
            "srad": "SWDown",
        }

    def test_get_rename_param_criteria_partial_match(self):
        """Test with partial parameter matches."""
        params = ["tavg", "unknown_param"]
        param_map = {
            "Tair": {"input_param": ["tavg", "temp"]},
        }

        result = get_rename_param_criteria(params, param_map)

        assert result == {"tavg": "Tair"}
        assert "unknown_param" not in result

    def test_get_rename_param_criteria_no_input_param_key(self):
        """Test handling of param_map without input_param key."""
        params = ["tavg"]
        param_map = {
            "Tair": {"unit": "kelvin"},  # No input_param key
        }

        result = get_rename_param_criteria(params, param_map)

        assert result == {}


class TestGetUnitConvParams:
    """Test cases for get_unit_conv_params function."""

    def test_get_unit_conv_params_empty(self):
        """Test with empty param_map."""
        param_map = {}

        result = get_unit_conv_params(param_map)

        assert result == []

    def test_get_unit_conv_params_single_unit(self):
        """Test with single parameter having unit."""
        param_map = {
            "Tair": {"unit": "kelvin"},
            "vpd": {},  # No unit
        }

        result = get_unit_conv_params(param_map)
        assert result == ["Tair"]

    def test_get_unit_conv_params_multiple_units(self):
        """Test with multiple parameters having units."""
        param_map = {
            "Tair": {"unit": "kelvin"},
            "Rainf": {"unit": "kg m-2 s-1"},
            "SWDown": {"unit": "W m-2"},
            "vpd": {},  # No unit
        }

        result = get_unit_conv_params(param_map)

        assert len(result) == 3
        assert "Tair" in result
        assert "Rainf" in result
        assert "SWDown" in result
        assert "vpd" not in result

    def test_get_unit_conv_params_none_unit(self):
        """Test with None unit value."""
        param_map = {
            "Tair": {"unit": "kelvin"},
            "other": {"unit": None},
        }

        result = get_unit_conv_params(param_map)

        assert result == ["Tair"]


class TestProcessDependencies:
    """Test cases for process_dependencies function."""

    def test_process_dependencies_empty(self):
        """Test with empty param_map."""
        param_map = {}

        result = process_dependencies(param_map)

        assert result == {}

    def test_process_dependencies_standard_param(self, param_map):
        """Test processing standard parameter dependencies."""
        result = process_dependencies(param_map)

        assert isinstance(result, dict)
        # Should contain Qair with multiple calculation options
        assert "Qair" in result

    def test_process_dependencies_optional_param(self, param_map):
        """Test processing optional parameter dependencies."""
        result = process_dependencies(param_map)

        # Optional parameters should be processed
        assert "LWDown" in result or "PSurf" in result

    def test_process_dependencies_multiple_calc_options(self, param_map):
        """Test that parameters with multiple calc options are handled."""
        result = process_dependencies(param_map)

        # Qair should have multiple calculation options
        if "Qair" in result:
            assert len(result["Qair"]) >= 1


class TestCycleCheck:
    """Test cases for cycle_check function."""

    def test_cycle_check_no_cycle(self):
        """Test detection when no cycle exists."""
        node = "A"
        visited = {}
        adj_list = {"A": ["B", "C"], "B": [], "C": []}

        result = cycle_check(node, visited, adj_list)

        assert result is False

    def test_cycle_check_simple_cycle(self):
        """Test detection of simple cycle."""
        node = "A"
        visited = {}
        adj_list = {"A": ["B"], "B": ["A"]}

        result = cycle_check(node, visited, adj_list)

        assert result is True

    def test_cycle_check_self_loop(self):
        """Test detection of self-loop cycle."""
        node = "A"
        visited = {}
        adj_list = {"A": ["A"]}

        result = cycle_check(node, visited, adj_list)

        assert result is True

    def test_cycle_check_complex_cycle(self):
        """Test detection of complex cycle."""
        node = "A"
        visited = {}
        adj_list = {"A": ["B"], "B": ["C"], "C": ["A"]}

        result = cycle_check(node, visited, adj_list)

        assert result is True


class TestOrderLoadDep:
    """Test cases for order_load_dep function."""

    def test_order_load_dep_no_dependencies(self):
        """Test ordering with no dependencies."""
        res = []
        dependencies = {"A": [], "B": []}
        input_list = []

        result = order_load_dep(res, dependencies, input_list)

        assert isinstance(result, list)

    def test_order_load_dep_linear_dependency(self):
        """Test ordering with linear dependency chain."""
        res = []
        dependencies = {
            "A": [(["input1"], lambda: None)],
            "B": [(["A"], lambda: None)],
        }
        input_list = ["input1"]

        result = order_load_dep(res, dependencies, input_list)

        assert isinstance(result, list)

    def test_order_load_dep_multiple_options(self, param_map):
        """Test ordering with multiple calculation options."""
        res = []
        dependencies = process_dependencies(param_map)
        input_list = ["vpd", "Tair", "none"]

        result = order_load_dep(res, dependencies, input_list)

        assert isinstance(result, list)
        # Should select appropriate calculation based on available inputs


@pytest.fixture()
def test_params(sample_xarray_data):
    """Fixture providing test parameters from sample data."""
    return list(sample_xarray_data.keys())


@pytest.fixture()
def test_ord_deps():
    """Fixture providing expected ordered dependencies."""
    return [
        ("Qair", ["vpd", "Tair"], vpd_tair_sh),
        ("LWDown", ["Tair"], calc_lwdown_swinbank),
    ]


@pytest.fixture()
def test_all_deps(param_map):
    """Fixture providing all processed dependencies."""
    return process_dependencies(param_map)


def test_order_load_dep_integration(test_params, test_all_deps, test_ord_deps):
    """Integration test for order_load_dep with sample data."""
    result = order_load_dep([], test_all_deps, test_params)

    assert isinstance(result, list)

