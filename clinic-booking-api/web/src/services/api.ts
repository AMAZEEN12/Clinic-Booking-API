// The only place that talks to the clinic booking API (see clinic-booking-api/app/routers).
// Every failure becomes an ApiError with a `kind`, so screens never look at raw status codes.

import type {
    Booking,
    BookingList,
    BookingPage,
    CreateBookingArgs,
    DashboardAppointment,
    DashboardSummary,
    LoginResponse,
    Payment,
    Session,
    Slot,
} from "@/models"
import { clearSession, getSession, setSession } from "@/services/session"
import { env } from "@/utils/env"

export type ApiErrorKind =
    | "network" // no answer: offline, timed out, or blocked
    | "unauthorized" // 401: the API key is missing or wrong, or the login is missing, wrong or ended
    | "forbidden" // 403: signed in, but not as clinic staff
    | "invalid" // 400
    | "not_found" // 404
    | "conflict" // 409: for example the slot was just taken
    | "rate_limited" // 429
    | "server" // anything else

export class ApiError extends Error {
    readonly kind: ApiErrorKind
    readonly status: number | null
    /** Whole seconds from the Retry-After header, when the API sent one. */
    readonly retryAfterSeconds: number | null

    constructor(kind: ApiErrorKind, status: number | null, message: string, retryAfterSeconds: number | null = null) {
        super(message)
        this.name = "ApiError"
        this.kind = kind
        this.status = status
        this.retryAfterSeconds = retryAfterSeconds
    }
}

// The free Render plan sleeps when idle and can need about a minute to wake up.
const REQUEST_TIMEOUT_MS = 60_000

export function kindForStatus(status: number): ApiErrorKind {
    switch (status) {
        case 400:
            return "invalid"
        case 401:
            return "unauthorized"
        case 403:
            return "forbidden"
        case 404:
            return "not_found"
        case 409:
            return "conflict"
        case 429:
            return "rate_limited"
        default:
            return "server"
    }
}

type RequestOptions = {
    method?: "GET" | "POST" | "DELETE"
    body?: unknown
    idempotencyKey?: string
    /** The login form itself must not end a session when it fails. */
    isLogin?: boolean
}

async function readJson(response: Response): Promise<unknown> {
    try {
        return await response.json()
    } catch {
        return null
    }
}

function readRetryAfter(response: Response): number | null {
    const seconds = Number(response.headers.get("Retry-After"))
    return Number.isFinite(seconds) && seconds > 0 ? Math.ceil(seconds) : null
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const headers: Record<string, string> = { Accept: "application/json", "X-API-Key": env.apiKey }
    if (options.body !== undefined) headers["Content-Type"] = "application/json"
    if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey
    // The login token is what the API checks for staff-only screens such as the dashboard.
    const session = getSession()
    if (session) headers["Authorization"] = `Bearer ${session.token}`

    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

    let response: Response
    try {
        response = await fetch(`${env.apiBaseUrl}${path}`, {
            method: options.method ?? "GET",
            headers,
            body: options.body === undefined ? undefined : JSON.stringify(options.body),
            signal: controller.signal,
        })
    } catch {
        throw new ApiError("network", null, "no response from the API")
    } finally {
        clearTimeout(timer)
    }

    const payload = await readJson(response)

    if (!response.ok) {
        // The login has ended or was refused: forget it, so the screens send the person to sign in.
        if (response.status === 401 && session && !options.isLogin) clearSession()
        const message =
            payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
                ? payload.error
                : `request failed with status ${response.status}`
        throw new ApiError(kindForStatus(response.status), response.status, message, readRetryAfter(response))
    }

    return payload as T
}

/** Signs in and remembers the login. Throws an ApiError (401 for a wrong email or password). */
export async function login(email: string, password: string): Promise<Session> {
    const result = await request<LoginResponse>("/auth/login", {
        method: "POST",
        body: { email, password },
        isLogin: true,
    })
    const session: Session = {
        token: result.token,
        role: result.role,
        name: result.name,
        expiresAt: result.expires_at,
    }
    setSession(session)
    return session
}

export async function getSlots(): Promise<Slot[]> {
    const slots = await request<unknown>("/slots")
    if (!Array.isArray(slots)) throw new ApiError("server", 200, "unexpected slots response")
    return slots as Slot[]
}

export function createBooking({ body, idempotencyKey }: CreateBookingArgs): Promise<Booking> {
    return request<Booking>("/bookings", { method: "POST", body, idempotencyKey })
}

export function getBooking(id: string): Promise<Booking> {
    return request<Booking>(`/bookings/${encodeURIComponent(id)}`)
}

export function cancelBooking(id: string): Promise<Booking> {
    return request<Booking>(`/bookings/${encodeURIComponent(id)}`, { method: "DELETE" })
}

export function getPayment(id: string): Promise<Payment> {
    return request<Payment>(`/bookings/${encodeURIComponent(id)}/payment`)
}

/** Demo payment: sends no body, so no card details can ever leave the page. */
export function payForBooking(id: string): Promise<Payment> {
    return request<Payment>(`/bookings/${encodeURIComponent(id)}/payment`, { method: "POST" })
}
/** `date` is a UTC day, YYYY-MM-DD. */
export function getDashboardSummary(date: string): Promise<DashboardSummary> {
    return request<DashboardSummary>(`/dashboard/summary?date=${encodeURIComponent(date)}`)
}

export async function getDashboardAppointments(date: string): Promise<DashboardAppointment[]> {
    const items = await request<unknown>(`/dashboard/appointments?date=${encodeURIComponent(date)}`)
    if (!Array.isArray(items)) throw new ApiError("server", 200, "unexpected appointments response")
    return items as DashboardAppointment[]
}

const LIST_PAGE_SIZE = 50
const LIST_MAX_PAGES = 6

function isBookingPage(value: unknown): value is BookingPage {
    return (
        !!value &&
        typeof value === "object" &&
        Array.isArray((value as BookingPage).bookings) &&
        ((value as BookingPage).next_cursor === null || typeof (value as BookingPage).next_cursor === "string")
    )
}

/** Every booking made with this email, newest first. Follows next_cursor (the API lists oldest first). */
export async function listBookings(email: string): Promise<BookingList> {
    const all: Booking[] = []
    let cursor: string | null = null
    for (let pageNumber = 0; pageNumber < LIST_MAX_PAGES; pageNumber++) {
        const query: string = `email=${encodeURIComponent(email)}&limit=${LIST_PAGE_SIZE}` + (cursor ? `&cursor=${encodeURIComponent(cursor)}` : "")
        const result: unknown = await request<unknown>(`/bookings?${query}`)
        if (!isBookingPage(result)) throw new ApiError("server", 200, "unexpected bookings response")
        all.push(...result.bookings)
        cursor = result.next_cursor
        if (cursor === null) break
    }
    const items = all.reverse()
    return { items, total: items.length }
}