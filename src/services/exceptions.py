class DomainError(Exception):
    """Base domain error."""


class NotFoundError(DomainError):
    """Entity not found."""


class UserNotFoundError(NotFoundError):
    pass


class BookNotFoundError(NotFoundError):
    pass


class LoanNotFoundError(NotFoundError):
    pass


class ReservationNotFoundError(NotFoundError):
    pass


class UserBlockedError(DomainError):
    pass


class ReaderRoleRequiredError(DomainError):
    pass


class LibrarianRoleRequiredError(DomainError):
    pass


class InsufficientCopiesError(DomainError):
    pass


class ReferenceBookNotLoanableError(DomainError):
    pass


class LoanLimitExceededError(DomainError):
    pass


class InvalidLoanStateError(DomainError):
    pass


class DuplicateReservationError(DomainError):
    pass


class ReservationAccessDeniedError(DomainError):
    pass
