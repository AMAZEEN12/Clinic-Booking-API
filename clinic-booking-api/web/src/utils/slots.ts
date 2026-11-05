import type { Slot } from "@/models"
import { clinicDateKey } from "./clinicTime"

export type DayGroup = {
    /** YYYY-MM-DD in clinic time. */
    key: string
    /** Earliest first. */
    slots: Slot[]
    freeCount: number
}

/** Groups slots by clinic day, days earliest first. Day chips and the time grid are built from this. */
export function groupByDay(slots: readonly Slot[]): DayGroup[] {
    const byDay = new Map<string, Slot[]>()
    for (const slot of slots) {
        const key = clinicDateKey(slot.start)
        const list = byDay.get(key)
        if (list) list.push(slot)
        else byDay.set(key, [slot])
    }

    return [...byDay.keys()].sort().map((key) => {
        const daySlots = [...(byDay.get(key) ?? [])].sort((a, b) => Date.parse(a.start) - Date.parse(b.start))
        return { key, slots: daySlots, freeCount: daySlots.filter((s) => s.available).length }
    })
}