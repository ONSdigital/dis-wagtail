from decimal import Decimal

import pytest


def test_add(calculator):
    assert calculator.add(Decimal("5")) == Decimal("5")
    assert calculator.add(Decimal("10")) == Decimal("15")

    assert calculator.cumulative_total == Decimal("15")


def test_subtract(calculator):
    assert calculator.subtract(Decimal("5")) == Decimal("-5")
    assert calculator.subtract(Decimal("10")) == Decimal("-15")

    assert calculator.cumulative_total == Decimal("-15")


def test_multiply(calculator):
    calculator.add(Decimal("1"))
    assert calculator.multiply(Decimal("10")) == Decimal("10")
    assert calculator.multiply(Decimal("2")) == Decimal("20")

    assert calculator.cumulative_total == Decimal("20")


def test_divide(calculator):
    calculator.add(Decimal("6"))
    assert calculator.divide(Decimal("2")) == Decimal("3")
    assert calculator.divide(Decimal("3")) == Decimal("1")

    assert calculator.cumulative_total == Decimal("1")


def test_divide_by_zero(calculator):
    with pytest.raises(ValueError):
        calculator.divide(Decimal("0"))


def test_multiple_operations(calculator):
    assert calculator.cumulative_total == Decimal("0")

    calculator.add(Decimal("15"))  # 15
    calculator.subtract(Decimal("5"))  # 10
    calculator.multiply(Decimal("2"))  # 20
    calculator.divide(Decimal("4"))  # 5

    assert calculator.cumulative_total == Decimal("5")


def test_reset_cumulative_total(calculator):
    calculator.add(Decimal("15"))
    assert calculator.cumulative_total == Decimal("15")

    calculator.reset_cumulative_total()
    assert calculator.cumulative_total == Decimal("0")
