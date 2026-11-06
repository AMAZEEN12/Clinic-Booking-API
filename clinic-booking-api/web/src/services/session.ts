// Who is signed in. One small store that screens read through useAuth() and that api.ts clears
// when the API says the login has ended.
//
// The login token lives in sessionStorage: it survives a refresh but not closing the tab.
// This is a screen-hiding convenience only. The real protection is on the API, which refuses
// the dashboard to anyone without a staff token (see app/auth.py).

import type { Session } from "@/models"

const STORAGE_KEY = "clinic.session"

const listeners = new Set<() => void>()

function isSession(value: unknown): value is Session {
    if (!value || typeof value !== "object") return false
    const v = value as Record<string, unknown>
    return (
        typeof v.token === "string" &&
        typeof v.name === "string" &&
        typeof v.expiresAt === "string" &&
        (v.role === "staff" || v.role === "patient")
    )
}

function isExpired(session: Session): boolean {
    const expires = Date.parse(session.expiresAt)
    return !Number.isFinite(expires) || expires <= Date.now()
}

function readStored(): Session | null {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY)
        if (!raw) return null
        const parsed: unknown = JSON.parse(raw)
        return isSession(parsed) && !isExpired(parsed) ? parsed : null
    } catch {
        return null // no storage (private mode, tests) or damaged data: start signed out
    }
}

function writeStored(session: Session | null) {
    try {
        if (session) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
        else sessionStorage.removeItem(STORAGE_KEY)
    } catch {
        // Storage is blocked: the login still works until the page is refreshed.
    }
}

let current: Session | null = readStored()

/** The signed-in person, or null. Returns the same object until something changes. */
export function getSession(): Session | null {
    if (current && isExpired(current)) {
        current = null
        writeStored(null)
    }
    return current
}

export function setSession(session: Session) {
    current = session
    writeStored(session)
    listeners.forEach((listener) => listener())
}

export function clearSession() {
    if (current === null) return
    current = null
    writeStored(null)
    listeners.forEach((listener) => listener())
}

export function subscribeToSession(listener: () => void): () => void {
    listeners.add(listener)
    return () => {
        listeners.delete(listener)
    }
}
