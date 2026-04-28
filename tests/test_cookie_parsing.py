"""Tests for Wi-Tek session cookie handling."""

from pathlib import Path
import sys

INTEGRATION_DIR = Path(__file__).parents[1] / "custom_components" / "witek_bridge"
sys.path.insert(0, str(INTEGRATION_DIR))

from parsing import cookie_header_from_set_cookie_headers  # noqa: E402


def test_cookie_header_from_response() -> None:
    """Bridge Set-Cookie metadata is reduced to a reusable Cookie header."""
    headers = [
        (
            "_app_=session-value; Expires=Tue, 28 Apr 2026 15:40:12 GMT; "
            "Max-Age=3600; Path=/"
        )
    ]

    assert cookie_header_from_set_cookie_headers(headers) == "_app_=session-value"


def test_cookie_header_from_empty_response() -> None:
    """Missing Set-Cookie headers do not create a Cookie header."""
    assert cookie_header_from_set_cookie_headers([]) is None
