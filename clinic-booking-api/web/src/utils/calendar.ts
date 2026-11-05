// Month grids for the day picker. Everything here works on plain YYYY-MM-DD text and UTC dates,
// so the phone's timezone can never shift a day.

export type MonthCell = { key: string; day: number } | null

/** "2026-12-10" -> "2026-12" */
export function monthOf(dateKey: string): string {
    return dateKey.slice(0, 7)
}

/** "2026-12" -> "December 2026" */
export function monthLabel(month: string): string {
    const [year, monthNumber] = month.split("-").map(Number)
    return new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", month: "long", year: "numeric" }).format(
        new Date(Date.UTC(year, monthNumber - 1, 1, 12)),
    )
}

/** The weeks of a month, Monday first. Days outside the month are null. */
export function buildMonth(month: string): MonthCell[][] {
    const [year, monthNumber] = month.split("-").map(Number)
    const leading = (new Date(Date.UTC(year, monthNumber - 1, 1)).getUTCDay() + 6) % 7
    const daysInMonth = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate()

    const cells: MonthCell[] = new Array<MonthCell>(leading).fill(null)
    for (let day = 1; day <= daysInMonth; day++) {
        cells.push({ key: `${month}-${String(day).padStart(2, "0")}`, day })
    }
    while (cells.length % 7 !== 0) cells.push(null)

    const weeks: MonthCell[][] = []
    for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7))
    return weeks
}