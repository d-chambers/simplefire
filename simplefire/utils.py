"""
Misc utilities for simplefire.
"""
import numpy as np
import pandas as pd
from simplefire.constants import _data_path


def get_year_index(start_year="now", year_count=50) -> pd.Index:
    """Return a pandas index for years from start to max_years"""

    start = pd.Timestamp(start_year)
    index = pd.date_range(str(start.year), str(start.year + year_count), freq="Y")
    return index


def get_increasing_df(index, start_value, annual_increase):
    """
    Return a series of values increase by annual_increase amount.
    """
    ones = np.ones(len(index))
    growth_ = ones + annual_increase / 100
    growth = growth_ ** np.arange(len(index))
    income = growth * start_value
    return pd.Series(income, index=index)


def read_data(data_type: str, status=None):
    """
    Read one of the dataframes containing tax information.

    Parameters
    ----------
    data_type
        The type of data to read
    status
        The filing status, if needed.

    Returns
    -------

    """
    # first determine if
    maybe_dir = _data_path / data_type
    if maybe_dir.is_dir():
        assert status is not None, f"you must specify status for {data_type}"
        path = maybe_dir / f"{status}.csv"
        if path.exists():
            return pd.read_csv(path)
    # data is a csv independent of filing status
    if not data_type.endswith(".csv"):
        data_type = data_type + ".csv"
    path = _data_path / data_type
    # date types doesn't exist, raise
    if not path.exists():
        msg = f"{data_type} / {status} is not a valid dataset combination!"
        raise FileNotFoundError(msg)
    return pd.read_csv(path)
