from __future__ import annotations

from flask import Flask, render_template, request

from web.context import LibraryContext
from web.index_data import (
    LIBRARIAN_ID,
    book_ids,
    build_index_context,
    default_reader_id,
    reader_ids,
)
from web.route_handlers import (
    apply_and_flash_penalty_strategy,
    block_reader_admin_safe,
    flash_advance_time,
    log_borrow,
    log_return,
)
from web.route_helpers import RouteHelpers
from web.security import (
    clamp_advance_days,
    clamp_block_days,
    pick_book_id,
    pick_mode,
    pick_penalty_kind,
    pick_reader_id,
    sanitize_search_query,
)
from web.simulation import log_event, parse_penalty_rate


def register_routes(app: Flask, ctx: LibraryContext) -> None:
    h = RouteHelpers(ctx)
    _register_index_routes(app, ctx)
    _register_reader_routes(app, ctx, h)
    _register_simulation_routes(app, ctx, h)
    _register_librarian_routes(app, ctx, h)


def _register_index_routes(app: Flask, ctx: LibraryContext) -> None:
    @app.get("/")
    def index():
        mode = pick_mode(request.args.get("mode", "reader"))
        reader_id = pick_reader_id(
            request.args.get("reader_id", default_reader_id(ctx)),
            reader_ids(ctx),
            default_reader_id(ctx),
        )
        search_q = sanitize_search_query(request.args.get("q", ""))
        return render_template(
            "index.html",
            **build_index_context(ctx, reader_id=reader_id, mode=mode, search_q=search_q),
        )


def _register_reader_routes(app: Flask, ctx: LibraryContext, h: RouteHelpers) -> None:
    @app.post("/borrow")
    def borrow():
        rid, mode = h.form_reader_id(), h.form_mode()
        bid = pick_book_id(request.form.get("book_id", ""), book_ids(ctx))
        return h.run_action(
            lambda: log_borrow(ctx, rid, bid),
            "Книгу видано. Перевірте розділ «Мої позики».",
            rid,
            mode,
        )

    @app.post("/return")
    def return_loan():
        rid, mode = h.form_reader_id(), h.form_mode()
        loan_id = request.form.get("loan_id", "")
        return h.run_action(
            lambda: log_return(ctx, loan_id),
            "Книгу повернено.",
            rid,
            mode,
        )

    @app.post("/reserve")
    def reserve():
        rid, mode = h.form_reader_id(), h.form_mode()
        bid = pick_book_id(request.form.get("book_id", ""), book_ids(ctx))

        def _reserve() -> None:
            ctx.reservation_service.enqueue(rid, bid)
            log_event(ctx, f"UC-04 Резерв: {rid} → {bid}")

        return h.run_action(_reserve, "Додано до черги резерву.", rid, mode)

    @app.post("/cancel-reservation")
    def cancel_reservation():
        rid, mode = h.form_reader_id(), h.form_mode()
        res_id = request.form.get("reservation_id", "")

        def _cancel() -> None:
            ctx.reservation_service.cancel(rid, res_id)
            log_event(ctx, f"Скасовано резерв {res_id}")

        return h.run_action(_cancel, "Резерв скасовано.", rid, mode)


def _register_simulation_routes(app: Flask, ctx: LibraryContext, h: RouteHelpers) -> None:
    @app.post("/advance-time")
    def advance_time():
        rid, mode = h.form_reader_id(), h.form_mode()
        days = clamp_advance_days(request.form.get("days", "1"))
        flash_advance_time(ctx, days)
        return h.redirect_back(rid, mode)

    @app.post("/set-penalty-strategy")
    def set_penalty_strategy_route():
        rid, mode = h.form_reader_id(), h.form_mode()
        kind = pick_penalty_kind(request.form.get("strategy", "linear"))
        rate = parse_penalty_rate(request.form.get("rate", "10"))
        apply_and_flash_penalty_strategy(ctx, kind, rate)
        return h.redirect_back(rid, mode)


def _register_librarian_routes(app: Flask, ctx: LibraryContext, h: RouteHelpers) -> None:
    @app.post("/block")
    def block_reader():
        if not h.require_librarian_mode():
            return h.redirect_back(h.form_reader_id(), "reader")
        target_id = pick_reader_id(
            request.form.get("target_reader_id", ""),
            reader_ids(ctx),
            default_reader_id(ctx),
        )
        days = clamp_block_days(request.form.get("days", "7"))
        block_reader_admin_safe(ctx, target_id, days)
        return h.redirect_back(h.form_reader_id(), "librarian")

    @app.post("/unblock")
    def unblock_reader():
        if not h.require_librarian_mode():
            return h.redirect_back(h.form_reader_id(), "reader")
        target_id = pick_reader_id(
            request.form.get("target_reader_id", ""),
            reader_ids(ctx),
            default_reader_id(ctx),
        )

        def _unblock() -> None:
            ctx.admin_service.unblock_reader(LIBRARIAN_ID, target_id)
            log_event(ctx, f"UC-06 Розблокування {target_id}")

        return h.run_action(
            _unblock,
            "Читача розблоковано.",
            h.form_reader_id(),
            "librarian",
        )
