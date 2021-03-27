"""
Core functions for computing financial stats.
"""

from typing import Sequence
from typing_extensions import Literal

import numpy as np
import pandas as pd
from pydantic.dataclasses import dataclass

from simplefire.utils import get_year_index, get_increasing_df, read_data

filling_types = Literal["single", "married", "head_of_household"]


def get_tax_brackets():
    """
    Return a dataframe with tax brackets for a given year.

    Use the most recent year if year-specific data are not included.
    """


@dataclass()
class Income:
    """
    A class representing potential w2-type earned income produced by a
    household.

    Parameters
    ----------
    yearly_income
        The annually salary of the household, in dollars.
    starting_year
        The year for starting income
    yearly_income_growth_percent
        The percent the income is expected to grow each year above inflation.
    """

    annual_income: float = 75_000
    annual_growth_percent: float = 1.0

    def get_income_series(self, index=None):
        """Get potential income for next 45 years."""
        index = index if index is not None else get_year_index()
        income = get_increasing_df(
            index=index,
            start_value=self.annual_income,
            annual_increase=self.annual_growth_percent,
        )
        return pd.Series(income, index=index)


@dataclass()
class Spending:
    """
    A class to represent spending of a household.

    Parameters
    ----------
    annual_spending
        The spending for a household per year.
    """

    annual_spending: float = 35_000
    annual_growth_percent: float = 0.0

    def get_spending_df(self, index=None):
        """Return a series """
        index = index if index is not None else get_year_index()
        spending = get_increasing_df(
            index=index,
            start_value=self.annual_income,
            annual_increase=self.annual_growth_percent,
        )
        return spending


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
        claimable = ages <= self._max_age
        credit_by_year = pd.Series(claimable.sum(axis=1), index=index)
        allowable_tax_credit = read_data('child_tax_credit', index=index)
        child_tax_credit = credit_by_year * allowable_tax_credit

        # read in
        breakpoint()


@dataclass()
class FireCalculator:
    """
    A class to simulate your FIRE journey.
    """

    income: Income
    spending: Spending
    kids: int = 2
    investment_growth_percent: float = 7.0
    draw_down_percent: float = 4.0
    traditional_401_balance = 0
    roth_401_balance = 0
    traditional_ira_balance = 0
    roth_ira_balance = 0

    def get_fire_plan(self) -> pd.DataFrame:
        """Return a dataframe with a fire plan."""
        trial_income = self._get_income_series()

        breakpoint()

    def _get_income_series(self):
        """Get potential income for next 45 years."""

        breakpoint()
        breakpoint()


def get_fire_dataframe(
    income: float,
    kids: int,
    annual_spending: float,
    status: Literal["married", "head_of_household", ""] = "married",
):
    """
    Create a dataframe with basic info about income/family.

    Parameters
    ----------
    income
    kids
    status
    annual_spending

    Returns
    -------

    """
