import { NavLink, Outlet } from "react-router-dom"
import { cn } from "@/lib/cn"
import { CLINIC_TZ_LABEL } from "@/utils/clinicTime"
import { routes } from "@/utils/routes"

function NavItem({ to, children }: { to: string; children: string }) {
    return (
        <NavLink
            to={to}
            end
            className={({ isActive }) =>
                cn(
                    "inline-flex h-11 items-center rounded-full px-4 text-base font-medium",
                    isActive
                        ? "bg-[var(--color-primary)] text-[var(--color-on-primary)]"
                        : "text-[var(--color-text)] hover:bg-[var(--color-surface)]",
                )
            }
        >
            {children}
        </NavLink>
    )
}

/** The frame around every page: skip link, header with navigation, content, footer. */
export function Shell() {
    return (
        <div className="flex min-h-screen flex-col">
            <a
                href="#main"
                className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-10 focus:rounded-full focus:bg-[var(--color-primary)] focus:px-4 focus:py-2 focus:text-[var(--color-on-primary)]"
            >
                Skip to content
            </a>

            <header className="border-b border-[var(--color-border)] bg-[var(--color-surface)]">
                <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-3 sm:px-6">
                    <p className="font-heading text-xl font-extrabold">Demo clinic</p>
                    <nav aria-label="Main" className="flex gap-1">
                        <NavItem to={routes.book}>Book</NavItem>
                        <NavItem to={routes.find}>Find a booking</NavItem>
                        <NavItem to={routes.find}>Find a booking</NavItem>
                        <NavItem to={routes.dashboard}>Dashboard</NavItem>
                    </nav>
                </div>
            </header>

            <main id="main" tabIndex={-1} className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6 sm:py-10">
                <Outlet />
            </main>

            <footer className="px-4 pb-8 text-center text-sm text-[var(--color-text-muted)]">
                All times are shown in {CLINIC_TZ_LABEL}.
            </footer>
        </div>
    )
}