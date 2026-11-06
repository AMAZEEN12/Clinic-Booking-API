import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "@/hooks/useAuth"
import type { Role } from "@/models"
import { homeFor, routes } from "@/utils/routes"

/**
 * Wraps the screens only one role may see. Nobody signed in goes to the login page; someone
 * signed in with the other role goes back to their own home (a patient never reaches the
 * dashboard, staff never reach the booking screens).
 */
export function RequireRole({ role }: { role: Role }) {
    const session = useAuth()
    const location = useLocation()

    if (!session) return <Navigate to={routes.login} replace state={{ from: location.pathname }} />
    if (session.role !== role) return <Navigate to={homeFor(session.role)} replace />
    return <Outlet />
}
