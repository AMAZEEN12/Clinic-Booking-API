-- V1: core schema. Migrations are forward-only and additive (D28): never edit this file once applied.

CREATE TABLE slots (
                       id        TEXT PRIMARY KEY,
                       provider  TEXT NOT NULL,
                       start_at  TIMESTAMPTZ NOT NULL,
                       end_at    TIMESTAMPTZ NOT NULL
);

CREATE TABLE bookings (
                          id          TEXT PRIMARY KEY,
                          slot_id     TEXT NOT NULL REFERENCES slots (id) ON DELETE CASCADE,
                          name        TEXT NOT NULL,
                          email       TEXT NOT NULL,
                          status      TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled')),
                          created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The database itself guarantees a slot never has two confirmed bookings (R7, N2).
-- Cancelled bookings are not covered, so a cancelled slot can be booked again (R8).
CREATE UNIQUE INDEX bookings_one_confirmed_per_slot
    ON bookings (slot_id)
    WHERE status = 'confirmed';

-- Supports paging a person's bookings, newest first (R10).
CREATE INDEX bookings_email_created_idx
    ON bookings (lower(email), created_at DESC);

-- Idempotency-Key replays (R9).
CREATE TABLE idempotency_keys (
                                  key           TEXT PRIMARY KEY,
                                  request_hash  TEXT NOT NULL,
                                  booking_id    TEXT NOT NULL REFERENCES bookings (id) ON DELETE CASCADE,
                                  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Simulated payments, kept apart from the core booking (R13).
CREATE TABLE payments (
                          booking_id  TEXT PRIMARY KEY REFERENCES bookings (id) ON DELETE CASCADE,
                          status      TEXT NOT NULL CHECK (status IN ('paid')),
                          reference   TEXT NOT NULL,
                          paid_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);