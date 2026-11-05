export const routes = {
    book: "/",
    find: "/find",
    dashboard: "/dashboard",
    booking: (id: string) => `/booking/${encodeURIComponent(id)}`,
} as const