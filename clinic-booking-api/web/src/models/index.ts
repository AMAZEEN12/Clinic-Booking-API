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

export type Role = "staff" | "patient"

/** The signed-in person (kept by services/session.ts). */
export type Session = {
    token: string
    role: Role
    name: string
    /** ISO 8601 UTC: when the login ends. */
    expiresAt: string
}

/** POST /auth/login answer (clinic-booking-api/app/schemas.py, LoginResponse). */
export type LoginResponse = {
    token: string
    role: Role
    name: string
    expires_at: string
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
/** Counts for one UTC day (clinic-booking-api/app/schemas.py, DashboardSummary). */
export type DashboardSummary = {
    /** YYYY-MM-DD, the UTC day the counts are for. */
    date: string
    booked: number
    cancelled: number
    open_slots: number
    total_slots: number
}

/** One booking on the dashboard. `patient` is already masked by the API (for example "Ada O."): there is no email. */
export type DashboardAppointment = {
    booking_id: string
    slot_id: string
    provider: string
    start: string
    end: string
    patient: string
    status: BookingStatus
    payment: PaymentStatus
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

/** One page of GET /bookings?email= (clinic-booking-api/app/schemas.py, BookingPage). Oldest first. */
export type BookingPage = {
    bookings: Booking[]
    next_cursor: string | null
}

/** All of a person's bookings, newest first: the pages from GET /bookings joined together. */
export type BookingList = {
    items: Booking[]
    total: number
}