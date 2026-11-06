import type { Role } from "@/models"

export const routes = {
    login: "/login",
    book: "/",
    find: "/find",
    dashboard: "/dashboard",
    booking: (id: string) => `/booking/${encodeURIComponent(id)}`,
} as const

/** The first screen each role sees after signing in. */
export function homeFor(role: Role): string {
    return role === "staff" ? routes.dashboard : routes.book
}
