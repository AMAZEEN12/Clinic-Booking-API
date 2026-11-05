// The API sends every time in UTC. Patients should see the clinic's own time, whatever their phone says.
// One constant to change if the clinic is somewhere else.
export const CLINIC_TZ = "Africa/Lagos"
export const CLINIC_TZ_LABEL = "Lagos time (WAT)"

const dateKeyFormat = new Intl.DateTimeFormat("en-CA", {
    timeZone: CLINIC_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
})

const timeFormat = new Intl.DateTimeFormat("en-GB", {
    timeZone: CLINIC_TZ,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
})

const longDateFormat = new Intl.DateTimeFormat("en-GB", {
    timeZone: CLINIC_TZ,
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
})

const chipWeekdayFormat = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", weekday: "short" })
const chipDayMonthFormat = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", day: "numeric", month: "short" })

/** The clinic's calendar date for an instant, as YYYY-MM-DD. */
export function clinicDateKey(iso: string): string {
    return dateKeyFormat.format(new Date(iso))
}

/** "09:20" in clinic time. */
export function formatClinicTime(iso: string): string {
    return timeFormat.format(new Date(iso))
}

/** "Thu 10 Dec 2026" in clinic time. */
export function formatClinicDate(iso: string): string {
    return longDateFormat.format(new Date(iso)).replace(",", "")
}

/** Label parts for a day chip, from a YYYY-MM-DD key: { weekday: "Thu", dayMonth: "10 Dec" }. */
export function formatDayChip(dateKey: string): { weekday: string; dayMonth: string } {
    // Noon UTC keeps the calendar date the same in every timezone.
    const date = new Date(`${dateKey}T12:00:00Z`)
    return { weekday: chipWeekdayFormat.format(date), dayMonth: chipDayMonthFormat.format(date) }
}