import { useNavigate } from "react-router-dom"
import { EmptyState } from "@/components/ui/empty-state"
import { usePageTitle } from "@/hooks/usePageTitle"
import { routes } from "@/utils/routes"

export function NotFoundPage() {
    usePageTitle("Page not found")
    const navigate = useNavigate()
    return (
        <EmptyState
            title="Page not found"
            description="That page doesn't exist."
            action={{ label: "Go to booking", onClick: () => navigate(routes.book) }}
        />
    )
}