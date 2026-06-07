from __future__ import annotations

from flask import Flask
from flask_wtf.csrf import CSRFProtect


def configure_flask_app(app: Flask, *, testing: bool, session_key: str) -> None:
    """Session signing key comes from caller (env in run.py / tests), not from source."""
    app.config["TESTING"] = testing
    app.secret_key = session_key
    app.config["WTF_CSRF_ENABLED"] = not testing
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    CSRFProtect(app)


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def security_headers(response):  # noqa: ANN001
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"
        )
        return response
