from __future__ import annotations

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


def sanitize_search_query(raw: str, *, max_len: int = 80) -> str:
    """Strip characters that could break HTML; breaks Sonar XSS taint on ?q=."""
    cleaned = raw.strip()[:max_len].lower()
    return "".join(c for c in cleaned if c.isalnum() or c in " -_")


def pick_reader_id(raw: str, allowed: frozenset[str], default: str) -> str:
    return raw if raw in allowed else default


def pick_mode(raw: str) -> str:
    return raw if raw in ("reader", "librarian") else "reader"


def pick_book_id(raw: str, allowed: frozenset[str]) -> str:
    return raw if raw in allowed else ""


def clamp_block_days(raw: str, *, default: int = 7, max_days: int = 90) -> int:
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(max_days, days))


def clamp_advance_days(raw: str, *, default: int = 1, max_days: int = 365) -> int:
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(max_days, days))


def pick_penalty_kind(raw: str) -> str:
    return raw if raw in ("linear", "tiered") else "linear"
