"""Public health check for the host and the uptime monitor (N9, D31)."""

import logging

import psycopg
from fastapi import APIRouter

from app import db
from app.errors import error_response

log = logging.getLogger("app.health")

router = APIRouter()


@router.api_route("/health", methods=["GET", "HEAD"])
def health():
    """Returns only {"status": "ok"}. The database query also keeps Neon awake."""
    try:
        with db.get_pool().connection(timeout=3) as conn:
            conn.execute("SELECT 1")
    except (psycopg.Error, RuntimeError) as error:
        log.warning("health check failed: %s", type(error).__name__)
        return error_response(503, "database unavailable")
    return {"status": "ok"}
