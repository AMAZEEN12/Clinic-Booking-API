/** Grey blocks shaped like the day chips and time grid while the slots load. */
export function SlotsSkeleton() {
    return (
        <div role="status" aria-busy="true" className="space-y-4">
            <span className="sr-only">Loading available times…</span>
            <div aria-hidden="true" className="flex flex-wrap gap-2">
                {[0, 1, 2, 3].map((n) => (
                    <div key={n} className="cf-skel h-14 w-24 rounded-[var(--radius-lg)]" />
                ))}
            </div>
            <div aria-hidden="true" className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                {[0, 1, 2, 3, 4, 5, 6, 7].map((n) => (
                    <div key={n} className="cf-skel h-14 rounded-[var(--radius-lg)]" />
                ))}
            </div>
        </div>
    )
}