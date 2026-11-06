import { afterEach, describe, expect, it, vi } from "vitest"
import { clearSession, getSession, setSession, subscribeToSession } from "./session"

afterEach(() => clearSession())

const future = () => new Date(Date.now() + 60 * 60 * 1000).toISOString()

describe("session store", () => {
    it("starts signed out", () => {
        expect(getSession()).toBeNull()
    })

    it("remembers a session and forgets it on sign out", () => {
        setSession({ token: "t", role: "patient", name: "P", expiresAt: future() })
        expect(getSession()?.role).toBe("patient")
        clearSession()
        expect(getSession()).toBeNull()
    })

    it("gives the same object until something changes (needed by useSyncExternalStore)", () => {
        setSession({ token: "t", role: "staff", name: "S", expiresAt: future() })
        expect(getSession()).toBe(getSession())
    })

    it("treats an expired session as signed out", () => {
        setSession({ token: "t", role: "staff", name: "S", expiresAt: new Date(Date.now() - 1000).toISOString() })
        expect(getSession()).toBeNull()
    })

    it("tells listeners when the session changes, and stops after unsubscribe", () => {
        const listener = vi.fn()
        const unsubscribe = subscribeToSession(listener)
        setSession({ token: "t", role: "staff", name: "S", expiresAt: future() })
        clearSession()
        expect(listener).toHaveBeenCalledTimes(2)
        unsubscribe()
        setSession({ token: "t", role: "staff", name: "S", expiresAt: future() })
        expect(listener).toHaveBeenCalledTimes(2)
    })
})
