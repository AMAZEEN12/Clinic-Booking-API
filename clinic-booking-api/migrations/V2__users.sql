-- V2: staff and patient logins. Additive: V1 is untouched (D28).
-- Passwords are stored only as salted scrypt hashes. The two demo accounts are created (or
-- refreshed) at startup from environment variables, never from this file.

CREATE TABLE users (
    id             TEXT PRIMARY KEY,
    email          TEXT NOT NULL,
    name           TEXT NOT NULL,
    role           TEXT NOT NULL CHECK (role IN ('staff', 'patient')),
    password_hash  TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX users_email_unique ON users (lower(email));
