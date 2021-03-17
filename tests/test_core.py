"""
Tests for simplefire's main functionality.
"""
import pytest


from simplefire import FireCalculator


@pytest.fixture()
def default_fire():
    return FireCalculator()


class TestFireCalculator:
    """Tests for calculating Fire."""




