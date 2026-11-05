"""The connection pool survives the database closing its connections (Neon sleeps when idle)."""

import psycopg

from app import db


def test_requests_still_work_after_the_server_closes_every_pooled_connection(
    client, api_headers, database_url
):
    # Make sure the pool holds a connection, then close all of them from the server side,
    # the way Neon does when its compute goes to sleep.
    assert client.get("/slots", headers=api_headers).status_code == 200
    with psycopg.connect(database_url, autocommit=True) as admin:
        admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = current_database() AND pid <> pg_backend_pid()"
        )

    # Every request after that must work: the pool has to notice the dead connections and
    # replace them instead of handing them out (one per pooled connection, plus one spare).
    # The first one can take a few seconds while the pool reconnects.
    statuses = [
        client.get("/slots", headers=api_headers).status_code for _ in range(db.POOL_MAX_SIZE + 1)
    ]
    assert statuses == [200] * (db.POOL_MAX_SIZE + 1)
