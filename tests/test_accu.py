import pytest
import numpy as np
import pandas as pd
import xarray as xr

from met_preprocessor.accu import daily_to_hourly_acc


class TestDailyToHourlyAcc:
    """Test cases for daily_to_hourly_acc function."""

    @pytest.fixture
    def single_day_data(self):
        """Create simple daily data with one day.
        Rainfall increasing by 1mm every hour"""
        time = pd.date_range("2024-01-01", periods=24, freq="h")
        # Simulate daily accumulation
        data = xr.DataArray(
            np.arange(1, 25).cumsum(),
            coords={"time": time},
            dims=["time"],
            name="Rainf",
            attrs={"units": "mm"},
        )
        return data
    
    # TODO: Multiday data

    def test_daily_to_hourly_acc(self, single_day_data):
        """Test basic daily to hourly accumulation conversion."""
        result = daily_to_hourly_acc(single_day_data)

        assert (result.values == np.arange(1, 25)).all()
        assert type(result) is not None
        assert result.attrs == {"units" : "mm hr**-1"}

    def test_preserve_attribute(self, single_day_data):
        """Test basic daily to hourly accumulation conversion."""
        single_day_data.attrs = {"long_name": "RainFall", "units" : "mm"}
        result = daily_to_hourly_acc(single_day_data)
        expected_attrs = {"long_name": "RainFall", "units" : "mm hr**-1"}

        assert result.attrs == expected_attrs