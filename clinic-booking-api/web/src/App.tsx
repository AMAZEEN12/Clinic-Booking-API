import { BrowserRouter, Route, Routes } from "react-router-dom"
import { RequireRole } from "@/components/auth/RequireRole"
import { Shell } from "@/components/layout/Shell"
import { BookPage } from "@/pages/BookPage"
import { BookingPage } from "@/pages/BookingPage"
import { DashboardPage } from "@/pages/DashboardPage"
import { FindPage } from "@/pages/FindPage"
import { LoginPage } from "@/pages/LoginPage"
import { NotFoundPage } from "@/pages/NotFoundPage"

export function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route element={<Shell />}>
                    <Route path="login" element={<LoginPage />} />
                    {/* Patients only: book, find and manage a booking. */}
                    <Route element={<RequireRole allow="patient" />}>
                        <Route index element={<BookPage />} />
                        <Route path="find" element={<FindPage />} />
                        <Route path="booking/:id" element={<BookingPage />} />
                    </Route>
                    {/* Staff only: the daily dashboard. */}
                    <Route element={<RequireRole allow="staff" />}>
                        <Route path="dashboard" element={<DashboardPage />} />
                    </Route>
                    <Route path="*" element={<NotFoundPage />} />
                </Route>
            </Routes>
        </BrowserRouter>
    )
}
