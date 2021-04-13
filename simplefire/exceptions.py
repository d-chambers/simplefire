"""
Custom exceptions
"""


class ContributionLimitsExceeded(ValueError):
    """Raised when contribution limits are exceeded."""


class BalanceError(ValueError):
    """Raised when an Error occurs with a balance."""
