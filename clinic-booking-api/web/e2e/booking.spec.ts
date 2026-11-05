import { expect, test, type Page } from "@playwright/test"
import { installFakeApi } from "./fakeApi"

function timeButton(page: Page, time: RegExp) {
    return page.getByRole("group", { name: "Choose a time" }).getByRole("button", { name: time })
}

test.describe("patient booking flow", () => {
    test("books a time and shows the confirmation", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/")
        await expect(page.getByRole("heading", { name: "Book an appointment", level: 1 })).toBeVisible()

        await timeButton(page, /^11:00/).click()
        await page.getByLabel("Full name").fill("Chidi Okafor")
        await page.getByLabel("Email").fill("chidi@example.test")
        await page.getByRole("button", { name: "Confirm booking" }).click()

        await expect(page).toHaveURL(/\/booking\/bk_/)
        await expect(page.getByRole("heading", { name: "Your booking is confirmed" })).toBeVisible()
        await expect(page.getByText("chidi@example.test")).toBeVisible()
    })

    test("a taken time is disabled and says Taken in words", async ({ page }) => {
        await installFakeApi(page, { takenSlotIds: ["slot_2"] })
        await page.goto("/")

        const taken = page.getByRole("button", { name: /Taken/ })
        await expect(taken).toBeVisible()
        await expect(taken).toBeDisabled()
    })

    test("asks for a time and your details before booking", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/")
        await page.getByRole("button", { name: "Confirm booking" }).click()

        await expect(page.getByText("Choose a day and a time first.")).toBeVisible()
        await expect(page.getByText("Enter your name.")).toBeVisible()
        await expect(page.getByText("Enter your email.")).toBeVisible()
        await expect(page).toHaveURL(/\/$/)
    })

    test("tells the patient when someone else took the time", async ({ page }) => {
        await installFakeApi(page, { conflictOnBook: true })
        await page.goto("/")

        await timeButton(page, /^10:00/).click()
        await page.getByLabel("Full name").fill("Chidi Okafor")
        await page.getByLabel("Email").fill("chidi@example.test")
        await page.getByRole("button", { name: "Confirm booking" }).click()

        await expect(page.getByRole("alert").first()).toBeVisible()
        await expect(page).toHaveURL(/\/$/)
    })

    test("cancels a booking", async ({ page }) => {
        const api = await installFakeApi(page)
        const booking = api.seedBooking({ slotId: "slot_1", name: "Chidi Okafor", email: "chidi@example.test" })
        await page.goto(`/booking/${booking.id}`)

        await page.getByRole("button", { name: "Cancel booking" }).click()
        await page.getByRole("button", { name: "Yes, cancel booking" }).click()

        await expect(page.getByText("Your booking has been cancelled.")).toBeVisible()
        await expect(page.getByRole("heading", { name: "This booking is cancelled" })).toBeVisible()
    })

    test("pays for a booking (demo)", async ({ page }) => {
        const api = await installFakeApi(page)
        const booking = api.seedBooking({ slotId: "slot_1", name: "Chidi Okafor", email: "chidi@example.test" })
        await page.goto(`/booking/${booking.id}`)

        await page.getByRole("button", { name: "Pay now (demo)" }).click()

        await expect(page.getByText("Payment recorded.")).toBeVisible()
        await expect(page.getByText("DEMO-1A2B3C4D5E")).toBeVisible()
    })

    test("finds a booking by its ID", async ({ page }) => {
        const api = await installFakeApi(page)
        const booking = api.seedBooking({ slotId: "slot_3", name: "Ngozi Eze", email: "ngozi@example.test" })
        await page.goto("/find")

        await page.getByLabel("Booking ID").fill(booking.id)
        await page.getByRole("button", { name: "Find booking" }).click()

        await expect(page).toHaveURL(new RegExp(`/booking/${booking.id}$`))
        await expect(page.getByRole("heading", { name: "Your booking is confirmed" })).toBeVisible()
    })

    test("finds your booking IDs by email", async ({ page }) => {
        const api = await installFakeApi(page)
        const booking = api.seedBooking({ slotId: "slot_2", name: "Ngozi Eze", email: "ngozi@example.test" })
        await page.goto("/find")

        await page.getByLabel("Email used to book").fill("Ngozi@Example.test")
        await page.getByRole("button", { name: "Find my bookings" }).click()

        await expect(page.getByRole("link", { name: booking.id })).toBeVisible()
        await page.getByRole("link", { name: booking.id }).click()
        await expect(page.getByRole("heading", { name: "Your booking is confirmed" })).toBeVisible()
    })

    test("says so when an email has no bookings", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/find")

        await page.getByLabel("Email used to book").fill("nobody@example.test")
        await page.getByRole("button", { name: "Find my bookings" }).click()

        await expect(page.getByText("No bookings found for nobody@example.test.")).toBeVisible()
    })

    test("says so when a booking ID does not exist", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/booking/bk_missing")

        await expect(page.getByText("Booking not found")).toBeVisible()
    })

    test("never scrolls sideways", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/")
        await expect(page.getByRole("heading", { name: "Book an appointment", level: 1 })).toBeVisible()

        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
        expect(overflow).toBeLessThanOrEqual(0)
    })
})