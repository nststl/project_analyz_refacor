from __future__ import annotations

from pathlib import Path

from flask import Flask

from web.app_config import configure_flask_app, register_security_headers
from web.context import LibraryContext
from web.routes import register_routes


def create_app(ctx: LibraryContext, *, testing: bool = False) -> Flask:
    root = Path(__file__).parent
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    configure_flask_app(app, testing=testing)
    register_security_headers(app)
    register_routes(app, ctx)
    return app
