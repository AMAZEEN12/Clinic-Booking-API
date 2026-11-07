import { describe, expect, it } from "vitest"
import type { Slot } from "@/models"
import { groupByDay, upcomingSlots } from "./slots"

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

describe("upcomingSlots", () => {
    const now = Date.parse("2026-12-10T10:00:00Z")

    it("drops slots that have already started, even when the API lists them as free", () => {
        const kept = upcomingSlots(
            [
                slot("past-day", "2026-12-09T09:00:00Z"),
                slot("earlier-today", "2026-12-10T09:00:00Z"),
                slot("starting-now", "2026-12-10T10:00:00Z"),
                slot("later-today", "2026-12-10T11:00:00Z"),
                slot("tomorrow", "2026-12-11T09:00:00Z"),
            ],
            now,
        )
        expect(kept.map((s) => s.id)).toEqual(["later-today", "tomorrow"])
    })

    it("returns nothing when every slot is in the past", () => {
        expect(upcomingSlots([slot("old", "2026-01-01T09:00:00Z")], now)).toEqual([])
    })
})