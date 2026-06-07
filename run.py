"""Запуск веб-інтерфейсу бібліотеки: python run.py → http://127.0.0.1:5000"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from web.app import create_app  # noqa: E402
from web.context import build_library_context  # noqa: E402


def main() -> None:
    ctx = build_library_context(seed=True)
    app = create_app(ctx)
    print("Відкрий у браузері: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
