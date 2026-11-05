import type { Page, Route } from "@playwright/test"

// Must equal VITE_API_KEY in playwright.config.ts. The fake API answers 401 without it, so the
// tests also prove the page sends the X-API-Key header.
export const API_KEY = "e2e-test-key"
const API_PREFIX = "/api-mock"

type FakeSlot = { id: string; provider: string; start: string; end: string }
type FakeBooking = {
    id: string
    slot_id: string
    name: string
    email: string
    status: "confirmed" | "cancelled"
    created_at: string
}
type FakePayment = { booking_id: string; status: "paid"; reference: string; paid_at: string }

export type FakeApiOptions = {
    /** Slots that show as taken from the start. */
    takenSlotIds?: string[]
    /** Every POST /bookings answers 409, as if someone else got the time first. */
    conflictOnBook?: boolean
}

export type SeedArgs = { slotId: string; name: string; email: string; status?: "confirmed" | "cancelled" }

export type FakeApi = {
    slots: FakeSlot[]
    bookings: Map<string, FakeBooking>
    /** Adds a booking before the page loads and returns it. */
    seedBooking: (args: SeedArgs) => FakeBooking
}

function maskName(full: string): string {
    const parts = full.trim().split(/\s+/)
    return parts.length === 1 ? parts[0] : `${parts[0]} ${parts[parts.length - 1][0].toUpperCase()}.`
}

function reply(route: Route, status: number, body: unknown) {
    return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })
}

/** Three slots today (UTC): 09:00, 10:00 and 11:00 UTC, shown as 10:00, 11:00 and 12:00 Lagos time. */
export async function installFakeApi(page: Page, options: FakeApiOptions = {}): Promise<FakeApi> {
    const midnight = new Date()
    midnight.setUTCHours(0, 0, 0, 0)
    const at = (hour: number, minutes = 0) => new Date(midnight.getTime() + (hour * 60 + minutes) * 60_000).toISOString()

    const slots: FakeSlot[] = [
        { id: "slot_1", provider: "Dr. Bello", start: at(9), end: at(9, 30) },
        { id: "slot_2", provider: "Dr. Eze", start: at(10), end: at(10, 30) },
        { id: "slot_3", provider: "Dr. Bello", start: at(11), end: at(11, 30) },
    ]
    const taken = new Set(options.takenSlotIds ?? [])
    const bookings = new Map<string, FakeBooking>()
    const payments = new Map<string, FakePayment>()
    let counter = 0

    const isBooked = (slotId: string) =>
        taken.has(slotId) || [...bookings.values()].some((b) => b.slot_id === slotId && b.status === "confirmed")

    function addBooking(args: SeedArgs): FakeBooking {
        counter += 1
        const booking: FakeBooking = {
            id: `bk_e2e${counter}`,
            slot_id: args.slotId,
            name: args.name,
            email: args.email,
            status: args.status ?? "confirmed",
            created_at: new Date().toISOString(),
        }
        bookings.set(booking.id, booking)
        return booking
    }

    function dayOf(date: string) {
        const onDay = slots.filter((s) => s.start.slice(0, 10) === date)
        const ids = new Set(onDay.map((s) => s.id))
        const onDayBookings = [...bookings.values()].filter((b) => ids.has(b.slot_id))
        return { onDay, onDayBookings }
    }

    await page.route(`**${API_PREFIX}/**`, async (route) => {
        const request = route.request()
        if (request.headers()["x-api-key"] !== API_KEY) return reply(route, 401, { error: "unauthorized" })

        const url = new URL(request.url())
        const path = url.pathname.slice(API_PREFIX.length)
        const method = request.method()

        if (method === "GET" && path === "/slots") {
            return reply(
                route,
                200,
                slots.map((s) => ({ ...s, available: !isBooked(s.id) })),
            )
        }

        if (method === "POST" && path === "/bookings") {
            if (options.conflictOnBook) return reply(route, 409, { error: "slot already booked" })
            const body = request.postDataJSON() as { slot_id: string; name: string; email: string }
            if (!slots.some((s) => s.id === body.slot_id)) return reply(route, 404, { error: "slot not found" })
            if (isBooked(body.slot_id)) return reply(route, 409, { error: "slot already booked" })
            return reply(route, 201, addBooking({ slotId: body.slot_id, name: body.name, email: body.email }))
        }

        const bookingMatch = path.match(/^\/bookings\/([^/]+)(\/payment)?$/)
        if (bookingMatch) {
            const booking = bookings.get(decodeURIComponent(bookingMatch[1]))
            if (!booking) return reply(route, 404, { error: "booking not found" })
            const isPayment = bookingMatch[2] !== undefined

            if (!isPayment && method === "GET") return reply(route, 200, booking)
            if (!isPayment && method === "DELETE") {
                booking.status = "cancelled"
                return reply(route, 200, booking)
            }
            if (isPayment && method === "GET") {
                const paid = payments.get(booking.id)
                return reply(route, 200, paid ?? { booking_id: booking.id, status: "unpaid", reference: null, paid_at: null })
            }
            if (isPayment && method === "POST") {
                if (booking.status === "cancelled") return reply(route, 409, { error: "booking is cancelled" })
                const paid: FakePayment = payments.get(booking.id) ?? {
                    booking_id: booking.id,
                    status: "paid",
                    reference: "DEMO-1A2B3C4D5E",
                    paid_at: new Date().toISOString(),
                }
                payments.set(booking.id, paid)
                return reply(route, 200, paid)
            }
        }

        if (method === "GET" && path === "/dashboard/summary") {
            const date = url.searchParams.get("date") ?? ""
            const { onDay, onDayBookings } = dayOf(date)
            return reply(route, 200, {
                date,
                booked: onDayBookings.filter((b) => b.status === "confirmed").length,
                cancelled: onDayBookings.filter((b) => b.status === "cancelled").length,
                open_slots: onDay.filter((s) => !isBooked(s.id)).length,
                total_slots: onDay.length,
            })
        }

        if (method === "GET" && path === "/dashboard/appointments") {
            const { onDayBookings } = dayOf(url.searchParams.get("date") ?? "")
            return reply(
                route,
                200,
                onDayBookings.map((b) => {
                    const slot = slots.find((s) => s.id === b.slot_id) as FakeSlot
                    return {
                        booking_id: b.id,
                        slot_id: b.slot_id,
                        provider: slot.provider,
                        start: slot.start,
                        end: slot.end,
                        patient: maskName(b.name),
                        status: b.status,
                        payment: payments.has(b.id) ? "paid" : "unpaid",
                    }
                }),
            )
        }

        return reply(route, 404, { error: "not found" })
    })

    return { slots, bookings, seedBooking: addBooking }
}