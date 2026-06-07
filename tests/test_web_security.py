from __future__ import annotations

from web.security import safe_error_message
from services.exceptions import BookNotFoundError, ReferenceBookNotLoanableError


def test_safe_error_message_ignores_user_controlled_args():
    msg = safe_error_message(BookNotFoundError("<script>alert(1)</script>"))
    assert "<script>" not in msg
    assert msg == "Книгу не знайдено."


def test_reference_error_message_for_ui():
    msg = safe_error_message(ReferenceBookNotLoanableError("ignored"))
    assert "reference" in msg.lower()
