from __future__ import annotations

from enum import Enum, auto


class Role(Enum):
    READER = auto()
    LIBRARIAN = auto()


class BookCategory(Enum):
    STANDARD = auto()
    REFERENCE = auto()
    RARE = auto()


class LoanState(Enum):
    ACTIVE = auto()
    RETURNED = auto()
