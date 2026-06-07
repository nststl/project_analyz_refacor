from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from services.exceptions import DomainError
from utils.time_utils import calendar_overdue_days
from web.context import LibraryContext


def create_app(ctx: LibraryContext) -> Flask:
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
    app.secret_key = "library-demo-secret-change-in-production"

    @app.get("/")
    def index():
        reader_id = request.args.get("reader_id", "reader-1")
        books = ctx.books.list_all()
        users = [u for u in ctx.users.list_all() if u.role.name == "READER"]
        active = ctx.loan_service.active_loans_for(reader_id)
        notifications = ctx.observer.notifications[-5:]
        reader = ctx.users.get_by_id(reader_id)
        blocked = reader.is_blocked_at(ctx.clock.now()) if reader else False
        queues = {b.id: ctx.reservation_service.queue(b.id) for b in books}
        return render_template(
            "index.html",
            books=books,
            users=users,
            reader_id=reader_id,
            active_loans=active,
            notifications=notifications,
            blocked=blocked,
            queues=queues,
        )

    @app.post("/borrow")
    def borrow():
        reader_id = request.form.get("reader_id", "reader-1")
        book_id = request.form.get("book_id", "")
        try:
            loan = ctx.loan_service.borrow(reader_id, book_id)
            flash(f"Видано: {loan.id}, повернути до {loan.due_at.date()}", "success")
        except DomainError as exc:
            flash(str(exc), "error")
        return redirect(url_for("index", reader_id=reader_id))

    @app.post("/return")
    def return_loan():
        reader_id = request.form.get("reader_id", "reader-1")
        loan_id = request.form.get("loan_id", "")
        try:
            loan = ctx.loan_service.return_loan(loan_id)
            overdue = 0
            if loan.returned_at is not None:
                overdue = calendar_overdue_days(loan.due_at, loan.returned_at)
            msg = f"Повернено. Штраф: {loan.penalty_amount}"
            if ctx.observer.notifications:
                last = ctx.observer.notifications[-1]
                msg += f" | Черга: книга {last[0]}, читач {last[1]}"
            flash(msg, "success")
            if loan.penalty_amount > 0:
                ctx.auto_blocking.maybe_suspend_reader(
                    loan.user_id,
                    overdue,
                    loan.penalty_amount,
                    ctx.clock.now(),
                )
        except DomainError as exc:
            flash(str(exc), "error")
        return redirect(url_for("index", reader_id=reader_id))

    @app.post("/reserve")
    def reserve():
        reader_id = request.form.get("reader_id", "reader-1")
        book_id = request.form.get("book_id", "")
        try:
            res = ctx.reservation_service.enqueue(reader_id, book_id)
            flash(f"У черзі: #{res.sequence} ({res.id})", "success")
        except DomainError as exc:
            flash(str(exc), "error")
        return redirect(url_for("index", reader_id=reader_id))

    @app.post("/block")
    def block_reader():
        reader_id = request.form.get("reader_id", "reader-1")
        days = int(request.form.get("days", "7"))
        try:
            until = ctx.clock.now() + timedelta(days=days)
            ctx.admin_service.block_reader_until("lib-1", reader_id, until)
            flash(f"Читача {reader_id} заблоковано на {days} дн.", "success")
        except DomainError as exc:
            flash(str(exc), "error")
        return redirect(url_for("index", reader_id=reader_id))

    @app.post("/unblock")
    def unblock_reader():
        reader_id = request.form.get("reader_id", "reader-1")
        try:
            ctx.admin_service.unblock_reader("lib-1", reader_id)
            flash(f"Читача {reader_id} розблоковано", "success")
        except DomainError as exc:
            flash(str(exc), "error")
        return redirect(url_for("index", reader_id=reader_id))

    return app
