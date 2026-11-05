import { useState } from "react"
import { PaymentBadge } from "@/components/shared/payment-badge"
import { StatusBadge } from "@/components/shared/status-badge"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { FormField } from "@/components/ui/form-field"
import { Input } from "@/components/ui/input"
import { Panel } from "@/components/ui/panel"
import { useAsync } from "@/hooks/useAsync"
import { usePageTitle } from "@/hooks/usePageTitle"
import { getDashboardAppointments, getDashboardSummary } from "@/services/api"
import { CLINIC_TZ_LABEL, formatClinicTime } from "@/utils/clinicTime"
import { formatDayHeading, isDayKey, todayUtcKey } from "@/utils/dashboardDate"
import { describeError } from "@/utils/messages"

function SummaryCard({ label, value }: { label: string; value: number }) {
    return (
        <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
            <dt className="text-base text-[var(--color-text-muted)]">{label}</dt>
            <dd className="font-heading text-4xl font-extrabold">{value}</dd>
        </div>
    )
}

function SummarySkeleton() {
    return (
        <div role="status" aria-busy="true">
            <span className="sr-only">Loading the summary…</span>
            <div aria-hidden="true" className="grid gap-3 sm:grid-cols-3">
                {[0, 1, 2].map((n) => (
                    <div key={n} className="cf-skel h-24 rounded-[var(--radius-card)]" />
                ))}
            </div>
        </div>
    )
}

function ListSkeleton() {
    return (
        <div role="status" aria-busy="true">
            <span className="sr-only">Loading appointments…</span>
            <div aria-hidden="true" className="space-y-3">
                {[0, 1, 2].map((n) => (
                    <div key={n} className="cf-skel h-20 rounded-[var(--radius-lg)]" />
                ))}
            </div>
        </div>
    )
}

/** One day's numbers and appointments. The page gives it a new key for each day, so it starts fresh. */
function DashboardDay({ date }: { date: string }) {
    const summary = useAsync(() => getDashboardSummary(date), `summary:${date}`)
    const appointments = useAsync(() => getDashboardAppointments(date), `appointments:${date}`)
    const heading = formatDayHeading(date)

    return (
        <>
            <section aria-labelledby="summary-heading" className="space-y-3">
                <h2 id="summary-heading" className="sr-only">
                    Summary for {heading}
                </h2>
                {summary.state.status === "loading" && <SummarySkeleton />}
                {summary.state.status === "error" && (
                    <Panel>
                        <ErrorState
                            headingLevel="h3"
                            title="We couldn't load the summary"
                            description={describeError(summary.state.error, "load")}
                            onRetry={summary.reload}
                        />
                    </Panel>
                )}
                {summary.state.status === "ready" && (
                    <dl className="grid gap-3 sm:grid-cols-3">
                        <SummaryCard label="Booked" value={summary.state.data.booked} />
                        <SummaryCard label="Cancelled" value={summary.state.data.cancelled} />
                        <SummaryCard label="Open slots" value={summary.state.data.open_slots} />
                    </dl>
                )}
            </section>

            <section aria-labelledby="appointments-heading" className="space-y-3">
                <h2 id="appointments-heading" className="font-heading text-xl font-bold">
                    Appointments · {heading}
                </h2>
                {appointments.state.status === "loading" && <ListSkeleton />}
                {appointments.state.status === "error" && (
                    <Panel>
                        <ErrorState
                            headingLevel="h3"
                            title="We couldn't load the appointments"
                            description={describeError(appointments.state.error, "load")}
                            onRetry={appointments.reload}
                        />
                    </Panel>
                )}
                {appointments.state.status === "ready" && appointments.state.data.length === 0 && (
                    <Panel>
                        <EmptyState
                            headingLevel="h3"
                            title="No appointments on this day"
                            description="Nothing is booked for this day. Pick another day."
                        />
                    </Panel>
                )}
                {appointments.state.status === "ready" && appointments.state.data.length > 0 && (
                    <ul className="space-y-3">
                        {appointments.state.data.map((item) => (
                            <li
                                key={item.booking_id}
                                className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
                            >
                                <div className="min-w-0">
                                    <p className="break-words font-heading text-lg font-bold">
                                        {formatClinicTime(item.start)}–{formatClinicTime(item.end)} · {item.patient}
                                    </p>
                                    <p className="break-words text-sm text-[var(--color-text-muted)]">{item.provider}</p>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    <StatusBadge status={item.status} />
                                    {item.payment === "paid" && <PaymentBadge status="paid" />}
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </section>
        </>
    )
}

/** The clinic's view of one day: how many are booked, cancelled and open, and who is coming. */
export function DashboardPage() {
    usePageTitle("Clinic dashboard")
    const [date, setDate] = useState(todayUtcKey)

    return (
        <div className="space-y-6">
            <div className="space-y-1">
                <p className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                    Clinic dashboard
                </p>
                <h1 className="font-heading text-3xl font-extrabold sm:text-4xl">Appointments</h1>
            </div>

            <Panel>
                <FormField
                    label="Day"
                    hint={`A day runs from midnight to midnight UTC. Times are shown in ${CLINIC_TZ_LABEL}. Patient names are shortened and emails are never shown.`}
                    className="sm:max-w-md"
                >
                    {(field) => (
                        <Input
                            {...field}
                            type="date"
                            value={date}
                            onChange={(event) => {
                                // Clearing the box gives "": keep the day we have.
                                if (isDayKey(event.target.value)) setDate(event.target.value)
                            }}
                        />
                    )}
                </FormField>
            </Panel>

            <DashboardDay key={date} date={date} />
        </div>
    )
}