import type { HTMLAttributes } from "react"
import { cn } from "../../lib/cn"

/** The one card surface: white, 1px border, 24px radius, flat. */
export function Panel({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={cn(
                "min-w-0 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 sm:p-6",
                className,
            )}
            {...rest}
        />
    )
}