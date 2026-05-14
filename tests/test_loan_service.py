from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from models.entities import Book, User
from models.enums import BookCategory, LoanState, Role
from patterns.observer import BookAvailabilitySubject
from patterns.penalty_strategy import LinearPenaltyStrategy
from services.exceptions import (
    BookNotFoundError,
    InsufficientCopiesError,
    InvalidLoanStateError,
    LoanLimitExceededError,
    ReaderRoleRequiredError,
    ReferenceBookNotLoanableError,
    UserBlockedError,
    UserNotFoundError,
)
from services.loan_service import LoanService, SequentialIdGenerator


def test_borrow_happy_path(repos, t0, frozen_clock) -> None:
    users, books, loans, _ = repos
    users.save(User("r1", "R", Role.READER, None, 3))
    books.save(Book("b1", "T", BookCategory.STANDARD, 2, 2))
    svc = LoanService(
        users,
        books,
        loans,
        LinearPenaltyStrategy(Decimal("10")),
        frozen_clock,
        SequentialIdGenerator(),
        BookAvailabilitySubject(),
    )
    loan = svc.borrow("r1", "b1")
    assert loan.state == LoanState.ACTIVE
    assert books.get_by_id("b1").available_copies == 1


def test_borrow_blocks_when_reader_blocked(repos, t0, frozen_clock) -> None:
    users, books, loans, _ = repos
    until = t0 + timedelta(days=5)
    users.save(User("r1", "R", Role.READER, until, 3))
    books.save(Book("b1", "T", BookCategory.STANDARD, 1, 1))
    svc = LoanService(
        users,
        books,
        loans,
        LinearPenaltyStrategy(Decimal("1")),
        frozen_clock,
        SequentialIdGenerator(),
        BookAvailabilitySubject(),
    )
    with pytest.raises(UserBlockedError):
        svc.borrow("r1", "b1")


def test_borrow_reference_forbidden(repos, t0, frozen_clock) -> None:
    users, books, loans, _ = repos
    users.save(User("r1", "R", Role.READER, None, 3))
    books.save(Book("b1", "Ref", BookCategory.REFERENCE, 1, 1))
    svc = LoanService(
        users,
        books,
        loans,
        LinearPenaltyStrategy(Decimal("1")),
        frozen_clock,
        SequentialIdGenerator(),
        BookAvailabilitySubject(),
    )
    with pytest.raises(ReferenceBookNotLoanableError):
        svc.borrow("r1", "b1")


def test_borrow_requires_reader_role(repos, t0, frozen_clock) -> None:
    users, books, loans, _ = repos
    users.save(User("l1", "L", Role.LIBRARIAN))
    books.save(Book("b1", "T", BookCategory.STANDARD, 1, 1))
    svc = LoanService(
        users,
        books,
        loans,
        LinearPenaltyStrategy(Decimal("1")),
        frozen_clock,
        SequentialIdGenerator(),
        BookAvailabilitySubject(),
    )
    with pytest.raises(ReaderRoleRequiredError):
        svc.borrow("l1", "b1")


def test_borrow_user_not_found(repos, t0, frozen_clock) -> None:
    users, books, loans, _ = repos
    books.save(Book("b1", "T", BookCategory.STANDARD, 1, 1))
    svc = LoanService(
        users,
        books,
        loans,
        LinearPenaltyStrategy(Decimal("1")),
        frozen_clock,
        SequentialIdGenerator(),
        BookAvailabilitySubject(),
    )
    with pytest.raises(UserNotFoundError):
        svc.borrow("missing", "b1")


def test_borrow_book_not_found(repos, t0, frozen_clock) -> None:
    users, books, loans, _ = repos
    users.save(User("r1", "R", Role.READER, None, 3))
    svc = LoanService(
        users,
        books,
        loans,
        LinearPenaltyStrategy(Decimal("1")),
        frozen_clock,
        SequentialIdGenerator(),
        BookAvailabilitySubject(),
    )
    with pytest.raises(BookNotFoundError):
        svc.borrow("r1", "missing")


def test_borrow_insufficient_copies(repos, t0, frozen_clock) -> None:
    users, books, loans, _ = repos
    users.save(User("r1", "R", Role.READER, None, 3))
    books.save(Book("b1", "T", BookCategory.STANDARD, 1, 0))
    svc = LoanService(
        users,
        books,
        loans,
        LinearPenaltyStrategy(Decimal("1")),
        frozen_clock,
        SequentialIdGenerator(),
        BookAvailabilitySubject(),
    )
    with pytest.raises(InsufficientCopiesError):
        svc.borrow("r1", "b1")


def test_loan_limit_enforced(repos, t0, frozen_clock) -> None:
    users, books, loans, _ = repos
    users.save(User("r1", "R", Role.READER, None, 2))
    for bid in ("b1", "b2", "b3"):
        books.save(Book(bid, bid, BookCategory.STANDARD, 1, 1))
    svc = LoanService(
        users,
        books,
        loans,
        LinearPenaltyStrategy(Decimal("1")),
        frozen_clock,
        SequentialIdGenerator(),
        BookAvailabilitySubject(),
        default_loan_days=7,
    )
    svc.borrow("r1", "b1")
    svc.borrow("r1", "b2")
    with pytest.raises(LoanLimitExceededError):
        svc.borrow("r1", "b3")


def test_return_applies_penalty(repos, t0, frozen_clock) -> None:
    users, books, loans, _ = repos
    users.save(User("r1", "R", Role.READER, None, 3))
    books.save(Book("b1", "T", BookCategory.STANDARD, 1, 1))
    svc = LoanService(
        users,
        books,
        loans,
        LinearPenaltyStrategy(Decimal("10")),
        frozen_clock,
        SequentialIdGenerator(),
        BookAvailabilitySubject(),
    )
    loan = svc.borrow("r1", "b1")
    frozen_clock.set(t0 + timedelta(days=20))
    returned = svc.return_loan(loan.id)
    assert returned.state == LoanState.RETURNED
    assert returned.penalty_amount > 0


def test_return_restores_copy(repos, t0, frozen_clock) -> None:
    users, books, loans, _ = repos
    users.save(User("r1", "R", Role.READER, None, 3))
    books.save(Book("b1", "T", BookCategory.STANDARD, 1, 1))
    svc = LoanService(
        users,
        books,
        loans,
        LinearPenaltyStrategy(Decimal("1")),
        frozen_clock,
        SequentialIdGenerator(),
        BookAvailabilitySubject(),
    )
    loan = svc.borrow("r1", "b1")
    frozen_clock.set(t0 + timedelta(days=1))
    svc.return_loan(loan.id)
    assert books.get_by_id("b1").available_copies == 1


def test_return_twice_raises(repos, t0, frozen_clock) -> None:
    users, books, loans, _ = repos
    users.save(User("r1", "R", Role.READER, None, 3))
    books.save(Book("b1", "T", BookCategory.STANDARD, 1, 1))
    svc = LoanService(
        users,
        books,
        loans,
        LinearPenaltyStrategy(Decimal("1")),
        frozen_clock,
        SequentialIdGenerator(),
        BookAvailabilitySubject(),
    )
    loan = svc.borrow("r1", "b1")
    svc.return_loan(loan.id)
    with pytest.raises(InvalidLoanStateError):
        svc.return_loan(loan.id)


def test_invalid_loan_days_raises(make_system, sample_reader, sample_book) -> None:
    loan_svc, *_ = make_system()
    with pytest.raises(ValueError):
        loan_svc.borrow(sample_reader.id, sample_book.id, loan_days=0)


def test_integration_return_notifies_observer(make_system, sample_reader, sample_book, t0):
    loan_svc, res_svc, obs, _, _, clock = make_system()
    res_svc.enqueue(sample_reader.id, sample_book.id)
    loan = loan_svc.borrow(sample_reader.id, sample_book.id)
    clock.set(t0 + timedelta(days=1))
    loan_svc.return_loan(loan.id)
    assert obs.notifications
