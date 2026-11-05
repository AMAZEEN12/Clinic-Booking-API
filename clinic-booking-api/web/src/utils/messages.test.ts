import { describe, expect, it } from "vitest"
import { ApiError } from "@/services/api"
import { describeError } from "./messages"

describe("describeError", () => {
    it("tells the patient a taken time is gone", () => {
        expect(describeError(new ApiError("conflict", 409, "x"), "book")).toMatch(/just taken/)
    })

    it("includes the wait time for rate limits", () => {
        expect(describeError(new ApiError("rate_limited", 429, "x", 6), "book")).toMatch(/6 seconds/)
    })

    it("says which booking was not found", () => {
        expect(describeError(new ApiError("not_found", 404, "x"), "lookup")).toMatch(/booking with that ID/)
    })

    it("never shows the server's own message", () => {
        const message = describeError(new ApiError("server", 500, "psycopg.errors.Boom: secret detail"), "load")
        expect(message).not.toMatch(/psycopg|secret|Boom/)
    })

    it("has a safe answer for unknown errors", () => {
        expect(describeError(new Error("oops"), "load")).toMatch(/Something went wrong/)
    })
})