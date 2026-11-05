import { afterEach, describe, expect, it, vi } from "vitest"
import {
    ApiError,
    cancelBooking,
    createBooking,
    getBooking,
    getDashboardAppointments,
    getDashboardSummary,
    getPayment,
    getSlots,
    kindForStatus,
    payForBooking,
} from "./api"
vi.mock("@/utils/env", () => ({ env: { apiBaseUrl: "https://api.example.test", apiKey: "test-key" } }))

function reply(status: number, body: unknown, headers: Record<string, string> = {}) {
    return new Response(JSON.stringify(body), { status, headers })
}

function stubFetch(response: Response | Error) {
    const fetchMock = vi.fn(async () => {
        if (response instanceof Error) throw response
        return response
    })
    vi.stubGlobal("fetch", fetchMock)
    return fetchMock
}

function lastCall(fetchMock: ReturnType<typeof stubFetch>) {
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    return { url, init, headers: init.headers as Record<string, string> }
}

afterEach(() => vi.unstubAllGlobals())

describe("kindForStatus", () => {
    it("maps the statuses the API uses", () => {
        expect(kindForStatus(400)).toBe("invalid")
        expect(kindForStatus(401)).toBe("unauthorized")
        expect(kindForStatus(404)).toBe("not_found")
        expect(kindForStatus(409)).toBe("conflict")
        expect(kindForStatus(429)).toBe("rate_limited")
        expect(kindForStatus(500)).toBe("server")
        expect(kindForStatus(503)).toBe("server")
    })
})

describe("getSlots", () => {
    it("sends the key and returns the list", async () => {
        const slots = [{ id: "s1", provider: "Dr Ade", start: "2026-12-10T09:00:00Z", end: "2026-12-10T09:30:00Z", available: true }]
        const fetchMock = stubFetch(reply(200, slots))

        await expect(getSlots()).resolves.toEqual(slots)

        const { url, headers } = lastCall(fetchMock)
        expect(url).toBe("https://api.example.test/slots")
        expect(headers["X-API-Key"]).toBe("test-key")
    })

    it("rejects an answer that is not a list", async () => {
        stubFetch(reply(200, { slots: [] }))
        await expect(getSlots()).rejects.toMatchObject({ kind: "server" })
    })
})

describe("createBooking", () => {
    it("posts the body with the Idempotency-Key header", async () => {
        const booking = { id: "bk_1", slot_id: "s1", name: "Ada Obi", email: "ada@example.com", status: "confirmed", created_at: "2026-12-01T10:00:00Z" }
        const fetchMock = stubFetch(reply(201, booking))
        const body = { slot_id: "s1", name: "Ada Obi", email: "ada@example.com" }

        await expect(createBooking({ body, idempotencyKey: "key-123" })).resolves.toEqual(booking)

        const { init, headers } = lastCall(fetchMock)
        expect(init.method).toBe("POST")
        expect(init.body).toBe(JSON.stringify(body))
        expect(headers["Idempotency-Key"]).toBe("key-123")
        expect(headers["Content-Type"]).toBe("application/json")
    })

    it("turns a 409 into a conflict error", async () => {
        stubFetch(reply(409, { error: "slot already booked" }))
        const error = await createBooking({ body: { slot_id: "s1", name: "A", email: "a@b.c" }, idempotencyKey: "k" }).catch((e) => e)
        expect(error).toBeInstanceOf(ApiError)
        expect(error).toMatchObject({ kind: "conflict", status: 409, message: "slot already booked" })
    })

    it("keeps Retry-After on a 429", async () => {
        stubFetch(reply(429, { error: "too many requests" }, { "Retry-After": "6" }))
        const error = await createBooking({ body: { slot_id: "s1", name: "A", email: "a@b.c" }, idempotencyKey: "k" }).catch((e) => e)
        expect(error).toMatchObject({ kind: "rate_limited", retryAfterSeconds: 6 })
    })
})

describe("getBooking and cancelBooking", () => {
    it("escapes the id in the path", async () => {
        const fetchMock = stubFetch(reply(404, { error: "not found" }))
        await expect(getBooking("a/b c")).rejects.toMatchObject({ kind: "not_found" })
        expect(lastCall(fetchMock).url).toBe("https://api.example.test/bookings/a%2Fb%20c")
    })

    it("cancels with DELETE and sends no body", async () => {
        const fetchMock = stubFetch(reply(200, { id: "bk_1", status: "cancelled" }))
        await cancelBooking("bk_1")
        const { init, headers } = lastCall(fetchMock)
        expect(init.method).toBe("DELETE")
        expect(init.body).toBeUndefined()
        expect(headers["Content-Type"]).toBeUndefined()
    })
})

describe("getPayment and payForBooking", () => {
    const paid = { booking_id: "bk_1", status: "paid", reference: "DEMO-1A2B3C4D5E", paid_at: "2026-12-01T10:00:00Z" }

    it("reads the payment with GET", async () => {
        const unpaid = { booking_id: "bk_1", status: "unpaid", reference: null, paid_at: null }
        const fetchMock = stubFetch(reply(200, unpaid))

        await expect(getPayment("bk_1")).resolves.toEqual(unpaid)

        const { url, init, headers } = lastCall(fetchMock)
        expect(url).toBe("https://api.example.test/bookings/bk_1/payment")
        expect(init.method).toBe("GET")
        expect(headers["X-API-Key"]).toBe("test-key")
    })

    it("pays with POST and sends no body, so no card details can be sent", async () => {
        const fetchMock = stubFetch(reply(200, paid))

        await expect(payForBooking("bk_1")).resolves.toEqual(paid)

        const { url, init, headers } = lastCall(fetchMock)
        expect(url).toBe("https://api.example.test/bookings/bk_1/payment")
        expect(init.method).toBe("POST")
        expect(init.body).toBeUndefined()
        expect(headers["Content-Type"]).toBeUndefined()
    })

    it("escapes the id in the path", async () => {
        const fetchMock = stubFetch(reply(200, paid))
        await payForBooking("a/b c")
        expect(lastCall(fetchMock).url).toBe("https://api.example.test/bookings/a%2Fb%20c/payment")
    })

    it("turns paying a cancelled booking into a conflict error", async () => {
        stubFetch(reply(409, { error: "booking is cancelled" }))
        await expect(payForBooking("bk_1")).rejects.toMatchObject({ kind: "conflict", status: 409 })
    })
})

describe("dashboard requests", () => {
    it("reads the summary for a day", async () => {
        const summary = { date: "2026-12-10", booked: 1, cancelled: 1, open_slots: 2, total_slots: 3 }
        const fetchMock = stubFetch(reply(200, summary))

        await expect(getDashboardSummary("2026-12-10")).resolves.toEqual(summary)

        const { url, init, headers } = lastCall(fetchMock)
        expect(url).toBe("https://api.example.test/dashboard/summary?date=2026-12-10")
        expect(init.method).toBe("GET")
        expect(headers["X-API-Key"]).toBe("test-key")
    })

    it("reads the appointments for a day", async () => {
        const items = [
            {
                booking_id: "bk_1",
                slot_id: "s1",
                provider: "Dr Ade",
                start: "2026-12-10T09:00:00Z",
                end: "2026-12-10T09:30:00Z",
                patient: "Ada O.",
                status: "confirmed",
                payment: "paid",
            },
        ]
        const fetchMock = stubFetch(reply(200, items))

        await expect(getDashboardAppointments("2026-12-10")).resolves.toEqual(items)
        expect(lastCall(fetchMock).url).toBe("https://api.example.test/dashboard/appointments?date=2026-12-10")
    })

    it("rejects an appointments answer that is not a list", async () => {
        stubFetch(reply(200, { items: [] }))
        await expect(getDashboardAppointments("2026-12-10")).rejects.toMatchObject({ kind: "server" })
    })

    it("turns a bad date into an invalid error", async () => {
        stubFetch(reply(400, { error: "date must be YYYY-MM-DD" }))
        await expect(getDashboardSummary("nope")).rejects.toMatchObject({ kind: "invalid", status: 400 })
    })
})

describe("failures without an answer", () => {
    it("reports a network error", async () => {
        stubFetch(new TypeError("Failed to fetch"))
        await expect(getSlots()).rejects.toMatchObject({ kind: "network", status: null })
    })

    it("copes with an error page that is not JSON", async () => {
        vi.stubGlobal("fetch", vi.fn(async () => new Response("<html>Bad gateway</html>", { status: 502 })))
        await expect(getSlots()).rejects.toMatchObject({ kind: "server", status: 502 })
    })
})