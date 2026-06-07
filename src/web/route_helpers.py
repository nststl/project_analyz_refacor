from __future__ import annotations

from collections.abc import Callable

from flask import flash, redirect, request, url_for

from services.exceptions import DomainError
from web.context import LibraryContext
from web.index_data import book_ids, default_reader_id, reader_ids
from web.security import pick_mode, pick_reader_id, safe_error_message, sanitize_search_query


class RouteHelpers:
    """Shared request helpers for Flask routes (keeps register_routes complexity low)."""

    def __init__(self, ctx: LibraryContext) -> None:
        self.ctx = ctx

    def redirect_back(self, reader_id: str, mode: str = "reader", **extra: str) -> redirect:
        safe_reader = pick_reader_id(reader_id, reader_ids(self.ctx), default_reader_id(self.ctx))
        safe_mode = pick_mode(mode)
        safe_extra = {k: v for k, v in extra.items() if k == "q" and v}
        if "q" in safe_extra:
            safe_extra["q"] = sanitize_search_query(safe_extra["q"])
        return redirect(url_for("index", reader_id=safe_reader, mode=safe_mode, **safe_extra))

    def form_reader_id(self) -> str:
        return pick_reader_id(
            request.form.get("reader_id", default_reader_id(self.ctx)),
            reader_ids(self.ctx),
            default_reader_id(self.ctx),
        )

    def form_mode(self) -> str:
        return pick_mode(request.form.get("mode", "reader"))

    def run_action(
        self,
        action: Callable[[], None],
        success_message: str,
        reader_id: str,
        mode: str,
    ) -> redirect:
        try:
            action()
            flash(success_message, "success")
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return self.redirect_back(reader_id, mode)

    def require_librarian_mode(self) -> bool:
        if request.form.get("mode") != "librarian":
            flash("Ця дія доступна лише в режимі бібліотекаря.", "error")
            return False
        return True
