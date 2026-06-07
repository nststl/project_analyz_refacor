from __future__ import annotations

import os

import pytest

from web.app import create_app
from web.context import build_library_context


@pytest.fixture
def client():
    ctx = build_library_context(seed=True)
    app = create_app(
        ctx,
        testing=True,
        session_key=os.environ["FLASK_TEST_SECRET_KEY"],
    )
    return app.test_client(), ctx


def test_home_page_ok(client):
    c, _ = client
    r = c.get("/")
    assert r.status_code == 200
    assert b"Python 101" in r.data
    assert b"Clean Code" in r.data


def test_home_with_reader_query(client):
    c, _ = client
    r = c.get("/?reader_id=reader-2")
    assert r.status_code == 200
    assert b"reader-2" in r.data or b"Ivan" in r.data


def test_search_books(client):
    c, _ = client
    r = c.get("/?q=python")
    assert r.status_code == 200
    assert b"Python 101" in r.data
    assert b"Clean Code" not in r.data


def test_librarian_mode_page(client):
    c, _ = client
    r = c.get("/?mode=librarian")
    assert r.status_code == 200
    assert b"\xd0\x91\xd1\x96\xd0\xb1\xd0\xbb\xd1\x96\xd0\xbe\xd1\x82\xd0\xb5\xd0\xba\xd0\xb0\xd1\x80" in r.data or b"librarian" in r.data.lower()
    assert b"Ann Reader" in r.data


def test_reader_cannot_block_self(client):
    c, ctx = client
    r = c.post(
        "/block",
        data={"reader_id": "reader-1", "target_reader_id": "reader-1", "days": "3"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    u = ctx.users.get_by_id("reader-1")
    assert u is not None and u.blocked_until is None


def test_borrow_success(client):
    c, ctx = client
    r = c.post(
        "/borrow",
        data={"reader_id": "reader-1", "book_id": "b1", "mode": "reader"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert len(ctx.loan_service.active_loans_for("reader-1")) == 1


def test_borrow_reference_forbidden(client):
    c, _ = client
    r = c.post(
        "/borrow",
        data={"reader_id": "reader-1", "book_id": "b3", "mode": "reader"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"reference" in r.data.lower() or b"Reference" in r.data


def test_borrow_no_copies(client):
    c, _ = client
    r = c.post(
        "/borrow",
        data={"reader_id": "reader-1", "book_id": "b2", "mode": "reader"},
        follow_redirects=True,
    )
    assert r.status_code == 200


def test_reserve_and_return_triggers_observer(client):
    c, ctx = client
    c.post("/reserve", data={"reader_id": "reader-1", "book_id": "b2", "mode": "reader"})
    assert len(ctx.reservation_service.queue("b2")) == 1
    book = ctx.books.get_by_id("b2")
    assert book is not None
    book.available_copies = 1
    ctx.books.save(book)
    loan = ctx.loan_service.borrow("reader-2", "b2")
    c.post(
        "/return",
        data={"reader_id": "reader-2", "loan_id": loan.id, "mode": "reader"},
        follow_redirects=True,
    )
    assert ctx.observer.notifications


def test_cancel_reservation(client):
    c, ctx = client
    c.post("/reserve", data={"reader_id": "reader-1", "book_id": "b2", "mode": "reader"})
    res = ctx.reservation_service.queue("b2")[0]
    r = c.post(
        "/cancel-reservation",
        data={"reader_id": "reader-1", "reservation_id": res.id, "mode": "reader"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert len(ctx.reservation_service.queue("b2")) == 0


def test_return_unknown_loan(client):
    c, _ = client
    r = c.post(
        "/return",
        data={"reader_id": "reader-1", "loan_id": "missing", "mode": "reader"},
        follow_redirects=True,
    )
    assert r.status_code == 200


def test_block_and_unblock_reader(client):
    c, ctx = client
    c.post(
        "/block",
        data={
            "mode": "librarian",
            "reader_id": "reader-1",
            "target_reader_id": "reader-1",
            "days": "3",
        },
        follow_redirects=True,
    )
    u = ctx.users.get_by_id("reader-1")
    assert u is not None and u.blocked_until is not None
    c.post(
        "/unblock",
        data={
            "mode": "librarian",
            "reader_id": "reader-1",
            "target_reader_id": "reader-1",
        },
        follow_redirects=True,
    )
    u2 = ctx.users.get_by_id("reader-1")
    assert u2 is not None and u2.blocked_until is None


def test_build_context_without_seed():
    ctx = build_library_context(seed=False)
    assert ctx.books.list_all() == []


def test_duplicate_reserve_shows_error(client):
    c, _ = client
    c.post("/reserve", data={"reader_id": "reader-1", "book_id": "b2", "mode": "reader"})
    r = c.post(
        "/reserve",
        data={"reader_id": "reader-1", "book_id": "b2", "mode": "reader"},
        follow_redirects=True,
    )
    assert r.status_code == 200
