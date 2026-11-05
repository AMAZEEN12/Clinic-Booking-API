/** A fresh random key for the Idempotency-Key header (one per booking attempt). */
export function newIdempotencyKey(): string {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return crypto.randomUUID()
    }
    return `key-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
}