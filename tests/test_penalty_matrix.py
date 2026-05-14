from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from models.enums import BookCategory
from patterns.penalty_strategy import LinearPenaltyStrategy, TieredPenaltyStrategy


_DAYS = list(range(0, 22))
_CATS = [BookCategory.STANDARD, BookCategory.REFERENCE, BookCategory.RARE]


@pytest.mark.parametrize("days", _DAYS)
@pytest.mark.parametrize("cat", _CATS)
def test_linear_penalty_non_negative(days: int, cat: BookCategory) -> None:
    s = LinearPenaltyStrategy(Decimal("7"))
    assert s.calculate(days, cat) >= 0


@pytest.mark.parametrize("cat", _CATS)
def test_linear_penalty_zero_when_no_overdue(cat: BookCategory) -> None:
    s = LinearPenaltyStrategy(Decimal("9"))
    assert s.calculate(0, cat) == 0


@pytest.mark.parametrize("days", _DAYS)
@pytest.mark.parametrize("cat", _CATS)
def test_tiered_penalty_non_negative(days: int, cat: BookCategory) -> None:
    s = TieredPenaltyStrategy(Decimal("5"), Decimal("20"), threshold_days=5)
    assert s.calculate(days, cat) >= 0


@pytest.mark.parametrize("days", [d for d in _DAYS if d <= 10])
@pytest.mark.parametrize("cat", _CATS)
def test_tiered_matches_linear_when_under_threshold(days: int, cat: BookCategory) -> None:
    thr = 10
    low = Decimal("3")
    high = Decimal("99")
    s = TieredPenaltyStrategy(low, high, threshold_days=thr)
    assert s.calculate(days, cat) == low * Decimal(days) * (
        Decimal("2") if cat == BookCategory.RARE else Decimal("1")
    )
