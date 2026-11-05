import { describe, expect, it } from "vitest"
import { clinicDateKey, formatClinicDate, formatClinicTime, formatDayChip } from "./clinicTime"

describe("clinic time (Lagos, UTC+1)", () => {
    it("shows the time one hour after UTC", () => {
        expect(formatClinicTime("2026-12-10T09:00:00Z")).toBe("10:00")
    })

    it("rolls the date over at midnight Lagos time", () => {
        expect(clinicDateKey("2026-12-10T22:59:00Z")).toBe("2026-12-10")
        expect(clinicDateKey("2026-12-10T23:00:00Z")).toBe("2026-12-11")
    })

    it("writes a readable date", () => {
        expect(formatClinicDate("2026-12-10T09:00:00Z")).toBe("Thu 10 Dec 2026")
    })

    it("builds day chip labels from a date key", () => {
        expect(formatDayChip("2026-12-10")).toEqual({ weekday: "Thu", dayMonth: "10 Dec" })
    })
})