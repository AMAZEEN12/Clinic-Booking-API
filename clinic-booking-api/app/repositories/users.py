"""SQL for user accounts. No business rules live here."""

from psycopg import Connection


def get_by_email(conn: Connection, email: str) -> dict | None:
    return conn.execute(
        "SELECT id, email, name, role, password_hash FROM users WHERE lower(email) = lower(%s)",
        (email,),
    ).fetchone()


def insert(
    conn: Connection, user_id: str, email: str, name: str, role: str, password_hash: str
) -> None:
    conn.execute(
        "INSERT INTO users (id, email, name, role, password_hash) VALUES (%s, %s, %s, %s, %s)",
        (user_id, email, name, role, password_hash),
    )


def update_password(conn: Connection, user_id: str, password_hash: str) -> None:
    conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
