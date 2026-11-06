import { useSyncExternalStore } from "react"
import type { Session } from "@/models"
import { getSession, subscribeToSession } from "@/services/session"

/** The signed-in person, or null. Re-renders the screen when someone signs in or out. */
export function useAuth(): Session | null {
    return useSyncExternalStore(subscribeToSession, getSession)
}
