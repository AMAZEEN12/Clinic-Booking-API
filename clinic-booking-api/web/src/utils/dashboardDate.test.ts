import { describe, expect, it } from "vitest"
import { formatDayHeading, isDayKey, todayUtcKey } from "./dashboardDate"

describe("todayUtcKey", () => {
    it("uses the UTC date, not the local one", () => {
        expect(todayUtcKey(new Date("2026-12-10T23:30:00Z"))).toBe("2026-12-10")
        expect(todayUtcKey(new Date("2026-12-11T00:00:00Z"))).toBe("2026-12-11")
    })
})

describe("isDayKey", () => {
    it("accepts a real day", () => {
        expect(isDayKey("2026-12-10")).toBe(true)
        expect(isDayKey("2028-02-29")).toBe(true)
    })

    it("rejects other shapes and days that do not exist", () => {
        for (const value of ["", "2026-13-01", "2026-02-30", "2027-02-29", "10-12-2026", "20261210", "2026-12-10T00:00:00Z"]) {
            expect(isDayKey(value)).toBe(false)
        }
    })
})

describe("formatDayHeading", () => {
    it("writes the day out in words", () => {
        expect(formatDayHeading("2026-12-10")).toBe("Thu 10 Dec 2026")
    })
})