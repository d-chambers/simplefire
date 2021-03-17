"""
Core functions for computing financial stats.
"""

from typing_extensions import Literal
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
    yearly_income: float = 75_000
    kids: int = 2
    annual_spending: float = 35_000
    status: Literal['married', 'head_of_household', 'single'] = 'married'
    yearly_income_growth_percent: float = 2.5
    investment_growth_percent: float = 7.0
    draw_down_percent: float = 4.0
    maximum_income_tax: float = 0.0





def get_fire_dataframe(
        income: float,
        kids: int,
        annual_spending: float,
        status: Literal['married', 'head_of_household', ''] = 'married',
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




