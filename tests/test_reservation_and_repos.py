from __future__ import annotations

import pytest

from models.entities import Book, Loan, Reservation, User
from models.enums import BookCategory, LoanState, Role
from services.exceptions import ReservationAccessDeniedError, ReservationNotFoundError
from services.loan_service import SequentialIdGenerator
from services.reservation_service import ReservationService
from storage.in_memory import (
    InMemoryBookRepository,
    InMemoryLoanRepository,
    InMemoryReservationRepository,
    InMemoryUserRepository,
)


@pytest.fixture
def wired_reservations():
    users = InMemoryUserRepository()
    books = InMemoryBookRepository()
    res = InMemoryReservationRepository()
    ids = SequentialIdGenerator()
    users.save(User("r1", "A", Role.READER))
    users.save(User("r2", "B", Role.READER))
    books.save(Book("b1", "T", BookCategory.STANDARD, 1, 0))
    return ReservationService(users, books, res, ids)


def test_enqueue_orders_fifo(wired_reservations: ReservationService) -> None:
    s = wired_reservations
    a = s.enqueue("r1", "b1")
    b = s.enqueue("r2", "b1")
    assert a.sequence < b.sequence
    q = s.queue("b1")
    assert [x.user_id for x in q] == ["r1", "r2"]


def test_enqueue_duplicate_raises(wired_reservations: ReservationService) -> None:
    s = wired_reservations
    s.enqueue("r1", "b1")
    from services.exceptions import DuplicateReservationError

    with pytest.raises(DuplicateReservationError):
        s.enqueue("r1", "b1")


def test_cancel_removes(wired_reservations: ReservationService) -> None:
    s = wired_reservations
    r = s.enqueue("r1", "b1")
    s.cancel("r1", r.id)
    assert s.queue("b1") == []


def test_cancel_wrong_user_raises(wired_reservations: ReservationService) -> None:
    s = wired_reservations
    r = s.enqueue("r1", "b1")
    with pytest.raises(ReservationAccessDeniedError):
        s.cancel("r2", r.id)


def test_cancel_missing_raises(wired_reservations: ReservationService) -> None:
    s = wired_reservations
    with pytest.raises(ReservationNotFoundError):
        s.cancel("r1", "missing")


def test_repository_queue_stable_after_delete() -> None:
    res_repo = InMemoryReservationRepository()
    ids = SequentialIdGenerator()
    r1 = Reservation(ids.new_id("res"), "u1", "b1", res_repo.next_sequence())
    r2 = Reservation(ids.new_id("res"), "u2", "b1", res_repo.next_sequence())
    res_repo.save(r1)
    res_repo.save(r2)
    res_repo.delete(r1.id)
    assert [x.user_id for x in res_repo.queue_for_book("b1")] == ["u2"]


def test_loan_repo_active_filter() -> None:
    from datetime import datetime, timedelta, timezone

    loans = InMemoryLoanRepository()
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    active = Loan("L1", "u", "b", t, t + timedelta(days=7), LoanState.ACTIVE)
    done = Loan(
        "L2",
        "u",
        "b",
        t,
        t + timedelta(days=7),
        LoanState.RETURNED,
        t + timedelta(days=8),
    )
    loans.save(active)
    loans.save(done)
    assert len(loans.list_active_by_user("u")) == 1
