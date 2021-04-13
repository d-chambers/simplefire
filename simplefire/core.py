"""
Core functions for computing financial stats.
"""

from typing import Sequence, List, Optional, Collection, Any, Union

from typing_extensions import Literal
from operator import add

from functools import reduce

import numpy as np
import pandas as pd

from simplefire.dataclasses import dataclass
from simplefire.utils import get_year_index, get_increasing_df, read_data, extend_df_to_years, tax_to_income
from simplefire.exceptions import ContributionLimitsExceeded, BalanceError

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
    years: Optional[Union[Sequence[int], pd.Index]] = None

    def __post_init__(self):
        if self.years is None:
            self.years = get_year_index()

    def get_income_series(self):
        """Get potential income for next 45 years."""
        income = get_increasing_df(
            index=self.years,
            start_value=self.annual_income,
            annual_increase=self.annual_growth,
        )
        return pd.Series(income, index=self.years)


@dataclass
class FamilyIncome:
    """A container for a families income."""
    income_list: List[Income]
    years: Optional[Union[Sequence[int], pd.Index]] = None

    def __post_init__(self):
        """Ensure no more than two incomes provided."""
        if self.years is None:
            self.years = get_year_index()
        assert len(self.income_list) <= 2

    def get_df(self):
        """Get the required match amount and such."""
        out = pd.DataFrame(index=self.years)
        contrib_limit_total = []
        required_contribution_total = []
        match_amount_total = []
        income_total = []
        for income in self.income_list:
            ret_limit = read_data('employee_retirement_limits')
            contrib_limit_total.append(
                extend_df_to_years(ret_limit, self.years)
                .set_index('year')['amount']
            )
            income_ser = income.get_income_series()
            match_ = income_ser * (income.retirement_match / 100.)
            required_ = match_
            required_contribution_total.append(required_)
            match_amount_total.append(match_)
            income_total.append(income_ser)
        out['match'] = reduce(add, match_amount_total)
        out['required'] = reduce(add, required_contribution_total)
        out['income'] = reduce(add, income_total)
        out['contribution_limit'] = reduce(add, contrib_limit_total)
        return out

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
    children_age: Collection[int] = ()
    annual_spending: float = 35_000
    annual_growth: float = 0.0
    years: Optional[Union[Sequence[int], pd.Index]] = None
    _max_age = 18
    _credits = ('child_tax_credit', )
    _tax_df: Optional[pd.DataFrame] = None
    _captial_gains_df: Optional[pd.DataFrame] = None
    _std_ser: Optional[pd.Series] = None

    def __post_init__(self):
        if self.years is None:
            self.years = get_year_index()
        self._tax_df = read_data("income", status=self.status)
        self._captial_gains_df = read_data('capital_gains', status=self.status)
        # get the standard deduction for each year
        std = read_data('standard_deduction', status=self.status)
        self._std_ser = (
            extend_df_to_years(std, self.years)
            .set_index('year')
            ['amount']
        )

    def get_household_modifier_df(self):
        """
        Get a dataframe of deductions, credits, and adjustments
        for this household by year.
        """
        index = self.years
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

    def get_spending_df(self,):
        """Return a series """
        spending = get_increasing_df(
            index=self.years,
            start_value=self.annual_spending,
            annual_increase=self.annual_growth,
        )
        return spending

    def get_tax_free_series(self) -> pd.Series:
        """
        Return a datafarme of the amount of w2 that can be earned without
        paying taxes
        """
        mod = self.get_household_modifier_df()
        credits = mod[list(self._credits)].sum(axis=1)
        income = tax_to_income(credits, self._tax_df)
        return income + self._std_ser

    def get_ira_limit_series(self) -> pd.Series:
        """Return a dataframe of IRA limits."""
        df = (
            extend_df_to_years(read_data('ira_limits'), self.years)
            .set_index('year')['amount']
        )
        if self.status == 'married':  # assume two IRAs for married
            df *= 2
        return df

    def _get_tax_free_gains(self) -> pd.Series:
        """return a series of tax free capital gains."""
        ser = pd.Series(np.zeros(len(self.years)), index=self.years)
        gains = tax_to_income(ser, self._captial_gains_df)
        return gains

    def get_df(self):
        """Return a dataframe will all household info."""
        out = pd.DataFrame(index=self.years)
        out['spending'] = self.get_spending_df()
        out['tax_free_income'] = self.get_tax_free_series()
        out['ira_limit'] = self.get_ira_limit_series()
        out['tax_free_gains'] = self._get_tax_free_gains()
        return out


@dataclass
class Withdrawal:
    """A withdrawal from an investment account."""

    amount: float
    tax: float
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

    def __init__(
            self,
            years,
            starting_balance=0,
            starting_basis=0,
            annual_growth=4.5,
    ):
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
            raise ContributionLimitsExceeded(msg)
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
        new_basis, tax = self._calc_new_basis(amount, strategy)
        self.df.loc[year, "contribution"] -= amount
        # modify tax based on account type
        if self.taxfree:
            tax = 0
        elif self.pretax:
            tax = amount
        # create/return withdrawal object
        tax_type = 'capital_gains' if self.captial_gains else 'income'
        self.df.loc[year, "basis"] = new_basis
        return Withdrawal(amount=amount, tax=tax, tax_type=tax_type)

    def _get_taxable(self, potential_tax):
        """Return taxable amount based on """

    def _calc_new_basis(self, amount, strategy):
        """
        Determine the new basis after withdrawing and potential taxable amount.
        """
        def _balanced():
            raise NotImplementedError('Balanced is not yet implemented')

        def _basis():
            new = basis - amount
            tax = 0
            if new < 0:
                tax = abs(new)
                new = 0

            return new, tax

        def _gains():
            gains = (start_balance + contribution) - basis
            if gains > amount:
                return basis, amount
            else:  # not enough gains, reduce basis somewhat
                new_balance = basis - (amount - gains)
                return new_balance, gains

        year = self.current_year
        start_balance = self.df.loc[year, "start_balance"]
        basis = self.df.loc[year, "basis"]
        contribution = self.df.loc[year, "basis"]
        out = {"balanced": _balanced, "basis": _basis, "gains": _gains}
        return out[strategy]()

    @property
    def current_year(self):
        """Return the current (non-closed) year."""
        not_closed_index = self.df[self.df["end_balance"].isnull()].index
        return not_closed_index.min()

    @property
    def balance(self):
        """Return the total withdrawable amount"""
        ser = self.df.loc[self.current_year]
        return ser['start_balance'] + ser['contribution']

    @property
    def gains(self):
        """return the total gains on investments."""
        ser = self.df.loc[self.current_year]
        return ser['start_balance'] - ser['basis']


class Taxable(Investment):
    """
    A taxable investment account.
    """
    capital_gains = True


class Traditional401k(Investment):
    pretax = True


class TraditionalIRA(Investment):
    """
    A traditional Individual Retirement account
    """
    pretax = True


class RothIRA(Investment):
    """"""
    taxfree = True

#
# class Strategy:
#     """ A base class for calculating strategies."""
#
#     def get_fire_plan(self) -> pd.DataFrame:
#         """Return a dataframe with a fire plan."""
#         # first get a
#         incomes = self.get_total_w2_incomes()
#         spending = self.household.get_spending_df()
#         tax_free_income = self.household.get_tax_free_amount()
#         breakpoint()
#
#     def get_total_w2_incomes(self):
#         """Returns a summed dataframe of potential w2 income."""
#         income_series = [x.get_income_series() for x in self.incomes]
#         out = reduce(add, income_series)
#         return out
#
#     def _get_income_series(self):
#         """Get potential income for next 45 years."""
#
#         breakpoint()
#         breakpoint()


@dataclass
class TaxEvasionStrategy:
    """
    Try to find a path to FIRE while minimizing taxes.
    """
    household: Household
    family_income: FamilyIncome
    employee_investment: Optional[Investment] = None
    roth_ira: Optional[RothIRA] = None
    traditional_ira: Optional[TraditionalIRA] = None
    taxable: Optional[Taxable] = None
    retire_goal = 1.2  # retire when passive income is x times expenses
    goal_reached = False

    def __post_init__(self, **kwargs):
        # init empty investment accounts if None attached.
        self.years = self.household.years
        self.household_df = self.household.get_df()
        self.income_df = self.family_income.get_df()
        breakpoint()
        if self.employee_investment is None:
            self.employee_investment = Traditional401k(years=self.years)
        if self.traditional_ira is None:
            self.traditional_ira = TraditionalIRA(years=self.years)
        if self.roth_ira is None:
            self.roth_ira = RothIRA(years=self.years)
        if self.taxable is None:
            self.taxable = Taxable(years=self.years)

    @property
    def investments(self):
        """return a list of all investments in strategy"""
        invs = [
            self.taxable,
            self.employee_investment,
            self.traditional_ira,
            self.roth_ira,
        ]
        return invs

    def _do_retired_year(self, year):
        household_ser = self.household_df.loc[year]

        ira_limit = household_ser['ira_limit']
        spending = household_ser['spending']
        tax_free_income = household_ser['tax_free_income']
        tax_free_gains = household_ser['tax_free_gains']

        # first do roth rollover
        roll_over_amount = min([tax_free_income, self.traditional_ira.balance])
        transfer_with = self.traditional_ira.withdraw(roll_over_amount, 'gains')
        self.roth_ira.contribute(transfer_with.amount)
        # print(year, self.traditional_ira.balance)

        # next tap taxable account for income
        spending_with = min([spending, self.taxable.balance])
        spending_with = self.taxable.withdraw(spending_with, 'gains')
        spending -= spending_with.amount
        if spending > 0:  # not enough in taxable account, tap into roth IRA basis
            roth_with = self.roth_ira.withdraw(spending, 'basis')
        # tax free gains, realize remaining amount
        tf = tax_free_gains - (transfer_with.amount + spending_with.amount)
        taxable_amount = min([tf, self.taxable.balance])
        harvest_with = self.taxable.withdraw(taxable_amount, 'gains')
        self.taxable.contribute(harvest_with.amount)
        self._close_years(year)

    def _can_retire(self, spending):
        """Determine if retirement condition is met."""
        passive = 0
        for inv in self.investments:
            passive += inv.balance * inv.growth_rate
        if passive > (spending * self.retire_goal):
            return True
        return False

    def _close_years(self, year):
        """Close the years on the investments."""
        for inv in self.investments:
            assert year == inv.current_year
            inv.close_year(year)

    def _do_working_year(self, year):
        """Execute the strategy for a working year."""
        income_ser = self.income_df.loc[year]
        household_ser = self.household_df.loc[year]

        ira_limit = household_ser['ira_limit']
        employ_limit = income_ser['contribution_limit']
        spending = household_ser['spending']
        tax_free_income = household_ser['tax_free_income']
        tax_free_gains = household_ser['tax_free_gains']
        match = income_ser['match']
        match_requires = income_ser['required']
        balance = gross = income_ser['income']

        # first contribute enough to get full employer match (free money!)
        self.employee_investment.contribute(match, employee=True)
        self.employee_investment.contribute(match_requires, employee=False)
        balance -= income_ser['required']
        employ_limit -= income_ser['required']

        # next determine how much needs to go into pre-tax buckets and dump
        # as much as possible into pre-tax employee plan
        need_to_reduce = balance - tax_free_income
        additional_emp_contrib = min([need_to_reduce, employ_limit])
        self.employee_investment.contribute(additional_emp_contrib)
        need_to_reduce -= additional_emp_contrib
        balance -= additional_emp_contrib
        taxable = balance  # taxable income

        assert need_to_reduce == 0, 'deal with IRAs/HSA if this fails'

        # take out living expenses
        balance -= spending

        # contribute as much as possible to roth IRA
        roth_contrib = min([balance, ira_limit])
        self.roth_ira.contribute(roth_contrib)
        balance -= roth_contrib

        self.taxable.contribute(balance)
        # harvest capital gains
        harvest_amount = min([tax_free_gains, self.taxable.gains])
        wd = self.taxable.withdraw(harvest_amount, 'gains')
        self.taxable.contribute(wd.amount)
        self._close_years(year)

        can_retire = self._can_retire(spending)
        if can_retire:
            self._zero_income(year)
            self._roll_over_traditional()
        return can_retire

    def _zero_income(self, year):
        """Zero out the income dataframe after retirement."""
        self.income_df.loc[year+1:, ['match', 'required', 'income']] = 0.0

    def _roll_over_traditional(self):
        """Roll all employment retirement account into traditional IRA."""
        balance = self.employee_investment.balance
        withdrwa = self.employee_investment.withdraw(balance, 'gains')
        self.traditional_ira.contribute(withdrwa.amount, employee=False)

    def start_fire(self):
        """Calculate path to Fire."""
        # first get
        retired = False
        for year in self.years:
            if not retired:
                retired = self._do_working_year(year)
            else:
                self._do_retired_year(year)
        self.goal_reached = True

    def plot_yearly_table(self, plot_directory=None):
        """Make a directory with plots, one for each year."""
        from simplefire.plot import plot_yearly_table
        return plot_yearly_table(self, plot_directory=plot_directory)
