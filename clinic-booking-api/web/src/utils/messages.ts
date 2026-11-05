// Turns a failure into words a patient can act on. Raw codes and server messages never reach the screen.

import { ApiError } from "@/services/api"

export type Action = "load" | "book" | "lookup" | "cancel" | "pay"

export function describeError(error: unknown, action: Action): string {
    if (!(error instanceof ApiError)) return "Something went wrong. Please try again."

    switch (error.kind) {
        case "network":
            return "We couldn't reach the booking service. Check your connection and try again. If the service was asleep, it can take a minute to wake up."
        case "unauthorized":
            return "The booking service isn't set up correctly. Please tell the clinic."
        case "rate_limited":
            return error.retryAfterSeconds
                ? `Too many attempts. Please wait ${error.retryAfterSeconds} seconds and try again.`
                : "Too many attempts. Please wait a moment and try again."
        case "not_found":
            return action === "lookup" || action === "cancel" || action === "pay"
                ? "We couldn't find a booking with that ID. Check it and try again."
                : "We couldn't find what you were looking for."
        case "conflict":
            if (action === "book") return "That time was just taken. Please choose another time."
            if (action === "pay") return "This booking has been cancelled, so it can't be paid."
            if (action === "cancel") return "This booking was already cancelled."
            return "That booking can't be changed any more."
        case "invalid":
            return "Please check your details and try again."
        default:
            return "Something went wrong on our side. Please try again in a moment."
    }
}