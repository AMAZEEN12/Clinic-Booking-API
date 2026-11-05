import { BrowserRouter, Route, Routes } from "react-router-dom"
import { Shell } from "@/components/layout/Shell"
import { BookPage } from "@/pages/BookPage"
import { BookingPage } from "@/pages/BookingPage"
import { FindPage } from "@/pages/FindPage"
import { NotFoundPage } from "@/pages/NotFoundPage"

export function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route element={<Shell />}>
                    <Route index element={<BookPage />} />
                    <Route path="find" element={<FindPage />} />
                    <Route path="booking/:id" element={<BookingPage />} />
                    <Route path="*" element={<NotFoundPage />} />
                </Route>
            </Routes>
        </BrowserRouter>
    )
}