// The dashboard asks the API for one UTC day at a time (YYYY-MM-DD). These helpers keep that
// format in one place.

const DAY_SHAPE = /^\d{4}-\d{2}-\d{2}$/

const headingFormat = new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
})

/** Today's date in UTC as YYYY-MM-DD, which is the day the API uses when none is given. */
export function todayUtcKey(now: Date = new Date()): string {
    return now.toISOString().slice(0, 10)
}

/** True only for a real calendar day written as YYYY-MM-DD. */
export function isDayKey(value: string): boolean {
    if (!DAY_SHAPE.test(value)) return false
    const date = new Date(`${value}T00:00:00Z`)
    return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value
}

/** "Thu 10 Dec 2026" for a YYYY-MM-DD key. */
export function formatDayHeading(dayKey: string): string {
    // Noon UTC keeps the calendar date the same in every timezone.
    return headingFormat.format(new Date(`${dayKey}T12:00:00Z`)).replace(",", "")
}