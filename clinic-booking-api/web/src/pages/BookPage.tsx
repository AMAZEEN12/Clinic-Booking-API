import { useRef, useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { AppointmentSummary } from "@/components/booking/AppointmentSummary"
import { DayCalendar } from "@/components/booking/DayCalendar"
import { SlotsSkeleton } from "@/components/booking/SlotsSkeleton"
import { TimeGrid } from "@/components/booking/TimeGrid"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { FormField } from "@/components/ui/form-field"
import { Input } from "@/components/ui/input"
import { Panel } from "@/components/ui/panel"
import { useAsync } from "@/hooks/useAsync"
import { usePageTitle } from "@/hooks/usePageTitle"
import { ApiError, createBooking, getSlots } from "@/services/api"
import { newIdempotencyKey } from "@/utils/id"
import { describeError } from "@/utils/messages"
import { routes } from "@/utils/routes"
import { groupByDay } from "@/utils/slots"
import { validateDetails, type DetailsErrors } from "@/utils/validation"

export function BookPage() {
    usePageTitle("Book an appointment")
    const navigate = useNavigate()
    const slots = useAsync(getSlots, "slots")

    const [chosenDay, setChosenDay] = useState<string | null>(null)
    const [slotId, setSlotId] = useState<string | null>(null)
    const [name, setName] = useState("")
    const [email, setEmail] = useState("")
    const [errors, setErrors] = useState<DetailsErrors>({})
    const [slotError, setSlotError] = useState<string | null>(null)
    const [submitError, setSubmitError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    const nameRef = useRef<HTMLInputElement>(null)
    const emailRef = useRef<HTMLInputElement>(null)
    // One key per booking attempt: a retry of the same request reuses it, so it can never book twice.
    const attempt = useRef<{ signature: string; key: string } | null>(null)

    async function handleSubmit(event: FormEvent) {
        event.preventDefault()
        if (submitting || slots.state.status !== "ready") return

        const detailErrors = validateDetails(name, email)
        const noSlot = slotId === null
        setErrors(detailErrors)
        setSlotError(noSlot ? "Choose a day and a time first." : null)
        setSubmitError(null)
        if (detailErrors.name) return nameRef.current?.focus()
        if (detailErrors.email) return emailRef.current?.focus()
        if (noSlot) return

        const body = { slot_id: slotId, name: name.trim(), email: email.trim() }
        const signature = `${body.slot_id}|${body.name}|${body.email.toLowerCase()}`
        if (attempt.current?.signature !== signature) {
            attempt.current = { signature, key: newIdempotencyKey() }
        }

        setSubmitting(true)
        try {
            const booking = await createBooking({ body, idempotencyKey: attempt.current.key })
            navigate(routes.booking(booking.id))
        } catch (error) {
            setSubmitError(describeError(error, "book"))
            if (error instanceof ApiError && error.kind === "conflict") {
                // Someone else got the time first: drop the choice and show the fresh availability.
                setSlotId(null)
                slots.refresh()
            }
            setSubmitting(false)
        }
    }

    if (slots.state.status === "loading") {
        return (
            <Panel>
                <h1 className="mb-4 font-heading text-3xl font-extrabold">Book an appointment</h1>
                <SlotsSkeleton />
            </Panel>
        )
    }

    if (slots.state.status === "error") {
        return (
            <Panel>
                <ErrorState
                    title="We couldn't load the available times"
                    description={describeError(slots.state.error, "load")}
                    onRetry={slots.reload}
                />
            </Panel>
        )
    }

    const allSlots = slots.state.data
    if (allSlots.length === 0) {
        return (
            <Panel>
                <EmptyState title="No times to book yet" description="Please check back soon." />
            </Panel>
        )
    }

    const days = groupByDay(allSlots)
    const defaultDay = (days.find((d) => d.freeCount > 0) ?? days[0]).key
    const activeDay = days.find((d) => d.key === chosenDay) ?? days.find((d) => d.key === defaultDay) ?? days[0]
    const selectedSlot = allSlots.find((s) => s.id === slotId && s.available) ?? null

    return (
        <div className="space-y-6">
            <div>
                <h1 className="font-heading text-3xl font-extrabold sm:text-4xl">Book an appointment</h1>
                <p className="mt-1 text-[var(--color-text-muted)]">
                    Pick a day and a time, then tell us who the appointment is for.
                </p>
            </div>

            <form onSubmit={handleSubmit} noValidate className="grid gap-6 lg:grid-cols-[1.5fr_1fr] lg:items-start">
                <div className="space-y-6">
                    <Panel className="space-y-4">
                        <h2 className="font-heading text-xl font-bold">1. Choose a day and time</h2>
                        <DayCalendar
                            days={days}
                            selectedKey={activeDay.key}
                            onSelect={(key) => {
                                setChosenDay(key)
                                setSlotId(null)
                                setSlotError(null)
                            }}
                        />
                        <TimeGrid
                            slots={activeDay.slots}
                            selectedId={selectedSlot?.id ?? null}
                            onSelect={(id) => {
                                setSlotId(id)
                                setSlotError(null)
                                setSubmitError(null)
                            }}
                        />
                        {activeDay.freeCount === 0 && (
                            <p className="text-sm text-[var(--color-text-muted)]">
                                Every time on this day is taken. Try another day.
                            </p>
                        )}
                        {slotError && (
                            <p role="alert" className="text-sm font-medium text-[var(--color-danger)]">
                                <span aria-hidden="true">! </span>
                                {slotError}
                            </p>
                        )}
                    </Panel>

                    <Panel className="space-y-4">
                        <h2 className="font-heading text-xl font-bold">2. Your details</h2>
                        <FormField label="Full name" required error={errors.name}>
                            {(field) => (
                                <Input
                                    {...field}
                                    ref={nameRef}
                                    value={name}
                                    autoComplete="name"
                                    onChange={(e) => setName(e.target.value)}
                                />
                            )}
                        </FormField>
                        <FormField label="Email" required error={errors.email}>
                            {(field) => (
                                <Input
                                    {...field}
                                    ref={emailRef}
                                    type="email"
                                    value={email}
                                    autoComplete="email"
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            )}
                        </FormField>
                    </Panel>
                </div>

                <Panel className="space-y-4 lg:sticky lg:top-6">
                    <h2 className="font-heading text-xl font-bold">Your appointment</h2>
                    <AppointmentSummary slot={selectedSlot} />

                    <div aria-live="polite">
                        {submitError && (
                            <p role="alert" className="text-sm font-medium text-[var(--color-danger)]">
                                <span aria-hidden="true">! </span>
                                {submitError}
                            </p>
                        )}
                    </div>

                    <Button type="submit" size="lg" className="w-full" loading={submitting}>
                        Confirm booking
                    </Button>
                    <p className="text-center text-sm text-[var(--color-text-muted)]">
                        Already booked?{" "}
                        <Link to={routes.find} className="font-medium underline">
                            Find your booking
                        </Link>
                    </p>
                </Panel>
            </form>
        </div>
    )
}