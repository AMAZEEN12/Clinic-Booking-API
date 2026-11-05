import type { PaymentStatus } from "@/models"
import { StatusBadge as UiStatusBadge, type StatusBadgeTone } from "@/components/ui/status-badge"

// The word "demo" is part of the label so nobody reads it as a real payment.
const LABELS: Record<PaymentStatus, string> = {
    paid: "Paid (demo)",
    unpaid: "Not paid",
}

const TONES: Record<PaymentStatus, StatusBadgeTone> = {
    paid: "success",
    unpaid: "neutral",
}

// The status is always written out; colour and the dot are extras.
export function PaymentBadge({ status }: { status: PaymentStatus }) {
    return (
        <UiStatusBadge tone={TONES[status]} className="rounded-full px-3 py-1 text-sm">
            <span aria-hidden="true" className="mr-1.5 inline-block size-1.5 rounded-full bg-current" />
            {LABELS[status]}
        </UiStatusBadge>
    )
}