import pytest
import numpy as np
import pandas as pd
import xarray as xr
from metpy.units import units

from met_preprocessor.standard_param import (
    vp_vpd_tair_sh,
    vp_tair_sh,
    vpd_tair_sh,
    sp_dewp_sh,
    wind_speed,
)


class TestVpVpdTairSh:
    """Test cases for vp_vpd_tair_sh (vapor pressure, VPD, temperature -> specific humidity)."""

    @pytest.fixture
    def vp_vpd_tair_data(self):
        """Create sample vapor pressure, VPD, and temperature data."""
        time = pd.date_range("2024-01-01", periods=4, freq="D")
        vp = xr.DataArray(
            [1000, 1200, 1400, 1600],
            coords={"time": time},
            dims=["time"],
            attrs={"units": "hPa"},
        ).metpy.quantify()

        vpd = xr.DataArray(
            [500, 600, 700, 800],
            coords={"time": time},
            dims=["time"],
            attrs={"units": "hPa"},
        ).metpy.quantify()

        tair = xr.DataArray(
            [283.15, 288.15, 293.15, 298.15],  # temperature in K
            coords={"time": time},
            dims=["time"],
            attrs={"units": "kelvin"},
        ).metpy.quantify()

        return vp, vpd, tair

    def test_vp_vpd_tair_sh_basic(self, vp_vpd_tair_data):
        """Test basic specific humidity calculation from vp, vpd, and tair."""
        vp, vpd, tair = vp_vpd_tair_data

        result = vp_vpd_tair_sh(vp, vpd, tair)

        assert result is not None
        assert len(result) == len(tair)
        assert all(result >= 0)  # Specific humidity should be non-negative
        assert all(result <= 1)  # Specific humidity should not exceed 1

    def test_vp_vpd_tair_sh_units(self, vp_vpd_tair_data):
        """Test that output has correct units (kg/kg)."""
        # Arrange
        vp, vpd, tair = vp_vpd_tair_data

        # Act
        result = vp_vpd_tair_sh(vp, vpd, tair)
        result_deq = result.metpy.dequantify()

        # Assert
        assert "kg" in str(result_deq.attrs["units"]) or "dimensionless" in str(
            result_deq.attrs["units"]
        )


class TestSpDewpSh:
    """Test cases for sp_dewp_sh (surface pressure, dewpoint -> specific humidity)."""

    @pytest.fixture
    def sp_dewp_data(self):
        """Create sample surface pressure and dewpoint data."""
        time = pd.date_range("2024-01-01", periods=4, freq="D")
        sp = xr.DataArray(
            [101325, 101325, 101325, 101325],  # constant surface pressure
            coords={"time": time},
            dims=["time"],
            attrs={"units": "hPa"},
        ).metpy.quantify()

        dewp = xr.DataArray(
            [268.15, 273.15, 278.15, 283.15],  # dew point in K
            coords={"time": time},
            dims=["time"],
            attrs={"units": "kelvin"},
        ).metpy.quantify()

        return sp, dewp

    def test_sp_dewp_sh_basic(self, sp_dewp_data):
        """Test specific humidity calculation from surface pressure and dewpoint."""
        sp, dewp = sp_dewp_data

        result = sp_dewp_sh(sp, dewp)

        assert result is not None
        assert len(result) == len(dewp)
        assert all(result >= 0)
        assert all(result <= 1)

    def test_sp_dewp_sh_increases_with_dewpoint(self, sp_dewp_data):
        """Test that higher dewpoint increases specific humidity."""
        sp, dewp = sp_dewp_data

        result = sp_dewp_sh(sp, dewp)
        result_deq = result.metpy.dequantify()

        assert float(result_deq[0]) < float(result_deq[-1])


class TestWindSpeed:
    """Test cases for wind_speed function."""

    @pytest.fixture
    def wind_components(self):
        """Create sample east and north wind components."""
        time = pd.date_range("2024-01-01", periods=4, freq="D")
        wind_e = xr.DataArray(
            [3, 4, 0, 5],
            coords={"time": time},
            dims=["time"],
            attrs={"units": "m/s"},
        ).metpy.quantify()

        wind_n = xr.DataArray(
            [4, 3, 5, 12],
            coords={"time": time},
            dims=["time"],
            attrs={"units": "m/s"},
        ).metpy.quantify()

        return wind_e, wind_n

    def test_wind_speed_basic(self, wind_components):
        """Test basic wind speed calculation from components."""
        wind_e, wind_n = wind_components

        result = wind_speed(wind_e, wind_n)

        assert result is not None
        assert len(result) == len(wind_e)
        assert all(result >= 0)  # Wind speed should be non-negative

    @pytest.mark.parametrize(
        "east,north,expected",
        [
            (0, 0, 0),      # no wind
            (5, 0, 5),      # easterly only
            (0, 5, 5),      # northerly only
            (3, 4, 5),      # 3-4-5 triangle
        ],
    )
    def test_wind_speed_various_components(self, east, north, expected):
        """Test wind speed with various component combinations."""
        wind_e = xr.DataArray(
            [east],
            attrs={"units": "m/s"},
        ).metpy.quantify()
        wind_n = xr.DataArray(
            [north],
            attrs={"units": "m/s"},
        ).metpy.quantify()

        result = wind_speed(wind_e, wind_n)

        assert float(result.metpy.dequantify()) == pytest.approx(expected, rel=1e-2)

