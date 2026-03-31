from xarray import DataArray
import xarray as xr
import pandas as pd


def daily_to_hourly_acc(da: DataArray) -> DataArray:
    gpd = da.groupby("time.date")
    diff_da = xr.concat(
        [
            gpd.first(keep_attrs=True).rename({"date": "time"}),
            gpd.apply(lambda x: x.diff("time")),
        ],
        dim="time",
    )

    # Internally, TimeStamp is being converted to datetime64
    # on groupby if timestamp is 00:00:00.
    diff_da['time'] = pd.DatetimeIndex(diff_da['time'].values)


    diff_da.attrs["units"] = f"{diff_da.attrs['units']} hr**-1"
    return diff_da
