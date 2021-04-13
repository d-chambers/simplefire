"""
Tests for utilities.
"""
import numpy as np
import pandas as pd

import pytest
from simplefire.utils import read_data, tax_to_income, income_to_tax


@pytest.fixture()
def married_income_tax_df():
    """Return the income dataframe for married"""
    tax_rate_df = read_data("income", status='married')
    return tax_rate_df


class TestReadData:
    """tests for reading tax info dataframes."""

    def test_read_child_tax_credit(self):
        """Ensure child tax credit is readable."""
        df = read_data("child_tax_credit")
        assert isinstance(df, pd.DataFrame)
        assert len(df)

    def test_read_capital_gains(self):
        """Ensure capital gains rates are readable"""
        df = read_data("capital_gains", "married")
        assert len(df)
        assert isinstance(df, pd.DataFrame)

    def test_missing_status_raises(self):
        """Ensure missing status raises."""
        with pytest.raises(Exception, match="must specify status"):
            read_data("capital_gains")

    def test_missing_dataset_raises(self):
        """Ensure if the dataset doesn't exist it raises a FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="valid dataset"):
            read_data("not_a_data_type")
        with pytest.raises(FileNotFoundError, match="valid dataset"):
            read_data("capital_gains", "married_but_single")


class TestTaxToIncome:
    """Tests for converting tax to income it covers."""

    def test_basic(self, married_income_tax_df):
        """Test getting basic tax to income."""
        ser = pd.Series([4000], index=[2020])
        out = tax_to_income(ser, married_income_tax_df)
        breakpoint()
        assert ((out < 40_000) & (out > 30_000)).all()

    def test_lowest_bracket(self, married_income_tax_df):
        """ensure the lowest bracket works as well."""
        ser = pd.Series([10], index=[2020])
        out = tax_to_income(ser, married_income_tax_df)
        assert (out == 100).all()

    def test_zero(self, married_income_tax_df):
        """Ensure zero returns zero"""
        ser = pd.Series([0], index=[2020])
        out = tax_to_income(ser, married_income_tax_df)
        assert (out == 0).all()

    def test_highest_bracket(self, married_income_tax_df):
        """Ensure the highest bracket works too."""
        income = 1_000_000_000_000_000_000
        ser = pd.Series([income], index=[2020])
        out = tax_to_income(ser, married_income_tax_df)
        assert isinstance(out, pd.Series)
        # the value should approximate the highest bracket
        df = married_income_tax_df
        max_tax = df[df['year'] == 2020]['tax_percent'].max() / 100.
        assert np.isclose(out.values[0], income / max_tax)


class TestIncomeToTax:
    """Tests for determine how much tax is owed on a taxable income."""

    def test_basic(self, married_income_tax_df):
        """tests for second bracket married"""
        amount = 100_000 - 24_800
        ser = pd.Series([amount], index=[2020])
        out = income_to_tax(ser, married_income_tax_df)
        assert ((out < 9_000) & (out > 8_000)).all()

    def test_lowest_bracket(self, married_income_tax_df):
        """ensure the lowest bracket works as well."""
        ser = pd.Series([10], index=[2020])
        out = income_to_tax(ser, married_income_tax_df)
        assert (out == 1).all()

    def test_zero(self, married_income_tax_df):
        """Ensure zero returns zero"""
        ser = pd.Series([0], index=[2020])
        out = income_to_tax(ser, married_income_tax_df)
        assert (out == 0).all()

    def test_highest_bracket(self, married_income_tax_df):
        """Ensure the highest bracket works too."""
        income = 1_000_000_000_000_000_000
        ser = pd.Series([income], index=[2020])
        out = income_to_tax(ser, married_income_tax_df)
        assert isinstance(out, pd.Series)
        # the value should approximate the highest bracket
        df = married_income_tax_df
        max_tax = df[df['year'] == 2020]['tax_percent'].max() / 100.
        assert np.isclose(out.values[0], income * max_tax)
