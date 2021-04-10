"""
Tests for simplefire's main functionality.
"""
import pytest

import pandas as pd

from simplefire.utils import get_year_index
from simplefire.core import (
    FireCalculator,
    Income,
    Household,
    RetirementStrategy,
    Investment,
)
from simplefire.exceptions import ContributuionLimitsExceeded, BalanceError

#
# @pytest.fixture()
# def default_fire():
#     """Return a happy path fire calculator."""
#     household = Household(
#         status="married",
#         children_age=[2, 4],
#         annual_spending=35_000,
#     )
#
#     fc = FireCalculator(
#         incomes=[Income(annual_income=75_000)],
#         investments=Investments(),
#         household=household,
#         retirement_strategy=RetirementStrategy(income_target_ratio=1.00),
#     )
#     return fc


@pytest.fixture()
def year_index():
    """Return an index of years."""
    return get_year_index()


@pytest.fixture()
def default_investment(year_index):
    return Investment(years=year_index)


@pytest.fixture()
def default_income():
    return Income()


@pytest.fixture()
def default_household():
    return Household(children_age=[1, 3], status="married")


# def fire_df(default_fire):
#     """Return the default fire dataframe."""
#     return default_fire.get_fire_plan()


class TestIncome:
    @pytest.fixture()
    def income_df(self, default_income):
        """Return the default income dataframe."""
        return default_income.get_income_series()

    def test_generate_income_df(self, income_df):
        """Tests income dataframe."""


class TestInvestments:
    """Tests for investments class"""

    @pytest.fixture()
    def populated_investment(self, default_investment):
        """Populate the default investment with several deposists/years."""
        for _ in range(5):
            default_investment.contribute(12_000)
            default_investment.close_year()
        return default_investment

    def test_default_init(self, default_investment):
        """Ensure the Investments class can be created."""
        df = default_investment.df
        # no ending balances yet
        assert pd.isnull(df["end_balance"]).all()

    def test_contribute(self, default_investment, year_index):
        """Ensure contributions can be made."""
        year = year_index[0]
        default_investment.contribute(12_000)
        default_investment.close_year(year)
        ser = default_investment.df.loc[year]
        assert ser["end_balance"] > ser["start_balance"]
        # interest for contributions should also have been calculated
        assert ser["end_balance"] > ser["contribution"]
        assert not pd.isnull(ser).all()

    def test_close_year(self, populated_investment):
        """Sanity tests on closing out a year"""
        df = populated_investment.df
        increasing_columns = ["basis", "start_balance", "end_balance"]
        for col in increasing_columns:
            shift = df[col].shift()
            gt = df[col] >= shift
            is_zero = df[col] == 0
            isna = pd.isnull(shift) | pd.isnull(df[col])
            assert (gt | isna | is_zero).all()

    def test_contribute_limit(self, default_investment):
        """Ensure contribution limits are enforced."""
        default_investment.contribution_limit = 18_000
        with pytest.raises(ContributuionLimitsExceeded, match="exceeds"):
            default_investment.contribute(1_000_000_000)

    def test_contribute_employer(self, default_investment):
        """Tests for employer contributions."""

        default_investment.contribution_limit = 1_000
        default_investment.contribute(10_000, employee=False)
        default_investment.close_year()
        df = default_investment.df
        # the basis should not have increased
        assert (df["basis"] == 0).all()

    def test_current_year(self, default_investment, year_index):
        """Test that the class keeps track of the year."""
        year1 = default_investment.current_year
        assert year1 == year_index[0]
        default_investment.close_year()
        year2 = default_investment.current_year
        assert year1 == (year2 - 1)

    def test_withdraw_error(self, populated_investment):
        """Ensure withdrawing more than account raises error."""
        with pytest.raises(BalanceError):
            populated_investment.withdraw(5_000_000)

    def test_balanced_withdraw(self, populated_investment):
        """Ensure withdraws can be made on balances"""
        df1 = populated_investment.df
        withdraw = populated_investment.withdraw(1_000, strategy="balanced")
        df2 = populated_investment.df

        breakpoint()
        default_investment


class TestHousehold:
    """Tests for household class."""

    @pytest.fixture()
    def modifier_df(self, default_household):
        """get the modifier dataframe """
        return default_household.get_household_modifier_df()

    def test_modified_df(self, modifier_df):
        """Ensure modifier works."""
        assert isinstance(modifier_df, pd.DataFrame)

    def test_spending_df(self, default_household):
        """Ensure spending df """
        out = default_household.get_spending_df()
        assert len(out)
        # assert isinstance(out, pd.DataFrame)

    def test_taxfree_df(self, default_household):
        """Get the amount of income-tax free income possible by year."""
        out = default_household.get_tax_free_amount()
        assert len(out)
