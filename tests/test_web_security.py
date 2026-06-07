from __future__ import annotations

from web.security import (
    clamp_block_days,
    pick_mode,
    pick_reader_id,
    sanitize_search_query,
)


def test_sanitize_search_query_strips_html():
    assert sanitize_search_query("<script>alert(1)</script>") == "scriptalert1script"


def test_sanitize_search_query_keeps_normal_text():
    assert sanitize_search_query("Python 101") == "python 101"


def test_pick_reader_id_whitelist():
    allowed = frozenset({"reader-1", "reader-2"})
    assert pick_reader_id("reader-2", allowed, "reader-1") == "reader-2"
    assert pick_reader_id("evil", allowed, "reader-1") == "reader-1"


def test_pick_mode():
    assert pick_mode("librarian") == "librarian"
    assert pick_mode("evil") == "reader"


def test_clamp_block_days():
    assert clamp_block_days("7") == 7
    assert clamp_block_days("999") == 90
    assert clamp_block_days("x") == 7
