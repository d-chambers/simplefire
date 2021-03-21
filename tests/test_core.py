"""
Tests for simplefire's main functionality.
"""
import pytest


from simplefire.core import FireCalculator, Income, Household


@pytest.fixture()
def default_fire():
    return FireCalculator()


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


class TestHousehold:
    """Tests for household class."""

    @pytest.fixture()
    def modifier_df(self, default_household):
        """get the modifier dataframe """
        return default_household.get_household_modifier_df()

    def test_modified_df(self, modifier_df):
        """Ensure modifier works."""
        breakpoint()
        print(modifier_df)


class TestFireCalculator:
    """Tests for calculating Fire."""

    # def test_get_plan(self, fire_df):
    #     out = fire_df
