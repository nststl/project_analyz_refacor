from __future__ import annotations

from flask import Flask
from flask_wtf.csrf import CSRFProtect


def configure_flask_app(app: Flask, *, testing: bool) -> None:
    """Session signing key: FLASK_SECRET_KEY env (Flask config), never hard-coded in source."""
    app.config.from_prefixed_env("FLASK")
    if not app.secret_key:
        raise RuntimeError("FLASK_SECRET_KEY environment variable is required")
    app.config["TESTING"] = testing
    app.config["WTF_CSRF_ENABLED"] = True
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
