import { describe, expect, it } from "vitest"
import { validateDetails } from "./validation"

describe("validateDetails", () => {
    it("accepts a normal name and email", () => {
        expect(validateDetails("Ada Obi", "ada@example.com")).toEqual({})
    })

    it("accepts the lenient addresses the API accepts (.test domain)", () => {
        expect(validateDetails("Ada", "ada@clinic.test")).toEqual({})
    })

    it("asks for a name and an email when blank", () => {
        const errors = validateDetails("   ", "")
        expect(errors.name).toBe("Enter your name.")
        expect(errors.email).toBe("Enter your email.")
    })

    it("rejects an email without a dot or an at sign", () => {
        expect(validateDetails("Ada", "ada@example").email).toBeDefined()
        expect(validateDetails("Ada", "ada.example.com").email).toBeDefined()
        expect(validateDetails("Ada", "a da@example.com").email).toBeDefined()
    })

    it("applies the same limits as the API", () => {
        expect(validateDetails("x".repeat(201), "a@b.c").name).toBeDefined()
        expect(validateDetails("x".repeat(200), "a@b.c").name).toBeUndefined()
        expect(validateDetails("Ada", `${"x".repeat(251)}@b.c`).email).toBeDefined()
        expect(validateDetails("Ada", `${"x".repeat(250)}@b.c`).email).toBeUndefined()
    })

    it("ignores spaces around the values", () => {
        expect(validateDetails("  Ada  ", "  ada@example.com  ")).toEqual({})
    })
})