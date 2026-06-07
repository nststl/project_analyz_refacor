from __future__ import annotations

import os

from services.exceptions import (
    BookNotFoundError,
    DomainError,
    DuplicateReservationError,
    InsufficientCopiesError,
    InvalidLoanStateError,
    LibrarianRoleRequiredError,
    LoanLimitExceededError,
    LoanNotFoundError,
    ReaderRoleRequiredError,
    ReferenceBookNotLoanableError,
    ReservationAccessDeniedError,
    ReservationNotFoundError,
    UserBlockedError,
    UserNotFoundError,
)

_SAFE_ERROR_MESSAGES: dict[type[DomainError], str] = {
    BookNotFoundError: "Книгу не знайдено.",
    UserNotFoundError: "Користувача не знайдено.",
    LoanNotFoundError: "Позику не знайдено.",
    ReservationNotFoundError: "Резерв не знайдено.",
    UserBlockedError: "Читача заблоковано.",
    ReaderRoleRequiredError: "Дія доступна лише читачам.",
    LibrarianRoleRequiredError: "Потрібні права бібліотекаря.",
    InsufficientCopiesError: "Немає вільних примірників.",
    ReferenceBookNotLoanableError: "Reference books are in-library only.",
    LoanLimitExceededError: "Перевищено ліміт активних позик.",
    InvalidLoanStateError: "Позика вже закрита.",
    DuplicateReservationError: "Ви вже в черзі на цю книгу.",
    ReservationAccessDeniedError: "Немає доступу до цього резерву.",
}


def safe_error_message(exc: DomainError) -> str:
    return _SAFE_ERROR_MESSAGES.get(type(exc), "Помилка операції.")


def resolve_flask_secret_key(*, testing: bool) -> str:
    if testing:
        key = os.environ.get("FLASK_TEST_SECRET_KEY") or os.environ.get("FLASK_SECRET_KEY")
        if not key:
            raise RuntimeError("Set FLASK_TEST_SECRET_KEY for tests")
        return key
    key = os.environ.get("FLASK_SECRET_KEY")
    if not key:
        raise RuntimeError("FLASK_SECRET_KEY environment variable is required")
    return key
