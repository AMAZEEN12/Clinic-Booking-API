import { defineConfig, devices } from "@playwright/test"

const PORT = 4173
const BASE_URL = `http://localhost:${PORT}`

// The page talks to a fake API served from the same origin (see e2e/fakeApi.ts), so no real
// API, database or CORS setup is needed. Keep VITE_API_KEY equal to API_KEY in e2e/fakeApi.ts.
export default defineConfig({
    testDir: "./e2e",
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 1 : 0,
    reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
    use: { baseURL: BASE_URL, trace: "retain-on-failure" },
    projects: [
        { name: "phone", use: { ...devices["Pixel 5"], viewport: { width: 390, height: 844 } } },
        { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
    ],
    webServer: {
        command: `pnpm exec vite --port ${PORT} --strictPort`,
        url: BASE_URL,
        reuseExistingServer: false,
        env: { VITE_API_BASE_URL: `${BASE_URL}/api-mock`, VITE_API_KEY: "e2e-test-key" },
    },
})