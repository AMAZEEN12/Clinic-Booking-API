import { useRef, useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { StatusBadge } from "@/components/shared/status-badge"
import { Button } from "@/components/ui/button"
import { FormField } from "@/components/ui/form-field"
import { Input } from "@/components/ui/input"
import { Panel } from "@/components/ui/panel"
import { usePageTitle } from "@/hooks/usePageTitle"
import type { BookingList, Slot } from "@/models"
import { getSlots, listBookings } from "@/services/api"
import { formatClinicDate, formatClinicTime } from "@/utils/clinicTime"
import { describeError } from "@/utils/messages"
import { routes } from "@/utils/routes"
import { validateEmail } from "@/utils/validation"

type EmailSearch =
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; email: string; result: BookingList; slots: Slot[] }

export function FindPage() {
    usePageTitle("Find a booking")
    const navigate = useNavigate()
    const [id, setId] = useState("")
    const [error, setError] = useState<string | undefined>()
    const inputRef = useRef<HTMLInputElement>(null)

    const [email, setEmail] = useState("")
    const [emailError, setEmailError] = useState<string | undefined>()
    const [search, setSearch] = useState<EmailSearch>({ status: "idle" })
    const emailRef = useRef<HTMLInputElement>(null)

    function handleSubmit(event: FormEvent) {
        event.preventDefault()
        const clean = id.trim()
        if (!clean) {
            setError("Enter your booking ID.")
            inputRef.current?.focus()
            return
        }
        navigate(routes.booking(clean))
    }

    async function handleEmailSubmit(event: FormEvent) {
        event.preventDefault()
        if (search.status === "loading") return
        const problem = validateEmail(email)
        setEmailError(problem)
        if (problem) {
            emailRef.current?.focus()
            return
        }

        const clean = email.trim()
        setSearch({ status: "loading" })
        try {
            // The times are only a nicety: if the slots cannot load, the IDs still show.
            const [result, slots] = await Promise.all([listBookings(clean), getSlots().catch((): Slot[] => [])])
            setSearch({ status: "ready", email: clean, result, slots })
        } catch (failure) {
            setSearch({ status: "error", message: describeError(failure, "load") })
        }
    }

    return (
        <div className="mx-auto max-w-xl space-y-6">
            <h1 className="font-heading text-3xl font-extrabold sm:text-4xl">Find a booking</h1>

            <Panel>
                <form onSubmit={handleSubmit} noValidate className="space-y-4">
                    <FormField
                        label="Booking ID"
                        required
                        hint="It starts with bk_ and was shown when you booked."
                        error={error}
                    >
                        {(field) => (
                            <Input
                                {...field}
                                ref={inputRef}
                                value={id}
                                autoComplete="off"
                                autoCapitalize="none"
                                spellCheck={false}
                                onChange={(e) => setId(e.target.value)}
                            />
                        )}
                    </FormField>
                    <Button type="submit" size="lg" className="w-full sm:w-auto">
                        Find booking
                    </Button>
                </form>
            </Panel>

            <Panel className="space-y-4">
                <h2 className="font-heading text-xl font-bold">Lost your booking ID?</h2>
                <form onSubmit={handleEmailSubmit} noValidate className="space-y-4">
                    <FormField
                        label="Email used to book"
                        required
                        hint="We will list the bookings made with this email."
                        error={emailError}
                    >
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
                    <Button
                        type="submit"
                        variant="secondary"
                        size="lg"
                        className="w-full sm:w-auto"
                        loading={search.status === "loading"}
                    >
                        Find my bookings
                    </Button>
                </form>

                <div aria-live="polite">
                    {search.status === "error" && (
                        <p role="alert" className="text-sm font-medium text-[var(--color-danger)]">
                            <span aria-hidden="true">! </span>
                            {search.message}
                        </p>
                    )}

                    {search.status === "ready" && search.result.items.length === 0 && (
                        <p className="text-[var(--color-text-muted)]">
                            No bookings found for {search.email}. Check the spelling and try again.
                        </p>
                    )}

                    {search.status === "ready" && search.result.items.length > 0 && (
                        <div className="space-y-3">
                            <ul className="space-y-3">
                                {search.result.items.map((booking) => {
                                    const slot = search.slots.find((s) => s.id === booking.slot_id)
                                    return (
                                        <li
                                            key={booking.id}
                                            className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-lg)] border border-[var(--color-border)] p-4"
                                        >
                                            <div className="min-w-0">
                                                <Link
                                                    to={routes.booking(booking.id)}
                                                    className="break-all font-mono font-medium underline"
                                                >
                                                    {booking.id}
                                                </Link>
                                                {slot && (
                                                    <p className="text-sm text-[var(--color-text-muted)]">
                                                        {formatClinicDate(slot.start)}, {formatClinicTime(slot.start)} with{" "}
                                                        {slot.provider}
                                                    </p>
                                                )}
                                            </div>
                                            <StatusBadge status={booking.status} />
                                        </li>
                                    )
                                })}
                            </ul>
                            {search.result.total > search.result.items.length && (
                                <p className="text-sm text-[var(--color-text-muted)]">
                                    Showing the newest {search.result.items.length} of {search.result.total}.
                                </p>
                            )}
                        </div>
                    )}
                </div>
            </Panel>
        </div>
    )
}