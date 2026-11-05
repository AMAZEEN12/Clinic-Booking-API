// Read at build time. Anything prefixed VITE_ ends up in the public JavaScript bundle.
const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "http://localhost:8000"
const rawApiKey = (import.meta.env.VITE_API_KEY as string | undefined) || ""

export const env = {
    apiBaseUrl: rawBaseUrl.trim().replace(/\/+$/, ""),
    apiKey: rawApiKey.trim(),
} as const