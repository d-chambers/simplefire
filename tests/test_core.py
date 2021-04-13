"""
Tests for simplefire's main functionality.
"""
import pytest


import pandas as pd

from simplefire.utils import get_year_index
from simplefire.core import (
    Income,
    Household,
    Investment,
    FamilyIncome,
    TaxEvasionStrategy
)
from simplefire.exceptions import ContributionLimitsExceeded, BalanceError


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
def default_family_income(default_income):
    return FamilyIncome([default_income])


@pytest.fixture()
def default_household():
    return Household(children_age=(1, 3), status="married")


@pytest.fixture()
def tax_evasion(default_household, default_family_income):
    """Init a tax evasion object"""
    return TaxEvasionStrategy(
        household=default_household, family_income=default_family_income,
    )


@pytest.fixture()
def fired_tax_evasion(tax_evasion):
    tax_evasion.start_fire()
    return tax_evasion


class TestIncome:
    @pytest.fixture()
    def income_df(self, default_income):
        """Return the default income dataframe."""
        return default_income.get_income_series()

    def test_generate_income_df(self, income_df):
        """Tests income dataframe."""


class TestFamilyIncome:
    """Tests for one or more income per family."""
    @pytest.fixture()
    def single_income(self):
        """A family with a single income."""
        income = Income()
        return FamilyIncome([income])

    @pytest.fixture()
    def double_income(self):
        """A family income with two incomes."""
        income1 = Income()
        income2 = Income(annual_income=60_000)
        return FamilyIncome([income1, income2])

    @pytest.fixture(params=['single_income', 'double_income'])
    def family_income(self, request) -> FamilyIncome:
        """meta fixture for gathering up incomes"""
        return request.getfixturevalue(request.param)

    def test_family_income_df(self, family_income):
        """Tests for the df produced by income."""
        out = family_income.get_df()
        assert isinstance(out, pd.DataFrame)
        assert (out['income'] > out['match']).all()


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
        cdf = pd.DataFrame([[2021, 18_000]], columns=['year', 'amount'], )
        default_investment.contribution_limit = 18_000
        with pytest.raises(ContributionLimitsExceeded, match="exceeds"):
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

    def test_basis_withdraw(self, populated_investment):
        """Ensure withdraws can be made on balances"""
        current_year = populated_investment.current_year
        ser1 = populated_investment.df.loc[current_year]
        withdraw = populated_investment.withdraw(1_000, strategy="basis")
        ser2 = populated_investment.df.loc[current_year]
        assert withdraw.tax == 0
        assert ser2['contribution'] == -withdraw.amount
        assert (ser1['basis'] - ser2['basis']) == withdraw.amount

    def test_gains_withdraw(self, populated_investment):
        """Ensure gains can be withdrawn."""
        current_year = populated_investment.current_year
        ser1 = populated_investment.df.loc[current_year]
        withdraw = populated_investment.withdraw(1_000, strategy="gains")
        ser2 = populated_investment.df.loc[current_year]
        assert withdraw.tax == withdraw.amount
        assert ser2['contribution'] == -withdraw.amount
        assert ser1['basis'] == ser2['basis']

    def test_balance(self, populated_investment):
        """Ensure the total balance can be easily queried."""
        balance = populated_investment.balance
        assert balance > 0
        new = Investment(years=[2020, 2021])
        assert new.balance == 0

    def test_gains(self, populated_investment):
        gains = populated_investment.gains
        assert gains > 0
        new = Investment(years=[2020, 2021])
        assert new.gains == 0


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
        out = default_household.get_tax_free_series()
        assert ((out > 20_000) & (out < 70_000)).all()
        assert len(out)


class TestTaxEvasionStrategy:
    """Tests for tax evasion fire strategy."""

    def test_fire(self, fired_tax_evasion):
        """Test fire simulation."""
        roth_df = fired_tax_evasion.roth_ira.df
        # ensure roth is filled out
        assert not roth_df.isnull().any().any()


class TestPlotTaxEvasionStrategy:
    """Tests for plotting tax evasion strategies."""

    def test_plot_fire(self, fired_tax_evasion, tmp_path):
        fired_tax_evasion.plot_yearly_table(tmp_path)



