from __future__ import annotations

import itertools
from datetime import timedelta
from decimal import Decimal

import pytest

from services.blocking_policy import suggested_block_duration


_OD = list(range(0, 16))
_PEN = [Decimal(str(x)) for x in range(0, 600, 75)]


@pytest.mark.parametrize("od,pen", itertools.product(_OD, _PEN))
def test_suggested_block_is_none_or_positive_duration(od: int, pen: Decimal) -> None:
    d = suggested_block_duration(od, pen)
    assert d is None or d >= timedelta(days=1)


@pytest.mark.parametrize("od", _OD)
def test_no_positive_overdue_and_zero_penalty_means_no_block_unless_overdue_rule(od: int) -> None:
    d = suggested_block_duration(od, Decimal("0"))
    if od <= 0:
        assert d is None
