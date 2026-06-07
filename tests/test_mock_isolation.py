"""Isolated unit tests using unittest.mock."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from models.entities import Book, Loan, User
from models.enums import BookCategory, LoanState, Role
from patterns.observer import BookAvailabilitySubject
from patterns.penalty_strategy import LinearPenaltyStrategy
from services.exceptions import BookNotFoundError
from services.loan_service import LoanService, SequentialIdGenerator


def test_borrow_propagates_book_not_found_from_mock_repository() -> None:
    users = MagicMock()
    users.get_by_id.return_value = User("r1", "R", Role.READER, None, 3)

    books = MagicMock()
    books.get_by_id.return_value = None

    loans = MagicMock()
    clock = MagicMock()
    clock.now.return_value = datetime(2026, 1, 1, tzinfo=timezone.utc)

    svc = LoanService(
        users=users,
        books=books,
        loans=loans,
        penalty=LinearPenaltyStrategy(Decimal("1")),
        clock=clock,
        ids=SequentialIdGenerator(),
        availability=BookAvailabilitySubject(),
    )

    with pytest.raises(BookNotFoundError):
        svc.borrow("r1", "missing-book")

    books.get_by_id.assert_called_once_with("missing-book")


def test_return_loan_notifies_subject_with_mock_availability() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    users = MagicMock()
    users.get_by_id.return_value = User("r1", "R", Role.READER, None, 3)

    book = Book("b1", "T", BookCategory.STANDARD, 1, 0)
    books = MagicMock()
    books.get_by_id.return_value = book

    active_loan = Loan(
        "loan-1",
        "r1",
        "b1",
        t0,
        t0 + timedelta(days=7),
        LoanState.ACTIVE,
    )
    loans = MagicMock()
    loans.get_by_id.return_value = active_loan

    clock = MagicMock()
    clock.now.return_value = t0 + timedelta(days=1)

    subject = MagicMock(wraps=BookAvailabilitySubject())
    svc = LoanService(
        users=users,
        books=books,
        loans=loans,
        penalty=LinearPenaltyStrategy(Decimal("1")),
        clock=clock,
        ids=SequentialIdGenerator(),
        availability=subject,
    )

    svc.return_loan("loan-1")
    subject.notify.assert_called_once()
    assert book.available_copies == 1
