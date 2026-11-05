import { describe, expect, it } from "vitest"
import type { Slot } from "@/models"
import { groupByDay } from "./slots"

function slot(id: string, start: string, available = true): Slot {
    return { id, provider: "Dr Ade", start, end: start, available }
}

describe("groupByDay", () => {
    it("groups by clinic day, earliest day and time first", () => {
        const days = groupByDay([
            slot("c", "2026-12-11T09:00:00Z"),
            slot("b", "2026-12-10T10:00:00Z"),
            slot("a", "2026-12-10T09:00:00Z"),
        ])
        expect(days.map((d) => d.key)).toEqual(["2026-12-10", "2026-12-11"])
        expect(days[0].slots.map((s) => s.id)).toEqual(["a", "b"])
    })

    it("counts the free slots", () => {
        const [day] = groupByDay([
            slot("a", "2026-12-10T09:00:00Z"),
            slot("b", "2026-12-10T10:00:00Z", false),
        ])
        expect(day.freeCount).toBe(1)
    })

    it("uses the clinic's calendar day, not UTC (23:30 UTC is already tomorrow in Lagos)", () => {
        const [day] = groupByDay([slot("late", "2026-12-10T23:30:00Z")])
        expect(day.key).toBe("2026-12-11")
    })

    it("returns nothing for no slots", () => {
        expect(groupByDay([])).toEqual([])
    })
})