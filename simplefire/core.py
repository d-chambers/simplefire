"""
Core functions for computing financial stats.
"""

from typing import Sequence, List, Optional
from typing_extensions import Literal
from operator import add

from functools import reduce

import numpy as np
import pandas as pd

from simplefire.dataclasses import dataclass
from simplefire.utils import get_year_index, get_increasing_df, read_data
from simplefire.exceptions import ContributuionLimitsExceeded, BalanceError

filling_types = Literal["single", "married", "head_of_household"]


@dataclass()
class Income:
    """
    A class representing potential w2-type earned income produced by a
    household.

    Parameters
    ----------
    annaul_income
        The annually salary of the household, in dollars.
    annaul_growth
        The percentage of income increase, normalized for inflation.
    retirement_match
        The percentage for which the employor matches retirement contributions.
    """

    annual_income: float = 75_000
    annual_growth: float = 0.5
    retirement_match: float = 5

    def get_income_series(self, index=None):
        """Get potential income for next 45 years."""
        index = index if index is not None else get_year_index()
        income = get_increasing_df(
            index=index,
            start_value=self.annual_income,
            annual_increase=self.annual_growth,
        )
        return pd.Series(income, index=index)


#
# @dataclass()
# class Spending:
#     """
#     A class to represent spending of a household.
#
#     Parameters
#     ----------
#     annual_spending
#         The spending for a household per year.
#     """
#
#     annual_spending: float = 35_000
#     annual_growth_percent: float = 0.0


@dataclass()
class Household:
    """
    An object to represent the status of a household.

    Parameters
    ----------
    status
        The filing status of the house hold. Options are:
            married, head_of_household, single
    children_age
        A list of dependents ages.
    """

    status: filling_types = "married"
    children_age: Sequence[int] = ()
    annual_spending: float = 35_000
    annual_growth: float = 0.0
    _max_age = 18

    def get_household_modifier_df(self, index=None):
        """
        Get a dataframe of deductions, credits, and adjustments
        for this household by year.
        """
        index = index if index is not None else get_year_index()
        age_list = [np.arange(x, x + len(index)) for x in self.children_age]
        ages = np.stack(age_list).T
        # get years credit is good
        claimable = (ages <= self._max_age).astype(bool)
        credit_by_year = pd.Series(claimable.sum(axis=1), index=index)
        allowable_tax_credit = read_data("child_tax_credit", index=index)["amount"]
        child_tax_credit = credit_by_year * allowable_tax_credit
        deduction = read_data("standard_deduction", status=self.status, index=index)
        out = pd.DataFrame(index=index)
        out["child_tax_credit"] = child_tax_credit
        out["deduction"] = deduction
        return out

    def get_spending_df(self, index=None):
        """Return a series """
        index = index if index is not None else get_year_index()
        spending = get_increasing_df(
            index=index,
            start_value=self.annual_spending,
            annual_increase=self.annual_growth,
        )
        return spending

    def get_tax_free_amount(self):
        """
        Return a datafarme of the amount of w2 that can be earned without
        paying taxes
        """
        tax_rate_df = read_data("income", status=self.status)
        mod = self.get_household_modifier_df()
        breakpoint()


@dataclass
class Withdrawal:
    """A withdrawal from an investment account."""

    amount: float
    taxable_amount: float
    tax_type: Literal["income", "capital_gains"]


class Investment:
    """
    A base class representing investments of some sort.

    Parameters
    ----------
    years
        A sequences of years the investment tracks
    starting_balance
        The starting balance of the investment account on Jan 1 of the first
        years;
    starting_basis
        The basis of the investments on Jan 1 of the first year. Only
        applicable if the investment isn't tax_free.
    annual_growth
        The anticipated growth percentage in inflation adjusted dollars.

    Attributes
    ----------
    pretax
        If True, contributions to the account are exempt from
        income tax.
    capital_gains
        If True, gains are taxed using capital gains rates.
    tax_free
        If True, contributions can be withdrawn tax-free.
    convertible
        If True, balances can be converted (usually to Roth style investments)
    contribution_limit
        If not NaN, the limit the employee (not employer) can make to the
        account.
    """

    pretax: bool = False
    captial_gains: bool = False
    taxfree: bool = False
    convertible: bool = False
    contribution_limit: float = np.NaN
    _columns = ("basis", "start_balance", "end_balance", "contribution", "gains")

    def __init__(self, years, starting_balance=0, starting_basis=0, annual_growth=4):
        self.df = pd.DataFrame(index=years, columns=list(self._columns))
        self.df["contribution"] = 0
        self.df["basis"] = 0
        # set starting balance and basis
        self.df.loc[years[0], "start_balance"] = starting_balance
        self.df.loc[years[0], "basis"] = starting_basis
        self.growth_rate = annual_growth / 100.0

    def contribute(self, amount, employee=True):
        """
        Make a contribution to the account.

        Parameters
        ----------
        amount
            The amount to contribute to the investment.
        employee
            If True, contributions are from an employee rather than
            an employer matching program.
            This enforces limits and increases the basis of the investment
            If false, the basis is not increased and no limits are enforced.
        """
        year = self.current_year
        new_contrib = self.df.loc[year, "contribution"] + amount
        if employee and new_contrib > self.contribution_limit:
            msg = (
                f"{new_contrib} exceeds contribution limit of "
                f"{self.contribution_limit}"
            )
            raise ContributuionLimitsExceeded(msg)
        self.df.loc[year, "contribution"] = new_contrib
        if employee:
            self.df.loc[year, "basis"] += amount

    def close_year(self, year=None):
        """
        Close out a year by calculating ending balance.

        Parameters
        ----------
        year
            The year to close. Must have a start_balance.
        """
        year = year or self.current_year
        start_balance = self.df.loc[year, "start_balance"]
        contributions = self.df.loc[year, "contribution"]
        # raise if start balance is not yet determined
        if pd.isnull(start_balance):
            msg = f"starting balance for year {year} not yet calculated"
            raise BalanceError(msg)
        # calculate gains and ending balance
        balance_gain = start_balance * self.growth_rate
        # contributions are assumed to be made at mid-year
        contribution_gain = contributions * self.growth_rate / 2.0
        gains = contribution_gain + balance_gain
        ending_balance = start_balance + gains + contributions
        # determine ending basis
        self.df.loc[year, "end_balance"] = ending_balance
        self.df.loc[year, "gains"] = gains
        # set next years stats
        next_year = year + 1
        if next_year in self.df.index:
            self.df.loc[next_year, "start_balance"] = ending_balance
            self.df.loc[next_year, "basis"] = self.df.loc[year, "basis"]

    def withdraw(
        self,
        amount,
        strategy: Literal["basis", "gains", "balanced"] = "balanced",
    ) -> Withdrawal:
        """
        Withdraw money from an investment account.

        Parameters
        ----------
        amount
            The amount to withdraw. A lesser amount can be withdrawn if
            the investment is depleted.
        strategy
            Determines which funds are withdrawn. Options are:
                basis - only withdraw from the basis
                gains - only withdraw gains from
                balanced - Withdraw a balance of gains and basis based on
                    their respective percentages of the account.
        """
        year = self.current_year
        contrib = self.df.loc[year, "contribution"]
        balance = self.df.loc[year, "start_balance"]
        funds = contrib + balance
        if (funds - amount) < 0:
            msg = f"Cannot withdraw {amount} only {funds} available"
            raise BalanceError(msg)
        self.df.loc[year, "basis"] = self._calc_new_basis(amount, strategy)
        self.df.loc[year, "contribution"] -= amount
        # create/return withdrawal object
        Withdrawal(amount=amount)

    def _calc_new_basis(self, amount, strategy):
        """Determine the new basis after withdrawing."""

        def _balanced():

            pass

        def _basis():
            pass

        def _gains():
            pass

        year = self.current_year
        start_balance = self.df.loc[year, "start_balance"]
        start_basis = self.df.loc[year, "basis"]
        contribution = self.df.loc[year, "basis"]
        out = {"balanced": _balanced, "basis": _basis, "gains": _gains}
        return out[strategy]()

    @property
    def current_year(self):
        """Return the current (non-closed) year."""
        not_closed_index = self.df[self.df["end_balance"].isnull()].index
        return not_closed_index.min()


@dataclass()
class Taxable(Investment):
    """
    A taxable investment account.
    """

    capital_gains = True


class TraditionalIRA(Investment):
    """
    A traditional Individual Retirement account
    """


class RothIRA(Investment):
    """"""


@dataclass()
class RetirementStrategy:
    """
    A class to specify retirement strategies.

    Parameters
    ----------
    income_target_ratio
        The ratio of a household's income which triggers retirement
    years_employed
        The total number of years of employment after which retirement
        will be triggered.
    """

    income_target_ratio: Optional[float] = 1.00
    years_employed: Optional[int] = None


class FireStrategy:
    """ A base class for calculating strategies."""

    def get_fire_plan(self) -> pd.DataFrame:
        """Return a dataframe with a fire plan."""
        # first get a
        incomes = self.get_total_w2_incomes()
        spending = self.household.get_spending_df()
        tax_free_income = self.household.get_tax_free_amount()
        breakpoint()

    def get_total_w2_incomes(self):
        """Returns a summed dataframe of potential w2 income."""
        income_series = [x.get_income_series() for x in self.incomes]
        out = reduce(add, income_series)
        return out

    def _get_income_series(self):
        """Get potential income for next 45 years."""

        breakpoint()
        breakpoint()


@dataclass()
class FireCalculator:
    """
    A class to simulate your FIRE journey.

    Parameters
    ----------
    incomes
        A list of income sources
    household
        Status of household
    investments
        Investments currently held
    retirement_strategy
        Strategy for determining when retirement triggers
    """

    incomes: List[Income]
    household: Household
    investments: List[Investment]
    retirement_strategy: RetirementStrategy


#
#
# def get_fire_dataframe(
#     income: float,
#     kids: int,
#     annual_spending: float,
#     status: Literal["married", "head_of_household", ""] = "married",
# ):
#     """
#     Create a dataframe with basic info about income/family.
#
#     Parameters
#     ----------
#     income
#     kids
#     status
#     annual_spending
#
#     Returns
#     -------
#
#     """
