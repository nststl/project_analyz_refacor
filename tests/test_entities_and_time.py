from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from models.entities import Book, User
from models.enums import BookCategory, LoanState, Role
from utils.time_utils import calendar_overdue_days, ensure_aware_utc


def test_user_blocked_when_until_future() -> None:
    now = datetime(2026, 5, 1, tzinfo=timezone.utc)
    u = User(id="u1", name="A", role=Role.READER, blocked_until=now + timedelta(days=1))
    assert u.is_blocked_at(now) is True


def test_user_not_blocked_when_until_past() -> None:
    now = datetime(2026, 5, 1, tzinfo=timezone.utc)
    u = User(id="u1", name="A", role=Role.READER, blocked_until=now - timedelta(seconds=1))
    assert u.is_blocked_at(now) is False


def test_user_not_blocked_when_none() -> None:
    u = User(id="u1", name="A", role=Role.READER, blocked_until=None)
    assert u.is_blocked_at(datetime.now(timezone.utc)) is False


def test_book_valid_copies() -> None:
    b = Book("b1", "T", BookCategory.STANDARD, 3, 2)
    assert b.available_copies == 2


@pytest.mark.parametrize("total,avail", [(-1, 0), (0, -1)])
def test_book_rejects_negative_copy_counts(total: int, avail: int) -> None:
    with pytest.raises(ValueError):
        Book("b1", "T", BookCategory.STANDARD, total, avail)


def test_book_rejects_available_gt_total() -> None:
    with pytest.raises(ValueError):
        Book("b1", "T", BookCategory.STANDARD, 1, 2)


def test_loan_default_state_active() -> None:
    from models.entities import Loan

    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    loan = Loan("L1", "u", "b", t, t + timedelta(days=7))
    assert loan.state == LoanState.ACTIVE
    assert loan.penalty_amount == Decimal("0")


def test_reservation_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    from models.entities import Reservation

    r = Reservation("r1", "u", "b", 1)
    with pytest.raises(FrozenInstanceError):
        r.user_id = "x"  # type: ignore[misc]


def test_role_enum_members() -> None:
    assert Role.READER.name == "READER"
    assert Role.LIBRARIAN.name == "LIBRARIAN"


def test_book_category_members() -> None:
    assert len(list(BookCategory)) == 3


def test_ensure_aware_utc_naive() -> None:
    naive = datetime(2026, 1, 1, 12, 0, 0)
    aw = ensure_aware_utc(naive)
    assert aw.tzinfo is not None


def test_calendar_overdue_zero_if_on_time() -> None:
    due = datetime(2026, 1, 10, tzinfo=timezone.utc)
    ret = datetime(2026, 1, 10, tzinfo=timezone.utc)
    assert calendar_overdue_days(due, ret) == 0


def test_calendar_overdue_one_day() -> None:
    due = datetime(2026, 1, 10, tzinfo=timezone.utc)
    ret = datetime(2026, 1, 11, tzinfo=timezone.utc)
    assert calendar_overdue_days(due, ret) == 1


def test_calendar_overdue_respects_dates_only() -> None:
    due = datetime(2026, 1, 10, 23, 59, tzinfo=timezone.utc)
    ret = datetime(2026, 1, 11, 0, 1, tzinfo=timezone.utc)
    assert calendar_overdue_days(due, ret) == 1


@pytest.mark.parametrize(
    "due,ret,expected",
    [
        (datetime(2026, 2, 1, tzinfo=timezone.utc), datetime(2026, 2, 1, tzinfo=timezone.utc), 0),
        (datetime(2026, 2, 1, tzinfo=timezone.utc), datetime(2026, 2, 5, tzinfo=timezone.utc), 4),
    ],
)
def test_calendar_overdue_param(due: datetime, ret: datetime, expected: int) -> None:
    assert calendar_overdue_days(due, ret) == expected
