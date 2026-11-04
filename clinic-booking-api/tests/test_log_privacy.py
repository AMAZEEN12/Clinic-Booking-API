"""Personal data must never reach the logs (N4). More checks are added with the audit lines."""

import logging

import app.main  # noqa: F401  (importing the app installs the access-log filter)


def _log_access_line(path: str) -> None:
    # The same arguments uvicorn passes for every request it serves.
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d', "127.0.0.1:5000", "GET", path, "1.1", 200
    )


def test_the_email_in_a_query_string_is_not_logged(caplog):
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        _log_access_line("/bookings?email=ada@example.com&page=2")
    assert "ada@example.com" not in caplog.text
    assert "page=2" not in caplog.text
    assert 'GET /bookings HTTP/1.1" 200' in caplog.text


def test_paths_without_a_query_string_are_logged_as_they_are(caplog):
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        _log_access_line("/slots")
    assert 'GET /slots HTTP/1.1" 200' in caplog.text
