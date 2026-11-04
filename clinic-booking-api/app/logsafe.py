"""Keeps personal data out of the web server's access log (N4).

GET /bookings takes the person's email in the query string (R10), and uvicorn writes the whole
request line to its access log. This filter cuts everything after the "?" before it is written.
"""

import logging


class HideQueryString(logging.Filter):
    """Rewrites an access-log record so its path has no query string."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        # uvicorn access records carry (client, method, path, http_version, status_code).
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            record.args = (*args[:2], args[2].split("?", 1)[0], *args[3:])
        return True


def hide_query_strings() -> None:
    """Install the filter on uvicorn's access logger (once)."""
    access_log = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, HideQueryString) for f in access_log.filters):
        access_log.addFilter(HideQueryString())
