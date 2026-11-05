import type { Slot } from "@/models"
import { cn } from "@/lib/cn"
import { formatClinicTime } from "@/utils/clinicTime"

type Props = {
    slots: readonly Slot[]
    selectedId: string | null
    onSelect: (slotId: string) => void
}

/** The times of one day. A taken time is disabled AND says "Taken" in words, never colour alone. */
export function TimeGrid({ slots, selectedId, onSelect }: Props) {
    return (
        <div role="group" aria-label="Choose a time" className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            {slots.map((slot) => {
                const selected = slot.id === selectedId
                return (
                    <button
                        key={slot.id}
                        type="button"
                        disabled={!slot.available}
                        aria-pressed={slot.available ? selected : undefined}
                        onClick={() => onSelect(slot.id)}
                        className={cn(
                            "cf-press flex min-h-14 min-w-0 flex-col items-center justify-center rounded-[var(--radius-lg)] border px-2 py-2",
                            "disabled:cursor-not-allowed disabled:border-dashed disabled:border-[var(--color-border)] disabled:bg-[var(--soft)] disabled:text-[var(--color-text-muted)]",
                            selected
                                ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-on-primary)]"
                                : "border-[var(--color-border-input)] bg-[var(--color-surface)] text-[var(--color-text)] enabled:hover:bg-[var(--soft)]",
                        )}
                    >
                        <span className={cn("font-mono text-base font-medium", !slot.available && "line-through")}>
                            {formatClinicTime(slot.start)}
                        </span>
                        <span className="max-w-full truncate text-xs" title={slot.available ? slot.provider : undefined}>
                            {slot.available ? slot.provider : "Taken"}
                        </span>
                    </button>
                )
            })}
        </div>
    )
}