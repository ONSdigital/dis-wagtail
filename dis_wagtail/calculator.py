"""A simple python module for demonstration purposes, replace it with your own code."""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Calculator:
    """A calculator class for basic arithmetic operations with high precision Decimal numbers.
    The class keeps track of a cumulative total that is updated with each operation.
    """

    _cumulative_total: Decimal = field(default=Decimal("0"), init=False, repr=False)

    @property
    def cumulative_total(
        self,
    ) -> Decimal:
        return self._cumulative_total

    def reset_cumulative_total(
        self,
    ) -> None:
        self._cumulative_total = Decimal("0")

    def add(self, number: Decimal) -> Decimal:
        """Adds a Decimal value to the cumulative total.

        Args:
            number: A Decimal value to be added to the cumulative total.

        Returns:
            The cumulative total after the addition.
        """
        self._cumulative_total += number
        return self._cumulative_total

    def subtract(self, number: Decimal) -> Decimal:
        """Subtracts a Decimal value from the cumulative total.

        Args:
            number: The Decimal value to be subtracted.

        Returns:
            The cumulative total after the subtraction as a Decimal.

        """
        self._cumulative_total -= number
        return self._cumulative_total

    def multiply(self, number: Decimal) -> Decimal:
        """Multiplies the cumulative total by a Decimal value.

        Args:
            number: The Decimal value to multiply the cumulative total by.

        Returns:
            The product of the provided factors as a Decimal.
        """
        self._cumulative_total *= number
        return self._cumulative_total

    def divide(self, divisor: Decimal) -> Decimal:
        """Divides the cumulative total by a Decimal value.

        Args:
            divisor: The Decimal value to divide the cumulative total by.

        Returns:
            The cumulative total after the division as a Decimal.
        """
        if divisor == Decimal("0"):
            raise ValueError("Cannot divide by zero.")

        self._cumulative_total /= divisor
        return self._cumulative_total
