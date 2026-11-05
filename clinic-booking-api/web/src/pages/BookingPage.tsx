import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import { AppointmentSummary } from "@/components/booking/AppointmentSummary"
import { PaymentBadge } from "@/components/shared/payment-badge"
import { StatusBadge } from "@/components/shared/status-badge"
import { Button } from "@/components/ui/button"
import { ErrorState } from "@/components/ui/error-state"
import { Panel } from "@/components/ui/panel"
import { useAsync } from "@/hooks/useAsync"
import { usePageTitle } from "@/hooks/usePageTitle"
import { ApiError, cancelBooking, getBooking, getPayment, getSlots, payForBooking } from "@/services/api"
import { describeError } from "@/utils/messages"
import { routes } from "@/utils/routes"

/** One booking: the confirmation after booking, the result of a lookup, and the cancel button. */
export function BookingPage() {
    const { id = "" } = useParams()
    const booking = useAsync(() => getBooking(id), `booking:${id}`)
    const slots = useAsync(getSlots, "slots")
    const payment = useAsync(() => getPayment(id), `payment:${id}`)

    const [confirmingCancel, setConfirmingCancel] = useState(false)
    const [cancelling, setCancelling] = useState(false)
    const [cancelError, setCancelError] = useState<string | null>(null)
    const [cancelledNow, setCancelledNow] = useState(false)
    const [paying, setPaying] = useState(false)
    const [payError, setPayError] = useState<string | null>(null)
    const [paidNow, setPaidNow] = useState(false)

    const data = booking.state.status === "ready" ? booking.state.data : null
    usePageTitle(data?.status === "cancelled" ? "Booking cancelled" : "Your booking")

    async function handleCancel() {
        setCancelling(true)
        setCancelError(null)
        try {
            booking.setData(await cancelBooking(id))
            setCancelledNow(true)
            setConfirmingCancel(false)
        } catch (error) {
            setCancelError(describeError(error, "cancel"))
        } finally {
            setCancelling(false)
        }
    }

    async function handlePay() {
        setPaying(true)
        setPayError(null)
        try {
            payment.setData(await payForBooking(id))
            setPaidNow(true)
        } catch (error) {
            setPayError(describeError(error, "pay"))
            // A conflict means the booking was cancelled somewhere else: show it as it is now.
            if (error instanceof ApiError && error.kind === "conflict") booking.refresh()
        } finally {
            setPaying(false)
        }
    }

    if (booking.state.status === "loading") {
        return (
            <Panel role="status" aria-busy="true" className="space-y-3">
                <span className="sr-only">Loading your booking…</span>
                <div aria-hidden="true" className="cf-skel h-8 w-48 rounded-[var(--radius-md)]" />
                <div aria-hidden="true" className="cf-skel h-24 rounded-[var(--radius-lg)]" />
            </Panel>
        )
    }

    if (booking.state.status === "error") {
        const notFound = booking.state.error instanceof ApiError && booking.state.error.kind === "not_found"
        return (
            <Panel>
                <ErrorState
                    title={notFound ? "Booking not found" : "We couldn't load your booking"}
                    description={describeError(booking.state.error, "lookup")}
                    onRetry={notFound ? undefined : booking.reload}
                />
                <p className="pb-4 text-center">
                    <Link to={routes.find} className="font-medium underline">
                        Try another booking ID
                    </Link>
                </p>
            </Panel>
        )
    }

    const current = booking.state.data
    const slot =
        slots.state.status === "ready" ? (slots.state.data.find((s) => s.id === current.slot_id) ?? null) : null
    const confirmed = current.status === "confirmed"
    const paid = payment.state.status === "ready" && payment.state.data.status === "paid"

    return (
        <div className="mx-auto max-w-2xl space-y-6">
            <div className="space-y-2">
                <h1 className="font-heading text-3xl font-extrabold sm:text-4xl">
                    {confirmed ? "Your booking is confirmed" : "This booking is cancelled"}
                </h1>
                <StatusBadge status={current.status} />
            </div>

            {/* Announced to screen readers when the cancel or the payment finishes. */}
            <div role="status">
                {paidNow && (
                    <p className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 font-medium">
                        Payment recorded. This is a demo: no real money was taken.
                    </p>
                )}
                {cancelledNow && (
                    <p className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 font-medium">
                        Your booking has been cancelled. The time is free for other patients.
                    </p>
                )}
            </div>

            <Panel className="space-y-4">
                <h2 className="font-heading text-xl font-bold">Appointment</h2>
                {slot ? (
                    <AppointmentSummary slot={slot} />
                ) : (
                    <p className="text-[var(--color-text-muted)]">
                        {slots.state.status === "loading"
                            ? "Loading appointment details…"
                            : "The appointment details are not available right now."}
                    </p>
                )}
            </Panel>

            <Panel className="space-y-4">
                <h2 className="font-heading text-xl font-bold">Booking details</h2>
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
                    <dt className="text-[var(--color-text-muted)]">Booking ID</dt>
                    <dd className="break-all font-mono font-medium">{current.id}</dd>
                    <dt className="text-[var(--color-text-muted)]">Name</dt>
                    <dd className="break-words font-medium">{current.name}</dd>
                    <dt className="text-[var(--color-text-muted)]">Email</dt>
                    <dd className="break-all font-medium">{current.email}</dd>
                </dl>
                {confirmed && (
                    <p className="text-sm text-[var(--color-text-muted)]">
                        Keep your booking ID. You need it to look up or cancel this booking.
                    </p>
                )}
            </Panel>

            {(confirmed || paid) && (
                <Panel className="space-y-4">
                    <h2 className="font-heading text-xl font-bold">Payment</h2>
                    {payment.state.status === "loading" && (
                        <p role="status" className="text-[var(--color-text-muted)]">
                            Checking payment…
                        </p>
                    )}
                    {payment.state.status === "error" && (
                        <>
                            <p className="text-[var(--color-text-muted)]">We couldn't check the payment status.</p>
                            <Button variant="secondary" onClick={payment.reload}>
                                Try again
                            </Button>
                        </>
                    )}
                    {payment.state.status === "ready" && payment.state.data.status === "paid" && (
                        <div className="space-y-2">
                            <PaymentBadge status="paid" />
                            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
                                <dt className="text-[var(--color-text-muted)]">Reference</dt>
                                <dd className="break-all font-mono font-medium">{payment.state.data.reference}</dd>
                            </dl>
                        </div>
                    )}
                    {payment.state.status === "ready" && payment.state.data.status === "unpaid" && confirmed && (
                        <>
                            <p className="text-[var(--color-text-muted)]">
                                This is a demo. No real money is taken and you don't enter any card details.
                            </p>
                            <Button loading={paying} onClick={handlePay}>
                                Pay now (demo)
                            </Button>
                        </>
                    )}
                    {payError && (
                        <p role="alert" className="text-sm font-medium text-[var(--color-danger)]">
                            <span aria-hidden="true">! </span>
                            {payError}
                        </p>
                    )}
                </Panel>
            )}

            {confirmed && (
                <Panel className="space-y-4">
                    {confirmingCancel ? (
                        <>
                            <h2 className="font-heading text-xl font-bold">Cancel this appointment?</h2>
                            <p className="text-[var(--color-text-muted)]">
                                Your time will be given to someone else. This can't be undone.
                            </p>
                            <div className="flex flex-wrap gap-2">
                                <Button variant="danger" loading={cancelling} onClick={handleCancel}>
                                    Yes, cancel booking
                                </Button>
                                <Button variant="secondary" onClick={() => setConfirmingCancel(false)}>
                                    Keep my booking
                                </Button>
                            </div>
                        </>
                    ) : (
                        <Button variant="secondary" onClick={() => setConfirmingCancel(true)}>
                            Cancel booking
                        </Button>
                    )}
                    {cancelError && (
                        <p role="alert" className="text-sm font-medium text-[var(--color-danger)]">
                            <span aria-hidden="true">! </span>
                            {cancelError}
                        </p>
                    )}
                </Panel>
            )}

            <p>
                <Link to={routes.book} className="font-medium underline">
                    {confirmed ? "Book another time" : "Book a new time"}
                </Link>
            </p>
        </div>
    )
}