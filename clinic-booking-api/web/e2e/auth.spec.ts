import { expect, test, type Page } from "@playwright/test"
import { ACCOUNTS, installFakeApi, type Role } from "./fakeApi"

async function signIn(page: Page, role: Role, password = ACCOUNTS[role].password) {
    await page.getByLabel("Email").fill(ACCOUNTS[role].email)
    await page.getByLabel("Password").fill(password)
    await page.getByRole("button", { name: "Sign in" }).click()
}

const dashboardHeading = (page: Page) => page.getByRole("heading", { name: "Appointments", level: 1 })
const bookingHeading = (page: Page) => page.getByRole("heading", { name: "Book an appointment", level: 1 })

test.describe("signed out", () => {
    test("every screen sends you to the sign-in page", async ({ page }) => {
        await installFakeApi(page)
        for (const path of ["/", "/find", "/booking/bk_1", "/dashboard"]) {
            await page.goto(path)
            await expect(page).toHaveURL(/\/login$/)
            await expect(page.getByRole("heading", { name: "Sign in", level: 1 })).toBeVisible()
        }
    })

    test("shows no navigation links", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/login")

        await expect(page.getByRole("navigation", { name: "Main" })).toHaveCount(0)
    })

    test("asks for both fields", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/login")
        await page.getByRole("button", { name: "Sign in" }).click()

        await expect(page.getByText("Enter your email.")).toBeVisible()
        await expect(page.getByText("Enter your password.")).toBeVisible()
    })

    test("a wrong password shows a message and stays on the page", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/login")
        await signIn(page, "staff", "not-the-password")

        await expect(page.getByRole("alert")).toHaveText(/Wrong email or password/)
        await expect(page).toHaveURL(/\/login$/)
    })
})

test.describe("staff", () => {
    test("sign in and land on the dashboard, with no booking links", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/login")
        await signIn(page, "staff")

        await expect(page).toHaveURL(/\/dashboard$/)
        await expect(dashboardHeading(page)).toBeVisible()
        const nav = page.getByRole("navigation", { name: "Main" })
        await expect(nav.getByRole("link", { name: "Dashboard" })).toBeVisible()
        await expect(nav.getByRole("link", { name: "Book" })).toHaveCount(0)
        await expect(nav.getByRole("link", { name: "Find a booking" })).toHaveCount(0)
    })

    test("are sent back to the dashboard from the patient screens", async ({ page }) => {
        await installFakeApi(page, { signedInAs: "staff" })
        for (const path of ["/", "/find"]) {
            await page.goto(path)
            await expect(page).toHaveURL(/\/dashboard$/)
        }
    })
})

test.describe("patients", () => {
    test("sign in and land on booking, with no dashboard link", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/login")
        await signIn(page, "patient")

        await expect(page).toHaveURL(/\/$/)
        await expect(bookingHeading(page)).toBeVisible()
        const nav = page.getByRole("navigation", { name: "Main" })
        await expect(nav.getByRole("link", { name: "Find a booking" })).toBeVisible()
        await expect(nav.getByRole("link", { name: "Dashboard" })).toHaveCount(0)
    })

    test("typing the dashboard address does not show the dashboard", async ({ page }) => {
        const api = await installFakeApi(page, { signedInAs: "patient" })
        api.seedBooking({ slotId: "slot_1", name: "Chidi Okafor", email: "chidi@example.test" })
        await page.goto("/dashboard")

        await expect(page).toHaveURL(/\/$/)
        await expect(bookingHeading(page)).toBeVisible()
        await expect(dashboardHeading(page)).toHaveCount(0)
        await expect(page.locator("body")).not.toContainText("Chidi O.")
    })
})

test.describe("sign out", () => {
    test("ends the session and locks the screens again", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/login")
        await signIn(page, "staff")
        await expect(dashboardHeading(page)).toBeVisible()

        await page.getByRole("button", { name: "Sign out" }).click()
        await expect(page).toHaveURL(/\/login$/)

        await page.goto("/dashboard")
        await expect(page).toHaveURL(/\/login$/)
    })

    test("staying signed in survives a refresh", async ({ page }) => {
        await installFakeApi(page)
        await page.goto("/login")
        await signIn(page, "patient")
        await expect(bookingHeading(page)).toBeVisible()

        await page.reload()

        await expect(bookingHeading(page)).toBeVisible()
    })
})
