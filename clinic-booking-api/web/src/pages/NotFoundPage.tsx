import { useNavigate } from "react-router-dom"
import { EmptyState } from "@/components/ui/empty-state"
import { useAuth } from "@/hooks/useAuth"
import { usePageTitle } from "@/hooks/usePageTitle"
import { homeFor, routes } from "@/utils/routes"

export function NotFoundPage() {
    usePageTitle("Page not found")
    const navigate = useNavigate()
    const session = useAuth()
    return (
        <EmptyState
            title="Page not found"
            description="That page doesn't exist."
            action={{
                label: session ? "Go back" : "Sign in",
                onClick: () => navigate(session ? homeFor(session.role) : routes.login),
            }}
        />
    )
}
