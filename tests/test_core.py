"""
Tests for simplefire's main functionality.
"""
import pytest


from simplefire import FireCalculator


@pytest.fixture()
def default_fire():
    return FireCalculator()


@pytest.fixture()
def fire_df(default_fire):
    """Return the default fire dataframe."""
    return default_fire.get_fire_plan()


class TestFireCalculator:
    """Tests for calculating Fire."""

    def test_get_plan(self, fire_df):
        out = fire_df
