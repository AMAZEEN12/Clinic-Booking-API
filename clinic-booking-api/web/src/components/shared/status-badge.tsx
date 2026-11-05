import type { BookingStatus } from "@/models"
import { StatusBadge as UiStatusBadge, type StatusBadgeTone } from "@/components/ui/status-badge"

const LABELS: Record<BookingStatus, string> = {
    confirmed: "Confirmed",
    cancelled: "Cancelled",
}

const TONES: Record<BookingStatus, StatusBadgeTone> = {
    confirmed: "success",
    cancelled: "neutral",
}

// The status is always written out; colour and the dot are extras.
export function StatusBadge({ status }: { status: BookingStatus }) {
    return (
        <UiStatusBadge tone={TONES[status]} className="rounded-full px-3 py-1 text-sm">
            <span aria-hidden="true" className="mr-1.5 inline-block size-1.5 rounded-full bg-current" />
            {LABELS[status]}
        </UiStatusBadge>
    )
}