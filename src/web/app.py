from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFProtect

from models.enums import LoanState, Role
from services.exceptions import DomainError
from utils.time_utils import calendar_overdue_days
from web.context import LibraryContext
from web.security import (
    clamp_block_days,
    pick_book_id,
    pick_mode,
    pick_reader_id,
    resolve_flask_secret_key,
    safe_error_message,
    sanitize_search_query,
)

LIBRARIAN_ID = "lib-1"


def create_app(ctx: LibraryContext, *, testing: bool = False) -> Flask:
    root = Path(__file__).parent
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    app.config["TESTING"] = testing
    app.config["SECRET_KEY"] = resolve_flask_secret_key(testing=testing)
    app.config["WTF_CSRF_ENABLED"] = not testing
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    CSRFProtect(app)

    @app.after_request
    def security_headers(response):  # noqa: ANN001
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"
        )
        return response

    def reader_ids() -> frozenset[str]:
        return frozenset(u.id for u in ctx.users.list_all() if u.role == Role.READER)

    def book_ids() -> frozenset[str]:
        return frozenset(b.id for b in ctx.books.list_all())

    def default_reader_id() -> str:
        ids = reader_ids()
        return "reader-1" if "reader-1" in ids else next(iter(ids), "reader-1")

    def redirect_back(reader_id: str, mode: str = "reader", **extra: str) -> redirect:
        safe_reader = pick_reader_id(reader_id, reader_ids(), default_reader_id())
        safe_mode = pick_mode(mode)
        safe_extra = {k: v for k, v in extra.items() if k == "q" and v}
        if "q" in safe_extra:
            safe_extra["q"] = sanitize_search_query(safe_extra["q"])
        return redirect(url_for("index", reader_id=safe_reader, mode=safe_mode, **safe_extra))

    def form_reader_id() -> str:
        return pick_reader_id(
            request.form.get("reader_id", default_reader_id()),
            reader_ids(),
            default_reader_id(),
        )

    def form_mode() -> str:
        return pick_mode(request.form.get("mode", "reader"))

    def require_librarian_mode() -> bool:
        if request.form.get("mode") != "librarian":
            flash("Ця дія доступна лише в режимі бібліотекаря.", "error")
            return False
        return True

    @app.get("/")
    def index():
        mode = pick_mode(request.args.get("mode", "reader"))
        reader_id = pick_reader_id(
            request.args.get("reader_id", default_reader_id()),
            reader_ids(),
            default_reader_id(),
        )
        search_q = sanitize_search_query(request.args.get("q", ""))

        books = ctx.books.list_all()
        if search_q:
            books = [b for b in books if search_q in b.title.lower()]

        users = [u for u in ctx.users.list_all() if u.role == Role.READER]
        librarian = ctx.users.get_by_id(LIBRARIAN_ID)
        active = ctx.loan_service.active_loans_for(reader_id)
        notifications = ctx.observer.notifications[-5:]
        reader = ctx.users.get_by_id(reader_id)
        blocked = reader.is_blocked_at(ctx.clock.now()) if reader else False
        queues = {b.id: ctx.reservation_service.queue(b.id) for b in ctx.books.list_all()}
        book_titles = {b.id: b.title for b in ctx.books.list_all()}
        user_names = {u.id: u.name for u in ctx.users.list_all()}
        now = ctx.clock.now()

        my_reservation_list: list[tuple] = []
        for b in ctx.books.list_all():
            for res in ctx.reservation_service.queue(b.id):
                if res.user_id == reader_id:
                    my_reservation_list.append((res, book_titles.get(b.id, b.id)))

        loan_history = [
            ln
            for ln in ctx.loans.list_by_user(reader_id)
            if ln.state == LoanState.RETURNED
        ]
        loan_history.sort(key=lambda ln: ln.returned_at or ln.due_at, reverse=True)
        loan_history = loan_history[:8]

        reader_rows = []
        for u in users:
            reader_rows.append(
                {
                    "user": u,
                    "blocked": u.is_blocked_at(now),
                    "active_loans": len(ctx.loan_service.active_loans_for(u.id)),
                    "reservations": sum(
                        1
                        for b in ctx.books.list_all()
                        for r in ctx.reservation_service.queue(b.id)
                        if r.user_id == u.id
                    ),
                }
            )

        return render_template(
            "index.html",
            books=books,
            users=users,
            reader_id=reader_id,
            reader=reader,
            librarian=librarian,
            mode=mode,
            search_q=search_q,
            active_loans=active,
            notifications=notifications,
            blocked=blocked,
            queues=queues,
            book_titles=book_titles,
            user_names=user_names,
            my_reservations=len(my_reservation_list),
            my_reservation_list=my_reservation_list,
            books_available=sum(b.available_copies for b in ctx.books.list_all()),
            loan_history=loan_history,
            reader_rows=reader_rows,
        )

    @app.post("/borrow")
    def borrow():
        reader_id = form_reader_id()
        mode = form_mode()
        book_id = pick_book_id(request.form.get("book_id", ""), book_ids())
        try:
            ctx.loan_service.borrow(reader_id, book_id)
            flash("Книгу видано. Перевірте розділ «Мої позики».", "success")
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(reader_id, mode)

    @app.post("/return")
    def return_loan():
        reader_id = form_reader_id()
        mode = form_mode()
        loan_id = request.form.get("loan_id", "")
        try:
            loan = ctx.loan_service.return_loan(loan_id)
            overdue = 0
            if loan.returned_at is not None:
                overdue = calendar_overdue_days(loan.due_at, loan.returned_at)
            flash("Книгу повернено.", "success")
            if loan.penalty_amount > 0:
                ctx.auto_blocking.maybe_suspend_reader(
                    loan.user_id,
                    overdue,
                    loan.penalty_amount,
                    ctx.clock.now(),
                )
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(reader_id, mode)

    @app.post("/reserve")
    def reserve():
        reader_id = form_reader_id()
        mode = form_mode()
        book_id = pick_book_id(request.form.get("book_id", ""), book_ids())
        try:
            ctx.reservation_service.enqueue(reader_id, book_id)
            flash("Додано до черги резерву.", "success")
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(reader_id, mode)

    @app.post("/cancel-reservation")
    def cancel_reservation():
        reader_id = form_reader_id()
        mode = form_mode()
        reservation_id = request.form.get("reservation_id", "")
        try:
            ctx.reservation_service.cancel(reader_id, reservation_id)
            flash("Резерв скасовано.", "success")
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(reader_id, mode)

    @app.post("/block")
    def block_reader():
        if not require_librarian_mode():
            return redirect_back(form_reader_id(), "reader")
        target_id = pick_reader_id(
            request.form.get("target_reader_id", ""),
            reader_ids(),
            default_reader_id(),
        )
        days = clamp_block_days(request.form.get("days", "7"))
        try:
            until = ctx.clock.now() + timedelta(days=days)
            ctx.admin_service.block_reader_until(LIBRARIAN_ID, target_id, until)
            flash("Читача заблоковано.", "success")
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(form_reader_id(), "librarian")

    @app.post("/unblock")
    def unblock_reader():
        if not require_librarian_mode():
            return redirect_back(form_reader_id(), "reader")
        target_id = pick_reader_id(
            request.form.get("target_reader_id", ""),
            reader_ids(),
            default_reader_id(),
        )
        try:
            ctx.admin_service.unblock_reader(LIBRARIAN_ID, target_id)
            flash("Читача розблоковано.", "success")
        except DomainError as exc:
            flash(safe_error_message(exc), "error")
        return redirect_back(form_reader_id(), "librarian")

    return app
