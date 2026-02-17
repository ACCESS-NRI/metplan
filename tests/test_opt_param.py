import pytest
import numpy as np
import pandas as pd
import xarray as xr
from metpy.units import units

from met_preprocessor.opt_param import (
    calc_lwdown_swinbank,
    calc_psurf,
    calc_snow,
    default_co2,
)


class TestCalcLwdownSwinbank:
    """Test cases for calc_lwdown_swinbank function."""

    @pytest.fixture
    def temperature_data(self):
        """Create sample temperature data in Kelvin."""
        time = pd.date_range("2024-01-01", periods=4, freq="D")
        data = xr.DataArray(
            [273.15, 283.15, 293.15, 303.15],
            coords={"time": time},
            dims=["time"],
            attrs={"units": "kelvin"},
        )
        return data.metpy.quantify()

    def test_calc_lwdown_swinbank_basic(self, temperature_data):
        """Test basic longwave radiation calculation."""
        result = calc_lwdown_swinbank(temperature_data)

        assert result is not None
        assert len(result) == len(temperature_data)
        assert all(result > 0)  # LW radiation should be positive
        # Check units are W/m²
        assert result.metpy.dequantify().attrs["units"] == "watt / meter ** 2"

    def test_calc_lwdown_swinbank_increases_with_temperature(self, temperature_data):
        """Test that longwave radiation increases with temperature (Stefan-Boltzmann)."""
        result = calc_lwdown_swinbank(temperature_data)
        result_deq = result.metpy.dequantify()

        # Higher temperature should produce higher radiation
        assert float(result_deq[0]) < float(result_deq[-1])

    @pytest.mark.parametrize(
        "temp_kelvin,expected_positive",
        [
            (273.15, True),  # 0°C
            (288.15, True),  # 15°C
            (310.15, True),  # 37°C
        ],
    )
    def test_calc_lwdown_swinbank_multiple_temps(self, temp_kelvin, expected_positive):
        """Test longwave calculation with various temperatures."""
        data = xr.DataArray(
            [temp_kelvin],
            attrs={"units": "kelvin"},
        ).metpy.quantify()

        result = calc_lwdown_swinbank(data)
        assert (result > 0) == expected_positive


class TestCalcPsurf:
    """Test cases for calc_psurf (pressure) function."""

    @pytest.fixture
    def temp_elev_data(self):
        """Create sample temperature and elevation data."""
        time = pd.date_range("2024-01-01", periods=3, freq="D")
        temp = xr.DataArray(
            [283.15, 283.15, 283.15],
            coords={"time": time},
            dims=["time"],
            attrs={"units": "kelvin"},
        ).metpy.quantify()

        elev = xr.DataArray(
            [0, 1000, 2000],
            coords={"time": time},
            dims=["time"],
            attrs={"units": "m"},
        ).metpy.quantify()

        return temp, elev

    def test_calc_psurf_basic(self, temp_elev_data):
        """Test basic surface pressure calculation."""
        temp, elev = temp_elev_data

        result = calc_psurf(temp, elev)

        assert result is not None
        assert len(result) == len(temp)
        assert all(result > 0)  # Pressure should be positive
        # Check units are Pa
        assert "pascal" in str(result.metpy.dequantify().attrs["units"])

    def test_calc_psurf_decreases_with_elevation(self, temp_elev_data):
        """Test that surface pressure decreases with elevation."""
        temp, elev = temp_elev_data

        result = calc_psurf(temp, elev)
        result_deq = result.metpy.dequantify()

        # Higher elevation should have lower pressure
        assert float(result_deq[0]) > float(result_deq[-1])

    def test_calc_psurf_sea_level(self):
        """Test surface pressure at sea level."""
        temp = xr.DataArray(
            [288.15],  # ~15°C
            attrs={"units": "kelvin"},
        ).metpy.quantify()

        elev = xr.DataArray(
            [0],  # sea level
            attrs={"units": "m"},
        ).metpy.quantify()

        result = calc_psurf(temp, elev)

        # Should be close to standard atmospheric pressure (~101325 Pa)
        assert 101000 < float(result) < 102000


class TestCalcSnow:
    """Test cases for calc_snow function."""

    @pytest.fixture
    def temp_rain_data(self):
        """Create sample temperature and rainfall data."""
        time = pd.date_range("2024-01-01", periods=4, freq="D")
        temp = xr.DataArray(
            [253.15, 273.15, 283.15, 293.15],  # -20°C, 0°C, 10°C, 20°C
            coords={"time": time},
            dims=["time"],
            attrs={"units": "kelvin"},
        ).metpy.quantify()

        rain = xr.DataArray(
            [10, 10, 10, 10],
            coords={"time": time},
            dims=["time"],
            attrs={"units": "mm/day"},
        ).metpy.quantify()

        return temp, rain

    def test_calc_snow_below_freezing(self, temp_rain_data):
        """Test that snowfall occurs below freezing point."""
        temp, rain = temp_rain_data

        result = calc_snow(temp, rain)

        print(result)
        # Below 0°C (273.15K) should have snow
        assert result[0] > 0
        assert result[1] == 0  # At freezing point

    def test_calc_snow_above_freezing(self, temp_rain_data):
        """Test that snowfall is zero above freezing point."""
        temp, rain = temp_rain_data

        result = calc_snow(temp, rain)

        # Above 0°C (273.15K) should have no snow
        assert result[2] == 0
        assert result[3] == 0

    def test_calc_snow_preserves_attributes(self, temp_rain_data):
        """Test that snow calculation preserves data attributes."""
        temp, rain = temp_rain_data
        original_attrs = rain.metpy.dequantify().attrs.copy()

        result = calc_snow(temp, rain)

        # Attributes should be preserved
        assert hasattr(result, "attrs")

    @pytest.mark.parametrize(
        "temp_value,expected_snow",
        [
            (253.15, True),   # -20°C -> snow
            (263.15, True),   # -10°C -> snow
            (273.15, False),  # 0°C -> no snow (threshold)
            (283.15, False),  # 10°C -> no snow
            (293.15, False),  # 20°C -> no snow
        ],
    )
    def test_calc_snow_various_temperatures(self, temp_value, expected_snow):
        """Test snow calculation with various temperature thresholds."""
        temp = xr.DataArray(
            [temp_value],
            attrs={"units": "kelvin"},
        ).metpy.quantify()

        rain = xr.DataArray(
            [10],
            attrs={"units": "mm/day"},
        ).metpy.quantify()

        result = calc_snow(temp, rain)

        if expected_snow:
            assert result.values[0] > 0
        else:
            assert result.values[0] == 0


class TestDefaultCo2:
    """Test cases for default_co2 function."""

    def test_default_co2_basic(self):
        """Test basic CO2 constant creation."""
        coords = {}
        dims = []

        result = default_co2(coords, dims)

        assert result is not None
        # 350 ppm
        assert float(result) == pytest.approx(0.00035, rel=1e-6)

    def test_default_co2_with_coords(self):
        """Test CO2 creation with coordinates."""
        time = pd.date_range("2024-01-01", periods=2, freq="D")
        coords = {"time": time}
        dims = ["time"]

        result = default_co2(coords, dims)

        assert result is not None
        assert "ppm" in str(result.attrs["units"])

    def test_default_co2_units(self):
        """Test that CO2 has correct units."""
        coords = {}
        dims = []

        result = default_co2(coords, dims)

        assert result.attrs["units"] == "ppm"
