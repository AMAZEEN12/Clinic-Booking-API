"""Audit trail for state changes (N5). Lines carry ids and counts only, never names or emails."""

import logging

_log = logging.getLogger("app.audit")


def record(event: str, **fields: str | int) -> None:
    details = " ".join(f"{key}={value}" for key, value in fields.items())
    _log.info("audit event=%s %s", event, details)
