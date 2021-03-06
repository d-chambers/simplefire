"""
Misc utilities for simplefire.
"""
import numpy as np

import pandas as pd
from simplefire.constants import _data_path


def get_year_index(start_year="now", year_count=50) -> pd.Index:
    """Return a pandas index for years from start to max_years"""
    start = pd.Timestamp(start_year).year
    years = np.arange(start, start + year_count)
    index = pd.Index(years, name="year")
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


def extrapolate_to_index(df, index):
    """
    Extrapolates rows to annual index.

    If no information is present for a given year use the closest year in
    the past for which data is available,
    """
    if index is None:
        return df
    if "year" in df.columns:
        df = df.set_index("year")
    out = pd.DataFrame(index=index, columns=df.columns)
    out.update(df)
    out = (pd.concat([df, out], axis=0).sort_index().fillna(method="ffill")).loc[index]
    return out


def read_data(data_type: str, status=None, index=None):
    """
    Read one of the dataframes containing tax information.

    Parameters
    ----------
    data_type
        The type of data to read
    status
        The filing status, if needed.
    index
        A pandas index of years to extrapolate data, optional.
    Returns
    -------

    """
    # first determine if
    maybe_dir = _data_path / data_type
    if maybe_dir.is_dir():
        assert status is not None, f"you must specify status for {data_type}"
        path = maybe_dir / f"{status}.csv"
        if path.exists():
            return extrapolate_to_index(pd.read_csv(path), index=index)
    # data is a csv independent of filing status
    if not data_type.endswith(".csv"):
        data_type = data_type + ".csv"
    path = _data_path / data_type
    # date types doesn't exist, raise
    if not path.exists():
        msg = f"{data_type} / {status} is not a valid dataset combination!"
        raise FileNotFoundError(msg)
    return extrapolate_to_index(pd.read_csv(path), index=index)


def extend_df_to_years(df, years):
    """
    Extend a dataframe to include values in years extrapolate forward.
    """
    year_set = set(df['year'])
    df_years = df['year']
    out = []
    for year in years:
        if year in year_set:
            out.append(df[df['year'] == year])
        closest_year = df_years[df_years < year].max()
        sub = df[df['year'] == closest_year].copy()
        sub['year'] = year
        out.append(sub)
    return pd.concat(out, ignore_index=True, axis=0)



def _get_tax_size(year, tax_df):
    """Get the tax bins (in decimals) and size of each bin for a given year."""
    sub = (
            tax_df[tax_df['year'] == year]
            .sort_values('amount')
            .drop_duplicates()
            .reset_index(drop=True)
        )
    tax = sub['tax_percent'].values / 100.
    size = sub['amount'] - sub['amount'].shift().fillna(0).values
    return tax, size


def _pad_bins(array):
    """insert 0 at begining of array and set last value to inf"""
    bins = np.insert(array, 0, 0).astype(float)
    bins[-1] = np.inf  # no upper limit
    return bins


def tax_to_income(ser: pd.Series, tax_df: pd.DataFrame) -> pd.Series:
    """
    Calculate the income an amount of tax paid (or tax credit) covers.
    """
    tdf = extend_df_to_years(tax_df, ser.index)
    out = {}
    for year in ser.index:
        amount = ser[year]
        assert amount >= 0
        tax, size = _get_tax_size(year, tdf)
        tax_cum = (tax * size).cumsum().values
        bins = _pad_bins(tax_cum)
        idx = np.digitize(amount, bins)
        # get tax from previous brackets
        previous_tax = tax_cum[:idx - 1].sum()
        previous_bracket = size[:idx - 1].sum()
        current_tax = amount - previous_tax
        current_bracket_ = current_tax / tax[idx - 1]
        out[year] = previous_bracket + current_bracket_
    return pd.Series(out)


def income_to_tax(ser: pd.Series, tax_df: pd.DataFrame) -> pd.Series:
    """
    Convert income by year to total tax for each year.
    """
    tdf = extend_df_to_years(tax_df, ser.index)
    out = {}
    for year in ser.index:
        amount = ser[year]
        assert amount >= 0
        tax, size = _get_tax_size(year, tdf)
        size_cum = size.cumsum().values
        tax_cum = (tax * size).cumsum().values
        bins = _pad_bins(size_cum)
        idx = np.digitize(amount, bins)
        # get tax from previous brackets
        previous_tax = tax_cum[:idx - 1].sum()
        previous_bracket = size[:idx - 1].sum()
        current_bracket_ = amount - previous_bracket
        current_tax = current_bracket_ * tax[idx - 1]
        out[year] = previous_tax + current_tax
    return pd.Series(out)
