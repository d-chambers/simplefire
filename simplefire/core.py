"""
Core functions for computing financial stats.
"""


from typing_extensions import Literal


import numpy as np
import pandas as pd
from pydantic.dataclasses import dataclass


def get_tax_brackets():
    """
    Return a dataframe with tax brackets for a given year.

    Use the most recent year if year-specific data are not included.
    """


@dataclass()
class FireCalculator:
    """
    A class to simulate your FIRE journey.
    """

    starting_year = "now"
    yearly_income: float = 75_000
    kids: int = 2
    annual_spending: float = 35_000
    status: Literal["married", "head_of_household", "single"] = "married"
    yearly_income_growth_percent: float = 1.0
    investment_growth_percent: float = 7.0
    draw_down_percent: float = 4.0
    traditional_401_balance = 0
    roth_401_balance = 0
    traditional_ira_balance = 0
    roth_ira_balance = 0

    _trial_years = 45

    def get_fire_plan(self) -> pd.DataFrame:
        """Return a dataframe with a fire plan."""
        trial_income = self._get_income_series()

        breakpoint()

    def _get_income_series(self):
        """Get potential income for next 45 years."""
        ones = np.ones(self._trial_years)

        growth_ = ones + self.yearly_income_growth_percent / 100
        growth = growth_ ** np.arange(self._trial_years)
        income = growth * self.yearly_income
        #
        start = pd.Timestamp(self.starting_year)

        index = pd.date_range(
            str(start.year), str(start.year + self._trial_years), freq="Y"
        )
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
