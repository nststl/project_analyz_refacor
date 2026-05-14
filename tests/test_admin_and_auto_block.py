from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from services.exceptions import LibrarianRoleRequiredError, ReaderRoleRequiredError, UserNotFoundError
from services.user_administration import UserAdministrationService


def test_block_and_unblock_reader(repos, sample_reader, sample_librarian, t0):
    users, *_ = repos
    admin = UserAdministrationService(users)
    until = t0 + timedelta(days=3)
    admin.block_reader_until(sample_librarian.id, sample_reader.id, until)
    u = users.get_by_id(sample_reader.id)
    assert u is not None and u.blocked_until is not None
    admin.unblock_reader(sample_librarian.id, sample_reader.id)
    u2 = users.get_by_id(sample_reader.id)
    assert u2 is not None and u2.blocked_until is None


def test_block_requires_librarian(repos, sample_reader, t0):
    users, *_ = repos
    admin = UserAdministrationService(users)
    with pytest.raises(LibrarianRoleRequiredError):
        admin.block_reader_until(sample_reader.id, sample_reader.id, t0 + timedelta(days=1))


def test_block_target_must_be_reader(repos, sample_librarian, t0):
    users, *_ = repos
    admin = UserAdministrationService(users)
    with pytest.raises(ReaderRoleRequiredError):
        admin.block_reader_until(sample_librarian.id, sample_librarian.id, t0 + timedelta(days=1))


def test_block_unknown_librarian_raises(repos, sample_reader, t0):
    users, *_ = repos
    admin = UserAdministrationService(users)
    with pytest.raises(UserNotFoundError):
        admin.block_reader_until("no-lib", sample_reader.id, t0 + timedelta(days=1))


def test_auto_block_triggers_on_large_penalty(make_system, sample_reader, sample_book, t0):
    loan_svc, _, _, auto, _, clock = make_system(penalty_per_day=Decimal("50"))
    loan = loan_svc.borrow(sample_reader.id, sample_book.id)
    clock.set(t0 + timedelta(days=60))
    ret = loan_svc.return_loan(loan.id)
    out = auto.maybe_suspend_reader(sample_reader.id, 30, ret.penalty_amount, clock.now())
    assert out is not None
    assert out.is_blocked_at(clock.now()) is True


def test_auto_block_skips_when_small(make_system, sample_reader, sample_book, t0):
    loan_svc, _, _, auto, _, clock = make_system(penalty_per_day=Decimal("1"))
    loan = loan_svc.borrow(sample_reader.id, sample_book.id)
    clock.set(t0 + timedelta(days=2))
    ret = loan_svc.return_loan(loan.id)
    out = auto.maybe_suspend_reader(sample_reader.id, 0, ret.penalty_amount, clock.now())
    assert out is None


def test_auto_block_skips_non_reader_target(repos, t0):
    from models.entities import User
    from models.enums import Role
    from services.auto_blocking import AutoBlockingService

    users, *_ = repos
    users.save(User("l1", "L", Role.LIBRARIAN))
    auto = AutoBlockingService(users)
    assert auto.maybe_suspend_reader("l1", 100, Decimal("9999"), t0) is None
