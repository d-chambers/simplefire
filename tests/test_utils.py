"""
Tests for utilities.
"""
import pandas as pd

import pytest
from simplefire.utils import read_data


class TestReadData:
    """tests for reading tax info dataframes."""

    def test_read_child_tax_credit(self):
        """Ensure child tax credit is readable."""
        df = read_data("child_tax_credit")
        assert isinstance(df, pd.DataFrame)
        assert len(df)

    def test_read_capital_gains(self):
        """Ensure capital gains rates are readable"""
        df = read_data("capital_gains", "married")
        assert len(df)
        assert isinstance(df, pd.DataFrame)

    def test_missing_status_raises(self):
        """Ensure missing status raises."""
        with pytest.raises(Exception, match="must specify status"):
            read_data("capital_gains")

    def test_missing_dataset_raises(self):
        """Ensure if the dataset doesn't exist it raises a FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="valid dataset"):
            read_data("not_a_data_type")
        with pytest.raises(FileNotFoundError, match="valid dataset"):
            read_data("capital_gains", "married_but_single")
