import { cn } from "@/lib/cn"
import { formatDayChip } from "@/utils/clinicTime"
import type { DayGroup } from "@/utils/slots"

type Props = {
    days: readonly DayGroup[]
    selectedKey: string
    onSelect: (key: string) => void
}

/** One chip per day. They wrap onto more lines instead of scrolling sideways. */
export function DayChips({ days, selectedKey, onSelect }: Props) {
    return (
        <div role="group" aria-label="Choose a day" className="flex flex-wrap gap-2">
            {days.map((day) => {
                const { weekday, dayMonth } = formatDayChip(day.key)
                const selected = day.key === selectedKey
                return (
                    <button
                        key={day.key}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => onSelect(day.key)}
                        className={cn(
                            "cf-press flex min-h-14 min-w-[5.5rem] flex-col items-center justify-center rounded-[var(--radius-lg)] border px-3 py-2 text-center",
                            selected
                                ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-on-primary)]"
                                : "border-[var(--color-border-input)] bg-[var(--color-surface)] text-[var(--color-text)] hover:bg-[var(--soft)]",
                        )}
                    >
                        <span className="text-sm font-medium">{weekday}</span>
                        <span className="font-heading text-base font-bold">{dayMonth}</span>
                        <span className="text-xs">{day.freeCount > 0 ? `${day.freeCount} free` : "Full"}</span>
                    </button>
                )
            })}
        </div>
    )
}