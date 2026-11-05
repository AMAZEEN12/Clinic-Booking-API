import type { Slot } from "@/models"
import { CLINIC_TZ_LABEL, formatClinicDate, formatClinicTime } from "@/utils/clinicTime"

/** Who, when and where for one slot. Shows a hint while nothing is chosen. */
export function AppointmentSummary({ slot }: { slot: Slot | null }) {
    if (!slot) {
        return <p className="text-[var(--color-text-muted)]">Choose a day and a time to see your appointment here.</p>
    }

    return (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
            <dt className="text-[var(--color-text-muted)]">Date</dt>
            <dd className="font-medium">{formatClinicDate(slot.start)}</dd>
            <dt className="text-[var(--color-text-muted)]">Time</dt>
            <dd className="font-medium">
                {formatClinicTime(slot.start)} to {formatClinicTime(slot.end)}
                <span className="block text-sm font-normal text-[var(--color-text-muted)]">{CLINIC_TZ_LABEL}</span>
            </dd>
            <dt className="text-[var(--color-text-muted)]">With</dt>
            <dd className="font-medium">{slot.provider}</dd>
        </dl>
    )
}