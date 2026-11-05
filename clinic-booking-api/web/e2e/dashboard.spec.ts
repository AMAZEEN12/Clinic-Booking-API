import { expect, test } from "@playwright/test"
import { installFakeApi } from "./fakeApi"

test.describe("clinic dashboard", () => {
    test("shows the day's counts and masked patient names", async ({ page }) => {
        const api = await installFakeApi(page)
        api.seedBooking({ slotId: "slot_1", name: "Chidi Okafor", email: "chidi@example.test" })
        api.seedBooking({ slotId: "slot_3", name: "Ngozi Eze", email: "ngozi@example.test", status: "cancelled" })
        await page.goto("/dashboard")

        await expect(page.getByText("Chidi O.")).toBeVisible()
        await expect(page.getByText("Ngozi E.")).toBeVisible()

        await expect(page.locator("dl > div").filter({ hasText: "Booked" })).toHaveText(/^Booked\s*1$/)
        await expect(page.locator("dl > div").filter({ hasText: "Cancelled" })).toHaveText(/^Cancelled\s*1$/)
        await expect(page.locator("dl > div").filter({ hasText: "Open slots" })).toHaveText(/^Open slots\s*2$/)
    })

    test("never shows an email or a full name (N10)", async ({ page }) => {
        const api = await installFakeApi(page)
        api.seedBooking({ slotId: "slot_1", name: "Chidi Okafor", email: "chidi@example.test" })
        await page.goto("/dashboard")
        await expect(page.getByText("Chidi O.")).toBeVisible()

        await expect(page.locator("body")).not.toContainText("@")
        await expect(page.locator("body")).not.toContainText("Okafor")
    })

    test("shows an empty state for a day with no appointments", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/dashboard")

        await page.getByLabel("Day").fill("2000-01-01")

        await expect(page.getByText("No appointments on this day")).toBeVisible()
    })

    test("is reachable from the menu", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/")

        await page.getByRole("link", { name: "Dashboard" }).click()

        await expect(page).toHaveURL(/\/dashboard$/)
        await expect(page.getByRole("heading", { name: "Appointments", level: 1 })).toBeVisible()
    })

    test("never scrolls sideways", async ({ page }) => {
        const api = await installFakeApi(page)
        api.seedBooking({ slotId: "slot_1", name: "Chidi Okafor", email: "chidi@example.test" })
        await page.goto("/dashboard")
        await expect(page.getByText("Chidi O.")).toBeVisible()

        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
        expect(overflow).toBeLessThanOrEqual(0)
    })
})