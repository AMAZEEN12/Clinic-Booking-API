import { describe, expect, it } from "vitest"
import { buildMonth, monthLabel, monthOf } from "./calendar"

describe("monthOf and monthLabel", () => {
    it("cuts the month out of a day", () => {
        expect(monthOf("2026-12-10")).toBe("2026-12")
    })

    it("writes the month in words", () => {
        expect(monthLabel("2026-12")).toBe("December 2026")
    })
})

describe("buildMonth", () => {
    it("starts weeks on Monday (1 December 2026 is a Tuesday)", () => {
        const weeks = buildMonth("2026-12")
        expect(weeks).toHaveLength(5)
        expect(weeks[0][0]).toBeNull()
        expect(weeks[0][1]).toEqual({ key: "2026-12-01", day: 1 })
        expect(weeks[4][3]).toEqual({ key: "2026-12-31", day: 31 })
        expect(weeks[4][4]).toBeNull()
    })

    it("has no empty cells when a month fits four whole weeks (February 2027)", () => {
        const weeks = buildMonth("2027-02")
        expect(weeks).toHaveLength(4)
        expect(weeks.flat().every((cell) => cell !== null)).toBe(true)
    })

    it("always gives rows of seven", () => {
        for (const month of ["2026-11", "2026-12", "2027-01", "2027-02", "2027-03"]) {
            expect(buildMonth(month).every((week) => week.length === 7)).toBe(true)
        }
    })
})