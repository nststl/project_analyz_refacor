from __future__ import annotations

import re

_CSRF_RE = re.compile(rb'name="csrf_token" value="([^"]+)"')


def extract_csrf_token(html: bytes) -> str:
    match = _CSRF_RE.search(html)
    assert match is not None, "CSRF token not found in page"
    return match.group(1).decode()


def csrf_post(client, url: str, data: dict, *, page: str = "/", follow: bool = True):
    """POST with CSRF token (CSRF always enabled in app)."""
    token_page = client.get(page)
    token = extract_csrf_token(token_page.data)
    payload = {**data, "csrf_token": token}
    return client.post(url, data=payload, follow_redirects=follow)
