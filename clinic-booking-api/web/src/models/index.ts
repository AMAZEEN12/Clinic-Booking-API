// Types for the clinic booking API (see clinic-booking-api/app/schemas.py).
// If the API's fields change, change them here and the compiler will point at every screen to fix.

export type Slot = {
    id: string
    provider: string
    /** ISO 8601, always UTC with a Z suffix. */
    start: string
    end: string
    available: boolean
}

export type BookingStatus = "confirmed" | "cancelled"

export type Booking = {
    id: string
    slot_id: string
    name: string
    email: string
    status: BookingStatus
    created_at: string
}
export type PaymentStatus = "unpaid" | "paid"

/** The simulated payment of one booking (clinic-booking-api/app/schemas.py, Payment). Demo only: no real money. */
export type Payment = {
    booking_id: string
    status: PaymentStatus
    /** Looks like DEMO-1A2B3C4D5E. Null until the booking is paid. */
    reference: string | null
    /** ISO 8601 UTC. Null until the booking is paid. */
    paid_at: string | null
}

export type NewBooking = {
    slot_id: string
    name: string
    email: string
}

export type CreateBookingArgs = {
    body: NewBooking
    /** Sent as the Idempotency-Key header so a retried request never books twice. */
    idempotencyKey: string
}