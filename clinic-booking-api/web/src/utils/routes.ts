export const routes = {
    book: "/",
    find: "/find",
    booking: (id: string) => `/booking/${encodeURIComponent(id)}`,
} as const