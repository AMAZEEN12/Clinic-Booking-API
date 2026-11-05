import { useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/cn"
import { buildMonth, monthLabel, monthOf } from "@/utils/calendar"
import { formatDayChip } from "@/utils/clinicTime"
import type { DayGroup } from "@/utils/slots"

type Props = {
    days: readonly DayGroup[]
    selectedKey: string
    onSelect: (key: string) => void
}

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

/**
 * A month calendar. Days with free times can be chosen; days with no times, or fully booked,
 * are disabled (a full day also says "Full" in words). The arrows only visit months that have slots.
 */
export function DayCalendar({ days, selectedKey, onSelect }: Props) {
    const byKey = new Map(days.map((day) => [day.key, day]))
    const months = [...new Set(days.map((day) => monthOf(day.key)))]

    const [shown, setShown] = useState(monthOf(selectedKey))
    const month = months.includes(shown) ? shown : monthOf(selectedKey)
    const index = months.indexOf(month)
    const previous = months[index - 1]
    const next = months[index + 1]

    return (
        <div role="group" aria-label="Choose a day" className="space-y-3">
            <div className="flex items-center justify-between gap-2">
                <Button
                    variant="secondary"
                    iconOnly
                    aria-label="Previous month"
                    disabled={!previous}
                    onClick={() => setShown(previous)}
                >
                    <ChevronLeft aria-hidden="true" className="size-5" />
                </Button>
                <p aria-live="polite" className="font-heading text-lg font-bold">
                    {monthLabel(month)}
                </p>
                <Button
                    variant="secondary"
                    iconOnly
                    aria-label="Next month"
                    disabled={!next}
                    onClick={() => setShown(next)}
                >
                    <ChevronRight aria-hidden="true" className="size-5" />
                </Button>
            </div>

            <div aria-hidden="true" className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-[var(--color-text-muted)]">
                {WEEKDAYS.map((name) => (
                    <span key={name}>{name}</span>
                ))}
            </div>

            <div className="space-y-1">
                {buildMonth(month).map((week, weekIndex) => (
                    <div key={weekIndex} className="grid grid-cols-7 gap-1">
                        {week.map((cell, cellIndex) => {
                            if (!cell) return <span key={cellIndex} />

                            const day = byKey.get(cell.key)
                            const free = day?.freeCount ?? 0
                            const selected = cell.key === selectedKey
                            const { weekday, dayMonth } = formatDayChip(cell.key)
                            const label = !day
                                ? `${weekday} ${dayMonth}, no times`
                                : free === 0
                                    ? `${weekday} ${dayMonth}, fully booked`
                                    : `${weekday} ${dayMonth}, ${free} ${free === 1 ? "time" : "times"} free`

                            return (
                                <button
                                    key={cell.key}
                                    type="button"
                                    disabled={free === 0}
                                    aria-pressed={free > 0 ? selected : undefined}
                                    aria-label={label}
                                    onClick={() => onSelect(cell.key)}
                                    className={cn(
                                        "cf-press flex min-h-14 min-w-0 flex-col items-center justify-center rounded-[var(--radius-lg)] border px-1 py-1 text-center",
                                        "disabled:cursor-not-allowed disabled:text-[var(--color-text-muted)]",
                                        day
                                            ? "disabled:border-dashed disabled:border-[var(--color-border)] disabled:bg-[var(--soft)]"
                                            : "disabled:border-transparent disabled:bg-transparent",
                                        selected
                                            ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-on-primary)]"
                                            : "border-[var(--color-border-input)] bg-[var(--color-surface)] text-[var(--color-text)] enabled:hover:bg-[var(--soft)]",
                                    )}
                                >
                                    <span className="font-heading text-base font-bold">{cell.day}</span>
                                    <span aria-hidden="true" className="text-xs">
                                        {day ? (free > 0 ? `${free} free` : "Full") : "\u00a0"}
                                    </span>
                                </button>
                            )
                        })}
                    </div>
                ))}
            </div>
        </div>
    )
}